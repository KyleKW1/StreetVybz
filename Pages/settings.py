"""
Pages/settings.py — Account settings (shown inside the Me tab).
Data export (JSON), account deletion, password change link.
"""

import streamlit as st
import json
from styles import inject_page_css


def _db(fn, *args, default=None, **kwargs):
    try:
        import database as db
        return getattr(db, fn)(*args, **kwargs)
    except Exception:
        return default


def _uid():
    u = st.session_state.get("user", {})
    return u.get("id") if u else None


def _username():
    u = st.session_state.get("user", {})
    return u.get("username", "User")


def settings_page():
    inject_page_css()
    uid = _uid()

    if not uid:
        st.error("Log in to access settings.")
        return

    # ── Data export ───────────────────────────────────────────────────────────
    st.html("""
<div class="hd-h3" style="margin-top:6px;">Your data</div>
<div class="hd-sub" style="margin-bottom:12px;">Download everything Hidden has on you: your profile, links,
  quiz results and history, as a JSON file.</div>
""")

    if st.button("Export all my data", use_container_width=True, key="export_data"):
        with st.spinner("Gathering your data…"):
            data = _db("export_user_data", uid, default={})
            try:
                import social_db
                data = {**(data or {}), **social_db.export_social_data(uid)}
            except Exception:
                pass
        if data:
            st.download_button(
                "Download data.json",
                data=json.dumps(data, indent=2, default=str),
                file_name="hidden_data.json",
                mime="application/json",
                use_container_width=True,
                key="download_export",
            )
        else:
            st.error("Couldn't export data. Try again.")

    st.html("<div style='height:1.5rem'></div>")

    # ── Password ──────────────────────────────────────────────────────────────
    st.html("""
<div class="hd-h3">Password</div>
<div class="hd-sub" style="margin-bottom:12px;">To change it, use password reset. Enter your email and
  you'll get a reset link.</div>
""")
    if st.button("Go to password reset", use_container_width=True, key="go_pw_reset"):
        for k in list(st.session_state.keys()):   # like logout: nothing carries over to the next login
            del st.session_state[k]
        st.session_state["_restore_tried"] = True
        st.session_state.page = "forgot"
        st.rerun()

    st.html("<div style='height:1.5rem'></div>")

    # ── Danger zone ───────────────────────────────────────────────────────────
    st.html("""
<div class="hd-h3">Delete your account</div>
<div class="hd-sub" style="margin-bottom:12px;">This removes your profile, links, chats, quiz results and
  all personal data. <b style="color:var(--ink);">It can't be undone.</b></div>
""")

    st.session_state.setdefault("delete_confirm_1", False)
    st.session_state.setdefault("delete_confirm_2", False)

    if not st.session_state.delete_confirm_1:
        if st.button("Delete my account", use_container_width=True, key="delete_step1"):
            st.session_state.delete_confirm_1 = True
            st.rerun()
    else:
        st.warning("Are you sure? This deletes everything permanently.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            confirm_text = st.text_input(
                f"Type your username to confirm",
                placeholder=_username(),
                key="delete_confirm_text",
            )
            if st.button("Yes, delete everything", type="primary", use_container_width=True,
                         key="delete_step2"):
                if confirm_text.strip().lower() == _username().lower():
                    with st.spinner("Deleting your account…"):
                        try:
                            import social_db
                            social_db.delete_social_data(uid)
                        except Exception:
                            pass
                        success = _db("delete_user_account", uid, default=False)
                    if success:
                        st.success("Account deleted.")
                        import time
                        time.sleep(1)
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.rerun()
                    else:
                        st.error("Deletion failed. Try again or contact support.")
                else:
                    st.error(f"Type '{_username()}' exactly to confirm.")
        with col_no:
            st.html("<div style='height:28px'></div>")
            if st.button("Cancel", use_container_width=True, key="delete_cancel"):
                st.session_state.delete_confirm_1 = False
                st.rerun()
