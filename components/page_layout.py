import streamlit as st

from utils.permissions import can_edit, init_session, require_login


def page_header(title: str, page_key: str, icon: str = ""):
    init_session()
    require_login()
    user = st.session_state.user
    st.title(f"{icon} {title}" if icon else title)
    col1, col2 = st.columns([3, 1])
    with col2:
        st.caption(f"Logged in: **{user['full_name']}** ({user['role']})")
        if not can_edit(page_key):
            st.info("View only mode")
    st.divider()


def get_db_session():
    from database.connection import get_session_factory

    if "db_session" not in st.session_state:
        st.session_state.db_session = get_session_factory()()
    return st.session_state.db_session
