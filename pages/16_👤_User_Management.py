import streamlit as st

from components.page_layout import get_db_session, page_header
from config import PAGE_KEYS, PAGE_LABELS
from database.models import User
from services.auth_service import create_user, reset_password, set_user_active, update_user_permissions
from utils.permissions import can_edit, default_permissions_for_role, require_permission

require_permission("user_management")
page_header("User Management", "user_management", "👤")
session = get_db_session()

if st.session_state.user.get("role") != "admin":
    st.warning("Only administrators can manage users.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Create User", "Manage Users", "Permissions"])

with tab1:
    with st.form("new_user"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        full_name = st.text_input("Full Name")
        role = st.selectbox("Role", ["admin", "manager", "sales"])
        if st.form_submit_button("Create User"):
            try:
                create_user(session, username, password, full_name, role)
                session.commit()
                st.success("User created!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

with tab2:
    users = session.query(User).all()
    for u in users:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{u.full_name}** (@{u.username}) – {u.role} – {'Active' if u.is_active else 'Inactive'}")
        with c2:
            if st.button("Deactivate" if u.is_active else "Activate", key=f"act_{u.id}"):
                set_user_active(session, u.id, not u.is_active)
                session.commit()
                st.rerun()
        with c3:
            new_pw = st.text_input("New Password", key=f"pw_{u.id}", type="password")
            if st.button("Reset PW", key=f"reset_{u.id}") and new_pw:
                reset_password(session, u.id, new_pw)
                session.commit()
                st.success("Password reset!")

with tab3:
    users = session.query(User).all()
    umap = {f"{u.full_name} ({u.username})": u.id for u in users}
    sel = st.selectbox("User", list(umap.keys()))
    user = session.get(User, umap[sel])
    perms = {}
    for pk in PAGE_KEYS:
        c1, c2 = st.columns(2)
        view = c1.checkbox(f"View {PAGE_LABELS[pk]}", value=True, key=f"v_{pk}")
        edit = c2.checkbox(f"Edit {PAGE_LABELS[pk]}", value=False, key=f"e_{pk}")
        perms[pk] = {"can_view": view, "can_edit": edit}
    if st.button("Apply Role Defaults"):
        perms = default_permissions_for_role(user.role)
        st.rerun()
    if st.button("Save Permissions"):
        update_user_permissions(session, user.id, perms)
        session.commit()
        st.success("Permissions updated!")
