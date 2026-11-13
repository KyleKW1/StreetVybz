"""
Pages/me.py — Your profile, the quiz, safety controls and account settings.
"""

import streamlit as st

import social_db
from matching import INTENTS, norm_intent
from Pages.profile_form import profile_form, age_text
from ui import esc, avatar, lifestyle_chips, setup_chips, open_quiz


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def _masthead(uid: int, p: dict):
    st.html(f"""
<div class="hd-card" style="display:flex;align-items:center;gap:18px;margin-bottom:14px;">
  {avatar(p.get('username', ''), uid)}
  <div style="min-width:0;">
    <div class="hd-title" style="margin:0;overflow-wrap:anywhere;">{esc(p.get('username', ''))}<span
         style="color:var(--soft);font-size:28px;">{', ' + age_text(p) if age_text(p) else ''}</span></div>
    <div class="hd-kicker" style="margin-top:4px;">📍 {esc(p.get('city') or '—')} · {esc(INTENTS.get(norm_intent(p.get('intent')), ''))}</div>
    <div class="hd-chips" style="margin-bottom:0;">{setup_chips(p, social_db.is_free_tonight(p))}{lifestyle_chips(p)}</div>
  </div>
</div>
""")


def _hide_toggle(uid: int, p: dict):
    hidden = st.toggle("👻  Hide me from Discover", value=bool(p.get("hidden")), key="me_hidden",
                       help="Nobody new will see you. Your links and chats stay.")
    if hidden != bool(p.get("hidden")):
        if social_db.save_profile(uid, {"hidden": int(hidden)}):
            st.toast("You're hidden 👻" if hidden else "You're visible again ✨")
            st.rerun()


def _quiz_tab(uid: int):
    q = social_db.load_quiz_summaries([uid]).get(uid)
    if q and q.get("result"):
        shared = ("Matches who took it too see your result, your freak score and only the hidden "
                  "desires you both share." if q.get("shared") else
                  "You took this before results were shown to matches, so it stays private. "
                  "Retake the quiz to share it with your links.")
        st.html(f"""
<div class="hd-card" style="padding:20px;">
  <div class="hd-kicker">Read Between The Lines</div>
  <div class="hd-title" style="font-size:32px;">{esc(q['result'])}</div>
  <div class="hd-sub">Freak score {int(q.get('openness') or 0)}% ·
    {len(q.get('signals') or [])} hidden desires. {shared}</div>
</div>""")
        label = "Retake the quiz →"
    else:
        st.html('<div class="hd-card" style="padding:20px;"><div class="hd-title" style="font-size:28px;">'
                'Read Between The Lines</div><div class="hd-sub">Take the quiz and your heat scores get real — '
                'it counts for 65% of every one. Links who took it too see your result, your '
                'freak score and only the hidden desires you both share. Never your individual answers.</div></div>')
        label = "Take the quiz →"
    st.html("<div style='height:10px'></div>")
    if st.button(label, type="primary", use_container_width=True, key="me_quiz"):
        open_quiz("me")
    if q and q.get("result"):
        from Pages.quiz_reveal import drop_codes_section
        drop_codes_section(uid)


def _safety_tab(uid: int):
    st.html("""
<div class="hd-card" style="padding:18px 20px;margin-bottom:12px;">
  <div class="hd-kicker" style="margin-bottom:6px;">Link up smart</div>
  <div class="hd-why" style="margin:0;padding:0;border:0;">
    <div>🍸 &nbsp;First time? Meet somewhere public before anywhere private</div>
    <div>📍 &nbsp;Send a friend the name, the spot and the time</div>
    <div>🗣 &nbsp;Consent is out loud, every time — and anyone can change their mind</div>
    <div>🛡 &nbsp;Bring protection. Don't rely on them to</div>
    <div>🥃 &nbsp;Watch your drink. Keep your own ride home</div>
    <div>💸 &nbsp;Never send money. Anyone asking gets reported</div>
  </div>
</div>""")
    st.html('<div class="hd-sub" style="margin-bottom:12px;">Report anyone who makes you uncomfortable '
            '— from their card in Discover or their chat in Links, under ⚑.</div>')
    blocked = social_db.load_blocked(uid)
    st.html('<div class="hd-kicker" style="margin:8px 0;">Blocked</div>')
    if not blocked:
        st.caption("You haven't blocked anyone.")
    for b in blocked:
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            st.html(f'<div class="hd-sub" style="color:var(--text);">{esc(b["username"])}</div>')
        with c2:
            if st.button("Unblock", key=f"unblock_{b['user_id']}", use_container_width=True):
                social_db.unblock_user(uid, b["user_id"])
                st.session_state.pop("disc_people", None)
                st.rerun()


def me_page():
    uid = _uid()
    p = social_db.get_profile(uid) or {"username": (st.session_state.get("user") or {}).get("username")}
    _masthead(uid, p)
    _hide_toggle(uid, p)

    from Pages.admin import is_admin
    admin = is_admin(st.session_state.get("user"))
    tabs = st.tabs(["Profile", "Quiz", "Safety", "Account"] + (["Reports"] if admin else []))
    t_profile, t_quiz, t_safety, t_account = tabs[:4]
    with t_profile:
        if profile_form(uid, p, "me", "Save changes"):
            st.toast("Saved ✨")
            st.rerun()
    with t_quiz:
        _quiz_tab(uid)
    with t_safety:
        _safety_tab(uid)
    with t_account:
        from Pages.settings import settings_page
        settings_page()
        st.html("<div style='height:10px'></div>")
        if st.button("❔  How Hidden works", use_container_width=True, key="me_intro"):
            from Pages.intro import open_intro
            open_intro("me")
        if st.button("⎋  Log out", use_container_width=True, key="me_logout"):
            from auth import logout
            logout()
    if admin:
        with tabs[4]:
            from Pages.admin import admin_page
            admin_page(uid)
