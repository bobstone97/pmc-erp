from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from components.page_layout import get_db_session, page_header
from services.dashboard_service import (
    get_dashboard_metrics,
    product_wise_sales_chart,
    sales_by_doctor_chart,
    sales_by_medical_chart,
    top_lists,
)
from services.pnl_service import get_outstanding_report
from utils.permissions import require_permission

require_permission("dashboard")
page_header("Dashboard", "dashboard", "📊")

session = get_db_session()
col1, col2 = st.columns(2)
with col1:
    from_d = st.date_input("From Date", value=date.today().replace(day=1))
with col2:
    to_d = st.date_input("To Date", value=date.today())

metrics = get_dashboard_metrics(session, from_d, to_d)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Supply Upload (Sales)", f"₹{metrics['total_sales']:,.0f}")
m2.metric("Total Collection", f"₹{metrics['total_collection']:,.0f}")
m3.metric("Outstanding", f"₹{metrics['outstanding']:,.0f}")
m4.metric("Gross Profit (Sold)", f"₹{metrics['gross_profit']:,.0f}",
          help="Sold Qty×Rate − Sold Qty×Cost from visits")

m4b, m5, m6, m7 = st.columns(4)
m4b.metric("Net Profit", f"₹{metrics['net_profit']:,.0f}",
           help="Gross profit minus commission & expenses")

m5.metric("Doctor Commission", f"₹{metrics['doctor_commission']:,.0f}")
m6.metric("Company Expense", f"₹{metrics['company_expense']:,.0f}")
m7.metric("Sales Person Expense", f"₹{metrics['sales_person_expense']:,.0f}")

st.subheader("Charts")
c1, c2 = st.columns(2)
with c1:
    df_doc = sales_by_doctor_chart(session, from_d, to_d)
    if not df_doc.empty:
        st.plotly_chart(px.bar(df_doc, x="Doctor", y="Sales", title="Sales By Doctor"), use_container_width=True)
with c2:
    df_med = sales_by_medical_chart(session, from_d, to_d)
    if not df_med.empty:
        st.plotly_chart(px.bar(df_med, x="Medical", y="Sales", title="Sales By Medical"), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    out_df = get_outstanding_report(session)
    if not out_df.empty:
        st.plotly_chart(px.bar(out_df.head(15), x="Medical", y="Outstanding", title="Outstanding By Medical"), use_container_width=True)
with c4:
    df_prod = product_wise_sales_chart(session, from_d, to_d)
    if not df_prod.empty:
        st.plotly_chart(px.pie(df_prod, names="Product", values="Qty", title="Product Wise Sales"), use_container_width=True)

lists = top_lists(session, from_d, to_d)
st.subheader("Top Lists")
l1, l2, l3, l4 = st.columns(4)
with l1:
    st.markdown("**Top Doctors**")
    st.dataframe(lists["top_doctors"], hide_index=True, use_container_width=True)
with l2:
    st.markdown("**Top Medicals**")
    st.dataframe(lists["top_medicals"], hide_index=True, use_container_width=True)
with l3:
    st.markdown("**Highest Outstanding**")
    st.dataframe(lists["highest_outstanding"], hide_index=True, use_container_width=True)
with l4:
    st.markdown("**Highest Expense Doctors**")
    st.dataframe(lists["highest_expense_doctors"], hide_index=True, use_container_width=True)
