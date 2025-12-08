"""
forgot_password.py - Password Reset and Username Recovery Module
Place this file in the same directory as Test3.py
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import re
import secrets
import smtplib
from email.message import EmailMessage

# ============================================
# EMAIL CONFIGURATION
# ============================================
APP_EMAIL = "fintrackeralerts@gmail.com"
APP_EMAIL_PASSWORD = "myhdkbyrzmpvwjyb"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ============================================
# DATABASE CONFIGURATION (same as Test3.py)
# ============================================


# ============================================
# DATABASE FUNCTIONS
# ============================================

def create_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            ssl_disabled=DB_CONFIG['ssl_disabled'],
            connection_timeout=30,
            autocommit=False
        )
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_email_exists(email):
    """Check if email exists in database"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result is not None
    except Error as e:
        if connection:
            connection.close()
        return False

def get_username_by_email(email):
    """Retrieve username by email"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT username FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return result['username']
        return None
    except Error as e:
        if connection:
            connection.close()
        return None

# ============================================
# PASSWORD RESET FUNCTIONS
# ============================================

def generate_reset_token():
    """Generate a random reset token"""
    return secrets.token_urlsafe(32)

def save_reset_token(email, token):
    """Save password reset token to database"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO password_resets (email, token, expires_at) 
               VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 1 HOUR))
               ON DUPLICATE KEY UPDATE token = %s, expires_at = DATE_ADD(NOW(), INTERVAL 1 HOUR)""",
            (email, token, token)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error saving reset token: {e}")
        if connection:
            connection.close()
        return False

def verify_reset_token(token):
    """Verify if reset token is valid and not expired"""
    connection = create_connection()
    if not connection:
        return False, None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT email FROM password_resets WHERE token = %s AND expires_at > NOW()",
            (token,)
        )
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            return True, result['email']
        return False, None
    except Error as e:
        if connection:
            connection.close()
        return False, None

def reset_password(email, new_password):
    """Reset user password"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        password_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (password_hash, email)
        )
        
        # Delete used token
        cursor.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        st.error(f"Error resetting password: {e}")
        if connection:
            connection.close()
        return False

# ============================================
# EMAIL FUNCTIONS
# ============================================

def send_reset_email(to_email, reset_token=None, reset_type='password'):
    """Send password reset or username recovery email"""
    try:
        msg = EmailMessage()
        msg['From'] = APP_EMAIL
        msg['To'] = to_email
        
        if reset_type == 'password':
            msg['Subject'] = "Finance Hub - Password Reset Request"
            # TODO: Change this to your deployed URL
            reset_url = f"https://fintrackertests.streamlit.app/?reset_token={reset_token}"
            body = f"""Dear User,

You requested to reset your password for Finance Hub.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you didn't request this, please ignore this email.

Best regards,
Finance Hub Team"""
        else:  # username recovery
            username = get_username_by_email(to_email)
            if not username:
                return False
            msg['Subject'] = "Finance Hub - Username Recovery"
            body = f"""Dear User,

You requested to recover your username for Finance Hub.

Your username is: {username}

If you didn't request this, please ignore this email.

Best regards,
Finance Hub Team"""
        
        msg.set_content(body)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# ============================================
# STYLING FUNCTIONS
# ============================================

def apply_custom_styles():
    """Apply custom CSS styles"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .auth-container {
        background: white;
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        margin: 2rem auto;
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .auth-subtitle {
        color: #6b7280;
        font-size: 1rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# PAGE FUNCTIONS
# ============================================

def forgot_password_page():
    """Forgot password/username page"""
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">🔐 Account Recovery</h1>
                    <p class="auth-subtitle">Recover your password or username</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        recovery_type = st.radio(
            "What do you need help with?",
            ["Reset Password", "Recover Username"],
            horizontal=True
        )
        
        email = st.text_input("Email Address", placeholder="your.email@example.com", key="recovery_email")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✉️ Send Recovery Email", use_container_width=True):
                if not email:
                    st.error("❌ Please enter your email address")
                elif not validate_email(email):
                    st.error("❌ Invalid email format")
                else:
                    # Check if email exists
                    if not check_email_exists(email):
                        st.error("❌ No account found with this email address")
                    else:
                        if recovery_type == "Reset Password":
                            # Generate and save reset token
                            token = generate_reset_token()
                            if save_reset_token(email, token):
                                if send_reset_email(email, token, 'password'):
                                    st.success("✅ Password reset email sent! Check your inbox.")
                                    st.info("The reset link will expire in 1 hour.")
                                else:
                                    st.error("❌ Failed to send email. Please try again.")
                            else:
                                st.error("❌ Failed to generate reset token.")
                        else:  # Recover Username
                            if send_reset_email(email, None, 'username'):
                                st.success("✅ Username recovery email sent! Check your inbox.")
                            else:
                                st.error("❌ Failed to send email. Please try again.")
        
        with col_btn2:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()

def reset_password_page():
    """Reset password page (accessed via email link)"""
    apply_custom_styles()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="auth-container">
                <div class="auth-header">
                    <h1 class="auth-title">🔑 Reset Password</h1>
                    <p class="auth-subtitle">Enter your new password</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Get token from session state
        if 'reset_token' not in st.session_state:
            st.error("❌ Invalid or expired reset link")
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = 'login'
                st.rerun()
            return
        
        token = st.session_state.reset_token
        
        # Verify token
        valid, email = verify_reset_token(token)
        
        if not valid:
            st.error("❌ This reset link is invalid or has expired")
            if st.button("← Request New Link", use_container_width=True):
                st.session_state.page = 'forgot'
                if 'reset_token' in st.session_state:
                    del st.session_state.reset_token
                st.rerun()
            return
        
        st.success(f"✅ Resetting password for: {email}")
        
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password (min 6 characters)", key="new_pass")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm new password", key="confirm_pass")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔐 Reset Password", use_container_width=True):
                if not new_password or not confirm_password:
                    st.error("❌ Please fill in all fields")
                elif len(new_password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    if reset_password(email, new_password):
                        st.success("✅ Password reset successful!")
                        st.balloons()
                        st.info("You can now login with your new password")
                        if 'reset_token' in st.session_state:
                            del st.session_state.reset_token
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error("❌ Failed to reset password. Please try again.")
        
        with col_btn2:
            if st.button("← Cancel", use_container_width=True):
                if 'reset_token' in st.session_state:
                    del st.session_state.reset_token
                st.session_state.page = 'login'
                st.rerun()
