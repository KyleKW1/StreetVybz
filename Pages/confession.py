"""
Pages/confessions.py — Mutual blind confession exchange.

Flow:
  1. Sender picks a recipient (by username) and writes N questions (1–10).
  2. Recipient opens their Inbox, answers those N questions AND writes N questions back.
  3. Sender sees recipient responded, answers recipient's N questions.
  4. REVEAL: both sides unlock simultaneously — neither saw anything until both were done.

The lock mechanic:
  - status='sent'      → recipient hasn't answered yet. Sender sees "waiting…"
  - status='responded' → recipient done. Sender must now answer. Recipient sees "waiting…"
  - status='revealed'  → both submitted. Full exchange visible to both parties.
"""

import streamlit as st
import secrets
import string
from datetime import datetime


# ─── CSS ─────────────────────────────────────────────────────────────────────

def inject_css():
    st.html("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d; --border:#2a2a35;
  --lime:#c6ff00; --magenta:#ff2d78; --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}
.stApp { background:var(--bg) !important; }
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container { padding-top:2rem !important; max-width:820px !important; }
section[data-testid="stSidebar"] { background:#0d0d10 !important; border-right:1px solid var(--border) !important; }
section[data-testid="stSidebar"] * { color:#c8c8d8 !important; }
section[data-testid="stSidebar"] .stButton > button {
  background:transparent !important; border:1px solid var(--border) !important;
  color:#c8c8d8 !important; border-radius:4px !important;
  font-family:'Space Mono',monospace !important; font-size:11px !important;
  letter-spacing:1px !important; text-transform:uppercase !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background:#1a1a20 !important; border-color:var(--lime) !important;
  color:var(--lime) !important; box-shadow:none !important;
}
.stButton > button {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important; border-radius:3px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1.5px !important; text-transform:uppercase !important;
  transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover { border-color:var(--lime) !important; color:var(--lime) !important; }
.stButton > button[kind="primary"] {
  background:var(--magenta) !important; color:#fff !important;
  border-color:var(--magenta) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#ff5590 !important; box-shadow:0 0 20px rgba(255,45,120,0.25) !important;
}
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stNumberInput > div > div > input {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:4px !important; color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
  border-color:var(--magenta) !important; box-shadow:0 0 0 2px rgba(255,45,120,0.12) !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important; color:var(--muted) !important;
}
.stSelectbox > div > div { background:var(--card) !important; border:1px solid var(--border) !important; color:var(--text) !important; }
.stRadio label { font-family:'DM Sans',sans-serif !important; font-size:13px !important; color:var(--soft) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")


# ─── DB HELPERS ──────────────────────────────────────────────────────────────

def _db_save_confession(sender_id, recipient_id, code, questions):
    try:
        import database as db
        return db.save_confession(sender_id, recipient_id, code, questions)
    except Exception:
        return None


def _db_load_inbox(user_id):
    try:
        import database as db
        return db.load_confessions_inbox(user_id)
    except Exception:
        return []


def _db_load_outbox(user_id):
    try:
        import database as db
        return db.load_confessions_outbox(user_id)
    except Exception:
        return []


def _db_get_confession(code):
    try:
        import database as db
        return db.get_confession_by_code(code)
    except Exception:
        return None


def _db_recipient_respond(code, recipient_answers, recipient_questions):
    try:
        import database as db
        return db.confession_recipient_respond(code, recipient_answers, recipient_questions)
    except Exception:
        return False


def _db_sender_answer(code, sender_answers):
    try:
        import database as db
        return db.confession_sender_answer(code, sender_answers)
    except Exception:
        return False


def _db_get_user_by_username(username):
    try:
        import database as db
        return db.get_user_by_username(username)
    except Exception:
        return None


# ─── UTILS ───────────────────────────────────────────────────────────────────

def _gen_code(n=8):
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(n))


def _current_user():
    return st.session_state.get("user", {})


def _current_uid():
    u = _current_user()
    return u.get("id") if u else None


def _current_username():
    u = _current_user()
    return u.get("username", "You")


# ─── SHARED UI HELPERS ───────────────────────────────────────────────────────

def _section_label(text):
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">{text}</div>
""")


def _status_badge(status, sender, recipient, is_sender):
    colors = {
        "sent":      ("var(--amber)",   "PENDING"),
        "responded": ("var(--cyan)",    "YOUR TURN"),
        "revealed":  ("var(--lime)",    "REVEALED"),
    }
    color, label = colors.get(status, ("var(--muted)", status.upper()))

    if status == "sent":
        if is_sender:
            detail = f"Waiting for {recipient} to answer & send back"
        else:
            detail = f"{sender} sent you questions — your move"
    elif status == "responded":
        if is_sender:
            detail = f"{recipient} answered — now answer their questions to reveal"
        else:
            detail = f"Waiting for {sender} to answer your questions"
    else:
        detail = "Both sides complete — exchange unlocked"

    st.html(f"""
<div style="display:inline-flex; align-items:center; gap:10px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:{color}; border:1px solid {color};
              border-radius:2px; padding:4px 10px;">{label}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);">{detail}</div>
</div>
""")


def _exchange_card(label, color, questions, answers):
    """Render a set of Q&A pairs side by side."""
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:{color}; margin-bottom:8px;">{label}</div>
""")
    for i, (q, a) in enumerate(zip(questions, answers)):
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {color}; border-radius:4px;
            padding:16px 18px; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Q{i+1}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              line-height:1.6; margin-bottom:10px;">{q}</div>
  <div style="height:1px; background:var(--border); margin-bottom:10px;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Answer</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:{color};
              line-height:1.7; font-style:italic;">"{a}"</div>
</div>
""")


# ─── SUB-PAGES ───────────────────────────────────────────────────────────────

def _render_compose():
    inject_css()
    _section_label("New Confession Exchange")

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-top:2px solid var(--magenta);
            border-radius:4px; padding:20px 22px; margin-bottom:24px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.9;">
    You write <strong style="color:var(--text);">N questions</strong> for someone.
    They must answer yours <em>and</em> send back exactly N questions of their own.
    You answer theirs. Then — and only then — do both of you see everything.
    <br><br>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">
      Nobody sees anything until both sides are done.
    </span>
  </div>
</div>
""")

    recipient_username = st.text_input(
        "Send to (username)",
        placeholder="Enter their ViceVault username",
        key="conf_recipient",
    )

    n = st.number_input("Number of questions", min_value=1, max_value=10, value=3, step=1, key="conf_n")
    n = int(n)

    st.html("<div style='height:8px'></div>")
    _section_label(f"Your {n} question{'s' if n != 1 else ''}")

    questions = []
    for i in range(n):
        q = st.text_area(
            f"Question {i+1}",
            placeholder=f"Ask them something you actually want to know…",
            key=f"conf_q_{i}",
            height=80,
        )
        questions.append(q)

    st.html("<div style='height:12px'></div>")

    if st.button("Send Confession →", type="primary", use_container_width=True, key="conf_send"):
        uid = _current_uid()
        if not uid:
            st.error("Not logged in.")
            return

        if not recipient_username or not recipient_username.strip():
            st.error("Enter a recipient username.")
            return

        if recipient_username.strip().lower() == _current_username().lower():
            st.error("You can't send a confession to yourself.")
            return

        blanks = [i+1 for i, q in enumerate(questions) if not q.strip()]
        if blanks:
            st.error(f"Question{'s' if len(blanks) > 1 else ''} {', '.join(str(b) for b in blanks)} {'are' if len(blanks) > 1 else 'is'} empty.")
            return

        recipient = _db_get_user_by_username(recipient_username.strip())
        if not recipient:
            st.error(f"No user found with username '{recipient_username.strip()}'.")
            return

        code = _gen_code()
        success = _db_save_confession(uid, recipient["id"], code, questions)

        if success:
            st.success(f"Sent. Now we wait for {recipient_username.strip()} to answer — and send their questions back.")
            # Clear fields
            for i in range(n):
                if f"conf_q_{i}" in st.session_state:
                    del st.session_state[f"conf_q_{i}"]
            st.session_state.conf_recipient = ""
            st.rerun()
        else:
            st.error("Something went wrong saving the confession. Try again.")


def _render_inbox():
    inject_css()
    _section_label("Inbox — Confessions sent to you")

    uid = _current_uid()
    items = _db_load_inbox(uid)

    if not items:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">NOTHING YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Nobody has sent you a confession.
  </div>
</div>
""")
        return

    for item in items:
        _render_inbox_item(item)


def _render_inbox_item(item):
    code         = item["code"]
    sender_name  = item.get("sender_username", "Someone")
    status       = item["status"]
    num_q        = len(item.get("sender_questions", []))
    created_at   = item.get("created_at", "")
    ts           = str(created_at)[:16] if created_at else ""

    # Header card
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid var(--magenta); border-radius:4px;
            padding:18px 20px; margin-bottom:4px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--text);
                letter-spacing:1px;">From {sender_name}</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
    {num_q} question{'s' if num_q != 1 else ''} waiting
  </div>
</div>
""")

    _status_badge(status, sender_name, _current_username(), is_sender=False)

    if status == "sent":
        # Recipient must answer sender's questions AND write their own
        with st.expander(f"Answer {sender_name}'s questions & send yours back", expanded=True):
            sender_questions = item.get("sender_questions", [])

            st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
            line-height:1.8; margin-bottom:16px; padding:12px;
            background:var(--surface); border-radius:4px;">
  Answer <strong style="color:var(--text);">{sender_name}'s {num_q} question{'s' if num_q != 1 else ''}</strong>
  below, then write <strong style="color:var(--text);">{num_q} question{'s' if num_q != 1 else ''}</strong>
  of your own to send back. Submit both at once.
  <br><span style="color:var(--magenta); font-family:'Space Mono',monospace; font-size:10px;">
    {sender_name} won't see your answers until they've answered yours.
  </span>
</div>
""")

            st.html(f"""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:12px;">
                Your answers to {sender_name}'s questions</div>""")

            recipient_answers = []
            for i, q in enumerate(sender_questions):
                st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
            margin-bottom:6px; padding:10px 14px; background:var(--surface);
            border-left:2px solid var(--magenta); border-radius:0 3px 3px 0;">
  {q}
</div>""")
                ans = st.text_area(
                    f"Your answer",
                    placeholder="Be honest…",
                    key=f"inbox_ans_{code}_{i}",
                    height=80,
                    label_visibility="collapsed",
                )
                recipient_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:16px'></div>")
            st.html(f"""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--cyan); margin-bottom:12px;">
                Your {num_q} question{'s' if num_q != 1 else ''} for {sender_name}</div>""")
            st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
            margin-bottom:12px;">{sender_name} must answer these before either of you sees anything.</div>""")

            recipient_questions = []
            for i in range(num_q):
                q = st.text_area(
                    f"Question {i+1}",
                    placeholder=f"Ask {sender_name} something real…",
                    key=f"inbox_rq_{code}_{i}",
                    height=80,
                )
                recipient_questions.append(q)

            st.html("<div style='height:8px'></div>")
            if st.button(
                f"Submit answers & send {sender_name} your questions →",
                key=f"inbox_submit_{code}",
                type="primary",
                use_container_width=True,
            ):
                blank_ans = [i+1 for i, a in enumerate(recipient_answers) if not a.strip()]
                blank_rq  = [i+1 for i, q in enumerate(recipient_questions) if not q.strip()]

                if blank_ans:
                    st.error(f"Answer{'s' if len(blank_ans) > 1 else ''} {', '.join(str(b) for b in blank_ans)} {'are' if len(blank_ans) > 1 else 'is'} empty.")
                elif blank_rq:
                    st.error(f"Your question{'s' if len(blank_rq) > 1 else ''} {', '.join(str(b) for b in blank_rq)} {'are' if len(blank_rq) > 1 else 'is'} empty.")
                else:
                    ok = _db_recipient_respond(code, recipient_answers, recipient_questions)
                    if ok:
                        st.success(f"Sent. Waiting for {sender_name} to answer your questions. When they do, the exchange unlocks for both of you.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "responded":
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You've answered {sender_name}'s questions and sent yours back.
    <br>Waiting for <strong style="color:var(--text);">{sender_name}</strong> to answer your questions.
    <br><span style="color:var(--cyan); font-family:'Space Mono',monospace; font-size:10px;">
      The exchange unlocks the moment they submit.
    </span>
  </div>
</div>
""")

    elif status == "revealed":
        _render_revealed(item, is_sender=False)

    st.html("<div style='height:12px'></div>")


def _render_outbox():
    inject_css()
    _section_label("Sent — Confessions you started")

    uid = _current_uid()
    items = _db_load_outbox(uid)

    if not items:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">NOTHING SENT YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Start a new confession from the Compose tab.
  </div>
</div>
""")
        return

    for item in items:
        _render_outbox_item(item)


def _render_outbox_item(item):
    code           = item["code"]
    recipient_name = item.get("recipient_username", "them")
    status         = item["status"]
    num_q          = len(item.get("sender_questions", []))
    created_at     = item.get("created_at", "")
    ts             = str(created_at)[:16] if created_at else ""

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid var(--lime); border-radius:4px;
            padding:18px 20px; margin-bottom:4px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--text);
                letter-spacing:1px;">To {recipient_name}</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
    {num_q} question{'s' if num_q != 1 else ''} sent
  </div>
</div>
""")

    _status_badge(status, _current_username(), recipient_name, is_sender=True)

    if status == "sent":
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    Waiting for <strong style="color:var(--text);">{recipient_name}</strong> to answer your questions
    and send theirs back.
  </div>
</div>
""")

    elif status == "responded":
        # Sender must now answer recipient's questions
        with st.expander(f"{recipient_name} answered — now answer their questions to unlock", expanded=True):
            recipient_questions = item.get("recipient_questions", [])
            num_rq = len(recipient_questions)

            st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
            line-height:1.8; margin-bottom:16px; padding:12px;
            background:var(--surface); border-radius:4px;">
  <strong style="color:var(--text);">{recipient_name}</strong> answered your questions and sent
  <strong style="color:var(--text);">{num_rq} question{'s' if num_rq != 1 else ''}</strong> back.
  Answer theirs to reveal everything — simultaneously — for both of you.
  <br><span style="color:var(--lime); font-family:'Space Mono',monospace; font-size:10px;">
    The second you submit, both sides unlock.
  </span>
</div>
""")

            sender_answers = []
            for i, q in enumerate(recipient_questions):
                st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
            margin-bottom:6px; padding:10px 14px; background:var(--surface);
            border-left:2px solid var(--lime); border-radius:0 3px 3px 0;">
  {q}
</div>""")
                ans = st.text_area(
                    f"Your answer",
                    placeholder="Be honest…",
                    key=f"outbox_ans_{code}_{i}",
                    height=80,
                    label_visibility="collapsed",
                )
                sender_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:8px'></div>")
            if st.button(
                "Submit answers — unlock the exchange →",
                key=f"outbox_submit_{code}",
                type="primary",
                use_container_width=True,
            ):
                blank = [i+1 for i, a in enumerate(sender_answers) if not a.strip()]
                if blank:
                    st.error(f"Answer{'s' if len(blank) > 1 else ''} {', '.join(str(b) for b in blank)} {'are' if len(blank) > 1 else 'is'} empty.")
                else:
                    ok = _db_sender_answer(code, sender_answers)
                    if ok:
                        st.success("Exchange unlocked. Check the Revealed tab.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "revealed":
        _render_revealed(item, is_sender=True)

    st.html("<div style='height:12px'></div>")


def _render_revealed(item, is_sender: bool):
    """Full mutual exchange view — only shown when status='revealed'."""
    sender_name    = item.get("sender_username",    "Sender")
    recipient_name = item.get("recipient_username", "Recipient")
    me             = _current_username()
    them           = recipient_name if is_sender else sender_name

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--lime); border-radius:4px;
            padding:16px 20px; margin-bottom:16px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime);
              letter-spacing:2px; margin-bottom:4px;">EXCHANGE REVEALED</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);">
    Both sides answered. Here's everything.
  </div>
</div>
""")

    sender_questions    = item.get("sender_questions",    [])
    recipient_answers   = item.get("recipient_answers",   [])
    recipient_questions = item.get("recipient_questions", [])
    sender_answers      = item.get("sender_answers",      [])

    # What YOU asked, what THEY answered
    if is_sender:
        _exchange_card(
            f"Your questions → {recipient_name}'s answers",
            "#c6ff00",
            sender_questions,
            recipient_answers,
        )
        st.html("<div style='height:12px'></div>")
        _exchange_card(
            f"{recipient_name}'s questions → Your answers",
            "#ff2d78",
            recipient_questions,
            sender_answers,
        )
    else:
        _exchange_card(
            f"{sender_name}'s questions → Your answers",
            "#ff2d78",
            sender_questions,
            recipient_answers,
        )
        st.html("<div style='height:12px'></div>")
        _exchange_card(
            f"Your questions → {sender_name}'s answers",
            "#c6ff00",
            recipient_questions,
            sender_answers,
        )


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def confessions_page():
    inject_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">
    CONFESSIONS
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Mutual. Blind. Nobody blinks first — because neither of you can.
  </div>
</div>
""")

    uid = _current_uid()
    if not uid:
        st.error("Log in to use Confessions.")
        return

    # Tab selector
    if "conf_tab" not in st.session_state:
        st.session_state.conf_tab = "compose"

    # Count inbox items that need action
    inbox_items  = _db_load_inbox(uid)
    outbox_items = _db_load_outbox(uid)
    inbox_action  = sum(1 for i in inbox_items  if i["status"] == "sent")
    outbox_action = sum(1 for i in outbox_items if i["status"] == "responded")
    revealed_all  = [i for i in inbox_items + outbox_items if i["status"] == "revealed"]

    col_compose, col_inbox, col_sent, col_revealed = st.columns(4)

    with col_compose:
        label = "◈  Compose"
        if st.button(label, use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "compose" else "secondary",
                     key="tab_compose"):
            st.session_state.conf_tab = "compose"; st.rerun()

    with col_inbox:
        badge = f"  ({inbox_action})" if inbox_action > 0 else ""
        if st.button(f"↓  Inbox{badge}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "inbox" else "secondary",
                     key="tab_inbox"):
            st.session_state.conf_tab = "inbox"; st.rerun()

    with col_sent:
        badge = f"  ({outbox_action})" if outbox_action > 0 else ""
        if st.button(f"↑  Sent{badge}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "sent" else "secondary",
                     key="tab_sent"):
            st.session_state.conf_tab = "sent"; st.rerun()

    with col_revealed:
        badge = f"  ({len(revealed_all)})" if revealed_all else ""
        if st.button(f"⚡  Revealed{badge}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "revealed" else "secondary",
                     key="tab_revealed"):
            st.session_state.conf_tab = "revealed"; st.rerun()

    st.html("<div style='height:1.5rem'></div>")

    tab = st.session_state.conf_tab

    if tab == "compose":
        _render_compose()

    elif tab == "inbox":
        _render_inbox()

    elif tab == "sent":
        _render_outbox()

    elif tab == "revealed":
        inject_css()
        _section_label("Revealed exchanges")
        if not revealed_all:
            st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:24px; letter-spacing:3px;
              color:var(--muted);">NOTHING REVEALED YET</div>
</div>
""")
        else:
            # Deduplicate by code
            seen = set()
            unique = []
            for item in revealed_all:
                if item["code"] not in seen:
                    seen.add(item["code"])
                    unique.append(item)

            for item in unique:
                is_s = item.get("sender_id") == uid
                other = item.get("recipient_username") if is_s else item.get("sender_username")
                ts = str(item.get("created_at", ""))[:16]

                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s)
