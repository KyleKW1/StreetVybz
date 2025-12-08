# database.py
"""
Database connection and operations module
Handles all database interactions including user management and file storage
"""

import mysql.connector
from mysql.connector import Error
import streamlit as st
import json
import ssl

# Import config - with fallback
try:
    from config import DB_CONFIG
except ImportError:
    st.error("config.py not found! Please create it with your database credentials.")
    st.stop()


def create_connection():
    """Create database connection with SSL fix"""
    try:
        # Create connection config with SSL disabled for Streamlit Cloud
        connection_config = {
            'host': DB_CONFIG['host'],
            'port': DB_CONFIG['port'],
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'database': DB_CONFIG['database'],
            'connection_timeout': 30,
            'autocommit': False,
            'ssl_disabled': True  # Disable SSL verification
        }
        
        connection = mysql.connector.connect(**connection_config)
        return connection
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None


# ============================================
# USER OPERATIONS
# ============================================

def get_user_by_username(username):
    """Get user by username"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    except Error as e:
        st.error(f"Error fetching user: {e}")
        if connection:
            connection.close()
        return None


def get_user_by_email(email):
    """Get user by email"""
    connection = create_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    except Error as e:
        st.error(f"Error fetching user: {e}")
        if connection:
            connection.close()
        return None


def create_user(username, email, password_hash):
    """Create new user"""
    connection = create_connection()
    if not connection:
        return False, "Database connection failed"
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        if connection:
            connection.close()
        return False, "Username or email already exists"
    except Error as e:
        if connection:
            connection.close()
        return False, f"Registration error: {e}"


def update_last_login(user_id):
    """Update user's last login timestamp"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        if connection:
            connection.close()
        return False


def update_user_password(user_id, new_password_hash):
    """Update user password"""
    connection = create_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        if connection:
            connection.close()
        return False

