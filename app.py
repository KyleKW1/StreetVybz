import streamlit as st
from auth import logout
from styles import apply_custom_styles
from Pages.auth_page import login_page, register_page
from password_reset import forgot_password_page, reset_password_page


def render_sidebar():
    with st.sidebar:
        user = st.session_state.get("user", {})
        st.markdown(f"""
<div style="padding:16px 0 12px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px; color:#c6ff00;">
    VICE<span style="color:#f0f0f5;">VAULT</span>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:#5a5a72; margin-top:2px;">
    {user.get('username', 'User')}
  </div>
</div>
<div style="height:1px; background:#2a2a35; margin-bottom:12px;"></div>
""", unsafe_allow_html=True)

        if st.button("◈  Dashboard", use_container_width=True):
            st.session_state.selected_feature = 'stats'
            st.rerun()
        if st.button("＋  Log Session", use_container_width=True):
            st.session_state.selected_feature = 'log'
            st.rerun()
        if st.button("≡  History", use_container_width=True):
            st.session_state.selected_feature = 'history'
            st.rerun()
        if st.button("◉  Analytics", use_container_width=True):
            st.session_state.selected_feature = 'analytics'
            st.rerun()

        st.markdown("<div style='height:1px; background:#2a2a35; margin:12px 0;'></div>",
                    unsafe_allow_html=True)

        if st.button("⚡  What Would You Do?", use_container_width=True):
            st.session_state.selected_feature = 'wwyd'
            st.rerun()

        st.markdown("<div style='height:1px; background:#2a2a35; margin:12px 0;'></div>",
                    unsafe_allow_html=True)

        if st.button("→  Logout", use_container_width=True):
            logout()


def main():
    st.set_page_config(
        page_title="ViceVault",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    for key, default in [
        ('authenticated', False), ('user', None), ('page', 'login'),
        ('selected_feature', 'stats'), ('file_page', 0),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

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
            from Pages.dashboard import log_session_page
            log_session_page()

        elif feature == 'history':
            from Pages.dashboard import history_page
            history_page()

        elif feature == 'analytics':
            from Pages.analytics import analytics_page
            analytics_page()

        elif feature == 'wwyd':
            from Pages.what_would_you_do import what_would_you_do_page
            what_would_you_do_page()

        else:  # 'stats' or default
            from Pages.dashboard import stats_page
            stats_page()


if __name__ == "__main__":
    main()
