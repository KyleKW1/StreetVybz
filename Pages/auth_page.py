"""
Pages/auth_page.py — uses st.html() for custom HTML (Streamlit Cloud safe)
"""
import streamlit as st
from auth import authenticate_user, register_user, validate_email


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
  <div class="auth-wordmark">VICE<span>VAULT</span></div>
  <p class="auth-tagline">Welcome back — no judgement here</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Sign in</div>
</div>
""")
        username = st.text_input("Username", placeholder="Your username", key="login_username")
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
  <div class="auth-wordmark">VICE<span>VAULT</span></div>
  <p class="auth-tagline">Let's get you set up</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Create account</div>
</div>
""")
        username         = st.text_input("Username", placeholder="At least 3 characters", key="reg_username")
        email            = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
        password         = st.text_input("Password", type="password", placeholder="At least 6 characters", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", placeholder="Same again", key="reg_confirm")

        st.html("<div style='height:8px'></div>")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Create Account →", use_container_width=True, type="primary", key="register_btn"):
                if not username or not email or not password:
                    st.error("All fields are required.")
                elif len(username) < 3:
                    st.error("Username needs at least 3 characters.")
                elif not validate_email(email):
                    st.error("That email doesn't look right.")
                elif len(password) < 6:
                    st.error("Password needs at least 6 characters.")
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
