import streamlit as st

from config import PAGE_KEYS


def init_session():
    defaults = {
        "authenticated": False,
        "user": None,
        "permissions": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_user_session(user, permissions: dict):
    st.session_state.authenticated = True
    st.session_state.user = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
    }
    st.session_state.permissions = permissions


def clear_session():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.permissions = {}


def can_view(page_key: str) -> bool:
    user = st.session_state.get("user")
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    perm = st.session_state.get("permissions", {}).get(page_key, {})
    return perm.get("can_view", False)


def can_edit(page_key: str) -> bool:
    user = st.session_state.get("user")
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    perm = st.session_state.get("permissions", {}).get(page_key, {})
    return perm.get("can_edit", False)


def require_login():
    init_session()
    if not st.session_state.authenticated:
        st.warning("Please login from the home page.")
        st.stop()


def require_permission(page_key: str, edit: bool = False):
    require_login()
    if edit and not can_edit(page_key):
        st.error("You do not have edit permission for this page.")
        st.stop()
    if not can_view(page_key):
        st.error("You do not have access to this page.")
        st.stop()


def filter_pages_for_user(all_pages: dict) -> dict:
    """Return pages the current user can view."""
    user = st.session_state.get("user")
    if user and user.get("role") == "admin":
        return all_pages
    return {k: v for k, v in all_pages.items() if can_view(k)}


def default_permissions_for_role(role: str) -> dict:
    """Default page permissions by role."""
    perms = {k: {"can_view": False, "can_edit": False} for k in PAGE_KEYS}
    if role == "admin":
        for k in PAGE_KEYS:
            perms[k] = {"can_view": True, "can_edit": True}
    elif role == "manager":
        view_pages = [
            "dashboard", "sales_upload", "product_master", "doctor_master",
            "medical_master", "area_master", "product_mapping", "stock_entry",
            "doctor_expense", "sales_expense", "doctor_payment",
            "payment_collection", "medical_ledger", "doctor_pnl", "company_pnl",
            "company_expense",
        ]
        edit_pages = view_pages
        for k in view_pages:
            perms[k] = {"can_view": True, "can_edit": k in edit_pages}
    elif role == "sales":
        view_pages = [
            "dashboard", "stock_entry", "doctor_expense", "sales_expense",
            "payment_collection",
        ]
        edit_pages = ["stock_entry", "doctor_expense", "sales_expense", "payment_collection"]
        for k in view_pages:
            perms[k] = {"can_view": True, "can_edit": k in edit_pages}
    return perms
