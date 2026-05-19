from datetime import date

import pandas as pd
import streamlit as st

from components.page_layout import get_db_session, page_header
from database.models import MedicalMaster, ProductMaster, SalesData
from services.sales_service import delete_sales_record, process_sales_upload, update_sales_record
from utils.permissions import can_edit, require_permission

require_permission("sales_upload")
page_header("Sales Upload", "sales_upload", "📤")
session = get_db_session()

tab_upload, tab_edit_sales, tab_edit_product = st.tabs([
    "Excel Upload",
    "Edit Uploaded Sales",
    "Edit Product (MRP / PTR / PTS)",
])

with tab_upload:
    st.info(
        "Aapke billing software jaisa Excel seedha upload ho sakta hai: "
        "**Party Name**, **Item Name**, **Date**, **Bill No#**, **Qty**, **Rate**. "
        "**MRP** column add karein (commission ke liye zaroori) — nahi hai to Product Master se pick hoga."
    )
    with st.expander("Supported column names"):
        st.markdown("""
| Aapki file | System |
|------------|--------|
| Party Name | Medical store |
| Item Name | Product |
| Date | Bill date |
| Bill No# | Bill number |
| Qty | Quantity |
| Rate | Rate |
| **MRP** | MRP (recommended) |
| Cost / PTS | Cost (optional) |

Ignored: Expiry Date, Batch, Month, Scheme, Disc, Free Qty
        """)
    uploaded = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    if uploaded:
        df = pd.read_excel(uploaded)
        st.dataframe(df.head(20), use_container_width=True)
        if "MRP" not in df.columns and "mrp" not in [str(c).lower() for c in df.columns]:
            st.warning(
                "Is file mein **MRP column nahi hai**. Upload ho jayega, lekin commission sahi ke liye "
                "Excel mein MRP column add karein ya upload ke baad **Edit Product** se MRP set karein."
            )
        if can_edit("sales_upload") and st.button("Process Upload", type="primary"):
            try:
                result = process_sales_upload(session, df)
                if not result.get("success"):
                    session.rollback()
                    st.error(result.get("message"))
                else:
                    session.commit()
                    msg = (
                        f"Inserted: {result['inserted']} | "
                        f"Already in DB (skipped): {result['duplicates']}"
                    )
                    if result.get("merged_in_file"):
                        msg += f" | Excel duplicates merged: {result['merged_in_file']}"
                    st.success(msg)
                    for w in result.get("warnings", []):
                        st.warning(w)
                    if result.get("mrp_missing_count", 0) > 0:
                        st.error(
                            f"{result['mrp_missing_count']} products par MRP missing — "
                            "**Edit Product** tab se MRP add karein."
                        )
                    if result.get("errors"):
                        with st.expander("Row details / missing MRP list"):
                            st.text("\n".join(result["errors"][:50]))
            except Exception as e:
                session.rollback()
                st.error(f"Upload failed: {e}")
                st.caption("Session reset ho gaya. Dubara **Process Upload** try karein.")

with tab_edit_sales:
    st.markdown("**Upload ki hui sales rows yahan edit / delete karein** (Qty, Rate, MRP, Cost, Bill Date, Bill No)")
    f1, f2, f3 = st.columns(3)
    with f1:
        filter_from = st.date_input("From Date", value=date.today().replace(day=1), key="sales_edit_from")
    with f2:
        filter_to = st.date_input("To Date", value=date.today(), key="sales_edit_to")
    with f3:
        medicals = session.query(MedicalMaster).order_by(MedicalMaster.medical_name).all()
        med_filter = st.selectbox("Medical Store", ["All"] + [m.medical_name for m in medicals])

    q = session.query(SalesData).filter(
        SalesData.bill_date >= filter_from,
        SalesData.bill_date <= filter_to,
    )
    if med_filter != "All":
        mid = next(m.id for m in medicals if m.medical_name == med_filter)
        q = q.filter(SalesData.medical_id == mid)
    sales_rows = q.order_by(SalesData.bill_date.desc()).limit(500).all()

    if not sales_rows:
        st.warning("Is date range mein koi sales record nahi mila.")
    else:
        labels = [
            f"ID {s.id} | {s.bill_date} | {s.medical.medical_name} | {s.product.product_name} | Qty {s.qty} | ₹{s.amount:,.0f}"
            for s in sales_rows
        ]
        label_to_id = dict(zip(labels, [s.id for s in sales_rows]))
        selected_label = st.selectbox("Record select karein", labels)
        record = session.get(SalesData, label_to_id[selected_label])

        if record and can_edit("sales_upload"):
            with st.form("edit_sales_form"):
                qty = st.number_input("Qty", value=float(record.qty), min_value=0.0)
                rate = st.number_input("Rate", value=float(record.rate), min_value=0.0)
                mrp = st.number_input("MRP", value=float(record.mrp), min_value=0.0)
                cost = st.number_input("Cost", value=float(record.cost), min_value=0.0)
                bill_date = st.date_input("Bill Date", value=record.bill_date)
                bill_no = st.text_input("Bill No", value=record.bill_no or "")
                sync_mrp = st.checkbox("Product Master mein bhi MRP update karein", value=False)
                c1, c2 = st.columns(2)
                save = c1.form_submit_button("Save Changes", type="primary")
                delete = c2.form_submit_button("Delete Record")

            if save:
                try:
                    update_sales_record(
                        session, record.id, qty, rate, mrp, cost, bill_date, bill_no, sync_mrp
                    )
                    session.commit()
                    st.success("Sales record update ho gaya!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            if delete:
                delete_sales_record(session, record.id)
                session.commit()
                st.success("Record delete ho gaya.")
                st.rerun()
        elif record:
            st.dataframe([{
                "Medical": record.medical.medical_name,
                "Product": record.product.product_name,
                "Qty": record.qty,
                "Rate": record.rate,
                "Amount": record.amount,
            }], hide_index=True)

with tab_edit_product:
    st.markdown(
        "Excel upload se jo **naya product** banta hai, uska sirf naam + MRP save hota hai. "
        "PTR / PTS yahan ya **Product Master** page se set karein."
    )
    products = session.query(ProductMaster).order_by(ProductMaster.product_name).all()
    if not products:
        st.warning("Abhi koi product nahi hai. Pehle sales upload karein ya Product Master se add karein.")
    elif can_edit("product_master") or can_edit("sales_upload"):
        pmap = {p.product_name: p.id for p in products}
        search = st.text_input("Product search", placeholder="Naam type karein...")
        names = sorted(pmap.keys())
        if search:
            names = [n for n in names if search.lower() in n.lower()]
        if not names:
            st.warning("Product nahi mila.")
        else:
            pname = st.selectbox("Product", names)
            prod = session.get(ProductMaster, pmap[pname])
            with st.form("quick_product_edit"):
                new_name = st.text_input("Product Name", value=prod.product_name)
                new_mrp = st.number_input("MRP", value=float(prod.mrp), min_value=0.0)
                new_ptr = st.number_input("PTR", value=float(prod.ptr), min_value=0.0)
                new_pts = st.number_input("PTS", value=float(prod.pts), min_value=0.0)
                active = st.checkbox("Active", value=prod.is_active)
                if st.form_submit_button("Save Product", type="primary"):
                    prod.product_name = new_name
                    prod.mrp, prod.ptr, prod.pts = new_mrp, new_ptr, new_pts
                    prod.is_active = active
                    session.commit()
                    st.success("Product update ho gaya!")
                    st.rerun()
    else:
        st.info("Edit permission nahi hai. Admin se Product Master access mangwayein.")
