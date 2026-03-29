import streamlit as st
from auth import logout
from styles import apply_custom_styles
from Pages.auth_page import login_page, register_page
from password_reset import forgot_password_page, reset_password_page
import json

def render_sidebar():
    with st.sidebar:
        user = st.session_state.get("user", {})
        st.markdown(f"### 👤 {user.get('username', 'User')}")
        st.markdown("---")
        
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state.selected_feature = None
            st.rerun()
        if st.button("📝 Log Session", use_container_width=True):
            st.session_state.selected_feature = 'log'
            st.rerun()
        if st.button("📜 History", use_container_width=True):
            st.session_state.selected_feature = 'history'
            st.rerun()
        if st.button("📊 Analytics", use_container_width=True):
            st.session_state.selected_feature = 'analytics'
            st.rerun()

        st.markdown("---")
        # ── NEW: What Would You Do quiz ──
        if st.button("🔥 What Would You Do?", use_container_width=True):
            st.session_state.selected_feature = 'wwyd'
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()


def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'selected_feature' not in st.session_state:
        st.session_state.selected_feature = None
    if 'file_page' not in st.session_state:
        st.session_state.file_page = 0

    apply_custom_styles()

    if not st.session_state.authenticated:
        if st.session_state.page == 'register':
            register_page()
        elif st.session_state.page == 'forgot':
            forgot_password_page()
        elif st.session_state.page == 'reset':
            reset_password_page()
        else:
            login_page()
    else:
        render_sidebar()

        feature = st.session_state.selected_feature

        if feature == 'log':
            from pages.log_session import log_session_page
            log_session_page()
        elif feature == 'history':
            from pages.session_history import session_history_page
            session_history_page()
        elif feature == 'analytics':
            from pages.analytics import analytics_page
            analytics_page()
        elif feature == 'wwyd':
            from pages.what_would_you_do import what_would_you_do_page
            what_would_you_do_page()
        else:
            from pages.dashboard import dashboard_page
            dashboard_page()


if __name__ == "__main__":
    main()
