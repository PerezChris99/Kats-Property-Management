"""New canonical GL engine: double-entry, replay safety, period closure."""
from datetime import date
import pytest
from sqlalchemy import func

from app.extensions import db
from app.finance.accounts import DEFAULT_ACCOUNTS
from app.finance.gl_models import GLAccount, GLEvent, GLLine, GLPeriodClose
from app.finance.ledger import GLPostingError, post_event, reverse_posted, close_period, ensure_chart
from app.finance.reports import trial_balance, income_statement, balance_sheet


def test_balanced_gl_entry_is_append_only_and_idempotent(app):
    assert post_event("source:1", "INVOICE_ACCRUAL", date(2025, 5, 1), [
        ("RENT_RECEIVABLE", 120000, 0),
        ("RENTAL_INCOME", 0, 120000),
    ])
    db.session.commit()
    assert not post_event("source:1", "INVOICE_ACCRUAL", date(2025, 5, 1), [
        ("RENT_RECEIVABLE", 120000, 0),
        ("RENTAL_INCOME", 0, 120000),
    ])
    with pytest.raises(GLPostingError, match="replay"):
        post_event("source:1", "INVOICE_ACCRUAL", date(2025, 5, 1), [
            ("RENT_RECEIVABLE", 120001, 0), ("RENTAL_INCOME", 0, 120001)
        ])
    assert db.session.query(GLEvent).count() == 1
    assert db.session.query(GLLine).count() == 2
    assert len(db.session.query(GLAccount).all()) == len(DEFAULT_ACCOUNTS)


@pytest.mark.parametrize("lines", [
    [("RENT_RECEIVABLE", 5, 0), ("RENTAL_INCOME", 0, 4)],
    [("RENT_RECEIVABLE", 5, 5), ("RENTAL_INCOME", 0, 5)],
    [("RENT_RECEIVABLE", 0, 0), ("RENTAL_INCOME", 0, 1)],
    [("RENT_RECEIVABLE", 1.5, 0), ("RENTAL_INCOME", 0, 1)],
    [("UNKNOWN_ACCOUNT", 1, 0), ("BANK", 0, 1)],
    [("RENT_RECEIVABLE", -1, 0), ("BANK", 0, 1)],
    [("RENT_RECEIVABLE", True, 0), ("BANK", 0, 1)],
])
def test_unbalanced_or_invalid_ugx_never_posts(app, lines):
    with pytest.raises(GLPostingError):
        post_event("bad:1", "INVOICE", date(2025, 5, 1), lines)
    assert db.session.query(GLEvent).count() == 0


def test_trial_balance_and_balance_sheet_reconcile_with_profit(app):
    post_event("rent:1", "INVOICE_ACCRUAL", date(2025, 2, 1),
               [("RENT_RECEIVABLE", 100000, 0), ("RENTAL_INCOME", 0, 100000)])
    post_event("receipt:1", "RECEIPT", date(2025, 2, 10),
               [("CASH_CLEARING", 75000, 0), ("RENT_RECEIVABLE", 0, 75000)])
    post_event("expense:1", "EXPENSE_ACCRUAL", date(2025, 2, 11),
               [("MAINTENANCE_EXPENSE", 20000, 0), ("ACCOUNTS_PAYABLE", 0, 20000)])
    db.session.commit()
    trial = trial_balance()
    assert trial["balanced"] and trial["difference_ugx"] == 0
    assert trial["debit_ugx"] == trial["credit_ugx"] == 195000
    profit = income_statement()
    assert profit["total_revenue_ugx"] == 100000
    assert profit["total_expense_ugx"] == 20000
    assert profit["net_income_ugx"] == 80000
    balance = balance_sheet()
    assert balance["balanced"]
    assert balance["assets_ugx"] == 100000
    assert balance["liabilities_ugx"] == 20000
    assert balance["unclosed_profit_ugx"] == 80000
    assert "NEW_GENERAL_LEDGER_EVENTS_ONLY" in trial["coverage"]


def test_reverse_event_offsets_original_without_editing_it(app):
    post_event("receipt:2", "RECEIPT", date(2025, 3, 5), [
        ("CASH_CLEARING", 30000, 0), ("RENT_RECEIVABLE", 0, 30000)])
    assert reverse_posted("receipt:2", "reverse:2", "REVERSAL")
    assert not reverse_posted("receipt:2", "reverse:2", "REVERSAL")
    assert not reverse_posted("missing-legacy", "reverse:legacy", "REVERSAL")
    db.session.commit()
    assert db.session.query(GLEvent).count() == 2
    assert all(r["net_debit_ugx"] == 0 for r in trial_balance()["accounts"])


def test_closed_period_rejects_backdated_financial_events(app):
    from app.models import User
    user = User(email="accountant-period@example.com", full_name="Accountant", role="ACCOUNTANT",
                password_hash="not-a-real-login")
    db.session.add(user)
    db.session.flush()
    assert close_period("2025-04", actor_id=user.id)
    db.session.commit()
    with pytest.raises(GLPostingError, match="closed"):
        post_event("backdated:1", "INVOICE", date(2025, 4, 12), [
            ("RENT_RECEIVABLE", 200, 0), ("RENTAL_INCOME", 0, 200)])
    assert not close_period("2025-04", actor_id=user.id)
    with pytest.raises(GLPostingError, match="current or future"):
        close_period("2099-01", actor_id=user.id)
    assert db.session.query(GLPeriodClose).count() == 1
