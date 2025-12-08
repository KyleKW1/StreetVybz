import streamlit as st
from auth import logout
from styles import apply_custom_styles
from Pages.auth_page import login_page, register_page
from password_reset import forgot_password_page, reset_password_page
import json

def main():
    # Initialize session state FIRST (before page config)
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
        # Auth pages
        if st.session_state.page == 'register':
            register_page()
        else:
            login_page()
    else:
        # Main app
        render_sidebar()
        
        if st.session_state.selected_feature == 'log':
            from pages.log_session import log_session_page
            log_session_page()
        elif st.session_state.selected_feature == 'history':
            from pages.session_history import session_history_page
            session_history_page()
        elif st.session_state.selected_feature == 'analytics':
            from pages.analytics import analytics_page
            analytics_page()
        else:
            from pages.dashboard import dashboard_page
            dashboard_page()


if __name__ == "__main__":
    main()
