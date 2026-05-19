"""Combined: Doctor, Sales person, Company expenses."""
from datetime import date
from pathlib import Path

import streamlit as st

from components.page_layout import get_db_session, page_header
from config import COMPANY_EXPENSE_TYPES, DOCTOR_EXPENSE_TYPES, SALES_EXPENSE_TYPES
from database.models import CompanyExpense, DoctorExpense, DoctorMaster, SalesPersonExpense, User
from utils.attachments import attachment_download_button, save_expense_attachment
from utils.permissions import can_edit, can_view, require_login

require_login()
if not any(can_view(k) for k in ("doctor_expense", "sales_expense", "company_expense")):
    st.error("You do not have access to Expenses.")
    st.stop()
page_header("Expenses", "doctor_expense", "💰")
session = get_db_session()

tab_doc, tab_sales, tab_co = st.tabs(["Doctor Expenses", "Sales Person Expenses", "Company Expenses"])

with tab_doc:
    doctors = {d.doctor_name: d.id for d in session.query(DoctorMaster).filter_by(is_active=True).all()}
    if can_edit("doctor_expense"):
        proof = st.file_uploader("Bill proof (optional)", type=["pdf", "png", "jpg", "jpeg"], key="doc_exp_file")
        with st.form("doc_expense"):
            doc = st.selectbox("Doctor", list(doctors.keys()))
            edate = st.date_input("Date", value=date.today())
            etype = st.selectbox("Expense Type", DOCTOR_EXPENSE_TYPES)
            amount = st.number_input("Amount", min_value=0.0)
            deduct = st.checkbox("Deduct From Doctor Commission", value=True)
            remarks = st.text_input("Remarks")
            if st.form_submit_button("Save"):
                path = save_expense_attachment(proof, "doctor")
                session.add(DoctorExpense(
                    doctor_id=doctors[doc], expense_date=edate, expense_type=etype,
                    amount=amount, deduct_from_commission=deduct, remarks=remarks,
                    attachment_path=path,
                ))
                session.commit()
                st.success("Saved")
                st.rerun()
    rows = session.query(DoctorExpense).order_by(DoctorExpense.expense_date.desc()).limit(100).all()
    for e in rows:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"{e.expense_date} | {e.doctor.doctor_name} | {e.expense_type} | Rs {e.amount:,.0f} | {e.remarks or ''}")
        with c2:
            attachment_download_button(e.attachment_path, key=f"doc_att_{e.id}")

with tab_sales:
    users = {u.full_name: u.id for u in session.query(User).filter_by(is_active=True).all()}
    if can_edit("sales_expense"):
        proof = st.file_uploader("Bill proof (optional)", type=["pdf", "png", "jpg", "jpeg"], key="sales_exp_file")
        with st.form("sales_exp"):
            person = st.selectbox("Sales Person", list(users.keys()) if users else ["—"])
            edate = st.date_input("Date", value=date.today(), key="se_date")
            etype = st.selectbox("Expense Type", SALES_EXPENSE_TYPES)
            amount = st.number_input("Amount", min_value=0.0, key="se_amt")
            remarks = st.text_input("Remarks", key="se_rem")
            if st.form_submit_button("Save") and users:
                path = save_expense_attachment(proof, "sales")
                session.add(SalesPersonExpense(
                    user_id=users[person], expense_date=edate, expense_type=etype,
                    amount=amount, remarks=remarks, attachment_path=path,
                ))
                session.commit()
                st.success("Saved")
                st.rerun()
    rows = session.query(SalesPersonExpense).order_by(SalesPersonExpense.expense_date.desc()).limit(100).all()
    for e in rows:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"{e.expense_date} | {e.user.full_name} | {e.expense_type} | Rs {e.amount:,.0f}")
        with c2:
            attachment_download_button(e.attachment_path, key=f"sales_att_{e.id}")

with tab_co:
    if can_edit("company_expense"):
        proof = st.file_uploader("Bill proof (optional)", type=["pdf", "png", "jpg", "jpeg"], key="co_exp_file")
        with st.form("co_exp"):
            edate = st.date_input("Date", value=date.today(), key="ce_date")
            cat = st.selectbox("Category", COMPANY_EXPENSE_TYPES)
            amount = st.number_input("Amount", min_value=0.0, key="ce_amt")
            remarks = st.text_input("Remarks", key="ce_rem")
            if st.form_submit_button("Save"):
                path = save_expense_attachment(proof, "company")
                session.add(CompanyExpense(
                    expense_date=edate, expense_category=cat, amount=amount,
                    remarks=remarks, attachment_path=path,
                ))
                session.commit()
                st.success("Saved")
                st.rerun()
    rows = session.query(CompanyExpense).order_by(CompanyExpense.expense_date.desc()).limit(100).all()
    for e in rows:
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"{e.expense_date} | {e.expense_category} | Rs {e.amount:,.0f} | {e.remarks or ''}")
        with c2:
            attachment_download_button(e.attachment_path, key=f"co_att_{e.id}")
