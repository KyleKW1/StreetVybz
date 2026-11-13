"""
Pages/admin.py — Reports and bans (shown inside the Me tab, only to admins).

Admins are the usernames listed in the ADMIN_USERS secret, comma-separated:
    ADMIN_USERS = "your_username"
"""

import streamlit as st

import social_db
from ui import esc


def is_admin(user: dict | None) -> bool:
    try:
        raw = st.secrets.get("ADMIN_USERS", "")
    except Exception:
        raw = ""
    names = {n.strip().lower() for n in str(raw).split(",") if n.strip()}
    return bool(user) and (user.get("username") or "").lower() in names


def _when(v) -> str:
    return str(v)[:16] if v else ""


def _evidence(chat: list, reported: str):
    lines = "".join(
        f'<div class="hd-bubble {"them" if msg.get("from") == "reported" else "me"}">{esc(msg.get("body"))}'
        f'<small>{esc(reported if msg.get("from") == "reported" else "reporter")} · {esc(_when(msg.get("at")))}'
        f'</small></div>' for msg in chat)
    st.html(f'<div style="display:flex;flex-direction:column;max-height:320px;overflow-y:auto;">{lines}</div>')


def _person(uid: int, p: dict):
    n = len(p["reports"])
    extra = f" · {p['all_time']} all time" if p["all_time"] > n else ""
    with st.container(border=True):
        st.html(f'<div class="hd-title" style="font-size:26px;margin:0;">{esc(p["username"])}</div>'
                f'<div class="hd-kicker">{n} open report{"s" if n != 1 else ""}{extra} · '
                f'joined {esc(_when(p["joined"])[:10])}</div>')
        for r in p["reports"]:
            st.html(f'<div class="hd-sub" style="margin-top:10px;"><b style="color:var(--text);">'
                    f'{esc(r["reason"])}</b> · from {esc(r["reporter"] or "a deleted account")} · '
                    f'{esc(_when(r["created_at"]))}</div>'
                    + (f'<div class="hd-sub" style="color:var(--text);">“{esc(r["details"])}”</div>'
                       if r.get("details") else ""))
            if r["evidence"]:
                with st.expander(f"Their chat ({len(r['evidence'])} messages)"):
                    _evidence(r["evidence"], p["username"])
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ban", type="primary", use_container_width=True, key=f"ban_{p['user_id']}"):
                reasons = ", ".join(sorted({r["reason"] for r in p["reports"]}))
                if social_db.ban_user(p["user_id"], uid, reasons):
                    st.toast(f"Banned {p['username']}")
                    st.rerun()
                else:
                    st.error("Couldn't ban — try again.")
        with c2:
            if st.button("Dismiss", use_container_width=True, key=f"dismiss_{p['user_id']}"):
                social_db.dismiss_reports(p["user_id"])
                st.rerun()


def admin_page(uid: int):
    people = social_db.open_reports()
    st.html('<div class="hd-sub" style="margin-bottom:10px;">Reports from Discover and matches. '
            'Banning someone logs them out, stops them logging in, and hides them from everyone. '
            'Dismiss clears the reports and leaves them as they are.</div>')
    if not people:
        st.caption("No open reports.")
    for p in people:
        _person(uid, p)

    bans = social_db.load_bans()
    st.html('<div class="hd-kicker" style="margin:18px 0 8px;">Banned</div>')
    if not bans:
        st.caption("Nobody is banned.")
    for b in bans:
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            st.html(f'<div class="hd-sub" style="color:var(--text);">{esc(b["username"])}</div>'
                    f'<div class="hd-kicker">{esc(b["reason"] or "")} · {esc(_when(b["created_at"])[:10])}</div>')
        with c2:
            if st.button("Unban", use_container_width=True, key=f"unban_{b['user_id']}"):
                social_db.unban_user(b["user_id"])
                st.rerun()
