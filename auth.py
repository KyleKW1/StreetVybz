import hashlib
import re
import streamlit as st

# Import database functions - with error handling
try:
    from database import (
        get_user_by_username, 
        create_user, 
        update_last_login,
        get_user_by_email,
        update_user_password
    )
  
except ImportError as e:
    st.error(f"Error importing database module: {e}")
    st.stop()


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def register_user(username, email, password):
    """Register a new user"""
    password_hash = hash_password(password)
    return create_user(username, email, password_hash)


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    try:
        user = get_user_by_username(username)
        
        if not user:
            return False, None
        
        password_hash = hash_password(password)
        
        if user['password_hash'] == password_hash:
            update_last_login(user['id'])
            return True, user
        
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None


def reset_user_password(user_id, new_password):
    """Reset user password"""
    new_password_hash = hash_password(new_password)
    return update_user_password(user_id, new_password_hash)


# ============================================
# SESSION STATE MANAGEMENT
# ============================================

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'selected_feature' not in st.session_state:
        st.session_state.selected_feature = None
    if 'selected_sub_feature' not in st.session_state:
        st.session_state.selected_sub_feature = None  # ADD THIS LINE
    if 'file_page' not in st.session_state:
        st.session_state.file_page = 0


def logout():
    """Logout user and clear session"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.selected_feature = None
    st.rerun()
