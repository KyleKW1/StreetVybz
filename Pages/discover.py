"""
Pages/discover.py — Meet people nearby who live like you. One card at a time.
"""

import time

import streamlit as st

import social_db
from matching import rank_candidates, filter_reasons, quiz_match, INTENTS
from ui import (esc, header, avatar, intent_chips, lifestyle_chips,
                score_ring, open_quiz, invite_link)

_QUEUE_TTL = 300  # re-rank at most every 5 minutes


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def _my_quiz(uid: int):
    if "my_quiz" not in st.session_state:
        st.session_state.my_quiz = social_db.load_quiz_summaries([uid]).get(uid)
    return st.session_state.my_quiz


def _load_queue(uid: int, me: dict) -> list:
    me = {**me, "quiz": _my_quiz(uid)}
    pool = social_db.load_candidate_pool(uid)
    queue = rank_candidates(me, pool)
    st.session_state.disc_queue = queue
    st.session_state.disc_filtered = filter_reasons(me, pool)
    st.session_state.disc_loaded_at = time.time()
    return queue


def _quiz_chip(c: dict, my_quiz) -> str:
    """Quiz match % when both took it; otherwise flag that they took it (so you might too)."""
    if not c.get("quiz"):
        return ""
    pct = quiz_match(my_quiz, c["quiz"])
    return (f'<span class="hd-chip lime">🎯 Quiz match {pct}%</span>' if pct is not None
            else '<span class="hd-chip lime">🎯 Took the quiz</span>')


def _card(c: dict, my_quiz=None):
    reasons = "".join(f"<div>✦ {esc(r)}</div>" for r in c["reasons"])
    why = ('<div class="hd-why"><div class="hd-kicker" style="margin-bottom:6px;">'
           f"Why you'd vibe</div>{reasons}</div>") if reasons else ""
    bio = (f'<div class="hd-sub" style="margin-top:12px;color:var(--text);">“{esc(c["bio"])}”</div>'
           if c.get("bio") else "")
    st.html(f"""
<div class="hd-card{' hot' if c['score'] >= 75 else ''}">
  <div style="display:flex;align-items:center;gap:16px;">
    {avatar(c['username'], c['user_id'])}
    <div style="flex:1;min-width:0;">
      <div class="hd-title" style="font-size:34px;margin:0;display:flex;align-items:baseline;">
        <span class="hd-name">{esc(c['username'])}</span><span
           style="color:var(--soft);font-size:26px;flex-shrink:0;">, {c['age']}</span></div>
      <div class="hd-kicker" style="margin-top:4px;">📍 {esc(c['where'])}</div>
    </div>
    {score_ring(c['score'])}
  </div>
  <div class="hd-chips">{_quiz_chip(c, my_quiz)}{intent_chips(c['shared_intents'])}{lifestyle_chips(c)}</div>
  {bio}
  {why}
</div>
""")


def _its_a_match(m: dict):
    st.balloons()
    st.html(f"""
<div class="hd-card hot" style="text-align:center;padding:40px 24px;">
  <div style="font-size:56px;animation:hd-pop .7s both;">💘</div>
  <div class="hd-brand" style="font-size:48px;margin:6px 0;">IT'S A MATCH</div>
  <div class="hd-sub">You and <b style="color:var(--text);">{esc(m['name'])}</b> both said yes.<br>
  Before you can chat, you each ask 3 questions — blind. Answers reveal together.</div>
</div>
""")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Keep swiping", use_container_width=True, key="match_keep"):
            st.session_state.pop("just_matched", None)
            st.rerun()
    with c2:
        if st.button("Start the Q&A →", type="primary", use_container_width=True, key="match_go"):
            st.session_state.pop("just_matched", None)
            st.session_state.open_match = m["id"]
            st.session_state.tab = "matches"
            st.rerun()


def _quiz_nudge(c: dict):
    # One slim row (text + button side by side, even on phones) so the card stays on screen
    line = (f"{esc(c['username'])} took it. See your quiz match" if c.get("quiz")
            else "Take the 5-minute quiz")
    with st.container(key="qnudge"):
        c1, c2 = st.columns([3, 1.3], vertical_alignment="center")
        with c1:
            st.html('<div class="hd-sub" style="line-height:1.35;"><b style="color:var(--text);">'
                    f'🎯 Sharper matches</b><br>{line}</div>')
        with c2:
            if st.button("Take quiz", key="disc_quiz_nudge", use_container_width=True):
                open_quiz("discover")


def _step(icon: str, title: str, text: str):
    st.html(f'<div style="display:flex;gap:14px;align-items:flex-start;margin:18px 0 8px;">'
            f'<div style="font-size:26px;line-height:1;">{icon}</div><div>'
            f'<div class="hd-title" style="font-size:22px;margin:0;">{esc(title)}</div>'
            f'<div class="hd-sub">{esc(text)}</div></div></div>')


def _people(n: int) -> str:
    return f"{n} {'person' if n == 1 else 'people'}"


def _filter_story(me: dict, f: dict) -> tuple[str, bool] | None:
    """(why nobody nearby shows up, whether changing my own settings would help)."""
    blocked = {k: f[k] for k in ("my_ages", "their_ages", "intent", "gender") if f.get(k)}
    if not f.get("nearby") or not blocked:
        return None
    reason = max(blocked, key=blocked.get)
    share = blocked[reason] / f["nearby"]
    if share <= 0.5:
        return (f"{_people(f['nearby'])} nearby, but none match your age range, "
                "who you date, or what you're looking for.", True)
    most, who = ("they're", "they") if share == 1 else ("most are", "most")
    want = INTENTS.get(me.get("intent"), "the same thing").lower()
    text = {
        "my_ages":    f"{most} outside your age range ({me.get('age_min') or 18}–{me.get('age_max') or 99}).",
        "their_ages": f"you're outside the age range {who} want.",
        "intent":     f"{most} not looking for {want}.",
        "gender":     f"{most} not a fit for who you want to date, or who they do.",
    }[reason]
    return f"{_people(f['nearby'])} nearby, but {text}", reason != "their_ages"


def _goto_me():
    st.session_state.tab = "me"
    st.rerun()


def _nobody_yet(uid: int, me: dict):
    """Empty Discover: say why, and put the one thing that would help first."""
    size = social_db.community_size(uid, me.get("city"))
    if size is None:
        st.html('<div class="hd-card" style="text-align:center;padding:36px 24px;">'
                '<div style="font-size:44px;margin-bottom:6px;">📡</div>'
                '<div class="hd-title" style="font-size:30px;">Can&#39;t load people right now</div>'
                '<div class="hd-sub">Hidden is having trouble connecting. Give it a moment.</div></div>')
        if st.button("↻ Try again", type="primary", use_container_width=True, key="disc_refresh"):
            st.session_state.pop("disc_queue", None)
            st.rerun()
        return

    city = (me.get("city") or "your area").strip().title()
    filtered = _filter_story(me, st.session_state.get("disc_filtered") or {})
    action = None   # (label, key, handler) — the one primary button for this case
    if filtered:
        headline, (sub, fixable) = "Nobody fits your filters", filtered
        if fixable:
            action = ("Change my filters →", "empty_me", _goto_me)
    elif size["total"] == 0:
        headline, sub = "You're one of the first", "Nobody else is on Hidden yet. Invite a few people and you'll have someone to meet."
    elif size["in_city"] == 0 and not size["passed"]:
        headline = f"No one in {city} yet"
        sub = f"{_people(size['total'])} {'is' if size['total'] == 1 else 'are'} on Hidden, just not near you."
    elif size["passed"]:
        headline = "You've seen everyone nearby"
        sub = f"New people show up here as they join. You passed on {_people(size['passed'])}."
        def _again():
            social_db.reset_passes(uid)
            st.session_state.pop("disc_queue", None)
            st.rerun()
        action = (f"Give {'them' if size['passed'] > 1 else 'it'} another look →", "disc_reset", _again)
    else:
        headline = "You've seen everyone nearby"
        sub = "You liked everyone here. If they like you back, it's a match. New people show up as they join."
    st.html(f'<div class="hd-card" style="text-align:center;padding:36px 24px;">'
            f'<div style="font-size:44px;margin-bottom:6px;">🌙</div>'
            f'<div class="hd-title" style="font-size:30px;">{esc(headline)}</div>'
            f'<div class="hd-sub">{esc(sub)}</div></div>')
    if action:
        st.html("<div style='height:4px'></div>")
        label, key, handler = action
        if st.button(label, type="primary", use_container_width=True, key=key):
            handler()

    st.html('<div class="hd-kicker" style="margin:22px 0 0;">While you wait</div>')

    if not _my_quiz(uid):
        _step("🎯", "Take the quiz", "Your answers make every future match smarter. About 5 minutes.")
        if st.button("Take the quiz →", type="secondary" if action else "primary",
                     use_container_width=True, key="empty_quiz"):
            open_quiz("discover")

    _step("📣", "Bring your people", "Hidden gets better with every person nearby. Send them this link:")
    st.code(f"Come find me on Hidden 👀 {invite_link()}", language=None, wrap_lines=True)

    if size["total"] and not size["in_city"] and me.get("location_mode") != "live":
        _step("📍", "Look beyond " + city, "Switch to live location in Me to see people within your distance, not just your city.")
        if st.button("Open Me", use_container_width=True, key="empty_me"):
            _goto_me()

    st.html("<div style='height:10px'></div>")
    if st.button("↻ Check again", use_container_width=True, key="disc_refresh"):
        st.session_state.pop("disc_queue", None)
        st.rerun()


@st.dialog("Report or block")
def _report_dialog(uid: int, c: dict):
    from Pages.matches import REPORT_REASONS
    st.html(f'<div class="hd-sub">{esc(c["username"])} won\'t see you again, and you won\'t see them. '
            "They aren't told.</div>")
    reason = st.selectbox("What's wrong?", ["Just block them"] + REPORT_REASONS, key="disc_rep_reason")
    details = ""
    if reason != "Just block them":
        details = st.text_area("Anything else we should know? (optional)", key="disc_rep_details",
                               max_chars=1000, height=80)
    label = "Block" if reason == "Just block them" else "Report and block"
    if st.button(label, type="primary", use_container_width=True, key="disc_rep_send"):
        if reason != "Just block them" and not social_db.report_user(uid, c["user_id"], reason, details):
            st.error("Couldn't send the report — try again.")
            return
        social_db.block_user(uid, c["user_id"])
        st.session_state.disc_queue = [q for q in st.session_state.get("disc_queue") or []
                                       if q["user_id"] != c["user_id"]]
        st.toast("Blocked." if reason == "Just block them" else "Report sent. Thanks for keeping Hidden safe.")
        st.rerun()


def discover_page():
    uid = _uid()
    me = social_db.get_profile(uid) or {}

    if st.session_state.get("just_matched"):
        _its_a_match(st.session_state.just_matched)
        return

    queue = st.session_state.get("disc_queue")
    if queue is None or time.time() - st.session_state.get("disc_loaded_at", 0) > _QUEUE_TTL:
        with st.spinner("Finding people…"):
            queue = _load_queue(uid, me)

    if queue:
        # Compact heading when there's a card, so Like/Pass fit on a phone screen
        st.html('<div class="hd-kicker" style="margin:2px 0 10px;">Who\'s around · best vibe first</div>')
    else:
        header("Discover", "Who's around")

    if me.get("hidden"):
        st.info("👻 You're hidden, so nobody can see you right now. Turn it off in **Me** to show up again.")
    if me.get("location_mode") == "live" and me.get("lat") is None:
        st.warning("📍 Share your location in **Me** to see distances — for now we're matching you by city.")

    if not queue:
        _nobody_yet(uid, me)
        return

    c = queue[0]
    if not _my_quiz(uid):
        _quiz_nudge(c)
    _card(c, _my_quiz(uid))

    with st.container(key="swipe"):
        col_pass, col_like = st.columns(2)
        with col_pass:
            passed = st.button("✕  Pass", use_container_width=True, key=f"pass_{c['user_id']}")
        with col_like:
            liked = st.button("♥  Like", type="primary", use_container_width=True,
                              key=f"like_{c['user_id']}")

    if passed or liked:
        match_id = social_db.record_swipe(uid, c["user_id"], liked)
        st.session_state.disc_queue = queue[1:]
        if match_id:
            st.session_state.just_matched = {"id": match_id, "name": c["username"]}
        elif liked:
            st.toast(f"Liked {c['username']} — if they like you back, it's a match 💘")
        st.rerun()

    more = len(queue) - 1
    st.html(f'<div class="hd-kicker" style="text-align:center;margin-top:14px;">'
            f'{f"{_people(more)} more nearby" if more else "Last one nearby for now"}</div>')
    with st.container(key="disc_report"):
        if st.button("⚑ Report or block", type="tertiary", key=f"report_{c['user_id']}"):
            _report_dialog(uid, c)
