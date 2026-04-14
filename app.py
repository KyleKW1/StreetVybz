import streamlit as st
from auth import logout
from styles import apply_custom_styles
from Pages.auth_page import login_page, register_page
from password_reset import forgot_password_page, reset_password_page, handle_reset_token_from_url


# ─── DB SYNC HELPERS ──────────────────────────────────────────────────────────

def _bootstrap_db():
    try:
        import database as db
        db.ensure_tables()
    except Exception:
        pass


def _load_vice_log_from_db(user_id: int):
    if st.session_state.get("vice_log_loaded"):
        return
    try:
        import database as db
        entries = db.load_vice_log(user_id)
        st.session_state.vice_log = list(reversed(entries))
    except Exception:
        if "vice_log" not in st.session_state:
            st.session_state.vice_log = []
    finally:
        st.session_state.vice_log_loaded = True


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

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

        if st.button("◈  Dashboard",              use_container_width=True, key="sb_dashboard"):
            st.session_state.selected_feature = 'stats'
            st.rerun()
        if st.button("＋  Log Session",            use_container_width=True, key="sb_log"):
            st.session_state.selected_feature = 'log'
            st.rerun()
        if st.button("≡  History",                 use_container_width=True, key="sb_history"):
            st.session_state.selected_feature = 'history'
            st.rerun()
        if st.button("◉  Analytics",               use_container_width=True, key="sb_analytics"):
            st.session_state.selected_feature = 'analytics'
            st.rerun()

        st.markdown("<div style='height:1px; background:#2a2a35; margin:12px 0;'></div>",
                    unsafe_allow_html=True)

        if st.button("⚡  Read Between The Lines", use_container_width=True, key="sb_wwyd"):
            st.session_state.selected_feature = 'wwyd'
            st.rerun()
        if st.button("📍  Kingston Hot Spots",     use_container_width=True, key="sb_hotspots"):
            st.session_state.selected_feature = 'hotspots'
            st.rerun()
        if st.button("🃏  Do or Drink",            use_container_width=True, key="sb_dod"):
            st.session_state.selected_feature = 'do_or_drink'
            st.rerun()
        if st.button(" Confessions",              use_container_width=True, key="sb_confessions"):
            st.session_state.selected_feature = 'confessions'
            st.rerun()

        st.markdown("<div style='height:1px; background:#2a2a35; margin:12px 0;'></div>",
                    unsafe_allow_html=True)

        if st.button("→  Logout",                  use_container_width=True, key="sb_logout"):
            st.session_state.pop("vice_log_loaded", None)
            logout()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

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

    handle_reset_token_from_url()
    apply_custom_styles()

    if not st.session_state.authenticated:
        page = st.session_state.page
        if page == 'register':
            register_page()
        elif page == 'forgot':
            forgot_password_page()
        elif page == 'reset_password':
            reset_password_page()
        else:
            login_page()
    else:
        user    = st.session_state.get("user", {})
        user_id = user.get("id") if user else None

        if user_id:
            _bootstrap_db()
            _load_vice_log_from_db(user_id)

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
        elif feature == 'hotspots':
            from Pages.hotspots import hotspots_page
            hotspots_page()
        elif feature == 'confessions':
            from Pages.confession import confessions_page
            confessions_page()
        elif feature == 'do_or_drink':
            from Pages.do_or_drink import do_or_drink_page
            do_or_drink_page()
        else:
            from Pages.dashboard import stats_page
            stats_page()


if __name__ == "__main__":
    main()
