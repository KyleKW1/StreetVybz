def main():
    # ... existing code ...
    
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
