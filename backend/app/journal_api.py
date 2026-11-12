"""Read-only, single-business journal control totals.

This shows new journal bridge coverage, NOT a complete accrual P&L or
external bank reconciliation. Legacy reconciled payments are counted
as missing until a separately approved historical backfill exists.
"""
from flask import Blueprint, jsonify
from sqlalchemy import func, case
from .api import roles
from .extensions import db
from .models import Payment
from .journal_models import JournalEvent, JournalLine

journal_api=Blueprint("journal_api",__name__)


@journal_api.get("/finance/journal-control")
@roles("OWNER","ACCOUNTANT","SUPER_ADMIN")
def journal_control(_user):
    totals=(db.session.query(
        JournalLine.account_code,
        func.coalesce(func.sum(JournalLine.debit_ugx),0),
        func.coalesce(func.sum(JournalLine.credit_ugx),0)
    ).group_by(JournalLine.account_code).order_by(JournalLine.account_code).all())
    debit=sum(int(row[1]) for row in totals)
    credit=sum(int(row[2]) for row in totals)
    recorded=(db.session.query(func.count(Payment.id))
        .outerjoin(JournalEvent,(JournalEvent.source_payment_id==Payment.id)
            &(JournalEvent.kind=="RECEIPT"))
        .filter(Payment.status=="RECONCILED",JournalEvent.id.is_(None)).scalar() or 0)
    reversed_unjournaled=(db.session.query(func.count(Payment.id))
        .outerjoin(JournalEvent,(JournalEvent.source_payment_id==Payment.id)
            &(JournalEvent.kind=="RECEIPT"))
        .filter(Payment.status=="REVERSED",JournalEvent.id.is_(None)).scalar() or 0)
    return jsonify(
        accounts=[{"code":row[0],"debit_ugx":int(row[1]),
                   "credit_ugx":int(row[2]),"net_debit_ugx":int(row[1]-row[2])} for row in totals],
        total_debit_ugx=debit,total_credit_ugx=credit,balanced=(debit==credit),
        legacy_reconciled_without_journal=int(recorded),
        legacy_reversed_without_journal=int(reversed_unjournaled),
        coverage="RECEIPT_AND_REVERSAL_EVENTS_ONLY",
        warning=("Not a complete general ledger. Invoice accrual, expenses, deposits, "
                 "bank settlements and approved historic backfill are outside this bridge."))
