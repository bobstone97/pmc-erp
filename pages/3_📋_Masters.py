"""Combined: Product, Medical, Area, Doctor masters."""
from datetime import date

import streamlit as st

from components.page_layout import get_db_session, page_header
from config import COMMISSION_TYPES, COMMISSION_VALUE_HELP
from database.models import AreaMaster, DoctorMaster, MedicalMaster, ProductMaster
from services.master_service import delete_area, delete_doctor, delete_medical, merge_medicals, update_area
from utils.permissions import can_edit, can_view, require_login

require_login()
if not any(can_view(k) for k in ("product_master", "medical_master", "area_master", "doctor_master")):
    st.error("You do not have access to Masters.")
    st.stop()
page_header("Masters", "product_master", "📋")
session = get_db_session()

tab_product, tab_medical, tab_area, tab_doctor = st.tabs([
    "Product", "Medical", "Area", "Doctor",
])

# ——— Product ———
with tab_product:
    if can_edit("product_master"):
        products = session.query(ProductMaster).order_by(ProductMaster.product_name).all()
        options = {"-- New --": None, **{p.product_name: p.id for p in products}}
        sel = st.selectbox("Select Product", list(options.keys()), key="m_prod_sel")
        existing = session.get(ProductMaster, options[sel]) if options[sel] else None
        with st.form("m_product_form"):
            name = st.text_input("Product Name", value=existing.product_name if existing else "")
            mrp = st.number_input("MRP", value=float(existing.mrp) if existing else 0.0, min_value=0.0)
            ptr = st.number_input("PTR", value=float(existing.ptr) if existing else 0.0, min_value=0.0)
            pts = st.number_input("PTS", value=float(existing.pts) if existing else 0.0, min_value=0.0)
            active = st.checkbox("Active", value=existing.is_active if existing else True)
            if st.form_submit_button("Save Product"):
                if existing:
                    existing.product_name, existing.mrp, existing.ptr, existing.pts = name, mrp, ptr, pts
                    existing.is_active = active
                else:
                    session.add(ProductMaster(product_name=name, mrp=mrp, ptr=ptr, pts=pts, is_active=active))
                session.commit()
                st.success("Saved")
                st.rerun()
    st.dataframe(
        [{"ID": p.id, "Product": p.product_name, "MRP": p.mrp, "PTR": p.ptr, "PTS": p.pts, "Active": p.is_active}
         for p in session.query(ProductMaster).all()],
        hide_index=True, use_container_width=True,
    )

# ——— Medical ———
with tab_medical:
    areas = {a.area_name: a.id for a in session.query(AreaMaster).filter_by(is_active=True).all()}
    if can_edit("medical_master"):
        medicals = session.query(MedicalMaster).order_by(MedicalMaster.medical_name).all()
        options = {"-- New --": None, **{m.medical_name: m.id for m in medicals}}
        sel = st.selectbox("Select Medical", list(options.keys()), key="m_med_sel")
        existing = session.get(MedicalMaster, options[sel]) if options[sel] else None
        with st.form("m_medical_form"):
            name = st.text_input("Medical Name", value=existing.medical_name if existing else "")
            area = st.selectbox("Area", ["--"] + list(areas.keys()))
            contact = st.text_input("Contact", value=existing.contact_person if existing else "")
            mobile = st.text_input("Mobile", value=existing.mobile if existing else "")
            address = st.text_area("Address", value=existing.address if existing else "")
            active = st.checkbox("Active", value=existing.is_active if existing else True)
            if st.form_submit_button("Save Medical"):
                aid = areas.get(area) if area != "--" else None
                if existing:
                    existing.medical_name, existing.area_id = name, aid
                    existing.contact_person, existing.mobile, existing.address = contact, mobile, address
                    existing.is_active = active
                else:
                    session.add(MedicalMaster(medical_name=name, area_id=aid, contact_person=contact, mobile=mobile, address=address, is_active=active))
                session.commit()
                st.success("Saved")
                st.rerun()

        if existing:
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Deactivate medical", key="med_deact"):
                    r = delete_medical(session, existing.id, hard=False)
                    session.commit()
                    st.warning(r)
                    st.rerun()
            with c2:
                if st.button("Delete medical (only if no sales/visits)", key="med_del"):
                    r = delete_medical(session, existing.id, hard=True)
                    if r == "deleted":
                        session.commit()
                        st.success("Deleted")
                        st.rerun()
                    else:
                        session.rollback()
                        st.error(r)

        st.subheader("Merge medical stores")
        st.caption("Closed shop ka saara data active shop mein move karein (sales, collections, visits, mappings).")
        med_list = session.query(MedicalMaster).order_by(MedicalMaster.medical_name).all()
        med_map = {m.medical_name: m.id for m in med_list}
        if len(med_list) >= 2:
            src = st.selectbox("Merge FROM (old/closed)", list(med_map.keys()), key="merge_src")
            tgt = st.selectbox("Merge INTO (keep this)", list(med_map.keys()), key="merge_tgt")
            if st.button("Merge all data", type="primary"):
                try:
                    stats = merge_medicals(session, med_map[src], med_map[tgt])
                    session.commit()
                    st.success(f"Merged: {stats}")
                    st.rerun()
                except ValueError as e:
                    session.rollback()
                    st.error(str(e))

    st.dataframe(
        [{"ID": m.id, "Name": m.medical_name, "Area": m.area.area_name if m.area else "", "Active": m.is_active}
         for m in session.query(MedicalMaster).all()],
        hide_index=True, use_container_width=True,
    )

# ——— Area ———
with tab_area:
    if can_edit("area_master"):
        all_areas = session.query(AreaMaster).order_by(AreaMaster.area_name).all()
        area_opts = {"-- New --": None, **{a.area_name: a.id for a in all_areas}}
        asel = st.selectbox("Select Area", list(area_opts.keys()), key="m_area_sel")
        aexisting = session.get(AreaMaster, area_opts[asel]) if area_opts[asel] else None
        with st.form("m_area_form"):
            aname = st.text_input("Area Name", value=aexisting.area_name if aexisting else "")
            aactive = st.checkbox("Active", value=aexisting.is_active if aexisting else True)
            if st.form_submit_button("Save Area"):
                if aexisting:
                    update_area(session, aexisting.id, aname, aactive)
                else:
                    session.add(AreaMaster(area_name=aname.strip(), is_active=aactive))
                session.commit()
                st.success("Saved")
                st.rerun()
        if aexisting:
            if st.button("Delete / deactivate area", key="area_del"):
                r = delete_area(session, aexisting.id)
                session.commit()
                st.warning(r)
                st.rerun()
    st.dataframe(
        [{"ID": a.id, "Area": a.area_name, "Active": a.is_active} for a in session.query(AreaMaster).all()],
        hide_index=True, use_container_width=True,
    )

# ——— Doctor ———
with tab_doctor:
    areas = {a.area_name: a.id for a in session.query(AreaMaster).filter_by(is_active=True).all()}
    if can_edit("doctor_master"):
        doctors = session.query(DoctorMaster).order_by(DoctorMaster.doctor_name).all()
        options = {"-- New --": None, **{d.doctor_name: d.id for d in doctors}}
        sel = st.selectbox("Select Doctor", list(options.keys()), key="m_doc_sel")
        existing = session.get(DoctorMaster, options[sel]) if options[sel] else None
        default_ct = 1
        if existing and existing.commission_type in COMMISSION_TYPES:
            default_ct = COMMISSION_TYPES.index(existing.commission_type)
        ct = st.selectbox("Commission Type", COMMISSION_TYPES, index=default_ct, key="m_doc_ct")
        st.caption(COMMISSION_VALUE_HELP.get(ct, ""))
        unit = "%" if ct != "FIXED" else "Rs"
        cv = st.number_input(f"Commission Value ({unit})", value=float(existing.commission_value) if existing else 0.0, key="m_doc_cv")
        with st.form("m_doctor_form"):
            name = st.text_input("Doctor Name", value=existing.doctor_name if existing else "")
            speciality = st.text_input("Speciality", value=existing.speciality if existing else "")
            mobile = st.text_input("Mobile", value=existing.mobile if existing else "")
            area = st.selectbox("Area", ["--"] + list(areas.keys()))
            active = st.checkbox("Active", value=existing.is_active if existing else True)
            if st.form_submit_button("Save Doctor"):
                aid = areas.get(area) if area != "--" else None
                if existing:
                    existing.doctor_name, existing.speciality = name, speciality
                    existing.mobile, existing.area_id = mobile, aid
                    existing.commission_type, existing.commission_value = ct, cv
                    existing.is_active = active
                else:
                    session.add(DoctorMaster(doctor_name=name, speciality=speciality, mobile=mobile, area_id=aid, commission_type=ct, commission_value=cv, is_active=active))
                session.commit()
                st.success("Saved")
                st.rerun()
        if existing:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Deactivate doctor", key="doc_deact"):
                    r = delete_doctor(session, existing.id, hard=False)
                    session.commit()
                    st.warning(r)
                    st.rerun()
            with c2:
                if st.button("Delete doctor (no visits/mappings)", key="doc_del"):
                    r = delete_doctor(session, existing.id, hard=True)
                    if r == "deleted":
                        session.commit()
                        st.success("Deleted")
                        st.rerun()
                    session.rollback()
                    st.error(r)
    st.dataframe(
        [{"ID": d.id, "Name": d.doctor_name, "Type": d.commission_type, "Value": d.commission_value, "Active": d.is_active}
         for d in session.query(DoctorMaster).all()],
        hide_index=True, use_container_width=True,
    )
