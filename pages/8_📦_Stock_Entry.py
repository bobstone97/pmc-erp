from datetime import date

import pandas as pd
import streamlit as st

from components.page_layout import get_db_session, page_header
from database.models import DoctorMaster, MedicalMaster, VisitDetail, VisitMaster
from services.stock_service import (
    build_visit_stock_rows,
    check_cycle_overlap,
    get_earliest_visit_date,
    get_previous_visit,
    get_visit_history,
    save_visit,
)
from utils.permissions import can_edit, require_permission

require_permission("stock_entry")
page_header("Visit Based Stock Entry", "stock_entry", "📦")
session = get_db_session()

doctors = {d.doctor_name: d.id for d in session.query(DoctorMaster).filter_by(is_active=True).all()}
medicals = {m.medical_name: m.id for m in session.query(MedicalMaster).filter_by(is_active=True).all()}

tab1, tab2, tab3 = st.tabs(["New Visit", "Visit History", "Edit Visit"])

with tab1:
    if not doctors or not medicals:
        st.warning("Add doctors and medical stores first.")
    else:
        doc = st.selectbox("Doctor", list(doctors.keys()), key="visit_doc")
        med = st.selectbox("Medical", list(medicals.keys()), key="visit_med")
        doctor_id, medical_id = doctors[doc], medicals[med]

        prev_visit = get_previous_visit(session, doctor_id, medical_id)
        min_visit = get_earliest_visit_date(session, doctor_id, medical_id)
        if prev_visit:
            st.warning(
                f"Last visit: **{prev_visit.visit_date}**. "
                f"Nayi visit ki date **{min_visit}** ya uske baad honi chahiye."
            )
        default_visit = min_visit if min_visit and min_visit > date.today() else (min_visit or date.today())
        visit_date = st.date_input(
            "Visit Date",
            value=default_visit,
            min_value=min_visit,
            key="visit_date_input",
        )

        if st.button("Load Mapped Products"):
            if check_cycle_overlap(session, doctor_id, medical_id, visit_date):
                st.error(
                    f"Date {visit_date} allowed nahi — pehle ki visit {prev_visit.visit_date} hai. "
                    f"Minimum date: {min_visit}"
                )
            else:
                st.session_state.stock_rows = build_visit_stock_rows(session, doctor_id, medical_id, visit_date)
                from services.stock_service import calculate_visit_cycle
                from_d, to_d = calculate_visit_cycle(session, doctor_id, medical_id, visit_date)
                st.info(f"Visit cycle: {from_d} to {to_d} | Formula: Sold = Opening + Supply - Current")

        if "stock_rows" in st.session_state and st.session_state.stock_rows:
            edited = []
            for i, row in enumerate(st.session_state.stock_rows):
                st.markdown(f"**{row['product_name']}**")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Opening", f"{row['opening_stock']:.0f}")
                c2.metric("Supply", f"{row['supply_qty']:.0f}")
                c3.metric("Max", f"{row['max_stock']:.0f}")
                current = c4.number_input("Current Stock", value=float(row["current_stock"]), key=f"cur_{i}", min_value=0.0, max_value=float(row["max_stock"]))
                sold = row["opening_stock"] + row["supply_qty"] - current
                c5.metric("Sold", f"{sold:.0f}")
                edited.append({**row, "current_stock": current})
            st.session_state.stock_rows = edited

            remarks = st.text_input("Remarks")
            if can_edit("stock_entry") and st.button("Save Visit", type="primary"):
                if check_cycle_overlap(session, doctor_id, medical_id, visit_date):
                    st.error(f"Visit date must be after {prev_visit.visit_date}. Use {min_visit} or later.")
                else:
                    try:
                        user_id = st.session_state.user.get("id")
                        save_visit(
                            session, doctor_id, medical_id, visit_date,
                            [{
                                "product_id": r["product_id"],
                                "opening_stock": r["opening_stock"],
                                "supply_qty": r["supply_qty"],
                                "current_stock": r["current_stock"],
                                "rate": r["rate"],
                                "cost": r["cost"],
                                "mrp": r["mrp"],
                            } for r in edited],
                            remarks, user_id,
                        )
                        session.commit()
                        st.success("Visit saved. Current stock carried forward.")
                        del st.session_state.stock_rows
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

with tab2:
    filter_doc = st.selectbox("Filter Doctor", ["All"] + list(doctors.keys()))
    visits = get_visit_history(session, doctors.get(filter_doc) if filter_doc != "All" else None)
    for v in visits:
        with st.expander(f"{v.visit_date} – {v.doctor.doctor_name} @ {v.medical.medical_name}"):
            details = session.query(VisitDetail).filter_by(visit_id=v.id).all()
            st.dataframe([{"Product": d.product.product_name, "Opening": d.opening_stock, "Supply": d.supply_qty,
                           "Current": d.current_stock, "Sold": d.sold_qty} for d in details], hide_index=True)

with tab3:
    visits = session.query(VisitMaster).order_by(VisitMaster.visit_date.desc()).limit(50).all()
    if visits and can_edit("stock_entry"):
        vsel = st.selectbox("Select Visit", [f"{v.id} - {v.visit_date}" for v in visits])
        vid = int(vsel.split(" - ")[0])
        visit = session.get(VisitMaster, vid)
        details = session.query(VisitDetail).filter_by(visit_id=vid).all()
        for d in details:
            st.markdown(f"**{d.product.product_name}**")
            ec1, ec2, ec3 = st.columns(3)
            new_rate = ec1.number_input("Rate", value=float(d.rate), min_value=0.0, key=f"rate_{d.id}")
            new_cost = ec2.number_input("Cost", value=float(d.cost), min_value=0.0, key=f"cost_{d.id}")
            new_cur = ec3.number_input("Current stock", value=float(d.current_stock), min_value=0.0, key=f"edit_{d.id}")
            sold = d.opening_stock + d.supply_qty - new_cur
            st.caption(f"Sold: {sold:g} | Sales: {sold * new_rate:,.2f} | Cost amt: {sold * new_cost:,.2f} | Profit: {sold * new_rate - sold * new_cost:,.2f}")
            if st.button(f"Save {d.product.product_name}", key=f"btn_{d.id}"):
                max_s = d.opening_stock + d.supply_qty
                if new_cur > max_s:
                    st.error("Current stock cannot exceed opening + supply")
                else:
                    d.rate = new_rate
                    d.cost = new_cost
                    d.current_stock = new_cur
                    d.sold_qty = d.opening_stock + d.supply_qty - new_cur
                    session.commit()
                    st.success("Updated")
