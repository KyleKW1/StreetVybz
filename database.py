# database.py — hardened version
"""
All DB functions in one place. Uses ssl_disabled=True for Streamlit Cloud.
If any individual query fails it returns a safe default rather than crashing.
"""

import streamlit as st

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    from config import DB_CONFIG
except ImportError:
    DB_CONFIG = {}


def create_connection():
    if not MYSQL_AVAILABLE:
        return None
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG.get('host', ''),
            port=int(DB_CONFIG.get('port', 3306)),
            user=DB_CONFIG.get('user', ''),
            password=DB_CONFIG.get('password', ''),
            database=DB_CONFIG.get('database', ''),
            connection_timeout=30,
            autocommit=False,
            ssl_disabled=True,
        )
        return conn
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        if conn:
            conn.close()
        return None


def get_user_by_email(email: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        if conn:
            conn.close()
        return None


def create_user(username: str, email: str, password_hash: str):
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        if conn:
            conn.close()
        return False, "Username or email already exists."
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Registration error: {e}"


def update_last_login(user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        if conn:
            conn.close()
        return False


def update_user_password(user_id: int, new_password_hash: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        if conn:
            conn.close()
        return False
