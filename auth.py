"""
auth.py — Core authentication functions + Auth page UI.
"""

import re
import secrets
import streamlit as st


# ─── CORE AUTH FUNCTIONS ──────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters."
    return True, ""


def validate_username(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_]{3,32}$", username.strip()))


def authenticate_user(username: str, password: str):
    """
    Returns (True, user_dict) on success.
    Returns (False, "locked") if rate-limited.
    Returns (False, None) on bad credentials.
    """
    import database as db
    import time

    key    = f"_login_fails_{username.lower()}"
    key_ts = f"_login_fails_ts_{username.lower()}"
    now    = time.time()

    fails     = st.session_state.get(key, 0)
    last_fail = st.session_state.get(key_ts, 0)

    if now - last_fail > 600:
        fails = 0

    if fails >= 5:
        return False, "locked"

    user = db.authenticate_user(username.strip(), password)
    if user:
        st.session_state[key] = 0
        try:
            token = secrets.token_urlsafe(32)
            db.create_session_token(user["id"], token)
            st.session_state["session_token"] = token
        except Exception:
            pass
        try:
            db.update_last_login(user["id"])
        except Exception:
            pass
        return True, user

    st.session_state[key]    = fails + 1
    st.session_state[key_ts] = now
    return False, None


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    import database as db

    uid, status = db.create_user(username.strip(), email.strip(), hash_password(password))

    if status == db.CREATE_USER_OK:
        return True, "Account created successfully."
    elif status == db.CREATE_USER_DUP_USERNAME:
        return False, "That username is already taken — try another."
    elif status == db.CREATE_USER_DUP_EMAIL:
        return False, "An account with that email already exists. Try logging in."
    elif status == db.CREATE_USER_DUP_UNKNOWN:
        return False, "Username or email already taken."
    else:
        return False, "Registration failed — please try again in a moment."


def check_session_valid() -> bool:
    """Returns True if the current session token is still valid."""
    user  = st.session_state.get("user")
    token = st.session_state.get("session_token")
    if not user or not token:
        return True
    try:
        import database as db
        return db.verify_session_token(user["id"], token)
    except Exception:
        return True


# ─── AUTH PAGE UI ─────────────────────────────────────────────────────────────

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --card:#18181d; --border:#2a2a35;
  --lime:#c6ff00; --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}
.auth-card {
  background:var(--card);
  border:1px solid var(--border);
  border-top:2px solid var(--lime);
  border-radius:4px;
  padding:32px 28px 24px;
  animation:slideUp 0.35s cubic-bezier(0.22,1,0.36,1) both;
}
@keyframes slideUp {
  from { opacity:0; transform:translateY(14px); }
  to   { opacity:1; transform:translateY(0); }
}
.auth-wordmark {
  font-family:'Bebas Neue',sans-serif;
  font-size:48px; letter-spacing:4px; line-height:1;
  color:var(--text); margin-bottom:4px; text-align:center;
}
.auth-wordmark span { color:var(--lime); }
.auth-tagline {
  font-family:'Space Mono',monospace; font-size:10px;
  color:var(--muted); letter-spacing:2px; text-transform:uppercase;
  margin:0; text-align:center;
}
.auth-divider { height:1px; background:var(--border); margin:20px 0 16px; }
.auth-section-label {
  font-family:'Space Mono',monospace; font-size:9px;
  text-transform:uppercase; letter-spacing:3px; color:var(--lime); margin-bottom:4px;
}
.auth-hint {
  font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
  text-align:center; margin-top:12px;
}
</style>
"""


def inject_auth_css():
    st.html(CSS)


def login_page():
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.html("""
<div class="auth-card">
  <div class="auth-wordmark">HID<span>DEN</span></div>
  <p class="auth-tagline">Welcome back — no judgement here</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Sign in</div>
</div>
""")
        username = st.text_input("Username or email", placeholder="Your username or email", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Your password", key="login_password")

        st.html("<div style='height:8px'></div>")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Sign In →", use_container_width=True, type="primary", key="login_btn"):
                if username and password:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("You're in.")
                        st.balloons()
                        st.rerun()
                    elif user == "locked":
                        st.error("Too many failed attempts. Try again in a few minutes.")
                    else:
                        st.error("Those credentials don't match.")
                else:
                    st.warning("Fill in both fields.")
        with col_b:
            if st.button("Create Account", use_container_width=True, type="secondary", key="go_register"):
                st.session_state.page = 'register'
                st.rerun()

        st.html("<div style='height:4px'></div>")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Forgot password?", use_container_width=True, type="secondary", key="go_forgot"):
                st.session_state.page = 'forgot'
                st.rerun()

        st.html('<p class="auth-hint">New here? Hit <strong>Create Account</strong> above.</p>')


def register_page():
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.html("""
<div class="auth-card">
  <div class="auth-wordmark">HID<span>DEN</span></div>
  <p class="auth-tagline">Let's get you set up</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Create account</div>
</div>
""")
        username         = st.text_input("Username", placeholder="Letters, numbers, underscores (3–32)", key="reg_username")
        email            = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
        password         = st.text_input("Password", type="password", placeholder="At least 8 characters", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", placeholder="Same again", key="reg_confirm")

        st.html("<div style='height:8px'></div>")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Create Account →", use_container_width=True, type="primary", key="register_btn"):
                ok_pw, pw_msg = validate_password(password)
                if not username or not email or not password:
                    st.error("All fields are required.")
                elif not validate_username(username):
                    st.error("Username must be 3–32 characters: letters, numbers, underscores only.")
                elif not validate_email(email):
                    st.error("That email doesn't look right.")
                elif not ok_pw:
                    st.error(pw_msg)
                elif password != confirm_password:
                    st.error("Passwords don't match.")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(f"You're all set! {message}")
                        st.balloons()
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)
        with col_b:
            if st.button("← Back", use_container_width=True, type="secondary", key="back_login"):
                st.session_state.page = 'login'
                st.rerun()

        st.html('<p class="auth-hint">Already have an account? Sign in on the previous screen.</p>')
