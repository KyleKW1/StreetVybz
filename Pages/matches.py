"""
Pages/matches.py — Your matches: blind Q&A first, then chat.

Flow per match: both write 3 questions (blind) → both answer the other's
→ everything reveals at once → chat opens.
"""

import random

import streamlit as st

import social_db
from Pages.quiz_reveal import match_quiz_card, screenshot_shield
from ui import esc, header, empty_state, waiting, avatar

N_QUESTIONS = 3

QUESTION_SPARKS = [
    "What's the most spontaneous thing you've done on a night out?",
    "What's something you'd never say on a first date?",
    "Weed, drinks or neither — what's your perfect Friday?",
    "What's a secret talent nobody would guess?",
    "What's the last thing that made you laugh out loud?",
    "What's your biggest green flag in a person?",
    "Where's the best spot in town that nobody knows about?",
    "What's one thing you want to try but haven't yet?",
    "What song instantly changes your mood?",
    "What would your friends say you're too much of?",
    "What's your idea of a perfect link-up?",
    "What's the boldest thing you've done for someone you liked?",
]

REPORT_REASONS = ["Fake profile / spam", "Harassment or threats", "Seems under 18",
                  "Inappropriate messages", "Other"]

_STAGE_LABEL = {
    "write":          ("✍️ Your move — ask your 3 questions", "var(--magenta)"),
    "wait_questions": ("⏳ Waiting for their questions",       "var(--muted)"),
    "answer":         ("💬 Your move — answer their questions", "var(--magenta)"),
    "wait_answers":   ("⏳ Waiting for their answers",          "var(--muted)"),
    "open":           ("",                                    "var(--lime)"),
}
_STEPS = ["Ask", "Answer", "Reveal", "Chat"]
_STEP_OF = {"write": 0, "wait_questions": 0, "answer": 1, "wait_answers": 1, "open": 3}


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def needs_action(matches: list) -> int:
    return sum(1 for m in matches if m["stage"] in ("write", "answer"))


# ─── LIST ────────────────────────────────────────────────────────────────────

def _status_line(m: dict, uid: int) -> tuple[str, str]:
    if m["stage"] != "open":
        return _STAGE_LABEL[m["stage"]]
    if m.get("last_message"):
        who = "You: " if m.get("last_sender") == uid else ""
        text = m["last_message"]
        return f"{who}{text[:60]}{'…' if len(text) > 60 else ''}", "var(--soft)"
    return "🔓 Chat's open — say hi", "var(--lime)"


def _match_list(uid: int, matches: list):
    header("Matches", "Your people", "Ask blind, answer honest, then talk.")
    if not matches:
        empty_state("💘", "No matches yet", "Like people in Discover — when it's mutual they show up here.")
        return
    for m in matches:
        line, color = _status_line(m, uid)
        with st.container(key=f"mrow_{m['id']}"):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            with c1:
                st.html(f"""
<div style="display:flex;align-items:center;gap:14px;padding:6px 0;">
  {avatar(m['other_name'], m['other_id'], small=True)}
  <div style="min-width:0;">
    <div class="hd-title" style="font-size:24px;margin:0;">{esc(m['other_name'])}</div>
    <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:{color};
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(line)}</div>
  </div>
</div>""")
            with c2:
                action = m["stage"] in ("write", "answer")
                if st.button("Open" if not action else "Go →", key=f"open_{m['id']}",
                             type="primary" if action else "secondary", use_container_width=True):
                    st.session_state.open_match = m["id"]
                    st.rerun()
        st.html("<div style='height:1px;background:var(--border);margin:2px 0;'></div>")


# ─── DETAIL ──────────────────────────────────────────────────────────────────

def _progress(stage: str):
    cur = _STEP_OF[stage]
    cells = "".join(
        f'<div style="flex:1;text-align:center;"><div style="height:4px;border-radius:99px;'
        f'background:{"var(--lime)" if i <= cur else "var(--border)"};margin-bottom:6px;"></div>'
        f'<span class="hd-kicker" style="color:{"var(--lime)" if i <= cur else "var(--muted)"};">{s}</span></div>'
        for i, s in enumerate(_STEPS))
    st.html(f'<div style="display:flex;gap:6px;margin:4px 0 20px;">{cells}</div>')


def _spark(key: str):
    st.session_state[key] = random.choice(QUESTION_SPARKS)


def _write_questions(m: dict, uid: int):
    st.html(f'<div class="hd-sub" style="margin-bottom:10px;">Ask <b style="color:var(--text);">'
            f'{esc(m["other_name"])}</b> 3 things you actually want to know. They can\'t see yours '
            f'until they\'ve written theirs.</div>')
    questions = []
    for i in range(N_QUESTIONS):
        key = f"qa_q_{m['id']}_{i}"
        with st.container(key=f"qrow_{m['id']}_{i}"):
            c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
            with c1:
                questions.append(st.text_input(f"Question {i + 1}", key=key, max_chars=200))
            with c2:
                st.button("🎲", key=f"spark_{m['id']}_{i}", on_click=_spark, args=(key,),
                          help="Suggest a question", use_container_width=True)
    if st.button("Lock in my questions →", type="primary", use_container_width=True, key=f"qa_send_{m['id']}"):
        cleaned = [q.strip() for q in questions]
        if any(len(q) < 8 for q in cleaned):
            st.error("Each question needs at least a few words.")
        elif social_db.save_questions(m["id"], uid, cleaned):
            st.toast("Questions locked in 🔒")
            st.rerun()
        else:
            st.error("Couldn't save — try again.")


def _answer_questions(m: dict, uid: int):
    st.html(f'<div class="hd-sub" style="margin-bottom:10px;">{esc(m["other_name"])} asked you this. '
            f'Be honest — your answers reveal at the same moment as theirs.</div>')
    answers = []
    for i, q in enumerate(m["their_questions"]):
        st.html(f'<div class="hd-card" style="padding:14px 18px;margin:10px 0 6px;border-radius:14px;">'
                f'<div class="hd-kicker">Q{i + 1}</div><div class="hd-sub" style="color:var(--text);'
                f'font-size:15px;">{esc(q)}</div></div>')
        answers.append(st.text_area("Your answer", key=f"qa_a_{m['id']}_{i}", height=80,
                                    max_chars=500, label_visibility="collapsed"))
    if st.button("Submit my answers →", type="primary", use_container_width=True, key=f"qa_ans_{m['id']}"):
        cleaned = [a.strip() for a in answers]
        if any(not a for a in cleaned):
            st.error("Answer every question.")
        elif social_db.save_answers(m["id"], uid, cleaned):
            st.toast("Answers in ✨")
            st.rerun()
        else:
            st.error("Couldn't save — try again.")


def _wait_for_them(m: dict, uid: int, text: str):
    waiting(text)

    @st.fragment(run_every=5)
    def _poll():
        fresh = social_db.get_match(m["id"], uid)
        if not fresh or fresh["stage"] != m["stage"]:
            st.rerun(scope="app")
    _poll()


def _exchange(title: str, questions: list, answers: list, color: str):
    rows = "".join(
        f'<div style="padding:10px 0;border-top:1px solid var(--border);">'
        f'<div class="hd-sub" style="color:var(--text);">{esc(q)}</div>'
        f'<div class="hd-sub" style="color:{color};font-style:italic;">“{esc(a)}”</div></div>'
        for q, a in zip(questions, answers))
    st.html(f'<div class="hd-card" style="padding:18px;margin-bottom:10px;">'
            f'<div class="hd-kicker" style="color:{color};margin-bottom:6px;">{esc(title)}</div>{rows}</div>')


def _chat(m: dict, uid: int):
    has_messages = bool(m.get("last_message")) or bool(social_db.load_messages(m["id"], uid, limit=1))
    with st.expander("✨ Your blind Q&A", expanded=not has_messages):
        _exchange(f"You asked {m['other_name']}", m["my_questions"], m["their_answers"], "var(--lime)")
        _exchange(f"{m['other_name']} asked you", m["their_questions"], m["my_answers"], "var(--magenta)")

    @st.fragment(run_every=3)
    def _messages():
        msgs = social_db.load_messages(m["id"], uid)
        if not msgs:
            st.html('<div class="hd-sub" style="text-align:center;padding:24px 0;">'
                    'Chat is open. Say something about their answers 👀</div>')
            return
        bubbles = "".join(
            f'<div class="hd-bubble {"me" if msg["sender_id"] == uid else "them"}">{esc(msg["body"])}'
            f'<small>{str(msg["created_at"])[11:16]}</small></div>' for msg in msgs)
        st.html(f'<div style="display:flex;flex-direction:column;padding:6px 0 12px;">{bubbles}</div>')
    _messages()

    text = st.chat_input(f"Message {m['other_name']}…", key=f"chat_{m['id']}", max_chars=1000)
    if text:
        if not social_db.send_message(m["id"], uid, text):
            st.error("Message didn't send — try again.")
        st.rerun()


def _safety(m: dict, uid: int):
    with st.expander("⚑  Unmatch · Block · Report"):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Unmatch", use_container_width=True, key=f"unmatch_{m['id']}"):
                social_db.unmatch(m["id"], uid)
                st.session_state.pop("open_match", None)
                st.toast(f"Unmatched {m['other_name']}")
                st.rerun()
        with c2:
            if st.button("Block", use_container_width=True, key=f"block_{m['id']}"):
                social_db.block_user(uid, m["other_id"])
                st.session_state.pop("open_match", None)
                st.session_state.pop("disc_queue", None)
                st.toast(f"Blocked {m['other_name']}")
                st.rerun()
        st.html('<div class="hd-kicker" style="margin:14px 0 4px;">Report</div>')
        reason = st.selectbox("Reason", REPORT_REASONS, key=f"rep_reason_{m['id']}")
        details = st.text_area("What happened? (optional)", key=f"rep_details_{m['id']}",
                               max_chars=1000, height=80)
        also_block = st.checkbox("Also block them", value=True, key=f"rep_block_{m['id']}")
        if st.button("Send report", use_container_width=True, key=f"rep_send_{m['id']}"):
            if social_db.report_user(uid, m["other_id"], reason, details):
                if also_block:
                    social_db.block_user(uid, m["other_id"])
                    st.session_state.pop("open_match", None)
                    st.session_state.pop("disc_queue", None)
                st.toast("Report sent. Thank you for keeping Hidden safe.")
                st.rerun()
            else:
                st.error("Couldn't send the report — try again.")


def _match_detail(uid: int, match_id: int):
    m = social_db.get_match(match_id, uid)
    if not m:
        st.session_state.pop("open_match", None)
        st.rerun()
        return

    if st.button("← Matches", key="back_matches"):
        st.session_state.pop("open_match", None)
        st.rerun()

    st.html(f'<div style="display:flex;align-items:center;gap:14px;margin:8px 0 14px;">'
            f'{avatar(m["other_name"], m["other_id"])}<div><div class="hd-kicker">Matched</div>'
            f'<div class="hd-title" style="margin:0;">{esc(m["other_name"])}</div></div></div>')
    screenshot_shield((st.session_state.get("user") or {}).get("username"))
    match_quiz_card(uid, m["other_id"], m["other_name"], m.get("created_at"), key=str(m["id"]))
    _progress(m["stage"])

    stage = m["stage"]
    if stage == "write":
        _write_questions(m, uid)
    elif stage == "wait_questions":
        _wait_for_them(m, uid, f"{m['other_name']} is writing their questions… "
                               "You'll see them the moment they lock in.")
    elif stage == "answer":
        _answer_questions(m, uid)
    elif stage == "wait_answers":
        _wait_for_them(m, uid, f"Waiting for {m['other_name']} to answer. "
                               "Everything reveals at the same time.")
    else:
        _chat(m, uid)

    st.html("<div style='height:16px'></div>")
    _safety(m, uid)


def matches_page():
    uid = _uid()
    if st.session_state.get("open_match"):
        _match_detail(uid, st.session_state.open_match)
    else:
        _match_list(uid, social_db.load_matches(uid))
