from datetime import date

import streamlit as st

from components.page_layout import get_db_session, page_header
from database.models import MedicalMaster
from services.pdf_service import generate_medical_ledger_pdf
from services.pnl_service import get_medical_ledger
from utils.helpers import df_to_excel_bytes
from utils.permissions import require_permission

require_permission("medical_ledger")
page_header("Medical Ledger", "medical_ledger", "📒")
session = get_db_session()

medicals = {m.medical_name: m.id for m in session.query(MedicalMaster).filter_by(is_active=True).all()}
med = st.selectbox("Medical Store", list(medicals.keys()))
from_d = st.date_input("From", value=date.today().replace(day=1))
to_d = st.date_input("To", value=date.today())

ledger = get_medical_ledger(session, medicals[med], from_d, to_d)

c1, c2, c3 = st.columns(3)
c1.metric("Total Sales/Supply", f"₹{ledger['total_sales']:,.2f}")
c2.metric("Total Collection", f"₹{ledger['total_collection']:,.2f}")
c3.metric("Outstanding", f"₹{ledger['outstanding']:,.2f}")

st.info("Medical statements do **not** show doctor names, commissions, or doctor expenses.")

st.subheader("Sales History")
st.dataframe(
    [{"Date": s.bill_date, "Product": s.product.product_name if s.product else "", "Qty": s.qty, "Rate": s.rate, "Amount": s.amount}
     for s in ledger["sales"]],
    hide_index=True, use_container_width=True,
)

st.subheader("Collection History")
st.dataframe(
    [{"Date": c.collection_date, "Receipt": c.receipt_number, "Amount": c.amount, "Mode": c.payment_mode, "Bank": c.bank}
     for c in ledger["collections"]],
    hide_index=True, use_container_width=True,
)

pdf = generate_medical_ledger_pdf(med, from_d, to_d, ledger)
st.download_button("Download PDF Statement", pdf, file_name=f"medical_ledger_{med}.pdf", mime="application/pdf")

import pandas as pd
excel_df = pd.DataFrame([
    {"Type": "Sales", "Date": s.bill_date, "Product": s.product.product_name if s.product else "", "Amount": s.amount}
    for s in ledger["sales"]
] + [
    {"Type": "Collection", "Date": c.collection_date, "Product": c.receipt_number, "Amount": c.amount}
    for c in ledger["collections"]
])
st.download_button("Download Excel", df_to_excel_bytes(excel_df), file_name=f"medical_ledger_{med}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
