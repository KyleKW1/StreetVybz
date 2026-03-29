"""
Pages/auth_page.py — ViceVault rebrand
"""
import streamlit as st
from auth import authenticate_user, register_user, validate_email


def inject_auth_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --card:#18181d; --border:#2a2a35;
  --lime:#c6ff00; --magenta:#ff2d78; --cyan:#00e5ff;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}
.stApp {
  background: var(--bg) !important;
  min-height: 100vh;
}
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container {
  padding-top:3.5rem !important; max-width:860px !important;
}

/* Card */
.auth-card {
  background:var(--card);
  border:1px solid var(--border);
  border-top:2px solid var(--lime);
  border-radius:4px;
  padding:40px 36px 32px;
  margin:0 auto;
  animation:slideUp 0.35s cubic-bezier(0.22,1,0.36,1) both;
}
@keyframes slideUp {
  from { opacity:0; transform:translateY(16px); }
  to   { opacity:1; transform:translateY(0); }
}

/* Wordmark */
.auth-wordmark {
  font-family:'Bebas Neue',sans-serif;
  font-size:52px; letter-spacing:4px; line-height:1;
  color:var(--text); margin-bottom:4px;
}
.auth-wordmark em { font-style:normal; color:var(--lime); }
.auth-tagline {
  font-family:'Space Mono',monospace; font-size:10px;
  color:var(--muted); letter-spacing:2px; text-transform:uppercase; margin:0;
}
.auth-divider { height:1px; background:var(--border); margin:22px 0 20px; }
.auth-section-label {
  font-family:'Space Mono',monospace; font-size:9px; font-weight:700;
  text-transform:uppercase; letter-spacing:3px; color:var(--lime); margin-bottom:18px;
}
.auth-hint {
  font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
  text-align:center; margin-top:14px;
}

/* Inputs */
.stTextInput > div > div > input {
  background:var(--bg) !important; border:1px solid var(--border) !important;
  border-radius:3px !important; padding:11px 14px !important;
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
  color:var(--text) !important; transition:border-color 0.15s,box-shadow 0.15s !important;
}
.stTextInput > div > div > input:focus {
  border-color:var(--lime) !important;
  box-shadow:0 0 0 2px rgba(198,255,0,0.12) !important; outline:none !important;
}
.stTextInput > div > div > input::placeholder { color:var(--muted) !important; }
.stTextInput label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important; color:var(--soft) !important;
}

/* Buttons */
.stButton > button {
  font-family:'Space Mono',monospace !important; font-weight:700 !important;
  font-size:10px !important; letter-spacing:1.5px !important; text-transform:uppercase !important;
  border-radius:3px !important; padding:11px 18px !important;
  transition:all 0.15s ease !important; box-shadow:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--lime) !important; color:#0a0a0b !important; border:none !important;
}
.stButton > button[kind="primary"]:hover {
  background:#d4ff1a !important; box-shadow:0 0 20px rgba(198,255,0,0.2) !important;
  transform:none !important;
}
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"][disabled] {
  background:var(--border) !important; color:var(--muted) !important;
  border:none !important; box-shadow:none !important; transform:none !important;
}
.stButton > button[kind="secondary"] {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
  background:var(--card) !important; border-color:var(--soft) !important;
  color:var(--text) !important; box-shadow:none !important; transform:none !important;
}

/* Alerts */
.stAlert {
  border-radius:3px !important; font-family:'DM Sans',sans-serif !important;
  font-size:13px !important; font-weight:400 !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background:#0d0d10 !important; border-right:1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color:#c8c8d8 !important; }
section[data-testid="stSidebar"] .stButton > button {
  background:transparent !important; border:1px solid var(--border) !important;
  color:#c8c8d8 !important; border-radius:4px !important;
  font-family:'Space Mono',monospace !important; font-size:11px !important;
  font-weight:600 !important; text-transform:uppercase !important; letter-spacing:1px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background:#1a1a20 !important; border-color:var(--lime) !important;
  color:var(--lime) !important; box-shadow:none !important; transform:none !important;
}

#MainMenu { visibility:hidden; }
footer    { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


def login_page():
    inject_auth_css()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
<div class="auth-card">
  <div style="text-align:center; margin-bottom:4px;">
    <div class="auth-wordmark">VICE<em>VAULT</em></div>
    <p class="auth-tagline">Welcome back — no judgement here</p>
  </div>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Sign in</div>
</div>
""", unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Your username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Your password", key="login_password")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

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

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Forgot password?", use_container_width=True, type="secondary", key="go_forgot"):
                st.session_state.page = 'forgot'
                st.rerun()

        st.markdown(
            '<p class="auth-hint">New here? Hit <strong>Create Account</strong> above.</p>',
            unsafe_allow_html=True
        )


def register_page():
    inject_auth_css()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
<div class="auth-card">
  <div style="text-align:center; margin-bottom:4px;">
    <div class="auth-wordmark">VICE<em>VAULT</em></div>
    <p class="auth-tagline">Let's get you set up</p>
  </div>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Create account</div>
</div>
""", unsafe_allow_html=True)

        username         = st.text_input("Username", placeholder="At least 3 characters", key="reg_username")
        email            = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
        password         = st.text_input("Password", type="password", placeholder="At least 6 characters", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", placeholder="Same again", key="reg_confirm")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

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

        st.markdown(
            '<p class="auth-hint">Already have an account? Sign in on the previous screen.</p>',
            unsafe_allow_html=True
        )
