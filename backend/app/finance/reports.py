"""Read-only UGX GL financial reports, with explicit historical coverage warnings."""
from collections import defaultdict
from datetime import date
from sqlalchemy import func
from ..extensions import db
from .gl_models import GLAccount, GLEvent, GLLine


def account_totals(*, through: date | None = None, from_date: date | None = None,
                   property_id: str | None = None):
    query = db.session.query(GLLine.account_code,
            func.coalesce(func.sum(GLLine.debit_ugx), 0),
            func.coalesce(func.sum(GLLine.credit_ugx), 0)).join(
                GLEvent, GLEvent.id == GLLine.event_id)
    if through is not None:
        query = query.filter(GLEvent.posted_on <= through)
    if from_date is not None:
        query = query.filter(GLEvent.posted_on >= from_date)
    if property_id is not None:
        query = query.filter(GLEvent.property_id == property_id)
    found = {code: (int(dr), int(cr)) for code, dr, cr in query.group_by(GLLine.account_code).all()}
    return [
        {
            "code": account.code,
            "name": account.name,
            "kind": account.kind,
            "debit_ugx": found.get(account.code, (0, 0))[0],
            "credit_ugx": found.get(account.code, (0, 0))[1],
            "net_debit_ugx": found.get(account.code, (0, 0))[0] -
                             found.get(account.code, (0, 0))[1],
        }
        for account in db.session.query(GLAccount).order_by(GLAccount.code).all()
    ]


def trial_balance(*, through=None, property_id=None):
    lines = account_totals(through=through, property_id=property_id)
    dr = sum(row["debit_ugx"] for row in lines)
    cr = sum(row["credit_ugx"] for row in lines)
    return {
        "accounts": lines, "debit_ugx": dr, "credit_ugx": cr,
        "difference_ugx": dr - cr, "balanced": dr == cr,
        "coverage": "NEW_GENERAL_LEDGER_EVENTS_ONLY",
        "warning": ("No automatic backfill of pre-migration invoices/payments. "
                    "Accountant-approved historical opening entries are required. "
                    "Receipt clearance is not bank settlement.")
    }


def income_statement(*, from_date=None, through=None, property_id=None):
    rows = account_totals(through=through, from_date=from_date, property_id=property_id)
    revenue = [{"code":r["code"], "name":r["name"],
                "amount_ugx":r["credit_ugx"] - r["debit_ugx"]}
               for r in rows if r["kind"] == "REVENUE"]
    expenses = [{"code":r["code"], "name":r["name"],
                 "amount_ugx":r["debit_ugx"] - r["credit_ugx"]}
                for r in rows if r["kind"] == "EXPENSE"]
    total_rev = sum(x["amount_ugx"] for x in revenue)
    total_expense = sum(x["amount_ugx"] for x in expenses)
    return {
        "revenues": revenue, "expenses": expenses,
        "total_revenue_ugx": total_rev, "total_expense_ugx": total_expense,
        "net_income_ugx": total_rev - total_expense,
        "accounting_policy": "INVOICE_ISSUANCE_ACCRUAL_SUBJECT_TO_ACCOUNTANT_APPROVAL",
        "coverage": "NEW_GENERAL_LEDGER_EVENTS_ONLY",
    }


def balance_sheet(*, through=None, property_id=None):
    rows = account_totals(through=through, property_id=property_id)
    sums = defaultdict(int)
    for row in rows:
        sums[row["kind"]] += row["net_debit_ugx"]
    assets = sums["ASSET"]
    liabilities = -sums["LIABILITY"]
    equity = -sums["EQUITY"]
    current_income = -sums["REVENUE"] - sums["EXPENSE"]
    difference = assets - (liabilities + equity + current_income)
    return {
        "assets_ugx": assets,
        "liabilities_ugx": liabilities,
        "equity_ugx": equity,
        "unclosed_profit_ugx": current_income,
        "liabilities_plus_equity_ugx": liabilities + equity + current_income,
        "difference_ugx": difference,
        "balanced": difference == 0,
        "coverage": "NEW_GENERAL_LEDGER_EVENTS_ONLY",
        "warning": "This is not a complete historical balance sheet until approved opening balances are posted.",
    }


def detail(*, account_code=None, from_date=None, through=None, property_id=None,
           page=1, page_size=25):
    query = db.session.query(GLLine, GLEvent).join(GLEvent, GLEvent.id == GLLine.event_id)
    if account_code:
        query = query.filter(GLLine.account_code == account_code)
    if from_date:
        query = query.filter(GLEvent.posted_on >= from_date)
    if through:
        query = query.filter(GLEvent.posted_on <= through)
    if property_id:
        query = query.filter(GLEvent.property_id == property_id)
    total = query.count()
    items = query.order_by(GLEvent.posted_on.desc(), GLEvent.id.desc(),
                           GLLine.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {"event_key": event.event_key, "event_kind": event.kind,
             "posted_on": event.posted_on.isoformat(),
             "property_id": event.property_id,
             "account_code": line.account_code,
             "debit_ugx": line.debit_ugx, "credit_ugx": line.credit_ugx}
            for line, event in items
        ],
        "total": total, "page": page, "page_size": page_size,
        "coverage": "NEW_GENERAL_LEDGER_EVENTS_ONLY"
    }
