"""
fix_security.py
Security fixes for ViceVault. Run from project root, AFTER (or before —
order doesn't matter, every patch is idempotent) apply_patches.py:

    python apply_patches.py
    python fix_security.py

Covers:
  Fix 1 — extra XSS escaping that apply_patches.py misses
          (usernames in confession cards / friends / compare panel,
           history notes, profile masthead, status badges)
  Fix 2 — remove plaintext password fallback; constant-time SHA-256
          legacy check with transparent bcrypt upgrade
  Fix 3 — confession deletion requires the caller to be sender/recipient
  Fix 5 — session validation fails CLOSED (DB errors / missing tokens
          no longer count as "valid")

Safe to re-run; each replacement is a no-op if already applied.
"""


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def replace_once(content, old, new, label, path):
    if old not in content:
        if new in content:
            print(f"  [skip] {label} (already applied)")
            return content
        print(f"  [WARN] {label}: pattern not found in {path} — check manually")
        return content
    print(f"  [ok]   {label}")
    return content.replace(old, new, 1)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 2 — database.py: kill plaintext fallback, harden legacy SHA-256 path
# FIX 3 — database.py: ownership check on delete_confession
# FIX 5 — database.py: verify_session_token fails closed
# ─────────────────────────────────────────────────────────────────────────────
def patch_database():
    path = "database.py"
    c = load(path)

    # ── Fix 2: authenticate_user ──────────────────────────────────────────
    c = replace_once(
        c,
        '''        stored = user.get("password_hash", "")

        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            try:
                import bcrypt
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    return user
            except Exception:
                pass
            return None

        if len(stored) == 64:
            import hashlib
            if hashlib.sha256(password.encode()).hexdigest() == stored:
                return user
            return None

        if stored == password:
            return user

        return None''',
        '''        stored = user.get("password_hash", "") or ""

        # bcrypt — current standard
        if stored.startswith(("$2b$", "$2a$", "$2y$")):
            try:
                import bcrypt
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    return user
            except Exception:
                pass
            return None

        # Legacy SHA-256 — constant-time compare, then transparently
        # upgrade the stored hash to bcrypt on successful login.
        if len(stored) == 64:
            import hashlib
            import hmac
            candidate = hashlib.sha256(password.encode()).hexdigest()
            if hmac.compare_digest(candidate, stored):
                try:
                    import bcrypt
                    new_hash = bcrypt.hashpw(
                        password.encode(), bcrypt.gensalt()
                    ).decode()
                    update_user_password(user["id"], new_hash)
                except Exception:
                    pass
                return user
            return None

        # Anything else — including legacy plaintext rows — is rejected.
        # Those users must use the password-reset flow.
        return None''',
        "Fix 2: remove plaintext fallback + bcrypt migration", path,
    )

    # ── Fix 3: delete_confession ownership ────────────────────────────────
    c = replace_once(
        c,
        '''def delete_confession(code: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM confessions WHERE code = %s", (code,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        return deleted''',
        '''def delete_confession(code: str, user_id: int = None) -> bool:
    """Delete a confession — only if the caller is the sender or recipient."""
    if user_id is None:
        return False
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM confessions
               WHERE code = %s AND (sender_id = %s OR recipient_id = %s)""",
            (code, user_id, user_id),
        )
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        return deleted''',
        "Fix 3: delete_confession requires sender/recipient", path,
    )

    # ── Fix 5: verify_session_token fails closed ──────────────────────────
    c = replace_once(
        c,
        '''def verify_session_token(user_id: int, token: str) -> bool:
    conn = create_connection()
    if not conn:
        return True''',
        '''def verify_session_token(user_id: int, token: str) -> bool:
    conn = create_connection()
    if not conn:
        return False''',
        "Fix 5: verify_session_token no-conn fails closed", path,
    )

    c = replace_once(
        c,
        '''        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return True''',
        '''        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return False''',
        "Fix 5: verify_session_token exception fails closed", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 5 — auth.py: check_session_valid fails closed; login fails if the
#         session token can't be stored (otherwise users get an instant-logout
#         loop now that validation is strict)
# ─────────────────────────────────────────────────────────────────────────────
def patch_auth():
    path = "auth.py"
    c = load(path)

    c = replace_once(
        c,
        '''def check_session_valid() -> bool:
    """Returns True if the current session token is still valid (or if no token system is in use)."""
    user = st.session_state.get("user")
    token = st.session_state.get("session_token")
    if not user or not token:
        return True  # No token system — don't block
    try:
        import database as db
        return db.verify_session_token(user["id"], token)
    except Exception:
        return True''',
        '''def check_session_valid() -> bool:
    """Fail closed: a logged-in user must hold a valid, unexpired session token."""
    user = st.session_state.get("user")
    if not user:
        return False
    token = st.session_state.get("session_token")
    if not token:
        return False
    try:
        import database as db
        return db.verify_session_token(user["id"], token)
    except Exception:
        return False''',
        "Fix 5: check_session_valid fails closed", path,
    )

    c = replace_once(
        c,
        '''    user = db.authenticate_user(username.strip(), password)
    if user:
        st.session_state[key] = 0
        # Issue a session token
        try:
            token = secrets.token_urlsafe(32)
            db.create_session_token(user["id"], token)
            st.session_state["session_token"] = token
        except Exception:
            pass''',
        '''    user = db.authenticate_user(username.strip(), password)
    if user:
        st.session_state[key] = 0
        # Issue a session token. Login FAILS if it can't be stored,
        # because session validation now fails closed — otherwise the
        # user would log in and be kicked out on the next page load.
        token = secrets.token_urlsafe(32)
        try:
            created = db.create_session_token(user["id"], token)
        except Exception:
            created = False
        if not created:
            return False, None
        st.session_state["session_token"] = token''',
        "Fix 5: login requires token creation to succeed", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 5 — app.py: registration also requires a stored session token
# ─────────────────────────────────────────────────────────────────────────────
def patch_app():
    path = "app.py"
    c = load(path)

    c = replace_once(
        c,
        '''                        import secrets as _secrets
                        token = _secrets.token_urlsafe(32)
                        try:
                            db.create_session_token(uid, token)
                            st.session_state.session_token = token
                        except Exception:
                            pass''',
        '''                        import secrets as _secrets
                        token = _secrets.token_urlsafe(32)
                        try:
                            created = db.create_session_token(uid, token)
                        except Exception:
                            created = False
                        if created:
                            st.session_state.session_token = token
                        else:
                            st.error("Account created — please log in.")
                            st.session_state.page = "login"
                            st.rerun()''',
        "Fix 5: registration requires token creation", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 + FIX 3 — Pages/confession.py
# Extra escaping beyond apply_patches.py (usernames everywhere they hit
# st.html) + authenticated delete via query param.
# ─────────────────────────────────────────────────────────────────────────────
def patch_confession():
    path = "Pages/confession.py"
    c = load(path)

    # html import (same patch as apply_patches.py — skips if already there)
    c = replace_once(
        c,
        "import streamlit as st\nimport secrets\nimport string\nimport re\nimport time\n",
        "import streamlit as st\nimport secrets\nimport string\nimport re\nimport time\nimport html as _html\n",
        "add html import", path,
    )

    # Fix 3: delete_code must carry the caller's user id
    c = replace_once(
        c,
        '''    delete_code = params.get("delete_code")
    if delete_code:
        _db("delete_confession", delete_code)
        st.query_params.clear()
        st.rerun()''',
        '''    delete_code = params.get("delete_code")
    if delete_code:
        uid = _uid()
        if uid:
            _db("delete_confession", delete_code, uid)
        st.query_params.clear()
        st.rerun()''',
        "Fix 3: authenticated delete via query param", path,
    )

    # Status badge interpolates names into HTML
    c = replace_once(
        c,
        '''def _status_badge(status, sender, recipient, is_sender):
    cfg = {''',
        '''def _status_badge(status, sender, recipient, is_sender):
    sender    = _html.escape(str(sender))
    recipient = _html.escape(str(recipient))
    cfg = {''',
        "escape names in _status_badge", path,
    )

    # Typing indicator
    c = replace_once(
        c,
        '''def _typing_indicator(name: str):
    st.html(f"""''',
        '''def _typing_indicator(name: str):
    name = _html.escape(str(name))
    st.html(f"""''',
        "escape name in _typing_indicator", path,
    )

    # Inbox card header
    c = replace_once(
        c,
        "      From {sender_name}\n",
        "      From {_html.escape(str(sender_name))}\n",
        "escape sender in inbox card", path,
    )

    # Outbox card header
    c = replace_once(
        c,
        "      To {recipient_name}\n",
        "      To {_html.escape(str(recipient_name))}\n",
        "escape recipient in outbox card", path,
    )

    # Revealed view labels
    c = replace_once(
        c,
        '''def _render_revealed(item, is_sender: bool):
    sender_name    = item.get("sender_username", "Sender")
    recipient_name = item.get("recipient_username") or item.get("recipient_email", "Recipient")''',
        '''def _render_revealed(item, is_sender: bool):
    sender_name    = _html.escape(str(item.get("sender_username", "Sender")))
    recipient_name = _html.escape(str(
        item.get("recipient_username") or item.get("recipient_email", "Recipient")
    ))''',
        "escape names in _render_revealed", path,
    )

    # Screenshot alert banner
    c = replace_once(
        c,
        '''        screenshotter = alert.get("screenshotter_username", "Someone")''',
        '''        screenshotter = _html.escape(str(alert.get("screenshotter_username", "Someone")))''',
        "escape screenshotter name", path,
    )

    # Friend request card
    c = replace_once(
        c,
        '''            sender   = req.get("sender_username", "Someone")''',
        '''            sender   = _html.escape(str(req.get("sender_username", "Someone")))''',
        "escape friend-request sender", path,
    )

    # Friends list card — keep the raw name for the Confess prefill
    c = replace_once(
        c,
        '''            fname     = f.get("username", "?")''',
        '''            fname_raw = f.get("username", "?")
            fname     = _html.escape(str(fname_raw))''',
        "escape friend username in list card", path,
    )
    c = replace_once(
        c,
        '''                    st.session_state[f"conf_prefill"] = fname''',
        '''                    st.session_state[f"conf_prefill"] = fname_raw''',
        "use raw username for compose prefill", path,
    )
    c = replace_once(
        c,
        '''            rbtl      = f.get("rbtl_name") or "—"''',
        '''            rbtl      = _html.escape(str(f.get("rbtl_name") or "—"))''',
        "escape rbtl name in friends list", path,
    )

    # Compare panel
    c = replace_once(
        c,
        '''    col_accent = "var(--lime)" if is_me else "var(--cyan)"
    username   = stats.get("username", label)
    initials   = username[:2].upper()''',
        '''    col_accent = "var(--lime)" if is_me else "var(--cyan)"
    username   = _html.escape(str(stats.get("username", label)))
    initials   = username[:2].upper()''',
        "escape username in compare panel", path,
    )
    c = replace_once(
        c,
        '''    rbtl        = stats.get("rbtl_name") or "—"''',
        '''    rbtl        = _html.escape(str(stats.get("rbtl_name") or "—"))''',
        "escape rbtl in compare panel", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 — Pages/dashboard.py: escape user notes/details in History
# ─────────────────────────────────────────────────────────────────────────────
def patch_dashboard():
    path = "Pages/dashboard.py"
    c = load(path)

    c = replace_once(
        c,
        "import streamlit as st\nimport time\nfrom datetime import datetime, timedelta, date\n",
        "import streamlit as st\nimport time\nimport html as _html\nfrom datetime import datetime, timedelta, date\n",
        "add html import", path,
    )

    c = replace_once(
        c,
        '''        data_str = "  ·  ".join(f"{k}: {val}" for k, val in e["data"].items()
                                 if val and k != "notes")
        notes    = e["data"].get("notes", "")''',
        '''        data_str = _html.escape("  ·  ".join(
            f"{k}: {val}" for k, val in e["data"].items()
            if val and k != "notes"
        ))
        notes    = _html.escape(str(e["data"].get("notes", "")))''',
        "escape history entry details + notes", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 — Pages/profile.py: escape username in masthead
# ─────────────────────────────────────────────────────────────────────────────
def patch_profile():
    path = "Pages/profile.py"
    c = load(path)

    c = replace_once(
        c,
        "import streamlit as st\nfrom datetime import datetime\nfrom styles import inject_page_css\n",
        "import streamlit as st\nimport html as _html\nfrom datetime import datetime\nfrom styles import inject_page_css\n",
        "add html import", path,
    )

    c = replace_once(
        c,
        '''    initials = username[:2].upper()''',
        '''    username = _html.escape(str(username))
    initials = username[:2].upper()''',
        "escape username in profile masthead", path,
    )

    save(path, c)


if __name__ == "__main__":
    print("Patching database.py ...")
    patch_database()
    print("Patching auth.py ...")
    patch_auth()
    print("Patching app.py ...")
    patch_app()
    print("Patching Pages/confession.py ...")
    patch_confession()
    print("Patching Pages/dashboard.py ...")
    patch_dashboard()
    print("Patching Pages/profile.py ...")
    patch_profile()
    print()
    print("Done. Notes:")
    print(" - Also run apply_patches.py if you haven't (covers the rest of Fix 1).")
    print(" - All existing sessions will be invalidated on deploy — everyone")
    print("   logs in again once (expected, fail-closed behaviour).")
    print(" - Any legacy PLAINTEXT password rows can no longer log in; those")
    print("   users must use the forgot-password flow. SHA-256 users migrate")
    print("   to bcrypt automatically on their next successful login.")
