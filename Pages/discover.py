"""
Pages/discover.py — Who's up for it nearby.

Two views:
  • Nearby — a grid of everyone who fits you (and you fit them), free tonight
    first, then by heat. Tap anyone to see their profile and send a link request.
  • Tonight posts — say what you're on tonight; it's gone at 6am. Reply to a
    post with a link request.

A link request is a short note. They accept (chat opens with your note as the
first message) or ignore it (you're never told). Nobody can message you
without you saying yes first.
"""

import random
import time

import streamlit as st

import social_db
from matching import (rank_candidates, filter_reasons, describe, quiz_match,
                      INTENTS, norm_intent)
from ui import (esc, header, avatar, intent_chips, lifestyle_chips, setup_chips,
                score_ring, open_quiz, invite_link)

_TTL = 120   # re-load the grid at most every 2 minutes

OPENERS = [
    "You free tonight?",
    "Your vibe is a lot. I'm into it.",
    "Your place or mine?",
    "Drinks first, then we'll see?",
    "I read between the lines on your profile. Link?",
    "Heat score doesn't lie. Wanna find out?",
    "Not looking for a date. Looking for you, tonight.",
    "What are you on later?",
    "Saw your post. I'm close. Say the word.",
    "Quiz says we fit. Let's test it.",
]

POST_IDEAS = [
    "Free after 10, Kingston side. Drinks then see where it goes.",
    "Can host tonight. Chill vibe, 420 friendly.",
    "Out at a party later. Come find me.",
    "Bored and up for something. Who's close?",
]


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def _my_quiz(uid: int):
    if "my_quiz" not in st.session_state:
        st.session_state.my_quiz = social_db.load_quiz_summaries([uid]).get(uid)
    return st.session_state.my_quiz


def _me_with_quiz(uid: int, me: dict) -> dict:
    return {**me, "quiz": _my_quiz(uid)}


def _load_people(uid: int, me: dict) -> list:
    me = _me_with_quiz(uid, me)
    pool = social_db.load_candidate_pool(uid)
    people = rank_candidates(me, pool, tonight=social_db.tonight())
    st.session_state.disc_people = people
    st.session_state.disc_filtered = filter_reasons(me, pool)
    st.session_state.disc_loaded_at = time.time()
    return people


def _people_now(uid: int, me: dict) -> list:
    people = st.session_state.get("disc_people")
    if people is None or time.time() - st.session_state.get("disc_loaded_at", 0) > _TTL:
        with st.spinner("Finding who's around…"):
            people = _load_people(uid, me)
    return people


def refresh():
    """Make the grid reload on the next run (after profile, quiz or block changes)."""
    st.session_state.pop("disc_people", None)


# ─── PROFILE CARD ────────────────────────────────────────────────────────────

def _quiz_chip(c: dict, my_quiz) -> str:
    """Quiz match % when both took it; otherwise flag that they took it (so you might too)."""
    if not c.get("quiz"):
        return ""
    pct = quiz_match(my_quiz, c["quiz"])
    return (f'<span class="hd-chip lime">🎯 Quiz match {pct}%</span>' if pct is not None
            else '<span class="hd-chip lime">🎯 Took the quiz</span>')


def person_card(c: dict, my_quiz=None):
    reasons = "".join(f"<div>✦ {esc(r)}</div>" for r in c["reasons"])
    why = ('<div class="hd-why"><div class="hd-kicker" style="margin-bottom:6px;">'
           f"Reading between the lines</div>{reasons}</div>") if reasons else ""
    bio = (f'<div class="hd-sub" style="margin-top:12px;color:var(--text);">“{esc(c["bio"])}”</div>'
           if c.get("bio") else "")
    where = f'📍 {esc(c["where"])}' if c.get("where") else ""
    st.html(f"""
<div class="hd-card{' hot' if c['score'] >= 75 or c.get('free_tonight') else ''}">
  <div style="display:flex;align-items:center;gap:16px;">
    {avatar(c['username'], c['user_id'])}
    <div style="flex:1;min-width:0;">
      <div class="hd-title" style="font-size:34px;margin:0;display:flex;align-items:baseline;">
        <span class="hd-name">{esc(c['username'])}</span><span
           style="color:var(--soft);font-size:26px;flex-shrink:0;">{', ' + str(c['age']) if c.get('age') else ''}</span></div>
      <div class="hd-kicker" style="margin-top:4px;">{where}</div>
    </div>
    {score_ring(c['score'])}
  </div>
  <div class="hd-chips">{setup_chips(c, c.get('free_tonight'))}{_quiz_chip(c, my_quiz)}{intent_chips(c['shared_intents'])}{lifestyle_chips(c)}</div>
  {bio}
  {why}
</div>
""")


def quoted_post(body: str, label: str = "Their post tonight"):
    st.html(f'<div class="hd-post-quote"><div class="hd-kicker" style="margin-bottom:4px;">'
            f'📌 {esc(label)}</div>{esc(body)}</div>')


# ─── NEARBY GRID ─────────────────────────────────────────────────────────────

_STATE_BADGE = {
    "linked":   '<span class="hd-tile-badge lime">✓ Linked</span>',
    "sent":     '<span class="hd-tile-badge">⏳ Asked</span>',
    "received": '<span class="hd-tile-badge magenta">📩 Wants you</span>',
}


def _tile(c: dict, state: str | None) -> str:
    near = c["where"].replace(" away", "").replace("In ", "")
    badge = _STATE_BADGE.get(state, "") or ('<span class="hd-tile-badge lime">🔥 Tonight</span>'
                                            if c.get("free_tonight") else "")
    return (f'<div class="hd-tile{" hot" if c.get("free_tonight") else ""}">'
            f'{avatar(c["username"], c["user_id"], small=True)}'
            f'<div class="hd-tile-name">{esc(c["username"])}, {c["age"]}</div>'
            f'<div class="hd-tile-meta">{esc(near)} · <b>{c["score"]}%</b></div>'
            f'<div class="hd-tile-badges">{badge}</div></div>')


def _open_profile(c: dict, post: dict | None = None):
    st.session_state.disc_view = {"person": c, "post": post}
    st.rerun()


def _grid(people: list, states: dict, cols: int = 3):
    for r in range(0, len(people), cols):
        row = people[r:r + cols]
        with st.container(key=f"grow_{r}"):
            columns = st.columns(cols)
            for col, c in zip(columns, row):
                with col:
                    st.html(_tile(c, states.get(c["user_id"], (None,))[0]))
                    if st.button("View", key=f"view_{c['user_id']}", use_container_width=True):
                        _open_profile(c)


# ─── PROFILE VIEW + LINK REQUEST ─────────────────────────────────────────────

def _opener(key: str):
    st.session_state[key] = random.choice(OPENERS)


def _go_chat(match_id: int):
    st.session_state.pop("disc_view", None)
    st.session_state.open_match = match_id
    st.session_state.tab = "matches"
    st.rerun()


def _request_form(uid: int, c: dict, post: dict | None):
    key = f"note_{c['user_id']}"
    st.html('<div class="hd-kicker" style="margin:16px 0 6px;">Send a link request</div>')
    with st.container(key=f"qrow_note_{c['user_id']}"):
        c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
        with c1:
            note = st.text_input("Your note", key=key, max_chars=300, label_visibility="collapsed",
                                 placeholder="Say what you're on. Keep it short.")
        with c2:
            st.button("🎲", key=f"opener_{c['user_id']}", on_click=_opener, args=(key,),
                      help="Suggest an opener", use_container_width=True)
    st.caption(f"{c['username']} sees your note and your profile. If they accept, chat opens. "
               "If not, nothing happens — you won't be told.")
    if st.button("🔥  Send link request", type="primary", use_container_width=True,
                 key=f"send_{c['user_id']}"):
        if len((note or "").strip()) < 2:
            st.error("Add a note — even a couple words.")
            return
        status, match_id = social_db.send_link_request(uid, c["user_id"], note,
                                                       (post or {}).get("id"))
        if status == "linked":
            st.balloons()
            st.toast(f"{c['username']} already asked you — you're linked 🔥")
            _go_chat(match_id)
        elif status == "already":
            _go_chat(match_id)
        elif status == "sent":
            st.toast(f"Sent. If {c['username']} is up for it, chat opens in Links 🔥")
            st.rerun()
        elif status == "limit":
            st.error(f"That's {social_db.REQUESTS_PER_DAY} requests today. Try again tomorrow.")
        elif status == "blocked":
            st.error("You can't send requests to this person.")
        else:
            st.error("Didn't send — try again.")


def _profile_view(uid: int, me: dict):
    view = st.session_state.disc_view
    c, post = view["person"], view.get("post")
    if st.button("← Back", key="disc_back"):
        st.session_state.pop("disc_view", None)
        st.rerun()

    person_card(c, _my_quiz(uid))
    if post:
        quoted_post(post["body"])

    state, ref = social_db.link_states(uid).get(c["user_id"], (None, None))
    if state == "linked":
        st.html('<div class="hd-sub" style="margin:14px 0 8px;">✓ You\'re linked.</div>')
        if st.button("Open chat →", type="primary", use_container_width=True, key="disc_chat"):
            _go_chat(ref)
    elif state == "received":
        req = next((r for r in social_db.load_incoming_requests(uid) or []
                    if r["request_id"] == ref), None)
        if req:
            quoted_post(req["note"], f"{c['username']} sent you a request")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ignore", use_container_width=True, key="disc_ignore"):
                social_db.ignore_link_request(uid, ref)
                st.session_state.pop("disc_view", None)
                st.rerun()
        with c2:
            if st.button("🔥  Accept", type="primary", use_container_width=True, key="disc_accept"):
                match_id = social_db.accept_link_request(uid, ref)
                if match_id:
                    _go_chat(match_id)
                st.error("Couldn't accept — try again.")
    elif state == "sent":
        st.html('<div class="hd-card" style="padding:14px 18px;margin-top:12px;">'
                '<div class="hd-sub">⏳ Request sent. If they\'re up for it, chat opens in '
                '<b style="color:var(--text);">Links</b>.</div></div>')
    else:
        _request_form(uid, c, post)

    with st.container(key="disc_report"):
        if st.button("⚑ Report or block", type="tertiary", key=f"report_{c['user_id']}"):
            _report_dialog(uid, c)


# ─── TONIGHT POSTS ───────────────────────────────────────────────────────────

def _post_idea(key: str):
    st.session_state[key] = random.choice(POST_IDEAS)


def _my_post_box(uid: int):
    mine = social_db.my_post(uid)
    if mine and not st.session_state.get("post_editing"):
        st.html(f'<div class="hd-card hot" style="padding:16px 18px;">'
                f'<div class="hd-kicker" style="margin-bottom:6px;">Your post · gone at 6am</div>'
                f'<div class="hd-sub" style="color:var(--text);font-size:15px;">{esc(mine["body"])}</div></div>')
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Edit", use_container_width=True, key="post_edit"):
                st.session_state.post_editing = True
                st.session_state.post_body = mine["body"]
                st.rerun()
        with c2:
            if st.button("Take it down", use_container_width=True, key="post_delete"):
                social_db.delete_post(uid)
                st.rerun()
        return

    with st.container(key="qrow_post"):
        c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
        with c1:
            body = st.text_area("What are you on tonight?", key="post_body", max_chars=280, height=80,
                                placeholder="Where you'll be, what you're up for, host or travel…")
        with c2:
            st.button("🎲", key="post_idea", on_click=_post_idea, args=("post_body",),
                      help="Give me an idea", use_container_width=True)
    st.caption("Only people who fit you see it. Don't post your exact address. Gone at 6am.")
    if st.button("📌  Post for tonight", type="primary", use_container_width=True, key="post_send"):
        if len((body or "").strip()) < 4:
            st.error("Say a bit more.")
        elif social_db.save_post(uid, body):
            st.session_state.pop("post_editing", None)
            st.toast("Posted until 6am 📌")
            st.rerun()
        else:
            st.error("Couldn't post — try again.")


def _posts(uid: int, me: dict, posts: list, states: dict):
    _my_post_box(uid)
    st.html("<div style='height:14px'></div>")
    if not posts:
        st.html('<div class="hd-card" style="text-align:center;padding:28px 20px;">'
                '<div style="font-size:36px;">📌</div>'
                '<div class="hd-title" style="font-size:24px;">No posts yet tonight</div>'
                '<div class="hd-sub">Be the first. People who fit you will see it.</div></div>')
        return
    for p in posts:
        state = states.get(p["user_id"], (None,))[0]
        st.html(f"""
<div class="hd-card" style="padding:16px 18px;margin-bottom:6px;">
  <div style="display:flex;align-items:center;gap:12px;">
    {avatar(p['username'], p['user_id'], small=True)}
    <div style="flex:1;min-width:0;">
      <div class="hd-title" style="font-size:22px;margin:0;">{esc(p['username'])}, {p['age']}</div>
      <div class="hd-kicker">📍 {esc(p['where'])} · {str(p.get('posted_at') or '')[11:16]}</div>
    </div>
    <div class="hd-tile-meta" style="font-size:12px;"><b>{p['score']}%</b> heat</div>
  </div>
  <div class="hd-sub" style="color:var(--text);font-size:15px;margin-top:10px;">{esc(p['body'])}</div>
  <div class="hd-chips" style="margin-bottom:0;">{setup_chips(p, p.get('free_tonight'))}</div>
</div>""")
        label = {"linked": "Open chat", "sent": "⏳ Asked", "received": "📩 They asked you"}.get(state, "Reply →")
        if st.button(label, key=f"reply_{p['post_id']}", use_container_width=True,
                     type="primary" if state is None else "secondary", disabled=state == "sent"):
            if state == "linked":
                _go_chat(states[p["user_id"]][1])
            _open_profile(p, {"id": p["post_id"], "body": p["body"]})
        st.html("<div style='height:10px'></div>")


def _load_posts(uid: int, me: dict) -> list:
    me = _me_with_quiz(uid, me)
    raw = social_db.load_posts(uid) or []
    quiz = social_db.load_quiz_summaries([p["user_id"] for p in raw]) if raw else {}
    out = []
    for p in raw:
        d = describe(me, {**p, "quiz": quiz.get(p["user_id"])}, tonight=social_db.tonight())
        if d:
            out.append(d)
    return out


# ─── EMPTY GRID ──────────────────────────────────────────────────────────────

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
                "who you're into, or what you're looking for.", True)
    most, who = ("they're", "they") if share == 1 else ("most are", "most")
    want = INTENTS.get(norm_intent(me.get("intent")), "the same thing").lower()
    text = {
        "my_ages":    f"{most} outside your age range ({me.get('age_min') or 18}–{me.get('age_max') or 99}).",
        "their_ages": f"you're outside the age range {who} want.",
        "intent":     f"{most} not looking for {want}.",
        "gender":     f"{most} not a fit for who you're into, or who they're into.",
    }[reason]
    return f"{_people(f['nearby'])} nearby, but {text}", reason != "their_ages"


def _goto_me():
    st.session_state.tab = "me"
    st.rerun()


def _nobody_yet(uid: int, me: dict):
    """Empty grid: say why, and put the one thing that would help first."""
    size = social_db.community_size(uid, me.get("city"))
    if size is None:
        st.html('<div class="hd-card" style="text-align:center;padding:36px 24px;">'
                '<div style="font-size:44px;margin-bottom:6px;">📡</div>'
                '<div class="hd-title" style="font-size:30px;">Can&#39;t load people right now</div>'
                '<div class="hd-sub">Hidden is having trouble connecting. Give it a moment.</div></div>')
        if st.button("↻ Try again", type="primary", use_container_width=True, key="disc_refresh"):
            refresh()
            st.rerun()
        return

    city = (me.get("city") or "your area").strip().title()
    filtered = _filter_story(me, st.session_state.get("disc_filtered") or {})
    action = None
    if filtered:
        headline, (sub, fixable) = "Nobody fits your filters", filtered
        if fixable:
            action = ("Change my filters →", "empty_me", _goto_me)
    elif size["total"] == 0:
        headline, sub = "You're one of the first", "Nobody else is on Hidden yet. Get a few people on and it comes alive."
    elif size["in_city"] == 0:
        headline = f"No one in {city} yet"
        sub = f"{_people(size['total'])} {'is' if size['total'] == 1 else 'are'} on Hidden, just not near you."
    else:
        headline, sub = "Nobody else around right now", "New people show up here as they join."
    st.html(f'<div class="hd-card" style="text-align:center;padding:36px 24px;">'
            f'<div style="font-size:44px;margin-bottom:6px;">🌙</div>'
            f'<div class="hd-title" style="font-size:30px;">{esc(headline)}</div>'
            f'<div class="hd-sub">{esc(sub)}</div></div>')
    if action:
        label, key, handler = action
        if st.button(label, type="primary", use_container_width=True, key=key):
            handler()

    st.html('<div class="hd-kicker" style="margin:22px 0 0;">While you wait</div>')
    if not _my_quiz(uid):
        _step("🎯", "Take the quiz", "Read Between The Lines is 65% of your heat score. About 5 minutes.")
        if st.button("Take the quiz →", type="secondary" if action else "primary",
                     use_container_width=True, key="empty_quiz"):
            open_quiz("discover")
    _step("📣", "Bring your people", "Hidden gets better with every person nearby. Send them this link:")
    st.code(f"Come find me on Hidden 👀 {invite_link()}", language=None, wrap_lines=True)
    if size["total"] and not size["in_city"] and me.get("location_mode") != "live":
        _step("📍", "Look beyond " + city, "Switch to live location in Me to see people within your distance, not just your city.")
        if st.button("Open Me", use_container_width=True, key="empty_me2"):
            _goto_me()
    st.html("<div style='height:10px'></div>")
    if st.button("↻ Check again", use_container_width=True, key="disc_refresh"):
        refresh()
        st.rerun()


# ─── SAFETY ──────────────────────────────────────────────────────────────────

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
        refresh()
        st.session_state.pop("disc_view", None)
        st.toast("Blocked." if reason == "Just block them" else "Report sent. Thanks for keeping Hidden safe.")
        st.rerun()


def _free_tonight_toggle(uid: int, me: dict):
    free = social_db.is_free_tonight(me)
    on = st.toggle("🔥  I'm free tonight", value=free, key="disc_free",
                   help="Puts you first in the grid for people nearby. Switches itself off at 6am.")
    if on != free:
        if social_db.set_free_tonight(uid, on):
            st.toast("You're showing as free tonight 🔥" if on else "Free tonight is off")
            st.rerun()
        else:
            st.error("Couldn't update — try again.")


def _quiz_nudge():
    with st.container(key="qnudge"):
        c1, c2 = st.columns([3, 1.3], vertical_alignment="center")
        with c1:
            st.html('<div class="hd-sub" style="line-height:1.35;"><b style="color:var(--text);">'
                    '🎯 Read Between The Lines</b><br>65% of every heat score</div>')
        with c2:
            if st.button("Take quiz", key="disc_quiz_nudge", use_container_width=True):
                open_quiz("discover")


# ─── PAGE ────────────────────────────────────────────────────────────────────

def discover_page():
    uid = _uid()
    me = social_db.get_profile(uid) or {}

    if st.session_state.get("disc_view"):
        _profile_view(uid, me)
        return

    header("Discover", "Who's up for it")
    _free_tonight_toggle(uid, me)
    if me.get("hidden"):
        st.info("👻 You're hidden, so nobody can see you right now. Turn it off in **Me** to show up again.")
    if me.get("location_mode") == "live" and me.get("lat") is None:
        st.warning("📍 Share your location in **Me** to see distances — for now it's by city.")

    people = _people_now(uid, me)
    posts = _load_posts(uid, me)
    states = social_db.link_states(uid)

    mode = st.segmented_control(
        "View", ["nearby", "posts"], default="nearby",
        key="disc_mode", required=True, label_visibility="collapsed", width="stretch",
        format_func=lambda k: f"👀 Nearby · {len(people)}" if k == "nearby"
        else f"📌 Tonight posts · {len(posts)}")

    if people and not _my_quiz(uid):
        _quiz_nudge()

    if mode == "posts":
        _posts(uid, me, posts, states)
        return

    if not people:
        _nobody_yet(uid, me)
        return
    st.html('<div class="hd-kicker" style="margin:4px 0 10px;">Free tonight first · then by heat</div>')
    _grid(people, states)
