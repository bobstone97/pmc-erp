from datetime import date

import streamlit as st

from components.page_layout import get_db_session, page_header
from config import PAYMENT_MODES
from database.models import DoctorMaster, DoctorPayment
from services.pdf_service import generate_doctor_payment_receipt
from utils.permissions import can_edit, require_permission

require_permission("doctor_payment")
page_header("Doctor Payments", "doctor_payment", "💳")
session = get_db_session()

doctors = {d.doctor_name: d.id for d in session.query(DoctorMaster).filter_by(is_active=True).all()}

if can_edit("doctor_payment"):
    with st.form("doc_pay"):
        doc = st.selectbox("Doctor", list(doctors.keys()))
        pdate = st.date_input("Payment Date", value=date.today())
        amount = st.number_input("Amount", min_value=0.0)
        mode = st.selectbox("Payment Mode", PAYMENT_MODES)
        remarks = st.text_input("Remarks")
        if st.form_submit_button("Record Payment"):
            payment = DoctorPayment(doctor_id=doctors[doc], payment_date=pdate, amount=amount, payment_mode=mode, remarks=remarks)
            session.add(payment)
            session.commit()
            pdf = generate_doctor_payment_receipt(doc, pdate, amount, mode, remarks)
            st.download_button("Download PDF Receipt", pdf, file_name=f"payment_{pdate}_{doc}.pdf", mime="application/pdf")
            st.success("Payment recorded!")
            st.rerun()

st.subheader("Payment History")
rows = session.query(DoctorPayment).order_by(DoctorPayment.payment_date.desc()).limit(200).all()
for p in rows:
    c1, c2 = st.columns([4, 1])
    with c1:
        st.write(f"**{p.doctor.doctor_name}** | {p.payment_date} | ₹{p.amount:,.2f} | {p.payment_mode}")
    with c2:
        pdf = generate_doctor_payment_receipt(p.doctor.doctor_name, p.payment_date, p.amount, p.payment_mode, p.remarks or "")
        st.download_button("PDF", pdf, key=f"pdf_{p.id}", file_name=f"receipt_{p.id}.pdf", mime="application/pdf")
