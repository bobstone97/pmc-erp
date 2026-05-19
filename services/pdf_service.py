import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _build_doc(title: str, subtitle: str, rows: list[list], headers: list[str]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Paragraph(subtitle, styles["Normal"]),
        Spacer(1, 0.2 * inch),
    ]
    data = [headers] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("Authorized Signatory: _______________________", styles["Normal"]))
    doc.build(elements)
    return buffer.getvalue()


def generate_doctor_payment_receipt(
    doctor_name: str,
    payment_date: date,
    amount: float,
    payment_mode: str,
    remarks: str,
) -> bytes:
    rows = [
        ["Doctor", doctor_name],
        ["Date", str(payment_date)],
        ["Amount", f"₹{amount:,.2f}"],
        ["Mode", payment_mode],
        ["Remarks", remarks or "-"],
    ]
    return _build_doc(
        "PMC ERP – Doctor Payment Receipt",
        f"Payment Date: {payment_date}",
        rows,
        ["Field", "Value"],
    )


def generate_doctor_pnl_pdf(doctor_name: str, from_date: date, to_date: date, pnl: dict) -> bytes:
    rows = [
        ["Total Sales", f"₹{pnl['total_sales']:,.2f}"],
        ["Total Commission", f"₹{pnl['total_commission']:,.2f}"],
        ["Expense Deductions", f"₹{pnl['deductible_expenses']:,.2f}"],
        ["Payments Made", f"₹{pnl['total_payments']:,.2f}"],
        ["Balance", f"₹{pnl['balance']:,.2f}"],
    ]
    for medical, amt in pnl.get("medical_wise", {}).items():
        rows.append([f"Medical: {medical}", f"₹{amt:,.2f}"])
    return _build_doc(
        f"Doctor PNL – {doctor_name}",
        f"Period: {from_date} to {to_date}",
        rows,
        ["Description", "Amount"],
    )


def generate_medical_ledger_pdf(medical_name: str, from_date: date, to_date: date, ledger: dict) -> bytes:
    rows = [
        ["Total Supply/Sales", f"₹{ledger['total_sales']:,.2f}"],
        ["Total Collection", f"₹{ledger['total_collection']:,.2f}"],
        ["Outstanding", f"₹{ledger['outstanding']:,.2f}"],
    ]
    for s in ledger.get("sales", [])[:50]:
        rows.append([
            str(s.bill_date),
            s.product.product_name if s.product else "",
            f"{s.qty}",
            f"₹{s.amount:,.2f}",
        ])
    return _build_doc(
        f"Medical Ledger – {medical_name}",
        f"Period: {from_date} to {to_date} (No doctor/commission data shown)",
        rows,
        ["Date", "Product", "Qty", "Amount"],
    )


def generate_company_pnl_pdf(from_date: date, to_date: date, pnl: dict) -> bytes:
    rows = [
        ["Sales Amount (Sold Qty × Rate)", f"₹{pnl.get('sales_amount', pnl.get('revenue', 0)):,.2f}"],
        ["Cost Amount (Sold Qty × Cost)", f"₹{pnl.get('cost_amount', 0):,.2f}"],
        ["Gross Profit", f"₹{pnl.get('gross_profit', 0):,.2f}"],
        ["Doctor Commission", f"₹{pnl['doctor_commission']:,.2f}"],
        ["Doctor Expenses", f"₹{pnl['doctor_expenses']:,.2f}"],
        ["Sales Person Expenses", f"₹{pnl['sales_person_expenses']:,.2f}"],
        ["Company Expenses", f"₹{pnl['company_expenses']:,.2f}"],
        ["Net Profit", f"₹{pnl['net_profit']:,.2f}"],
    ]
    for cat, amt in pnl.get("company_expense_breakdown", {}).items():
        rows.append([f"  {cat}", f"₹{amt:,.2f}"])
    return _build_doc(
        "PMC Company PNL Report",
        f"Period: {from_date} to {to_date}",
        rows,
        ["Item", "Amount"],
    )
