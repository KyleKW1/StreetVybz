"""
Pages/discover.py — Meet people nearby who live like you. One card at a time.
"""

import time

import streamlit as st

import social_db
from matching import rank_candidates
from ui import (esc, header, empty_state, avatar, intent_chips,
                lifestyle_chips, score_ring)

_QUEUE_TTL = 300  # re-rank at most every 5 minutes


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def _load_queue(uid: int, me: dict) -> list:
    me = {**me, "quiz": social_db.load_quiz_summaries([uid]).get(uid)}
    queue = rank_candidates(me, social_db.load_candidate_pool(uid))
    st.session_state.disc_queue = queue
    st.session_state.disc_loaded_at = time.time()
    return queue


def _card(c: dict):
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
  <div class="hd-chips">{intent_chips(c['shared_intents'])}{lifestyle_chips(c)}</div>
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


def discover_page():
    uid = _uid()
    me = social_db.get_profile(uid) or {}

    if st.session_state.get("just_matched"):
        _its_a_match(st.session_state.just_matched)
        return

    header("Discover", "Who's around", "Ranked by how much you vibe — lifestyle + quiz answers.")

    if me.get("hidden"):
        st.info("👻 You're hidden, so nobody can see you right now. Turn it off in **Me** to show up again.")
    if me.get("location_mode") == "live" and me.get("lat") is None:
        st.warning("📍 Share your location in **Me** to see distances — for now we're matching you by city.")

    queue = st.session_state.get("disc_queue")
    if queue is None or time.time() - st.session_state.get("disc_loaded_at", 0) > _QUEUE_TTL:
        with st.spinner("Finding people…"):
            queue = _load_queue(uid, me)

    if not queue:
        empty_state("🌙", "No one new nearby",
                    "Try a bigger distance or age range in Me, or check back later tonight.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↻ Refresh", use_container_width=True, key="disc_refresh"):
                st.session_state.pop("disc_queue", None)
                st.rerun()
        with c2:
            if st.button("See people I passed", use_container_width=True, key="disc_reset"):
                social_db.reset_passes(uid)
                st.session_state.pop("disc_queue", None)
                st.rerun()
        return

    c = queue[0]
    _card(c)

    st.html("<div style='height:12px'></div>")
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
            f'{more} more {"person" if more == 1 else "people"} nearby</div>')
