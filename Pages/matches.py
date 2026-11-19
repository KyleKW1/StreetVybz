"""
Pages/matches.py — Links: requests for you, your chats, and who you've asked.

A link request is a short note sent from Discover. Accepting it opens a chat
with that note as the first message, plus the Read Between The Lines reveal
(results and the hidden desires you both share). Ignoring it tells nobody.
"""

import streamlit as st

import social_db
from matching import describe
from Pages.quiz_reveal import match_quiz_card, screenshot_shield
from ui import esc, header, section, empty_state, avatar, score_ring, setup_chips

REPORT_REASONS = ["Fake profile / spam", "Seems under 18", "Pushed past a no / ignored consent",
                  "Harassment or threats", "Sent something I didn't ask for",
                  "Asked for money / selling", "Other"]


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def needs_action(uid: int) -> int:
    """Requests waiting on you — the red dot on the Links tab."""
    return social_db.count_incoming_requests(uid)


def _open_chat(match_id: int):
    st.session_state.open_match = match_id
    st.rerun()


# ─── REQUESTS FOR YOU ────────────────────────────────────────────────────────

def _requests(uid: int, me: dict, incoming: list):
    section("Requests for you", len(incoming))
    my_quiz = social_db.load_quiz_summaries([uid] + [r["user_id"] for r in incoming])
    for r in incoming:
        c = describe({**me, "quiz": my_quiz.get(uid)}, {**r, "quiz": my_quiz.get(r["user_id"])},
                     tonight=social_db.tonight(), require_fit=False)
        where = f"<span>{esc(c['where'])}</span>" if c.get("where") else ""
        reasons = "".join(f"<div>{esc(x)}</div>" for x in c["reasons"][:2])
        post = (f'<div class="hd-note" style="margin-top:12px;">Re: your post “{esc(r["post_body"])}”</div>'
                if r.get("post_body") else "")
        st.html(f"""
<div class="hd-row">
  {avatar(c['username'], c['user_id'])}
  <div style="flex:1;min-width:0;">
    <div class="hd-title hd-name">{esc(c['username'])}
      <span style="color:var(--smoke);font-weight:500;font-stretch:100%;">{c['age'] if c.get('age') else ''}</span></div>
    <div class="hd-meta" style="margin-top:2px;font-size:13px;"><span>{str(r.get('requested_at') or '')[11:16]}</span>{where}{score_ring(c['score'])}</div>
  </div>
</div>
{post}
<div class="hd-post-quote" style="font-size:17px;">{esc(r['note'])}</div>
<div class="hd-chips" style="margin-bottom:0;">{setup_chips(c, c.get('free_tonight'))}</div>
{f'<div class="hd-why" style="border:0;margin-top:10px;padding-top:0;"><h4>Why you might fit</h4>{reasons}</div>' if reasons else ''}
""")
        with st.container(key=f"mrow_req_{r['request_id']}"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Ignore", use_container_width=True, key=f"ign_{r['request_id']}",
                             help="They won't be told."):
                    social_db.ignore_link_request(uid, r["request_id"])
                    st.rerun()
            with c2:
                if st.button("Accept", type="primary", use_container_width=True,
                             key=f"acc_{r['request_id']}"):
                    match_id = social_db.accept_link_request(uid, r["request_id"])
                    if match_id:
                        st.session_state.pop("disc_people", None)
                        _open_chat(match_id)
                    st.error("Couldn't accept. Try again.")
        st.html("<div style='height:18px'></div>")


# ─── CHATS + SENT ────────────────────────────────────────────────────────────

def _status_line(m: dict, uid: int) -> tuple[str, str]:
    if m.get("last_message"):
        who = "You: " if m.get("last_sender") == uid else ""
        text = m["last_message"]
        return f"{who}{text[:60]}{'…' if len(text) > 60 else ''}", "var(--soft)"
    return "Linked. Make a plan.", "var(--sodium)"


def _chats(uid: int, links: list):
    section("Chats")
    for m in links:
        line, color = _status_line(m, uid)
        their_turn = m.get("last_message") and m.get("last_sender") != uid
        with st.container(key=f"mrow_{m['id']}"):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            with c1:
                st.html(f"""
<div class="hd-row">
  {avatar(m['other_name'], m['other_id'], small=True, lifted=True)}
  <div style="min-width:0;">
    <div class="hd-title hd-name">{esc(m['other_name'])}</div>
    <div style="font-family:var(--font);font-size:14px;color:{color};
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(line)}</div>
  </div>
</div>""")
            with c2:
                if st.button("Reply" if their_turn else "Open", key=f"open_{m['id']}",
                             type="primary" if their_turn else "secondary", use_container_width=True):
                    _open_chat(m["id"])
        st.html("<div class='hd-rule'></div>")


def _sent(outgoing: list):
    names = ", ".join(esc(r["username"]) for r in outgoing[:12])
    more = f" and {len(outgoing) - 12} more" if len(outgoing) > 12 else ""
    section("You asked")
    st.html(f'<div class="hd-sub" style="color:var(--ink);">{names}{more}</div>'
            '<div class="hd-note">If they\'re up for it, the chat shows up above.</div>')


def _links_list(uid: int):
    me = social_db.get_profile(uid) or {}
    incoming = social_db.load_incoming_requests(uid) or []
    links = social_db.load_matches(uid) or []
    outgoing = social_db.load_outgoing_requests(uid) or []
    header("Links", "Who's up for you", "Requests, chats, and who you've asked.")
    if not (incoming or links or outgoing):
        empty_state("🔥", "Nothing yet",
                    "Send a link request from Discover, or post what you're on tonight. "
                    "Requests for you land here.")
        if st.button("Go to Discover", type="primary", use_container_width=True, key="links_go"):
            st.session_state.tab = "discover"
            st.rerun()
        return
    if incoming:
        _requests(uid, me, incoming)
    if links:
        _chats(uid, links)
    if outgoing:
        _sent(outgoing)


# ─── CHAT ────────────────────────────────────────────────────────────────────

def _exchange(title: str, questions: list, answers: list, color: str):
    rows = "".join(
        f'<div style="padding:10px 0;border-top:1px solid var(--border);">'
        f'<div class="hd-sub" style="color:var(--text);">{esc(q)}</div>'
        f'<div class="hd-sub" style="color:{color};font-style:italic;">“{esc(a)}”</div></div>'
        for q, a in zip(questions, answers))
    st.html(f'<div class="hd-panel" style="margin-bottom:10px;">'
            f'<div class="hd-kicker" style="color:{color};margin-bottom:6px;">{esc(title)}</div>{rows}</div>')


def _chat(m: dict, uid: int):
    if m.get("my_questions") and m.get("their_answers"):   # links made back when there was a Q&A
        with st.expander("Your old blind Q&A"):
            _exchange(f"You asked {m['other_name']}", m["my_questions"], m["their_answers"], "var(--lime)")
            _exchange(f"{m['other_name']} asked you", m["their_questions"], m["my_answers"], "var(--magenta)")

    @st.fragment(run_every=3)
    def _messages():
        msgs = social_db.load_messages(m["id"], uid)
        if not msgs:
            st.html('<div class="hd-sub" style="padding:24px 0;">'
                    'You\'re linked. Make a plan.</div>')
            return
        bubbles = "".join(
            f'<div class="hd-bubble {"me" if msg["sender_id"] == uid else "them"}">{esc(msg["body"])}'
            f'<small>{str(msg["created_at"])[11:16]}</small></div>' for msg in msgs)
        st.html(f'<div style="display:flex;flex-direction:column;padding:6px 0 12px;">{bubbles}</div>')
    _messages()

    text = st.chat_input(f"Message {m['other_name']}…", key=f"chat_{m['id']}", max_chars=1000)
    if text:
        if not social_db.send_message(m["id"], uid, text):
            st.error("Message didn't send. Try again.")
        st.rerun()


def _safety(m: dict, uid: int):
    with st.expander("End link, block or report"):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("End link", use_container_width=True, key=f"unmatch_{m['id']}"):
                social_db.unmatch(m["id"], uid)
                st.session_state.pop("open_match", None)
                st.toast(f"Link with {m['other_name']} ended")
                st.rerun()
        with c2:
            if st.button("Block", use_container_width=True, key=f"block_{m['id']}"):
                social_db.block_user(uid, m["other_id"])
                st.session_state.pop("open_match", None)
                st.session_state.pop("disc_people", None)
                st.toast(f"Blocked {m['other_name']}")
                st.rerun()
        section("Report")
        reason = st.selectbox("Reason", REPORT_REASONS, key=f"rep_reason_{m['id']}")
        details = st.text_area("What happened? (optional)", key=f"rep_details_{m['id']}",
                               max_chars=1000, height=80)
        st.caption("Your recent messages with them are included so we can check what happened.")
        also_block = st.checkbox("Also block them", value=True, key=f"rep_block_{m['id']}")
        if st.button("Send report", use_container_width=True, key=f"rep_send_{m['id']}"):
            if social_db.report_user(uid, m["other_id"], reason, details):
                if also_block:
                    social_db.block_user(uid, m["other_id"])
                    st.session_state.pop("open_match", None)
                    st.session_state.pop("disc_people", None)
                st.toast("Report sent. Thank you for keeping Hidden safe.")
                st.rerun()
            else:
                st.error("Couldn't send the report. Try again.")


def _link_detail(uid: int, match_id: int):
    m = social_db.get_match(match_id, uid)
    if not m:
        st.session_state.pop("open_match", None)
        st.rerun()
        return

    if st.button("Links", key="back_matches", type="tertiary", icon=":material/arrow_back:"):
        st.session_state.pop("open_match", None)
        st.rerun()

    # The tint lifts the first time you open a link this session; after that it stays off
    seen = st.session_state.setdefault("_hd_seen_links", set())
    first = m["id"] not in seen
    seen.add(m["id"])
    st.html(f'<div class="hd-row" style="margin:4px 0 14px;">'
            f'{avatar(m["other_name"], m["other_id"], lifted=not first, lifting=first)}<div style="min-width:0;">'
            f'<div class="hd-title hd-name" style="font-size:26px;">{esc(m["other_name"])}</div>'
            f'<div class="hd-note">Linked</div></div></div>')
    screenshot_shield((st.session_state.get("user") or {}).get("username"))
    match_quiz_card(uid, m["other_id"], m["other_name"], m.get("created_at"), key=str(m["id"]))
    _chat(m, uid)
    st.html("<div style='height:16px'></div>")
    _safety(m, uid)


def matches_page():
    uid = _uid()
    if st.session_state.get("open_match"):
        _link_detail(uid, st.session_state.open_match)
    else:
        _links_list(uid)
