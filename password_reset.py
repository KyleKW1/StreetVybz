"""
password_reset.py — Password reset and username recovery.
"""

import streamlit as st
import hashlib
import re
import secrets
import smtplib
from email.message import EmailMessage

# ── DB config ─────────────────────────────────────────────────────────────────
try:
    from config import DB_CONFIG, EMAIL_CONFIG
    APP_EMAIL          = EMAIL_CONFIG.get("sender_email", "")
    APP_EMAIL_PASSWORD = EMAIL_CONFIG.get("sender_password", "")
    SMTP_SERVER        = EMAIL_CONFIG.get("smtp_server", "smtp.gmail.com")
    SMTP_PORT          = EMAIL_CONFIG.get("smtp_port", 587)
except Exception:
    DB_CONFIG          = {}
    APP_EMAIL          = ""
    APP_EMAIL_PASSWORD = ""
    SMTP_SERVER        = "smtp.gmail.com"
    SMTP_PORT          = 587

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


# ─── DB HELPERS ───────────────────────────────────────────────────────────────

def _create_connection():
    if not MYSQL_AVAILABLE or not DB_CONFIG.get("host"):
        return None
    try:
        return mysql.connector.connect(
            host=DB_CONFIG.get("host", ""),
            port=int(DB_CONFIG.get("port", 3306)),
            user=DB_CONFIG.get("user", ""),
            password=DB_CONFIG.get("password", ""),
            database=DB_CONFIG.get("database", ""),
            ssl_disabled=True,
            connection_timeout=30,
            autocommit=False,
        )
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def _check_email_exists(email: str) -> bool:
    conn = _create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        result = cur.fetchone()
        cur.close()
        return result is not None
    except Exception:
        return False
    finally:
        conn.close()


def _get_username_by_email(email: str):
    conn = _create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        cur.close()
        return row["username"] if row else None
    except Exception:
        return None
    finally:
        conn.close()


def _save_reset_token(email: str, token: str) -> bool:
    conn = _create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO password_resets (email, token, expires_at)
               VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 1 HOUR))
               ON DUPLICATE KEY UPDATE
                 token = VALUES(token),
                 expires_at = VALUES(expires_at)""",
            (email, token),
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving reset token: {e}")
        return False
    finally:
        conn.close()


def _verify_reset_token(token: str):
    """Returns (valid: bool, email: str | None)."""
    conn = _create_connection()
    if not conn:
        return False, None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT email FROM password_resets WHERE token = %s AND expires_at > NOW()",
            (token,),
        )
        row = cur.fetchone()
        cur.close()
        if row:
            return True, row["email"]
        return False, None
    except Exception:
        return False, None
    finally:
        conn.close()


def _reset_password(email: str, new_password: str) -> bool:
    conn = _create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (hash_password(new_password), email),
        )
        cur.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error resetting password: {e}")
        return False
    finally:
        conn.close()


# ─── EMAIL ────────────────────────────────────────────────────────────────────

def _send_email(to_email: str, token=None, reset_type="password") -> bool:
    if not APP_EMAIL or not APP_EMAIL_PASSWORD:
        st.warning("Email not configured — check secrets.")
        return False
    try:
        msg = EmailMessage()
        msg["From"] = APP_EMAIL
        msg["To"]   = to_email
        if reset_type == "password":
            msg["Subject"] = "ViceVault — Password Reset"
            # FIX: added https:// so email clients render it as a clickable link
            reset_url = f"https://testrun01.streamlit.app/?reset_token={token}"
            body = (
                f"Click the link below to reset your password (valid 1 hour):\n\n"
                f"{reset_url}\n\n"
                "If you didn't request this, ignore this email."
            )
        else:
            username = _get_username_by_email(to_email)
            if not username:
                return False
            msg["Subject"] = "ViceVault — Username Recovery"
            body = f"Your ViceVault username is: {username}"
        msg.set_content(body)
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email send failed: {e}")
        return False


# ─── QUERY PARAM HANDLER ──────────────────────────────────────────────────────

def handle_reset_token_from_url():
    """
    Call this at the TOP of your main app.py before any page routing.
    If a ?reset_token=... param is present in the URL, it stores the token
    in session_state, sets the page to 'reset_password', and clears the URL param.
    """
    params = st.query_params
    if "reset_token" in params:
        st.session_state["reset_token"] = params["reset_token"]
        st.session_state["page"] = "reset_password"
        st.query_params.clear()
        st.rerun()


# ─── PAGES ────────────────────────────────────────────────────────────────────

def forgot_password_page():
    from Pages.auth_page import inject_auth_css
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.html("""
<div class="auth-card">
  <div class="auth-wordmark">VICE<span>VAULT</span></div>
  <p class="auth-tagline">Account recovery</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Reset password or recover username</div>
</div>
""")
        recovery_type = st.radio(
            "What do you need?",
            ["Reset Password", "Recover Username"],
            horizontal=True,
            key="recovery_type",
        )
        email = st.text_input("Email address", placeholder="you@example.com", key="recovery_email")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Send Email →", use_container_width=True, type="primary"):
                if not email:
                    st.error("Enter your email address.")
                elif not validate_email(email):
                    st.error("That email doesn't look right.")
                elif not _check_email_exists(email):
                    st.error("No account with that email.")
                else:
                    if recovery_type == "Reset Password":
                        token = secrets.token_urlsafe(32)
                        if _save_reset_token(email, token) and _send_email(email, token, "password"):
                            st.success("Reset link sent — check your inbox.")
                        else:
                            st.error("Something went wrong. Try again.")
                    else:
                        if _send_email(email, reset_type="username"):
                            st.success("Username sent to your inbox.")
                        else:
                            st.error("Something went wrong. Try again.")
        with col_b:
            if st.button("← Back", use_container_width=True, type="secondary"):
                st.session_state.page = "login"
                st.rerun()


def reset_password_page():
    from Pages.auth_page import inject_auth_css
    inject_auth_css()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.html("""
<div class="auth-card">
  <div class="auth-wordmark">VICE<span>VAULT</span></div>
  <p class="auth-tagline">Choose a new password</p>
  <div class="auth-divider"></div>
  <div class="auth-section-label">Reset password</div>
</div>
""")
        token = st.session_state.get("reset_token")
        if not token:
            st.error("Invalid or expired reset link.")
            if st.button("← Back to login"):
                st.session_state.page = "login"
                st.rerun()
            return

        valid, email = _verify_reset_token(token)
        if not valid:
            st.error("This link is invalid or has expired.")
            if st.button("Request new link →"):
                st.session_state.page = "forgot"
                st.session_state.pop("reset_token", None)
                st.rerun()
            return

        st.success(f"Resetting password for {email}")
        new_pw  = st.text_input("New password", type="password", key="new_pw")
        conf_pw = st.text_input("Confirm password", type="password", key="conf_pw")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Reset →", use_container_width=True, type="primary"):
                if not new_pw:
                    st.error("Enter a password.")
                elif len(new_pw) < 6:
                    st.error("Minimum 6 characters.")
                elif new_pw != conf_pw:
                    st.error("Passwords don't match.")
                elif _reset_password(email, new_pw):
                    st.success("Password reset! Sign in now.")
                    st.session_state.pop("reset_token", None)
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Reset failed — try again.")
        with col_b:
            if st.button("Cancel", use_container_width=True, type="secondary"):
                st.session_state.pop("reset_token", None)
                st.session_state.page = "login"
                st.rerun()
