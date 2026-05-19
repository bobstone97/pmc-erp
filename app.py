"""PMC ERP – Pharmaceutical Secondary Sales, Incentive & Recovery Management."""
import streamlit as st

from database.connection import get_session, init_db
from init_db import seed_admin
from database.migrate import run_migrations
from services.auth_service import authenticate, get_user_permissions
from utils.permissions import clear_session, init_session, set_user_session

st.set_page_config(
    page_title="PMC ERP",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()

try:
    init_db()
    run_migrations()
    seed_admin()
except Exception as e:
    print(e)

st.markdown(
    """
    <style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1f4e79; }
    .sub-header { color: #555; margin-bottom: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.authenticated:
    user = st.session_state.user
    st.markdown('<p class="main-header">PMC ERP</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Pharmaceutical Secondary Sales, Incentive & Recovery Management</p>',
        unsafe_allow_html=True,
    )
    st.success(f"Welcome, **{user['full_name']}** ({user['role']})")
    st.info("Use the sidebar to navigate between modules.")
    if st.button("Logout", type="primary"):
        clear_session()
        if "db_session" in st.session_state:
            st.session_state.db_session.close()
            del st.session_state.db_session
        st.rerun()
else:
    st.markdown('<p class="main-header">PMC ERP – Login</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Pharmaceutical Secondary Sales, Incentive & Recovery Management System</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            try:
                init_db()
                with get_session() as session:
                    user = authenticate(session, username, password)
                    if user:
                        perms = get_user_permissions(session, user)
                        set_user_session(user, perms)
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password, or account is inactive.")
            except Exception as e:
                st.error(f"Database connection failed: {e}")
                st.caption("Ensure PostgreSQL is running and DATABASE_URL is set in .env")

    st.caption("Default: admin / admin123 (run `python init_db.py` first)")
