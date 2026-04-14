"""
auth.py — bcrypt password hashing with transparent SHA-256 migration.
Session tokens are stored in DB; invalidate_user_sessions actually works.
"""
import re
import secrets
import hashlib
import streamlit as st

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


def _db():
    try:
        import database as _database
        return _database
    except Exception:
        return None


# ── Hashing ───────────────────────────────────────────────────────────────────

def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def hash_password(password: str) -> str:
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return _sha256(password)


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify against bcrypt or legacy SHA-256 hash."""
    is_bcrypt = stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")
    if BCRYPT_AVAILABLE and is_bcrypt:
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except Exception:
            return False
    # Legacy SHA-256 path
    return _sha256(password) == stored_hash


def _is_legacy_hash(stored_hash: str) -> bool:
    return not (stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"))


# ── Validation ────────────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


# ── Registration / Authentication ─────────────────────────────────────────────

def register_user(username: str, email: str, password: str):
    db = _db()
    if not db:
        return False, "Database unavailable."
    try:
        return db.create_user(username, email, hash_password(password))
    except Exception:
        return False, "Registration error — please try again."


def authenticate_user(username: str, password: str):
    db = _db()
    if not db:
        return False, None
    try:
        user = db.get_user_by_username(username)
        if not user:
            return False, None

        stored = user.get("password_hash", "")
        if not _verify_password(password, stored):
            return False, None

        # Transparently migrate legacy SHA-256 → bcrypt
        if BCRYPT_AVAILABLE and _is_legacy_hash(stored):
            try:
                db.update_user_password(user["id"], hash_password(password))
            except Exception:
                pass

        try:
            db.update_last_login(user["id"])
        except Exception:
            pass

        # Issue session token
        token = secrets.token_urlsafe(32)
        try:
            db.create_session_token(user["id"], token)
            st.session_state.session_token = token
        except Exception:
            pass

        return True, user
    except Exception:
        return False, None


def check_session_valid() -> bool:
    """
    Called on every authenticated page load.
    Returns False if the token has been invalidated (e.g. after a screenshot logout).
    Fails open on DB error so a connectivity blip doesn't kick everyone out.
    """
    db = _db()
    if not db:
        return True
    token = st.session_state.get("session_token")
    if not token:
        # Older session pre-token — still let them in
        return True
    user = st.session_state.get("user", {})
    user_id = user.get("id") if user else None
    if not user_id:
        return False
    try:
        return db.verify_session_token(user_id, token)
    except Exception:
        return True


# ── Password reset helper ─────────────────────────────────────────────────────

def reset_user_password(user_id: int, new_password: str) -> bool:
    db = _db()
    if not db:
        return False
    try:
        return db.update_user_password(user_id, hash_password(new_password))
    except Exception:
        return False


# ── Session state ─────────────────────────────────────────────────────────────

def init_session_state():
    defaults = {
        "authenticated":        False,
        "user":                 None,
        "page":                 "login",
        "selected_feature":     None,
        "selected_sub_feature": None,
        "file_page":            0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def logout():
    db = _db()
    if db:
        token = st.session_state.get("session_token")
        if token:
            try:
                db.invalidate_session_token(token)
            except Exception:
                pass

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.session_state.authenticated = False
    st.session_state.user          = None
    st.session_state.page          = "login"
    st.rerun()
