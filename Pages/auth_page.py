import streamlit as st
from auth import authenticate_user, register_user, validate_email


def login_page():
    """Render login page"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">ViceVault</h1>
                    <p class="auth-subtitle">Sign in to your account</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Login →", use_container_width=True, type="primary"):
                if username and password:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Login successful.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                else:
                    st.warning("Please enter both username and password.")

        with col_btn2:
            if st.button("Create Account", use_container_width=True, type="secondary"):
                st.session_state.page = 'register'
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns([1, 2, 1])
        with col_f2:
            if st.button("Forgot Password / Username", use_container_width=True, type="secondary"):
                st.session_state.page = 'forgot'
                st.rerun()

        st.markdown("""
            <p style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;
               color:#9e9891;text-align:center;text-transform:uppercase;margin-top:20px;">
               New here? Create a free account to get started.
            </p>
        """, unsafe_allow_html=True)


def register_page():
    """Render registration page"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">Create Account</h1>
                    <p class="auth-subtitle">Join ViceVault</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="At least 3 characters", key="reg_username")
        email    = st.text_input("Email", placeholder="your@email.com", key="reg_email")
        password = st.text_input("Password", type="password", placeholder="At least 6 characters", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat your password", key="reg_confirm")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Register →", use_container_width=True, type="primary"):
                if not username or not email or not password:
                    st.error("All fields are required.")
                elif len(username) < 3:
                    st.error("Username must be at least 3 characters.")
                elif not validate_email(email):
                    st.error("Invalid email format.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = register_user(username, email, password)
                    if success:
                        st.success(f"{message}")
                        st.info("You can now log in with your new account.")
                        st.balloons()
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(f"{message}")

        with col_btn2:
            if st.button("← Back to Login", use_container_width=True, type="secondary"):
                st.session_state.page = 'login'
                st.rerun()
