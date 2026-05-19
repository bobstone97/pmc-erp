from datetime import date

import pandas as pd
import streamlit as st

from components.page_layout import get_db_session, page_header
from database.models import DoctorExpense, SalesData, SalesPersonExpense
from services.pnl_service import get_outstanding_report
from utils.helpers import df_to_excel_bytes
from utils.permissions import require_permission

require_permission("dashboard")
page_header("Export Reports", "dashboard", "📥")
session = get_db_session()

from_d = st.date_input("From", value=date.today().replace(day=1))
to_d = st.date_input("To", value=date.today())

st.subheader("Outstanding Report")
out_df = get_outstanding_report(session)
st.download_button("Outstanding Excel", df_to_excel_bytes(out_df), "outstanding.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.dataframe(out_df, hide_index=True)

st.subheader("Sales Report")
sales = session.query(SalesData).filter(SalesData.bill_date >= from_d, SalesData.bill_date <= to_d).all()
sales_df = pd.DataFrame([{"Date": s.bill_date, "Medical": s.medical.medical_name, "Product": s.product.product_name,
                          "Qty": s.qty, "Amount": s.amount, "Profit": s.profit} for s in sales])
st.download_button("Sales Excel", df_to_excel_bytes(sales_df), "sales_report.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.subheader("Expense Report")
doc_exp = session.query(DoctorExpense).filter(DoctorExpense.expense_date >= from_d, DoctorExpense.expense_date <= to_d).all()
sales_exp = session.query(SalesPersonExpense).filter(SalesPersonExpense.expense_date >= from_d, SalesPersonExpense.expense_date <= to_d).all()
exp_df = pd.DataFrame(
    [{"Type": "Doctor", "Date": e.expense_date, "Name": e.doctor.doctor_name, "Category": e.expense_type, "Amount": e.amount} for e in doc_exp]
    + [{"Type": "Sales", "Date": e.expense_date, "Name": e.user.full_name, "Category": e.expense_type, "Amount": e.amount} for e in sales_exp]
)
st.download_button("Expense Excel", df_to_excel_bytes(exp_df), "expense_report.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
