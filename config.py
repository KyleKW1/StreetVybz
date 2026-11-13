# config.py
"""
Configuration file for Hidden.
Uses Streamlit secrets — NEVER commit credentials!
"""

import streamlit as st

# ── Database ──────────────────────────────────────────────────────────────────
try:
    DB_CONFIG = {
        'host':               st.secrets["DB_HOST"],
        'port':               int(st.secrets["DB_PORT"]),
        'user':               st.secrets["DB_USER"],
        'password':           st.secrets["DB_PASSWORD"],
        'database':           st.secrets["DB_NAME"],
        'ssl_disabled':       True,
        'connection_timeout': 30,
        'autocommit':         False,
    }
except Exception as e:
    DB_CONFIG = {
        'host': '', 'port': 3306, 'user': '', 'password': '', 'database': '',
        'ssl_disabled': True, 'connection_timeout': 30, 'autocommit': False,
    }

# ── Email ─────────────────────────────────────────────────────────────────────
try:
    EMAIL_CONFIG = {
        'sender_email':    st.secrets["EMAIL_USER"],
        'sender_password': st.secrets["EMAIL_PASSWORD"],
        'smtp_server':     'smtp.gmail.com',
        'smtp_port':       587,
    }
except Exception:
    EMAIL_CONFIG = {
        'sender_email': '', 'sender_password': '',
        'smtp_server': 'smtp.gmail.com', 'smtp_port': 587,
    }

# ── Public address (invite and password-reset links) ──────────────────────────
# An APP_URL secret overrides it, e.g. while testing on another deployment.
DEFAULT_APP_URL = "https://hiddenneeds.streamlit.app"
try:
    APP_URL = (st.secrets.get("APP_URL") or DEFAULT_APP_URL).rstrip("/")
except Exception:
    APP_URL = DEFAULT_APP_URL

APP_TITLE = "Hidden"
APP_ICON  = "⚡"
