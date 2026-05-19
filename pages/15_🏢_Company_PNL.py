from datetime import date

import pandas as pd
import streamlit as st

from components.page_layout import get_db_session, page_header
from services.pdf_service import generate_company_pnl_pdf
from services.pnl_service import get_company_pnl
from utils.helpers import df_to_excel_bytes
from utils.permissions import require_permission

require_permission("company_pnl")
page_header("PMC Company PNL", "company_pnl", "🏢")
session = get_db_session()

from_d = st.date_input("From", value=date.today().replace(month=1, day=1))
to_d = st.date_input("To", value=date.today())

pnl = get_company_pnl(session, from_d, to_d)

st.caption("Sold lines: **Sales** = Sold Qty × Rate | **Cost** = Sold Qty × Cost | **Gross Profit** = Sales − Cost")

c1, c2, c3 = st.columns(3)
c1.metric("Sales Amount", f"₹{pnl['sales_amount']:,.2f}")
c2.metric("Cost Amount", f"₹{pnl['cost_amount']:,.2f}")
c3.metric("Gross Profit", f"₹{pnl['gross_profit']:,.2f}")

st.subheader("Operating expenses")
e1, e2, e3, e4 = st.columns(4)
e1.metric("Doctor Commission", f"₹{pnl['doctor_commission']:,.2f}")
e2.metric("Doctor Expenses", f"₹{pnl['doctor_expenses']:,.2f}")
e3.metric("Sales Person Expenses", f"₹{pnl['sales_person_expenses']:,.2f}")
e4.metric("Company Expenses", f"₹{pnl['company_expenses']:,.2f}")

st.metric("Net Profit (Gross Profit − expenses)", f"₹{pnl['net_profit']:,.2f}")

if pnl["company_expense_breakdown"]:
    st.dataframe(
        [{"Category": k, "Amount": v} for k, v in pnl["company_expense_breakdown"].items()],
        hide_index=True,
    )

pdf = generate_company_pnl_pdf(from_d, to_d, pnl)
st.download_button("Download PDF", pdf, file_name="company_pnl.pdf", mime="application/pdf")
df = pd.DataFrame([
    {"Item": "Sales Amount (Sold Qty × Rate)", "Amount": pnl["sales_amount"]},
    {"Item": "Cost Amount (Sold Qty × Cost)", "Amount": pnl["cost_amount"]},
    {"Item": "Gross Profit", "Amount": pnl["gross_profit"]},
    {"Item": "Doctor Commission", "Amount": pnl["doctor_commission"]},
    {"Item": "Doctor Expenses", "Amount": pnl["doctor_expenses"]},
    {"Item": "Sales Person Expenses", "Amount": pnl["sales_person_expenses"]},
    {"Item": "Company Expenses", "Amount": pnl["company_expenses"]},
    {"Item": "Net Profit", "Amount": pnl["net_profit"]},
])
st.download_button(
    "Download Excel",
    df_to_excel_bytes(df),
    file_name="company_pnl.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
