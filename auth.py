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
        import social_db
        if social_db.is_banned(user["id"]):
            return False, "banned"
        # Session validation fails closed, so login must fail if the token
        # can't be stored — otherwise the user is kicked out on the next check.
        token = secrets.token_urlsafe(32)
        try:
            created = db.create_session_token(user["id"], token)
        except Exception:
            created = False
        if not created:
            return False, None
        st.session_state["session_token"] = token
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
    """Fail closed: a logged-in user must hold a valid, unexpired session token."""
    user  = st.session_state.get("user")
    token = st.session_state.get("session_token")
    if not user or not token:
        return False
    try:
        import database as db
        return db.verify_session_token(user["id"], token)
    except Exception:
        return False


# ─── STAY LOGGED IN ───────────────────────────────────────────────────────────
# The session token also lives in a browser cookie, so a refresh or a reopened
# tab picks the session back up instead of landing on the login page.

SESSION_COOKIE = "hd_session"
_COOKIE_MAX_AGE = 30 * 24 * 3600   # matches session_tokens.expires_at


def remember_session():
    """Queue the cookie write; flush_session_cookie() does it on the next render."""
    st.session_state["_cookie_set"] = st.session_state.get("session_token")


def forget_session():
    st.session_state["_cookie_clear"] = True


def remember_flag(name: str):
    """Remember a one-off (like "already celebrated") in this browser for a year."""
    st.session_state.setdefault("_cookie_flags", []).append(name)


def has_flag(name: str) -> bool:
    try:
        return bool(st.context.cookies.get(name))
    except Exception:
        return False


def _cookie_js(name: str, value: str, age: int) -> str:
    return ("document.cookie = '" + name + "=" + value + "; Max-Age=" + str(age)
            + "; Path=/; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');")


def flush_session_cookie():
    """Write or clear cookies. Call once per run, from a run that doesn't rerun right away."""
    token = st.session_state.pop("_cookie_set", None)
    clear = st.session_state.pop("_cookie_clear", False)
    flags = st.session_state.pop("_cookie_flags", [])
    js = []
    if token and re.fullmatch(r"[A-Za-z0-9_-]+", token):
        js.append(_cookie_js(SESSION_COOKIE, token, _COOKIE_MAX_AGE))
    elif clear:
        js.append(_cookie_js(SESSION_COOKIE, "", 0))
    js += [_cookie_js(f, "1", 365 * 24 * 3600) for f in flags if re.fullmatch(r"[A-Za-z0-9_]+", f)]
    if js:
        st.html("<script>" + "".join(js) + "</script>", unsafe_allow_javascript=True, width=1)


def restore_session() -> bool:
    """Log back in from the cookie, once per browser session. True if it worked."""
    if st.session_state.get("_restore_tried"):
        return False
    st.session_state["_restore_tried"] = True
    try:
        token = st.context.cookies.get(SESSION_COOKIE)
    except Exception:
        token = None
    if not token:
        return False
    import database as db
    uid = db.user_id_for_session_token(token)
    if uid == 0:            # expired or logged out elsewhere
        forget_session()
        return False
    user = db.get_user_by_id(uid) if uid else None
    if not user:
        return False
    import social_db
    if social_db.is_banned(uid):
        forget_session()
        return False
    st.session_state.authenticated = True
    st.session_state.user = user
    st.session_state.session_token = token
    st.session_state.setdefault("tab", "discover")
    import time
    st.session_state["_session_checked_at"] = time.time()   # just verified it
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


def logout():
    """End the session server-side and clear local state."""
    try:
        import database as db
        token = st.session_state.get("session_token")
        if token:
            db.invalidate_session_token(token)
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state["_restore_tried"] = True   # don't log straight back in from the old cookie
    forget_session()
    st.rerun()
