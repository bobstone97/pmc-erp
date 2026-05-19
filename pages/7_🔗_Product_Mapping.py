from datetime import date

import streamlit as st

from components.page_layout import get_db_session, page_header
from config import COMMISSION_TYPES
from database.models import DoctorMaster, MappingMaster, MedicalMaster, ProductMaster
from services.mapping_service import (
    delete_mapping,
    get_mapping_by_keys,
    reset_mapping_current_stock,
    update_mapping_fields,
    upsert_mapping,
)
from utils.permissions import can_edit, require_permission

require_permission("product_mapping")
page_header("Product Mapping", "product_mapping", "🔗")
session = get_db_session()

doctors = {d.doctor_name: d.id for d in session.query(DoctorMaster).filter_by(is_active=True).all()}
medicals = {m.medical_name: m.id for m in session.query(MedicalMaster).filter_by(is_active=True).all()}
products = {p.product_name: p.id for p in session.query(ProductMaster).filter_by(is_active=True).all()}

tab_add, tab_edit, tab_manage = st.tabs([
    "Add / Update mapping",
    "Edit rate & cost (rectify)",
    "Remove / Reset stock",
])

with tab_add:
    if not doctors or not medicals or not products:
        st.warning("Pehle Doctor, Medical aur Product master mein entries add karein.")
    elif can_edit("product_mapping"):
        doc = st.selectbox("Doctor", list(doctors.keys()), key="map_doc")
        med = st.selectbox("Medical Store", list(medicals.keys()), key="map_med")
        prod = st.selectbox("Product", list(products.keys()), key="map_prod")
        existing_map = get_mapping_by_keys(
            session, doctors[doc], medicals[med], products[prod]
        )
        if existing_map:
            st.info(
                f"Existing mapping loaded — Rate **{existing_map.rate}**, Cost **{existing_map.cost}**. "
                "Save karenge to update ho jayega."
            )
        with st.form("mapping_form"):
            opening = st.number_input(
                "Opening Stock",
                min_value=0.0,
                value=float(existing_map.opening_stock) if existing_map else 0.0,
            )
            opening_date = st.date_input(
                "Opening Date",
                value=existing_map.opening_date if existing_map and existing_map.opening_date else date.today(),
            )
            rate = st.number_input(
                "Rate (sale price per unit)",
                min_value=0.0,
                value=float(existing_map.rate) if existing_map else 0.0,
            )
            cost = st.number_input(
                "Cost (per unit)",
                min_value=0.0,
                value=float(existing_map.cost) if existing_map else 0.0,
            )
            st.caption("Profit on visits = Sold Qty × Rate − Sold Qty × Cost")
            override = st.checkbox(
                "Override Commission",
                value=bool(existing_map and existing_map.commission_type_override),
            )
            ct = ""
            cv = 0.0
            if override:
                opts = [""] + COMMISSION_TYPES
                cur = existing_map.commission_type_override if existing_map else ""
                ct = st.selectbox(
                    "Commission Type Override",
                    opts,
                    index=opts.index(cur) if cur in opts else 0,
                )
                cv = st.number_input(
                    "Commission Value Override",
                    value=float(existing_map.commission_value_override or 0)
                    if existing_map
                    else 0.0,
                )
            if st.form_submit_button("Save Mapping (UPSERT)"):
                upsert_mapping(
                    session,
                    doctors[doc],
                    medicals[med],
                    products[prod],
                    opening_stock=opening,
                    opening_date=opening_date,
                    rate=rate,
                    cost=cost,
                    commission_type_override=ct or None,
                    commission_value_override=cv if override else None,
                )
                session.commit()
                st.success("Mapping saved.")
                st.rerun()
    else:
        st.info("Aapke paas edit permission nahi hai.")

with tab_edit:
    st.markdown(
        "Galat **Rate** ya **Cost** daal diya ho to yahan select karke sahi value save karein. "
        "Naye visits isi rate/cost se chalenge. Purani visit rows alag rehti hain — "
        "unke liye **Stock Entry → Edit Visit** use karein."
    )
    mappings = session.query(MappingMaster).order_by(MappingMaster.id.desc()).all()
    if not mappings:
        st.info("Koi mapping nahi.")
    elif can_edit("product_mapping"):
        labels = [
            f"ID {m.id} | {m.doctor.doctor_name if m.doctor else '?'} | "
            f"{m.medical.medical_name if m.medical else '?'} | "
            f"{m.product.product_name if m.product else '?'} | "
            f"Rate {m.rate} | Cost {m.cost}"
            for m in mappings
        ]
        id_by_label = dict(zip(labels, [m.id for m in mappings]))
        choice = st.selectbox("Mapping select karein", labels, key="map_edit_pick")
        mid = id_by_label[choice]
        sel = session.get(MappingMaster, mid)

        with st.form("edit_mapping_prices"):
            new_rate = st.number_input("Rate", min_value=0.0, value=float(sel.rate))
            new_cost = st.number_input("Cost", min_value=0.0, value=float(sel.cost))
            new_opening = st.number_input("Opening Stock", min_value=0.0, value=float(sel.opening_stock))
            new_opening_date = st.date_input(
                "Opening Date",
                value=sel.opening_date or date.today(),
            )
            override = st.checkbox(
                "Commission override",
                value=bool(sel.commission_type_override),
            )
            new_ct = ""
            new_cv = 0.0
            if override:
                opts = [""] + COMMISSION_TYPES
                cur = sel.commission_type_override or ""
                new_ct = st.selectbox(
                    "Commission Type",
                    opts,
                    index=opts.index(cur) if cur in opts else 0,
                )
                new_cv = st.number_input(
                    "Commission Value",
                    value=float(sel.commission_value_override or 0),
                )
            if st.form_submit_button("Save rate / cost / opening", type="primary"):
                update_mapping_fields(
                    session,
                    mid,
                    opening_stock=new_opening,
                    opening_date=new_opening_date,
                    rate=new_rate,
                    cost=new_cost,
                    commission_type_override=new_ct if override else None,
                    commission_value_override=new_cv if override else None,
                    clear_commission_override=not override,
                )
                session.commit()
                st.success("Rate / cost update ho gaya.")
                st.rerun()

with tab_manage:
    st.markdown(
        "Galat product map ho gaya ho to **delete** karein. Sirf **current stock** fix karna ho to reset buttons use karein."
    )
    mappings = session.query(MappingMaster).order_by(MappingMaster.id.desc()).all()
    if not mappings:
        st.info("Abhi koi mapping nahi hai.")
    elif can_edit("product_mapping"):
        labels = [
            f"ID {m.id} | {m.doctor.doctor_name if m.doctor else '?'} | "
            f"{m.medical.medical_name if m.medical else '?'} | "
            f"{m.product.product_name if m.product else '?'} | "
            f"Opening {m.opening_stock:g} | Current {m.current_stock:g}"
            for m in mappings
        ]
        id_by_label = dict(zip(labels, [m.id for m in mappings]))
        choice = st.selectbox("Mapping select karein", labels, key="map_pick")
        mid = id_by_label[choice]
        sel = session.get(MappingMaster, mid)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Current = Opening", key="btn_reset_open"):
                reset_mapping_current_stock(session, mid, use_opening=True)
                session.commit()
                st.success("Current = opening.")
                st.rerun()
        with c2:
            if st.button("Current = 0", key="btn_reset_zero"):
                reset_mapping_current_stock(session, mid, use_opening=False, value=0.0)
                session.commit()
                st.success("Current = 0.")
                st.rerun()
        with c3:
            new_cur = st.number_input(
                "Current stock",
                min_value=0.0,
                value=float(sel.current_stock),
                key="map_new_cur",
            )
            if st.button("Save current", key="btn_save_cur"):
                reset_mapping_current_stock(session, mid, use_opening=False, value=new_cur)
                session.commit()
                st.success("Current stock updated.")
                st.rerun()

        st.divider()
        confirm = st.checkbox("Confirm permanent delete", key="map_del_confirm")
        if st.button("Delete mapping", type="primary", disabled=not confirm):
            try:
                delete_mapping(session, mid)
                session.commit()
                st.success("Mapping deleted.")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(str(e))
    else:
        st.info("Edit permission required.")

st.subheader("All mappings")
mappings = session.query(MappingMaster).order_by(MappingMaster.id.desc()).all()
st.dataframe(
    [
        {
            "ID": m.id,
            "Doctor": m.doctor.doctor_name if m.doctor else "",
            "Medical": m.medical.medical_name if m.medical else "",
            "Product": m.product.product_name if m.product else "",
            "Opening": m.opening_stock,
            "Current": m.current_stock,
            "Rate": m.rate,
            "Cost": m.cost,
            "Comm Type": m.commission_type_override or "-",
            "Comm Value": m.commission_value_override or "-",
        }
        for m in mappings
    ],
    hide_index=True,
    use_container_width=True,
)
