"""
app.py — ViceVault main entry point.
"""

import streamlit as st
from styles import apply_custom_styles, inject_page_css, reset_css_flag

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ViceVault",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Reset CSS flag so styles always reinject on every full rerun
reset_css_flag()
apply_custom_styles()

# ─── FLOATING QUICK LOG BUTTON ────────────────────────────────────────────────

def _inject_floating_log_btn():
    st.html("""
<style>
#vv-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--lime, #c6ff00);
  color: #0a0a0b;
  font-size: 26px;
  line-height: 52px;
  text-align: center;
  cursor: pointer;
  box-shadow: 0 4px 18px rgba(198,255,0,0.35);
  border: none;
  font-family: 'Space Mono', monospace;
  transition: transform 0.15s, box-shadow 0.15s;
  user-select: none;
}
#vv-fab:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(198,255,0,0.5); }
#vv-fab:active { transform: scale(0.96); }
</style>
<button id="vv-fab" title="Quick Log" onclick="(function(){
  const url = new URL(window.location.href);
  url.searchParams.set('vv_action','quick_log');
  window.location.href = url.toString();
})()">＋</button>
""")


# ─── AUTH HELPERS ─────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated") and st.session_state.get("user"))


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


# ─── QUIZ PRE-WARM ────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def _prewarm_quiz():
    try:
        import requests, random
        subs = ["relationship_advice", "confession", "tifu", "TrueOffMyChest"]
        sub  = random.choice(subs)
        r    = requests.get(
            f"https://www.reddit.com/r/{sub}/hot.json?limit=10",
            headers={"User-Agent": "ViceVault/1.0"},
            timeout=5,
        )
        if r.ok:
            return [p["data"] for p in r.json()["data"]["children"] if not p["data"].get("over_18")]
    except Exception:
        pass
    return []


# ─── NAVIGATION SIDEBAR ───────────────────────────────────────────────────────

NAV_SECTIONS = [
    {
        "label": "Vault",
        "items": [
            ("stats",     "◈  Dashboard"),
            ("log",       "＋  Log Session"),
            ("history",   "▤  History"),
            ("analytics", "⌬  Analytics"),
        ],
    },
    {
        "label": "Features",
        "items": [
            ("rbtl",      "⚡  Read Between The Lines"),
            ("hotspots",  "📍  Where To Go Tonight"),
            ("dod",       "🃏  Do or Drink"),
            ("confess",   "◎  Confessions"),
        ],
    },
    {
        "label": "Account",
        "items": [
            ("profile",   "⬡  Profile"),
            ("settings",  "◧  Settings"),
        ],
    },
]

def _render_sidebar():
    with st.sidebar:
        user = st.session_state.get("user", {})
        uname = user.get("username", "—")
        initials = uname[:2].upper()

        st.html(f"""
<div style="padding:16px 0 20px; border-bottom:1px solid var(--border); margin-bottom:20px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:26px; color:var(--lime);
              letter-spacing:3px; line-height:1;">VICEVAULT</div>
  <div style="display:flex; align-items:center; gap:8px; margin-top:10px;">
    <div style="width:28px; height:28px; border-radius:50%; background:var(--lime);
                display:flex; align-items:center; justify-content:center; flex-shrink:0;">
      <span style="font-family:'Bebas Neue',sans-serif; font-size:12px; color:#0a0a0b;">
        {initials}
      </span>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft);
                letter-spacing:1px; text-transform:uppercase;">{uname}</div>
  </div>
</div>
""")

        selected = st.session_state.get("selected_feature", "stats")

        for section in NAV_SECTIONS:
            st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:7px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin:16px 0 6px;">{section['label']}</div>
""")
            for key, label in section["items"]:
                is_active = selected == key
                btn_type  = "primary" if is_active else "secondary"
                if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                    st.session_state.selected_feature = key
                    if key != "onboarding":
                        st.session_state.onboarding_done = True
                    st.rerun()

        st.html("<div style='height:24px'></div>")
        if st.button("⎋  Logout", use_container_width=True, key="nav_logout"):
            logout()


# ─── FEATURE ROUTER ───────────────────────────────────────────────────────────

def _render_feature(feature: str):
    if feature in ("stats", "dashboard"):
        from Pages.dashboard import stats_page
        stats_page()

    elif feature == "log":
        from Pages.dashboard import log_session_page
        log_session_page()

    elif feature == "history":
        from Pages.dashboard import history_page
        history_page()

    elif feature == "analytics":
        from Pages.analytics import analytics_page
        analytics_page()

    elif feature == "rbtl":
        from Pages.what_would_you_do import what_would_you_do_page
        what_would_you_do_page()

    elif feature == "hotspots":
        try:
            from Pages.hotspots import hotspots_page
            hotspots_page()
        except ImportError:
            inject_page_css()
            st.html("""
<div style="padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted);">COMING SOON</div>
</div>
""")

    elif feature == "dod":
        from Pages.do_or_drink_ui import render_setup, render_generating, render_game, render_game_over
        from Pages.do_or_drink_core import init_state
        init_state()
        phase = st.session_state.get("dod_phase", "setup")
        if phase == "setup":        render_setup()
        elif phase == "generating": render_generating()
        elif phase == "game":       render_game()
        elif phase == "gameover":   render_game_over()

    elif feature == "confess":
        from Pages.confession import confessions_page
        confessions_page()

    elif feature == "profile":
        from Pages.profile import profile_page
        profile_page()

    elif feature == "settings":
        from Pages.settings import settings_page
        settings_page()

    elif feature == "onboarding":
        from Pages.onboarding import onboarding_page
        onboarding_page()

    elif feature == "quick_log":
        from Pages.dashboard import log_session_page
        log_session_page()

    else:
        from Pages.dashboard import stats_page
        stats_page()


# ─── AUTH PAGES ───────────────────────────────────────────────────────────────

def _render_auth():
    inject_page_css()
    page = st.session_state.get("page", "login")
    if page == "login":
        _login_page()
    elif page == "register":
        _register_page()
    elif page == "forgot":
        _forgot_page()


def _login_page():
    st.html("""
<div style="max-width:400px; margin:60px auto 0;">
  <div style="text-align:center; margin-bottom:32px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:60px; color:var(--lime);
                letter-spacing:4px; line-height:0.9;">VICE<br>VAULT</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-top:10px;">
      Your vice. Your data. Private.
    </div>
  </div>
</div>
""")
    _, c, _ = st.columns([1, 2, 1])
    with c:
        username = st.text_input("Username", key="login_username", placeholder="your_username")
        password = st.text_input("Password", type="password", key="login_password")
        st.html("<div style='height:6px'></div>")
        if st.button("Log In →", type="primary", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Enter username and password.")
            else:
                try:
                    import database as db
                    user = db.authenticate_user(username.strip(), password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user          = user
                        st.session_state.vice_log      = db.load_vice_log(user["id"])
                        st.session_state.selected_feature = "stats"
                        try:
                            _prewarm_quiz()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")
                except Exception as e:
                    st.error(f"Login error: {e}")

        st.html("<div style='height:8px'></div>")
        col_r, col_f = st.columns(2)
        with col_r:
            if st.button("Create account", use_container_width=True, key="go_register"):
                st.session_state.page = "register"; st.rerun()
        with col_f:
            if st.button("Forgot password", use_container_width=True, key="go_forgot"):
                st.session_state.page = "forgot"; st.rerun()


def _register_page():
    st.html("""
<div style="max-width:400px; margin:60px auto 0; text-align:center; margin-bottom:32px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">CREATE ACCOUNT</div>
</div>
""")
    _, c, _ = st.columns([1, 2, 1])
    with c:
        username = st.text_input("Username",         key="reg_username")
        email    = st.text_input("Email",            key="reg_email")
        pw       = st.text_input("Password",         type="password", key="reg_pw")
        pw2      = st.text_input("Confirm password", type="password", key="reg_pw2")
        if st.button("Create Account →", type="primary", use_container_width=True, key="reg_btn"):
            if pw != pw2:
                st.error("Passwords don't match.")
            elif len(pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif not username.strip():
                st.error("Enter a username.")
            else:
                try:
                    import database as db
                    uid = db.create_user(username.strip(), email.strip(), pw)
                    if uid:
                        user = db.get_user_by_id(uid)
                        st.session_state.authenticated    = True
                        st.session_state.user             = user
                        st.session_state.vice_log         = []
                        st.session_state.selected_feature = "onboarding"
                        st.rerun()
                    else:
                        st.error("Username or email already taken.")
                except Exception as e:
                    st.error(f"Registration error: {e}")
        if st.button("← Back to login", use_container_width=True, key="reg_back"):
            st.session_state.page = "login"; st.rerun()


def _forgot_page():
    inject_page_css()
    st.html("""
<div style="max-width:400px; margin:60px auto 0; text-align:center; margin-bottom:32px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">RESET PASSWORD</div>
</div>
""")
    _, c, _ = st.columns([1, 2, 1])
    with c:
        email = st.text_input("Email address", key="forgot_email")
        if st.button("Send reset link →", type="primary", use_container_width=True, key="forgot_btn"):
            st.success("If that email is registered, a reset link is on its way.")
        if st.button("← Back to login", use_container_width=True, key="forgot_back"):
            st.session_state.page = "login"; st.rerun()


# ─── BOOTSTRAP ────────────────────────────────────────────────────────────────

def _bootstrap_db():
    try:
        import database as db
        db.ensure_tables()
    except Exception:
        pass


def _handle_query_params():
    params = st.query_params
    if params.get("vv_action") == "quick_log":
        st.query_params.clear()
        st.session_state.selected_feature = "log"
        st.rerun()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    _bootstrap_db()
    _handle_query_params()

    if not is_authenticated():
        _render_auth()
        return

    st.session_state.setdefault("selected_feature", "stats")
    st.session_state.setdefault("onboarding_done", False)

    from Pages.onboarding import should_show_onboarding
    if should_show_onboarding() and not st.session_state.onboarding_done:
        _render_sidebar()
        _inject_floating_log_btn()
        _render_feature("onboarding")
        return

    _render_sidebar()
    _inject_floating_log_btn()
    _render_feature(st.session_state.selected_feature)


if __name__ == "__main__":
    main()
