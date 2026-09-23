"""
app.py — Hidden main entry point.

Four tabs: Discover · Matches · Tonight (secret — unlocks at your first match) · Me.
New accounts see a short "How Hidden works" walkthrough (Pages/intro.py) before setup.
"""

from datetime import date

import streamlit as st

st.set_page_config(
    page_title="Hidden",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

import social_db
from matching import is_adult
from styles import apply_custom_styles, inject_page_css, reset_css_flag
from ui import inject_app_css

reset_css_flag()
apply_custom_styles()
inject_app_css()


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated") and st.session_state.get("user"))


# ─── NAVIGATION ──────────────────────────────────────────────────────────────

TABS = ["discover", "matches", "tonight", "me"]


def _on_nav():
    st.session_state.tab = st.session_state.nav
    if st.session_state.nav != "matches":
        st.session_state.pop("open_match", None)


def _nav(uid: int) -> str:
    """Brand + pill bar. Returns the selected tab."""
    from Pages.matches import needs_action
    from Pages.tonight import is_unlocked

    todo = needs_action(social_db.load_matches(uid))
    unlocked = is_unlocked(uid)
    labels = {
        "discover": "🔥 Discover",
        "matches":  "🔴 Matches" if todo else "💘 Matches",   # red dot = a match is waiting on you
        "tonight":  "🌙 Tonight" if unlocked else "🔒 ???",
        "me":       "👤 Me",
    }

    current = st.session_state.get("tab", "discover")
    if current not in TABS:
        current = "discover"
    # Clicks update `tab` via _on_nav before this runs; anything still out of sync
    # is a programmatic change (e.g. "Start the Q&A →"), so move the pill to match.
    if st.session_state.get("nav") != current:
        st.session_state.nav = current

    st.html('<div class="hd-brand" style="margin-bottom:10px;">HIDDEN</div>')
    st.segmented_control("Navigate", TABS, format_func=labels.get, key="nav", on_change=_on_nav,
                         label_visibility="collapsed", required=True, width="stretch")
    st.html("<div style='height:6px'></div>")
    return current


def _render_tab(tab: str):
    if tab == "matches":
        from Pages.matches import matches_page; matches_page()
    elif tab == "tonight":
        from Pages.tonight import tonight_page; tonight_page()
    elif tab == "me":
        from Pages.me import me_page; me_page()
    else:
        from Pages.discover import discover_page; discover_page()


# ─── AUTH PAGES ──────────────────────────────────────────────────────────────

def _render_auth():
    inject_page_css()
    # Handle reset token in URL before rendering auth pages
    try:
        from password_reset import handle_reset_token_from_url
        handle_reset_token_from_url()
    except Exception:
        pass

    page = st.session_state.get("page", "login")
    if page == "login":
        _login_page()
    elif page == "register":
        _register_page()
    elif page == "forgot":
        _forgot_page()
    elif page == "intro":
        from Pages.intro import intro_page
        intro_page(logged_in=False)
    elif page == "reset_password":
        try:
            from password_reset import reset_password_page
            reset_password_page()
        except Exception as e:
            st.error(f"Reset page error: {e}")
            st.session_state.page = "login"
            st.rerun()


def _login_page():
    st.html("""
<div style="max-width:400px; margin:60px auto 0; text-align:center; margin-bottom:32px;">
  <div class="hd-brand" style="font-size:72px; letter-spacing:8px;">HIDDEN</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft); margin-top:10px;">
    Meet people nearby who live like you do.
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-top:8px;">
    18+ · Blind Q&amp;A before you chat
  </div>
</div>
""")
    _, c, _ = st.columns([1, 2, 1])
    with c:
        username = st.text_input("Username or email", key="login_username", placeholder="your_username")
        password = st.text_input("Password", type="password", key="login_password")
        st.html("<div style='height:6px'></div>")
        if st.button("Log In →", type="primary", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Enter username and password.")
            else:
                try:
                    from auth import authenticate_user
                    success, user = authenticate_user(username.strip(), password)
                    if success and user:
                        st.session_state.authenticated = True
                        st.session_state.user          = user
                        st.session_state.tab           = "discover"
                        from auth import remember_session
                        remember_session()
                        st.rerun()
                    elif user == "locked":
                        st.error("Too many failed attempts. Try again in 10 minutes.")
                    else:
                        st.error("Wrong username or password.")
                except Exception as e:
                    st.error(f"Login error: {e}")
        st.html("<div style='height:8px'></div>")
        if st.button("New here? Create account", use_container_width=True, key="go_register"):
            st.session_state.page = "register"; st.rerun()
        if st.button("Forgot password", use_container_width=True, key="go_forgot"):
            st.session_state.page = "forgot"; st.rerun()
        if st.button("How does Hidden work?", use_container_width=True, key="go_intro", type="tertiary"):
            from Pages.intro import open_intro
            open_intro("login", logged_in=False)


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
        birthday = st.date_input("Birthday", value=None, key="reg_bd", format="DD/MM/YYYY",
                                 min_value=date(date.today().year - 100, 1, 1), max_value=date.today(),
                                 help="Hidden is 18+ only.")
        if st.button("Create Account →", type="primary", use_container_width=True, key="reg_btn"):
            from auth import validate_password, validate_email as _ve, hash_password
            import database as db
            import secrets as _secrets

            ok_pw, pw_msg = validate_password(pw)
            if not username.strip():
                st.error("Enter a username.")
            elif not _ve(email.strip()):
                st.error("That email doesn't look right.")
            elif not ok_pw:
                st.error(pw_msg)
            elif pw != pw2:
                st.error("Passwords don't match.")
            elif not birthday:
                st.error("Add your birthday.")
            elif not is_adult(birthday):
                st.error("Sorry — Hidden is for people 18 and over.")
            else:
                try:
                    # create_user now returns (uid, status_code)
                    uid, status = db.create_user(
                        username.strip(), email.strip(), hash_password(pw)
                    )
                    if status == db.CREATE_USER_OK:
                        user  = db.get_user_by_id(uid)
                        token = _secrets.token_urlsafe(32)
                        try:
                            created = db.create_session_token(uid, token)
                        except Exception:
                            created = False
                        if not created:
                            social_db.save_profile(uid, {"birthdate": birthday})
                            st.success("Account created — please log in.")
                            st.stop()
                        social_db.save_profile(uid, {"birthdate": birthday})
                        st.session_state.session_token = token
                        st.session_state.authenticated = True
                        st.session_state.user          = user
                        st.session_state.tab           = "intro"      # walkthrough, then setup
                        st.session_state._intro_return = "setup"
                        from auth import remember_session
                        remember_session()
                        st.rerun()
                    elif status == db.CREATE_USER_DUP_USERNAME:
                        st.error("That username is already taken — try another.")
                    elif status == db.CREATE_USER_DUP_EMAIL:
                        st.error("An account with that email already exists. Try logging in.")
                    else:
                        st.error("Registration failed — please try again.")
                except Exception as e:
                    st.error(f"Registration error: {e}")

        if st.button("← Back to login", use_container_width=True, key="reg_back"):
            st.session_state.page = "login"; st.rerun()


def _forgot_page():
    inject_page_css()
    # Delegate entirely to password_reset.py which has the real implementation
    try:
        from password_reset import forgot_password_page
        forgot_password_page()
    except Exception as e:
        st.error(f"Password reset error: {e}")
        if st.button("← Back to login"):
            st.session_state.page = "login"
            st.rerun()


def _bootstrap_db():
    if st.session_state.get("_db_bootstrapped"):
        return
    try:
        import database as db
        probe = db.create_connection()
        if not probe:
            return  # database unreachable — retry setup on the next run
        probe.close()
        db.ensure_tables()
        _ensure_password_resets_table()
        social_db.ensure_social_tables()
        st.session_state["_db_bootstrapped"] = True
    except Exception:
        pass


def _ensure_password_resets_table():
    """Create password_resets table if it doesn't exist yet."""
    try:
        import database as db
        conn = db.create_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    email      VARCHAR(255) NOT NULL PRIMARY KEY,
                    token      VARCHAR(128) NOT NULL UNIQUE,
                    expires_at DATETIME     NOT NULL,
                    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            conn.commit()
            cur.close()
        finally:
            conn.close()
    except Exception:
        pass


def main():
    _bootstrap_db()

    from auth import restore_session, flush_session_cookie
    if not is_authenticated():
        restore_session()        # stay logged in across refreshes
    _main()
    flush_session_cookie()       # skipped when _main() reruns, so it waits for a run that renders


def _main():
    from auth import forget_session
    if not is_authenticated():
        _render_auth()
        return

    import time as _t
    _now = _t.time()
    if _now - st.session_state.get("_session_checked_at", 0) > 300:
        try:
            from auth import check_session_valid
            if not check_session_valid():
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.session_state["_restore_tried"] = True
                forget_session()
                st.warning("Your session has ended. Please log in again.")
                _render_auth()
                return
            st.session_state["_session_checked_at"] = _now
        except Exception:
            pass

    uid = st.session_state.user["id"]

    # The quiz is a full-screen flow (from setup, Discover or Me)
    if st.session_state.get("tab") == "quiz":
        done = st.session_state.get("wwyd_phase") == "result"
        if st.button("Done — show me matches →" if done else "← Back to Hidden",
                     key="hd_quiz_exit", type="primary" if done else "secondary"):
            st.session_state.tab = st.session_state.pop("_quiz_return", "discover")
            st.session_state.pop("disc_queue", None)   # re-rank with the new answers
            st.session_state.pop("my_quiz", None)
            st.rerun()
        from Pages.what_would_you_do import what_would_you_do_page
        what_would_you_do_page()
        return

    if st.session_state.get("tab") == "intro":
        from Pages.intro import intro_page
        intro_page()
        return

    if st.session_state.get("tab") == "quiz_offer":
        from Pages.profile_form import quiz_offer_page
        quiz_offer_page()
        return

    # No complete profile yet (new user, or existing user from before matching) → setup
    profile = social_db.get_profile(uid)
    if not social_db.profile_complete(profile):
        st.html('<div class="hd-brand" style="margin-bottom:10px;">HIDDEN</div>')
        from Pages.profile_form import setup_page
        setup_page()
        return
    if not is_adult(profile["birthdate"]):
        st.error("Hidden is for people 18 and over.")
        return

    _render_tab(_nav(uid))


if __name__ == "__main__":
    main()
