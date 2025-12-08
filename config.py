# config.py
"""
Configuration file for Finance Hub application
Uses Streamlit secrets - NEVER commit credentials!
"""

import streamlit as st

# ============================================
# DATABASE CONFIGURATION - FROM SECRETS
# ============================================
try:
    DB_CONFIG = {
        'host': st.secrets["DB_HOST"],
        'port': int(st.secrets["DB_PORT"]),
        'user': st.secrets["DB_USER"],
        'password': st.secrets["DB_PASSWORD"],
        'database': st.secrets["DB_NAME"],
        'ssl_disabled': False,
        'ssl_verify_cert': True,
        'ssl_verify_identity': True,
        'connection_timeout': 30,
        'autocommit': False
    }
    
    EMAIL_CONFIG = {
        'sender_email': st.secrets["EMAIL_USER"],
        'sender_password': st.secrets["EMAIL_PASSWORD"],
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587
    }
except Exception as e:
    st.error(f"⚠️ Configuration error: {e}")
    st.info("Please configure secrets in Streamlit Cloud settings")
    # Set empty defaults to prevent crashes
    DB_CONFIG = {
        'host': '',
        'port': 11510,
        'user': '',
        'password': '',
        'database': '',
        'ssl_disabled': False,
        'ssl_verify_cert': True,
        'ssl_verify_identity': True,
        'connection_timeout': 30,
        'autocommit': False
    }
    EMAIL_CONFIG = {
        'sender_email': '',
        'sender_password': '',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587
    }


APP_TITLE = "Vice"
APP_ICON = "X"
