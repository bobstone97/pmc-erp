from datetime import date

import pandas as pd
import streamlit as st

from components.page_layout import get_db_session, page_header
from database.models import DoctorMaster
from services.pdf_service import generate_doctor_pnl_pdf
from services.pnl_service import get_doctor_pnl
from utils.helpers import df_to_excel_bytes
from utils.permissions import require_permission

require_permission("doctor_pnl")
page_header("Doctor PNL", "doctor_pnl", "📈")
session = get_db_session()

doctors = {d.doctor_name: d.id for d in session.query(DoctorMaster).filter_by(is_active=True).all()}
doc = st.selectbox("Doctor", list(doctors.keys()))
from_d = st.date_input("From", value=date.today().replace(day=1))
to_d = st.date_input("To", value=date.today())

pnl = get_doctor_pnl(session, doctors[doc], from_d, to_d)

st.caption("Per line: Sales = Sold Qty × Rate | Cost = Sold Qty × Cost | Profit = Sales − Cost")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sales Amount", f"₹{pnl['total_sales']:,.2f}")
c2.metric("Cost Amount", f"₹{pnl['total_cost']:,.2f}")
c3.metric("Gross Profit", f"₹{pnl['total_profit']:,.2f}")
c4.metric("Commission", f"₹{pnl['total_commission']:,.2f}")

c5, c6, c7 = st.columns(3)
c5.metric("Expense Deductions", f"₹{pnl['deductible_expenses']:,.2f}")
c6.metric("Payments", f"₹{pnl['total_payments']:,.2f}")
c7.metric("Balance", f"₹{pnl['balance']:,.2f}")

st.subheader("Medical-wise Sales")
st.dataframe([{"Medical": k, "Sales": v} for k, v in pnl["medical_wise"].items()], hide_index=True)

st.subheader("Product-wise Sold Qty")
st.dataframe([{"Product": k, "Sold Qty": v} for k, v in pnl["product_wise"].items()], hide_index=True)

st.subheader("Commission Lines (amount shown)")
if pnl["lines"]:
    st.dataframe(pd.DataFrame(pnl["lines"]), hide_index=True, use_container_width=True)

pdf = generate_doctor_pnl_pdf(doc, from_d, to_d, pnl)
st.download_button("Download PDF", pdf, file_name=f"doctor_pnl_{doc}.pdf", mime="application/pdf")
excel_df = pd.DataFrame(pnl["lines"]) if pnl["lines"] else pd.DataFrame([pnl])
st.download_button("Download Excel", df_to_excel_bytes(excel_df), file_name=f"doctor_pnl_{doc}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
