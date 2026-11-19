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
    intent = INTENTS.get(norm_intent(p.get('intent')), '')
    where = ", ".join(x for x in (esc(p.get('city') or ''), esc(intent).lower()) if x)
    st.html(f"""
<div class="hd" style="margin:6px 0 16px;">
  <div class="hd-row">
    {avatar(p.get('username', ''), uid, lifted=True)}
    <div style="min-width:0;">
      <div class="hd-title hd-name" style="font-size:26px;">{esc(p.get('username', ''))}
        <span style="color:var(--smoke);font-weight:500;font-stretch:100%;">{age_text(p)}</span></div>
      <div class="hd-note" style="font-size:14px;">{where}</div>
    </div>
  </div>
  <div class="hd-chips" style="margin-bottom:0;">{setup_chips(p, social_db.is_free_tonight(p))}{lifestyle_chips(p)}</div>
</div>
""")


def _hide_toggle(uid: int, p: dict):
    hidden = st.toggle("Hide me from Discover", value=bool(p.get("hidden")), key="me_hidden",
                       help="Nobody new will see you. Your links and chats stay.")
    if hidden != bool(p.get("hidden")):
        if social_db.save_profile(uid, {"hidden": int(hidden)}):
            st.toast("You're hidden" if hidden else "You're visible again")
            st.rerun()


def _quiz_tab(uid: int):
    q = social_db.load_quiz_summaries([uid]).get(uid)
    if q and q.get("result"):
        shared = ("Matches who took it too see your result, your freak score and only the hidden "
                  "desires you both share." if q.get("shared") else
                  "You took this before results were shown to matches, so it stays private. "
                  "Retake the quiz to share it with your links.")
        st.html(f"""
<div class="hd-panel">
  <div class="hd-kicker">Read Between The Lines</div>
  <div class="hd-title" style="font-size:28px;margin-top:4px;">{esc(q['result'])}</div>
  <div class="hd-sub">Freak score {int(q.get('openness') or 0)}%, {len(q.get('signals') or [])} hidden desires.
    {shared}</div>
</div>""")
        label = "Retake the quiz"
    else:
        st.html('<div class="hd-panel"><div class="hd-title" style="font-size:24px;">'
                'Read Between The Lines</div><div class="hd-sub">Take the quiz and your heat scores get real: '
                'it counts for 65% of every one. Links who took it too see your result, your '
                'freak score and only the hidden desires you both share. Never your individual answers.</div></div>')
        label = "Take the quiz"
    st.html("<div style='height:10px'></div>")
    if st.button(label, type="primary", use_container_width=True, key="me_quiz"):
        open_quiz("me")
    if q and q.get("result"):
        from Pages.quiz_reveal import drop_codes_section
        drop_codes_section(uid)


def _safety_tab(uid: int):
    st.html("""
<div class="hd-panel" style="margin-bottom:12px;">
  <div class="hd-h3" style="margin:0 0 6px;">Link up smart</div>
  <div class="hd-why" style="margin:0;padding:0;border:0;">
    <div>First time? Meet somewhere public before anywhere private.</div>
    <div>Send a friend the name, the spot and the time.</div>
    <div>Consent is out loud, every time, and anyone can change their mind.</div>
    <div>Bring protection. Don't rely on them to.</div>
    <div>Watch your drink. Keep your own ride home.</div>
    <div>Never send money. Report anyone who asks.</div>
  </div>
</div>""")
    st.html('<div class="hd-sub" style="margin-bottom:12px;">Report anyone who makes you uncomfortable '
            'from their profile in Discover or their chat in Links.</div>')
    blocked = social_db.load_blocked(uid)
    st.html('<div class="hd-h3">Blocked</div>')
    if not blocked:
        st.caption("You haven't blocked anyone.")
    for b in blocked:
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            st.html(f'<div class="hd-sub" style="color:var(--ink);">{esc(b["username"])}</div>')
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
            st.toast("Saved")
            st.rerun()
    with t_quiz:
        _quiz_tab(uid)
    with t_safety:
        _safety_tab(uid)
    with t_account:
        from Pages.settings import settings_page
        settings_page()
        st.html("<div style='height:10px'></div>")
        if st.button("How Hidden works", use_container_width=True, key="me_intro"):
            from Pages.intro import open_intro
            open_intro("me")
        if st.button("Log out", use_container_width=True, key="me_logout"):
            from auth import logout
            logout()
    if admin:
        with tabs[4]:
            from Pages.admin import admin_page
            admin_page(uid)
