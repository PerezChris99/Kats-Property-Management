"""Internal accounting reports and non-fiscal printable acknowledgements.

This module never asserts that a document is a URA EFRIS tax receipt.
"""
from datetime import datetime
from html import escape
from io import BytesIO
from flask import Blueprint, Response, abort, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import xlsxwriter
from .api import current_user, roles
from .extensions import db
from .models import User, Tenant, Lease, Invoice, Payment
from .extra_models import FiscalSubmission

report_api = Blueprint("report_exports",__name__)
FINANCE={"OWNER","ACCOUNTANT","SUPER_ADMIN"}
STAFF=FINANCE|{"MANAGER"}

def safe(value):
    return escape(str(value if value is not None else ""),quote=True)

def money(amount):
    return "UGX {:,}".format(int(amount))

def table_style():
    return TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0B1B3D")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),7),
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),
        ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#D4E0EA")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F0F5F8")]),
    ])

def pdf_document(title, lines, headers=None, rows=None, footer=None):
    stream=BytesIO()
    doc=SimpleDocTemplate(stream,pagesize=(210*mm,297*mm),rightMargin=15*mm,
                           leftMargin=15*mm,topMargin=20*mm,bottomMargin=20*mm)
    styles=getSampleStyleSheet()
    body=styles["BodyText"]
    heading=styles["Heading1"]
    blocks=[Paragraph(safe(title),heading),Spacer(1,6*mm)]
    for line in lines:
        blocks.append(Paragraph(safe(line),body))
        blocks.append(Spacer(1,2*mm))
    if headers and rows:
        normalized=[list(map(safe,headers))]
        normalized.extend([[safe(v) for v in row] for row in rows])
        t=Table(normalized,repeatRows=1,hAlign="LEFT")
        t.setStyle(table_style())
        blocks.extend([Spacer(1,5*mm),t])
    if footer:
        blocks.extend([Spacer(1,8*mm),Paragraph(safe(footer),body)])
    doc.build(blocks)
    return stream.getvalue()

def file_response(content,mime,filename):
    res=Response(content,content_type=mime)
    res.headers["Content-Disposition"]=f'attachment; filename="{filename}"'
    res.headers["Cache-Control"]="no-store"
    res.headers["X-Content-Type-Options"]="nosniff"
    return res

def scoped_tenant(user, tenant_id):
    tenant=db.session.get(Tenant,tenant_id)
    if not tenant:
        abort(404)
    if user.role=="TENANT" and tenant.user_id!=user.id:
        abort(404)
    if user.role not in STAFF and user.role!="TENANT":
        abort(403)
    return tenant

@report_api.get("/tenants/<tenant_id>/statement.pdf")
@jwt_required()
def statement_pdf(tenant_id):
    user=current_user()
    tenant=scoped_tenant(user,tenant_id)
    # Balance always includes entire history, not only the displayed excerpt.
    outstanding, all_count = db.session.query(
        func.coalesce(func.sum(Invoice.total_ugx - Invoice.credit_ugx - Invoice.paid_ugx), 0),
        func.count(Invoice.id)).filter(
            Invoice.tenant_id == tenant.id, Invoice.status != "VOID").one()
    invoices=db.session.query(Invoice).filter_by(tenant_id=tenant.id).order_by(
        Invoice.period_start.desc(),Invoice.created_at.desc()).limit(200).all()
    rows=[]
    for invoice in invoices:
        due=invoice.total_ugx-invoice.credit_ugx-invoice.paid_ugx
        rows.append([invoice.invoice_number,invoice.period_start.isoformat(),
                     money(invoice.total_ugx),money(invoice.credit_ugx),
                     money(invoice.paid_ugx),money(due if invoice.status!="VOID" else 0)])
    pdf=pdf_document("Kats · Tenant statement",
      ["Tenant: "+tenant.full_name,"Generated: "+datetime.now().date().isoformat(),
       "Currency: Uganda shillings (UGX)",
       "Outstanding invoiced balance (ALL non-void invoices): "+money(outstanding),
       "Showing up to 200 most recent invoices; older records are included in the balance."],
      headers=["Invoice","Period","Invoiced","Credits","Paid","Open"],rows=rows,
      footer="Internal statement. Not a URA tax invoice or official fiscal receipt.")
    return file_response(pdf,"application/pdf","kats-tenant-statement.pdf")

@report_api.get("/payments/<payment_id>/cash-acknowledgement.pdf")
@jwt_required()
def cash_custody_acknowledgement(payment_id):
    """Written in-person cash custody receipt, NOT a URA fiscal receipt.

    Required at intake while the independent finance reviewer still has to
    verify the underlying money and reconcile the invoice.
    """
    user=current_user()
    payment=db.session.get(Payment,payment_id)
    if not payment or payment.method!="CASH" or payment.status not in (
            "PENDING_REVIEW","RECONCILED","REVERSED"):
        abort(404)
    invoice=db.session.get(Invoice,payment.invoice_id)
    if not invoice: abort(404)
    if user.role=="TENANT":
        linked=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if not linked or linked!=invoice.tenant_id:abort(404)
    elif user.role=="CARETAKER":
        if payment.created_by!=user.id:abort(404)
    elif user.role not in STAFF:abort(403)
    tenant=db.session.get(Tenant,invoice.tenant_id)
    cashier=db.session.get(User,payment.created_by)
    state=("Cash received, awaiting independent accounting review" if payment.status=="PENDING_REVIEW"
           else "Cash receipt subsequently reversed: INVALID" if payment.status=="REVERSED"
           else "Cash received and reconciled")
    pdf=pdf_document("Kats · Written cash receipt",[
        "Cash receipt number: KATS-CASH-"+payment.id[:12].upper(),
        "Tenant: "+(tenant.full_name if tenant else "Unknown"),
        "Cash receiving staff: "+(cashier.full_name if cashier else payment.created_by),
        "Amount physically received: "+money(payment.amount_ugx),
        "Invoice: "+invoice.invoice_number,
        "Rent/charge period: "+invoice.period_start.isoformat()+" to "+invoice.period_end.isoformat(),
        "Cash recorded at: "+payment.created_at.isoformat(),
        "Review status: "+state],
        footer="Acknowledgement of cash custody only. Not a URA EFRIS e-receipt or fiscal invoice. The landlord must issue any required official tax document separately.")
    return file_response(pdf,"application/pdf","kats-cash-acknowledgement.pdf")


@report_api.get("/receipts/<payment_id>.pdf")
@jwt_required()
def receipt_pdf(payment_id):
    user=current_user()
    payment=db.session.get(Payment,payment_id)
    if not payment or payment.status not in ("RECONCILED","REVERSED"):
        abort(404)
    invoice=db.session.get(Invoice,payment.invoice_id)
    if user.role=="TENANT":
        linked=db.session.query(Tenant.id).filter_by(user_id=user.id).scalar()
        if linked is None or invoice.tenant_id!=linked:
            abort(404)
    elif user.role=="CARETAKER":
        if payment.created_by!=user.id:
            abort(404)
    elif user.role not in STAFF:
        abort(403)
    fiscal=db.session.query(FiscalSubmission).filter_by(
        invoice_id=invoice.id,state="ACCEPTED").first()
    fiscal_number=fiscal.fiscal_document_number if fiscal else None
    # Even a linked fiscal reference does not turn this internal receipt into
    # a standalone official URA fiscal document.
    lines=[
        "Reference: KATS-REC-"+payment.id[:12].upper(),
        "Invoice: "+invoice.invoice_number,
        "Method: "+payment.method,
        "Amount: "+money(payment.amount_ugx),
        "Status: "+("Reversed (INVALID)" if payment.status=="REVERSED" else "Verified"),
        "Recorded on: "+payment.created_at.date().isoformat(),
        "EFRIS invoice document reference: "+(fiscal_number or "Not fiscalized"),
    ]
    title = "Kats · Internal payment acknowledgement"
    if payment.advance_id:
        title = "Kats · Advance rent allocation"
        lines.append("Applied from advance receipt " + payment.advance_id + ". No additional cash received.")
    pdf=pdf_document(title,lines,
       footer="Internal acknowledgement ONLY. Not a URA EFRIS receipt. Reversed payments are invalid.")
    return file_response(pdf,"application/pdf","kats-internal-receipt.pdf")

@report_api.get("/reports/export/invoices.xlsx")
@roles("OWNER","ACCOUNTANT","SUPER_ADMIN")
def export_invoice_xlsx(user):
    items=db.session.query(Invoice).order_by(Invoice.period_start.desc()).limit(10000).all()
    output=BytesIO()
    workbook=xlsxwriter.Workbook(output,{"in_memory":True,
                                        "strings_to_formulas":False,"strings_to_urls":False})
    sheet=workbook.add_worksheet("Invoices")
    header=workbook.add_format({"bold":True,"bg_color":"#0B1B3D","font_color":"white",
                                "text_wrap":True,"valign":"vcenter"})
    amount=workbook.add_format({"num_format":"#,##0","align":"right"})
    date_fmt=workbook.add_format({"num_format":"yyyy-mm-dd"})
    sheet.set_column("A:A",25)
    sheet.set_column("B:B",40)
    sheet.set_column("C:E",17)
    sheet.set_column("F:F",18)
    sheet.set_column("G:J",19)
    sheet.freeze_panes(1,0)
    columns=["Invoice","Tenant ID","Period start","Period end","Due date","Status",
             "Total UGX","Credited UGX","Paid UGX","Outstanding UGX"]
    for col,title in enumerate(columns):
        sheet.write_string(0,col,title,header)
    for index,i in enumerate(items,1):
        sheet.write_string(index,0,i.invoice_number)
        sheet.write_string(index,1,i.tenant_id)
        for c,d in ((2,i.period_start),(3,i.period_end),(4,i.due_date)):
            sheet.write_datetime(index,c,datetime.combine(d,datetime.min.time()),date_fmt)
        sheet.write_string(index,5,i.status)
        amounts=[i.total_ugx,i.credit_ugx,i.paid_ugx,
                 i.total_ugx-i.credit_ugx-i.paid_ugx]
        for c,value in enumerate(amounts,6):
            sheet.write_number(index,c,value,amount)
    sheet.autofilter(0,0,len(items),len(columns)-1)
    workbook.close()
    return file_response(output.getvalue(),
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "kats-invoices.xlsx")


@report_api.get("/reports/export/period-summary.pdf")
@roles("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN", "TENANT")
def export_period_summary_pdf(user):
    """Printable source-of-truth management/tenant summary, never a fiscal receipt."""
    from .presentation_analytics import period_payload
    from .api import fail
    try:
        report = period_payload(user, request.args)
    except ValueError as error:
        return fail(str(error), 400)
    metrics = report["metrics"]
    lines = [
        f"Report: {report['start_month']} to {report['end_month']}",
        f"Previous comparison starts: {report['previous_start_month']}",
        f"Generated (UTC): {report['generated_at']}",
        "All financial amounts in Uganda shillings (UGX).",
    ]
    for metric in metrics.values():
        change = metric["change_percent"]
        lines.append(
            f"{metric['label']}: {money(metric['current'])}; "
            f"previous equal-length window: {money(metric['previous'])}; "
            f"change: {change if change is not None else 'not comparable'}"
            + ("%" if change is not None else ""))
    columns = ["Period", "Settled", "Invoiced"]
    if user.role == "TENANT":
        columns.append("Applied")
    else:
        columns.append("Expenses")
    rows = []
    for row in report["points"]:
        rows.append([
            row["name"], money(row["verified_collections_ugx"]),
            money(row["net_invoiced_ugx"]),
            money(row["applied_payments_ugx"] if user.role == "TENANT"
                  else row["approved_expenses_ugx"]),
        ])
    content = pdf_document(
        "KATS | Verified monthly financial performance",
        lines, headers=columns, rows=rows,
        footer=report["method"] + " Internal management information only. "
               "Not a tax invoice or independently audited statement.")
    return file_response(content, "application/pdf", "kats-period-performance.pdf")


@report_api.get("/reports/export/period-summary.xlsx")
@roles("OWNER", "MANAGER", "ACCOUNTANT", "SUPER_ADMIN", "TENANT")
def export_period_summary_xlsx(user):
    """Native Excel line chart plus exact, server-verified chart source and KPIs."""
    from .presentation_analytics import period_payload
    from .api import fail
    try:
        report = period_payload(user, request.args)
    except ValueError as error:
        return fail(str(error), 400)
    output = BytesIO()
    book = xlsxwriter.Workbook(
        output, {"in_memory": True, "strings_to_formulas": False,
                 "strings_to_urls": False})
    header = book.add_format({"bold": True, "font_color": "#FFFFFF",
                              "bg_color": "#0B1B3D"})
    integer = book.add_format({"num_format": "#,##0"})
    ws = book.add_worksheet("Monthly results")
    ws.set_column("A:A", 16)
    ws.set_column("B:E", 23)
    ws.freeze_panes(1, 0)
    final_title = "Applied to invoice" if user.role == "TENANT" else "Approved expenses"
    headers = ("Period", "Verified collections UGX", "Net invoices UGX",
               final_title + " UGX")
    for col, title in enumerate(headers):
        ws.write_string(0, col, title, header)
    for i, point in enumerate(report["points"], start=1):
        ws.write_string(i, 0, point["name"])
        for col, key in enumerate((
            "verified_collections_ugx", "net_invoiced_ugx",
            "applied_payments_ugx" if user.role == "TENANT"
            else "approved_expenses_ugx"), start=1):
            ws.write_number(i, col, int(point[key]), integer)
    ws.autofilter(0, 0, len(report["points"]), 3)
    chart = book.add_chart({"type": "line"})
    for col, color in ((1, "#1277A8"), (2, "#D8A42E")):
        chart.add_series({
            "name": ["Monthly results", 0, col],
            "categories": ["Monthly results", 1, 0, len(report["points"]), 0],
            "values": ["Monthly results", 1, col, len(report["points"]), col],
            "line": {"color": color, "width": 2.5},
            "marker": {"type": "circle", "size": 4},
        })
    chart.set_title({"name": "Settled collections versus invoiced rent"})
    chart.set_x_axis({"name": "Billing or settlement month"})
    chart.set_y_axis({"name": "UGX", "num_format": "#,##0"})
    chart.set_style(10)
    ws.insert_chart("F2", chart, {"x_scale": 1.3, "y_scale": 1.3})
    summary = book.add_worksheet("Method and comparison")
    summary.set_column("A:A", 29)
    summary.set_column("B:D", 26)
    for col, title in enumerate(("Metric", "Current period", "Previous period", "Change %")):
        summary.write_string(0, col, title, header)
    for index, metric in enumerate(report["metrics"].values(), 1):
        summary.write_string(index, 0, metric["label"])
        summary.write_number(index, 1, metric["current"], integer)
        summary.write_number(index, 2, metric["previous"], integer)
        if metric["change_percent"] is not None:
            summary.write_number(index, 3, metric["change_percent"])
        else:
            summary.write_string(index, 3, "N/A (no prior data)")
    row = len(report["metrics"]) + 3
    for line in (
        "Report: " + report["start_month"] + " to " + report["end_month"],
        "Generated UTC: " + report["generated_at"],
        report["method"],
        "Internal management report only; not a URA fiscal document or audited P&L.",
    ):
        summary.write_string(row, 0, line)
        row += 1
    book.close()
    return file_response(
        output.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "kats-period-performance.xlsx")
