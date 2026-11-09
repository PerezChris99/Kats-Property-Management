"""Internal accounting reports and non-fiscal printable acknowledgements.

This module never asserts that a document is a URA EFRIS tax receipt.
"""
from datetime import datetime
from html import escape
from io import BytesIO
from flask import Blueprint, Response, abort
from flask_jwt_extended import jwt_required
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
    invoices=db.session.query(Invoice).filter_by(tenant_id=tenant.id).order_by(
        Invoice.period_start,Invoice.created_at).limit(200).all()
    rows=[]
    outstanding=0
    for invoice in invoices:
        due=invoice.total_ugx-invoice.credit_ugx-invoice.paid_ugx
        outstanding+=due if invoice.status!="VOID" else 0
        rows.append([invoice.invoice_number,invoice.period_start.isoformat(),
                     money(invoice.total_ugx),money(invoice.credit_ugx),
                     money(invoice.paid_ugx),money(due)])
    pdf=pdf_document("Kats · Tenant statement",
      ["Tenant: "+tenant.full_name,"Generated: "+datetime.now().date().isoformat(),
       "Currency: Uganda shillings (UGX)",
       "Outstanding invoiced balance: "+money(outstanding)],
      headers=["Invoice","Period","Invoiced","Credits","Paid","Open"],rows=rows,
      footer="Internal statement. Not a URA tax invoice or official fiscal receipt.")
    return file_response(pdf,"application/pdf","kats-tenant-statement.pdf")

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
    pdf=pdf_document("Kats · Internal payment acknowledgement",lines,
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
