"""
auth.py — bcrypt password hashing with transparent SHA-256 migration.
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

MIN_PASSWORD_LENGTH = 8  # Fix #7: standardised across all flows


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
    """Verify against bcrypt or legacy SHA-256 hash. NO plaintext path."""
    is_bcrypt = stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")
    if BCRYPT_AVAILABLE and is_bcrypt:
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except Exception:
            return False
    # Legacy SHA-256 path (64 hex chars) — anything else is rejected
    if len(stored_hash) == 64:
        return _sha256(password) == stored_hash
    return False


def _is_legacy_hash(stored_hash: str) -> bool:
    return not (stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"))


# ── Validation ────────────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_password(password: str):
    """Returns (ok, message). Centralised so every flow enforces the same rule."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password needs at least {MIN_PASSWORD_LENGTH} characters."
    return True, ""


# ── Registration / Authentication ─────────────────────────────────────────────

def register_user(username: str, email: str, password: str):
    """Called by Pages/auth_page.py — returns (bool, str) tuple."""
    db = _db()
    if not db:
        return False, "Database unavailable."
    ok, msg = validate_password(password)
    if not ok:
        return False, msg
    try:
        uid = db.create_user(username, email, hash_password(password))
        if uid:
            return True, "Registration successful!"
        return False, "Username or email already exists."
    except Exception:
        return False, "Registration error — please try again."


def authenticate_user(username: str, password: str):
    """
    Fix #7: rate-limited. After 5 failed attempts within 10 minutes for a
    username, login is locked. Returns (success, user_or_None) — and
    (False, "locked") when rate limited so the UI can show a clear message.
    """
    db = _db()
    if not db:
        return False, None
    try:
        # Rate limit check (Fix #7)
        try:
            if db.is_login_locked(username):
                return False, "locked"
        except Exception:
            pass

        user = db.get_user_by_username(username)
        if not user:
            try:
                db.record_login_attempt(username, False)
            except Exception:
                pass
            return False, None

        stored = user.get("password_hash", "")
        if not _verify_password(password, stored):
            try:
                db.record_login_attempt(username, False)
            except Exception:
                pass
            return False, None

        try:
            db.record_login_attempt(username, True)
        except Exception:
            pass

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
    Fix #4: called on every authenticated page load (app.py main()).
    Fails CLOSED: if the token can't be positively verified, the session
    is invalid. Only when the database module itself isn't importable
    (pure local dev) do we allow through.
    """
    db = _db()
    if not db:
        return True
    token = st.session_state.get("session_token")
    user = st.session_state.get("user", {})
    user_id = user.get("id") if user else None
    if not user_id:
        return False
    if not token:
        # Authenticated session with no token at all — treat as invalid
        # (every login path now issues one).
        return False
    try:
        return db.verify_session_token(user_id, token)
    except Exception:
        return False


# ── Password reset helper ─────────────────────────────────────────────────────

def reset_user_password(user_id: int, new_password: str) -> bool:
    db = _db()
    if not db:
        return False
    ok, _ = validate_password(new_password)
    if not ok:
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
