"""
auth.py — hardened with lazy DB imports so a missing function never crashes the whole app.
"""
import hashlib
import re
import streamlit as st


def _db():
    """Lazy import of database module — errors are caught per-call, not at startup."""
    try:
        import database as _database
        return _database
    except Exception as e:
        st.error(f"Database module unavailable: {e}")
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def register_user(username: str, email: str, password: str):
    db = _db()
    if not db:
        return False, "Database unavailable."
    try:
        return db.create_user(username, email, hash_password(password))
    except Exception as e:
        return False, f"Registration error: {e}"


def authenticate_user(username: str, password: str):
    db = _db()
    if not db:
        return False, None
    try:
        user = db.get_user_by_username(username)
        if not user:
            return False, None
        if user.get('password_hash') == hash_password(password):
            try:
                db.update_last_login(user['id'])
            except Exception:
                pass  # non-critical
            return True, user
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None


def reset_user_password(user_id: int, new_password: str) -> bool:
    db = _db()
    if not db:
        return False
    try:
        return db.update_user_password(user_id, hash_password(new_password))
    except Exception as e:
        st.error(f"Password reset error: {e}")
        return False


# ── Session state ─────────────────────────────────────────────────────────────

def init_session_state():
    defaults = {
        'authenticated':        False,
        'user':                 None,
        'page':                 'login',
        'selected_feature':     None,
        'selected_sub_feature': None,
        'file_page':            0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def logout():
    st.session_state.authenticated   = False
    st.session_state.user             = None
    st.session_state.page             = 'login'
    st.session_state.selected_feature = None
    st.rerun()
