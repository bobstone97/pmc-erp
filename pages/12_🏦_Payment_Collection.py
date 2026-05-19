from datetime import date

import streamlit as st

from components.page_layout import get_db_session, page_header
from config import PAYMENT_MODES
from database.models import MedicalMaster, PaymentCollection
from utils.permissions import can_edit, require_permission

require_permission("payment_collection")
page_header("Payment Collection", "payment_collection", "🏦")
session = get_db_session()

medicals = {m.medical_name: m.id for m in session.query(MedicalMaster).filter_by(is_active=True).all()}

if can_edit("payment_collection"):
    with st.form("collection"):
        med = st.selectbox("Medical Store", list(medicals.keys()))
        receipt = st.text_input("Receipt Number")
        cdate = st.date_input("Date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0)
        mode = st.selectbox("Payment Mode", PAYMENT_MODES)
        bank = st.text_input("Bank")
        remarks = st.text_input("Remarks")
        if st.form_submit_button("Save Collection"):
            session.add(PaymentCollection(medical_id=medicals[med], receipt_number=receipt, collection_date=cdate, amount=amount, payment_mode=mode, bank=bank, remarks=remarks))
            session.commit()
            st.success("Collection recorded!")
            st.rerun()

st.dataframe(
    [{"Date": c.collection_date, "Medical": c.medical.medical_name, "Receipt": c.receipt_number,
      "Amount": c.amount, "Mode": c.payment_mode, "Bank": c.bank} for c in session.query(PaymentCollection).order_by(PaymentCollection.collection_date.desc()).limit(200).all()],
    hide_index=True, use_container_width=True,
)
