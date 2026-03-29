import streamlit as st
from auth import authenticate_user, register_user, validate_email


def inject_auth_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,300;0,600;0,700;1,300;1,600&family=Nunito:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>

:root {
    --sun:          #f9f3e8;
    --petal:        #fff8f0;
    --clay:         #c96a3a;
    --clay-soft:    rgba(201,106,58,0.11);
    --clay-border:  rgba(201,106,58,0.30);
    --sand:         #8c7355;
    --dusk:         #3d3530;
    --mist:         #a89880;
    --rule:         #e8ddd0;
    --white:        #fffdf9;
}

.stApp {
    background: radial-gradient(ellipse at 25% 15%, #fde8d0 0%, #f9f0e4 45%, #f0e6d4 100%) !important;
    min-height: 100vh;
}
section[data-testid="stMain"] { background: transparent !important; }
section.main .block-container {
    padding-top: 3.5rem !important;
    max-width: 860px !important;
}

/* Soft ambient blobs */
.stApp::before {
    content: '';
    position: fixed; top: -140px; right: -140px;
    width: 460px; height: 460px; border-radius: 50%;
    background: radial-gradient(circle, rgba(201,106,58,0.09) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed; bottom: -100px; left: -80px;
    width: 360px; height: 360px; border-radius: 50%;
    background: radial-gradient(circle, rgba(140,115,85,0.07) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
}

/* Card */
.auth-card {
    background: var(--white);
    border-radius: 22px;
    box-shadow:
        0 1px 3px rgba(61,53,48,0.05),
        0 8px 28px rgba(61,53,48,0.09),
        0 36px 72px rgba(61,53,48,0.07);
    padding: 44px 40px 36px;
    margin: 0 auto;
    position: relative;
    overflow: hidden;
    animation: slideUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
.auth-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #f0b07a, var(--clay), #a8522a);
    border-radius: 22px 22px 0 0;
}

/* Decorative dots */
.auth-dots {
    position: absolute; top: 20px; right: 22px;
    display: flex; gap: 5px; opacity: 0.22;
}
.auth-dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--clay);
}

/* Wordmark */
.auth-wordmark {
    font-family: 'Fraunces', serif;
    font-size: 44px;
    font-weight: 700;
    color: var(--dusk);
    letter-spacing: -1.5px;
    line-height: 1;
    margin-bottom: 5px;
}
.auth-wordmark em {
    font-style: italic;
    color: var(--clay);
}
.auth-tagline {
    font-family: 'Nunito', sans-serif;
    font-size: 13.5px;
    color: var(--mist);
    font-weight: 500;
    margin: 0;
}
.auth-divider {
    height: 1px; background: var(--rule); margin: 22px 0 20px;
}
.auth-section-label {
    font-family: 'Nunito', sans-serif;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 2px;
    color: var(--clay); margin-bottom: 18px;
}
.auth-hint {
    font-family: 'Nunito', sans-serif;
    font-size: 12px; color: var(--mist);
    text-align: center; margin-top: 14px;
}

/* Input fields */
.stTextInput > div > div > input {
    background: var(--sun) !important;
    border: 1.5px solid var(--rule) !important;
    border-radius: 11px !important;
    padding: 11px 14px !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 14px !important; font-weight: 500 !important;
    color: var(--dusk) !important;
    transition: border-color 0.18s, box-shadow 0.18s, background 0.18s !important;
    box-shadow: none !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--clay) !important;
    background: var(--white) !important;
    box-shadow: 0 0 0 3px var(--clay-soft) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: var(--mist) !important; }
.stTextInput label {
    font-family: 'Nunito', sans-serif !important;
    font-size: 12.5px !important; font-weight: 700 !important;
    color: var(--sand) !important;
    text-transform: none !important; letter-spacing: 0 !important;
}

/* Buttons */
.stButton > button {
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important; font-size: 13.5px !important;
    letter-spacing: 0.2px !important; text-transform: none !important;
    border-radius: 11px !important; padding: 11px 18px !important;
    transition: all 0.18s ease !important;
    box-shadow: none !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #d4733f, var(--clay)) !important;
    color: white !important; border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #dc7a45, #c96a3a) !important;
    box-shadow: 0 4px 18px rgba(201,106,58,0.38) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"][disabled] {
    background: var(--rule) !important; color: var(--mist) !important;
    border: none !important; box-shadow: none !important; transform: none !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--sand) !important;
    border: 1.5px solid var(--rule) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--sun) !important;
    border-color: var(--clay-border) !important;
    color: var(--clay) !important;
    box-shadow: none !important; transform: none !important;
}

/* Alerts */
.stAlert {
    border-radius: 11px !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 13px !important; font-weight: 500 !important;
}

/* Sidebar — keep dark */
section[data-testid="stSidebar"] {
    background: #121110 !important;
    border-right: 1px solid #1e1c1a !important;
}
section[data-testid="stSidebar"] * { color: #c8c2b8 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid #2a2826 !important; color: #c8c2b8 !important;
    border-radius: 6px !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 12.5px !important; font-weight: 600 !important;
    text-transform: none !important; letter-spacing: 0 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #1a1714 !important; border-color: #c96a3a !important;
    color: #faf8f3 !important; box-shadow: none !important; transform: none !important;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def login_page():
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="auth-card">
                <div class="auth-dots">
                    <div class="auth-dot"></div>
                    <div class="auth-dot"></div>
                    <div class="auth-dot"></div>
                </div>
                <div style="text-align:center; margin-bottom:4px;">
                    <div class="auth-wordmark">Vice<em>Vault</em></div>
                    <p class="auth-tagline">Welcome back — good to see you again ✦</p>
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
                        st.success("You're in! Welcome back.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Those credentials don't match. Try again?")
                else:
                    st.warning("Please fill in both fields.")
        with col_b:
            if st.button("Create Account", use_container_width=True, type="secondary", key="go_register"):
                st.session_state.page = 'register'
                st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            if st.button("Forgot password or username?", use_container_width=True, type="secondary", key="go_forgot"):
                st.session_state.page = 'forgot'
                st.rerun()

        st.markdown(
            '<p class="auth-hint">New here? Hit <strong>Create Account</strong> above — it only takes a moment.</p>',
            unsafe_allow_html=True
        )


def register_page():
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="auth-card">
                <div class="auth-dots">
                    <div class="auth-dot"></div>
                    <div class="auth-dot"></div>
                    <div class="auth-dot"></div>
                </div>
                <div style="text-align:center; margin-bottom:4px;">
                    <div class="auth-wordmark">Vice<em>Vault</em></div>
                    <p class="auth-tagline">Let's get you set up ✦</p>
                </div>
                <div class="auth-divider"></div>
                <div class="auth-section-label">Create your account</div>
            </div>
        """, unsafe_allow_html=True)

        username         = st.text_input("Username", placeholder="At least 3 characters", key="reg_username")
        email            = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
        password         = st.text_input("Password", type="password", placeholder="At least 6 characters", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", placeholder="Same password, once more", key="reg_confirm")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Create Account →", use_container_width=True, type="primary", key="register_btn"):
                if not username or not email or not password:
                    st.error("All fields are required.")
                elif len(username) < 3:
                    st.error("Username needs at least 3 characters.")
                elif not validate_email(email):
                    st.error("That email doesn't look quite right.")
                elif len(password) < 6:
                    st.error("Password needs at least 6 characters.")
                elif password != confirm_password:
                    st.error("Passwords don't match — double check?")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(f"You're all set! {message}")
                        st.info("Head back and sign in with your new account.")
                        st.balloons()
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)
        with col_b:
            if st.button("← Back to Login", use_container_width=True, type="secondary", key="back_login"):
                st.session_state.page = 'login'
                st.rerun()

        st.markdown(
            '<p class="auth-hint">Already have an account? Sign in on the previous screen.</p>',
            unsafe_allow_html=True
        )
