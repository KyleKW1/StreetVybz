"""
Pages/confessions.py — Mutual blind confession exchange.

Status machine (4 steps, nobody can cheat):
  sent        → Recipient must submit THEIR questions first (blind — sender's hidden)
  questioning → Recipient submitted their questions. Now they unlock sender's questions to answer.
  responded   → Recipient answered sender's questions. Sender must now answer recipient's.
  revealed    → Sender answered. Full exchange visible to both. Simultaneous unlock.

Question validation:
  - Must be at least 8 characters
  - Must end with '?' OR start with a recognised question word
  - No duplicate questions within the same submission
"""

import streamlit as st
import secrets
import string
import re


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
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:4px !important; color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color:var(--magenta) !important;
  box-shadow:0 0 0 2px rgba(255,45,120,0.12) !important;
}
.stTextInput label, .stTextArea label,
.stNumberInput label, .stSelectbox label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important;
  color:var(--muted) !important;
}
.stSelectbox > div > div {
  background:var(--card) !important; border:1px solid var(--border) !important;
  color:var(--text) !important;
}
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")


# ─── QUESTION VALIDATION ─────────────────────────────────────────────────────

QUESTION_WORDS = {
    "what", "why", "how", "when", "where", "who", "whom", "which", "whose",
    "would", "could", "should", "do", "did", "does", "have", "has", "had",
    "are", "is", "was", "were", "will", "can", "may", "might", "shall",
    "if", "tell", "describe", "explain", "name",
}


def _validate_questions(questions: list) -> list:
    """
    Returns a list of error strings. Empty list = all valid.
    Rules per question:
      - Not blank
      - At least 8 non-whitespace characters
      - Ends with '?' OR first word is a recognised question word
      - No duplicate questions in the same submission
    """
    errors = []
    seen   = {}

    for i, raw in enumerate(questions):
        q   = raw.strip()
        num = i + 1

        if not q:
            errors.append(f"Question {num} is empty.")
            continue

        if len(q) < 8:
            errors.append(f"Question {num} is too short — ask something real.")
            continue

        ends_with_q = q.endswith("?")
        first_word  = re.split(r'\W+', q.lower())[0]
        starts_as_q = first_word in QUESTION_WORDS

        if not ends_with_q and not starts_as_q:
            errors.append(
                f"Question {num} doesn't look like a question. "
                "End it with '?' or start with a question word (what, why, how, would, etc.)."
            )
            continue

        # Duplicate check — strip punctuation, lowercase, compare
        normalised = re.sub(r'[^\w\s]', '', q.lower()).strip()
        if normalised in seen:
            errors.append(
                f"Question {num} is the same as question {seen[normalised]}. "
                "They deserve something different."
            )
        else:
            seen[normalised] = num

    return errors


# ─── DB HELPERS ──────────────────────────────────────────────────────────────

def _db_save_confession(sender_id, recipient_id, code, questions):
    try:
        import database as db
        return db.save_confession(sender_id, recipient_id, code, questions)
    except Exception:
        return False


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


def _db_recipient_submit_questions(code, recipient_questions):
    """Step 1 for recipient: submit their questions blind. sent -> questioning."""
    try:
        import database as db
        return db.confession_recipient_submit_questions(code, recipient_questions)
    except Exception:
        return False


def _db_recipient_answer(code, recipient_answers):
    """Step 2 for recipient: answer sender's now-visible questions. questioning -> responded."""
    try:
        import database as db
        return db.confession_recipient_answer(code, recipient_answers)
    except Exception:
        return False


def _db_sender_answer(code, sender_answers):
    """Sender answers recipient's questions. responded -> revealed."""
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
    cfg = {
        "sent": {
            True:  ("var(--amber)",   "WAITING",    f"Waiting for {recipient} to send their questions first"),
            False: ("var(--magenta)", "YOUR MOVE",  f"Write your questions before you can see {sender}'s"),
        },
        "questioning": {
            True:  ("var(--amber)",   "WAITING",    f"{recipient} sent their questions — waiting for them to answer yours"),
            False: ("var(--cyan)",    "YOUR TURN",  f"Your questions are locked in — now answer {sender}'s"),
        },
        "responded": {
            True:  ("var(--cyan)",    "YOUR TURN",  f"{recipient} answered — now answer their questions to reveal"),
            False: ("var(--amber)",   "WAITING",    f"Waiting for {sender} to answer your questions"),
        },
        "revealed": {
            True:  ("var(--lime)",    "REVEALED",   "Exchange unlocked for both of you"),
            False: ("var(--lime)",    "REVEALED",   "Exchange unlocked for both of you"),
        },
    }
    defaults = ("var(--muted)", status.upper(), "")
    color, label, detail = cfg.get(status, {}).get(is_sender, defaults)

    st.html(f"""
<div style="display:inline-flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:{color}; border:1px solid {color};
              border-radius:2px; padding:4px 10px; white-space:nowrap;">{label}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);">{detail}</div>
</div>
""")


def _question_fields(prefix, count, sender_name=None):
    """Render `count` question text areas; return list of raw strings."""
    ph = (
        f"Ask {sender_name} something real…"
        if sender_name else
        "Ask them something you actually want to know…"
    )
    return [
        st.text_area(
            f"Question {i + 1}",
            placeholder=ph,
            key=f"{prefix}_{i}",
            height=80,
        )
        for i in range(count)
    ]


def _exchange_card(label, color, questions, answers):
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


# ─── COMPOSE ─────────────────────────────────────────────────────────────────

def _render_compose():
    inject_css()
    _section_label("New Confession Exchange")

    if "conf_form_gen" not in st.session_state:
        st.session_state.conf_form_gen = 0
    if "conf_sent_to" not in st.session_state:
        st.session_state.conf_sent_to = None

    gen = st.session_state.conf_form_gen

    if st.session_state.conf_sent_to:
        st.success(
            f"Sent. {st.session_state.conf_sent_to} must write their own questions "
            "before they can even see what you asked."
        )
        st.session_state.conf_sent_to = None

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-top:2px solid var(--magenta);
            border-radius:4px; padding:20px 22px; margin-bottom:24px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.9;">
    Write <strong style="color:var(--text);">N questions</strong> for someone.
    Before they can see a single one, they have to write their own N questions back — blind.
    Then they answer yours. Then you answer theirs. Then everything reveals at once.
    <br><br>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">
      Nobody sees anything until every step is done. No shortcuts.
    </span>
  </div>
</div>
""")

    recipient_username = st.text_input(
        "Send to (username)",
        placeholder="Enter their ViceVault username",
        key=f"conf_recipient_{gen}",
    )

    n = int(st.number_input(
        "Number of questions (they'll have to match this)",
        min_value=1, max_value=10, value=3, step=1,
        key=f"conf_n_{gen}",
    ))

    st.html("<div style='height:8px'></div>")
    _section_label(f"Your {n} question{'s' if n != 1 else ''}")

    st.html("""
<div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
            margin-bottom:12px; padding:8px 12px; background:var(--surface); border-radius:4px;">
  Each question must end with <strong style="color:var(--text);">?</strong> or
  start with a question word (what, why, how, would, etc.).
  No copy-pasting the same question twice.
</div>
""")

    questions = _question_fields(f"conf_q_{gen}", n)

    st.html("<div style='height:12px'></div>")

    if st.button(
        "Send Confession →", type="primary",
        use_container_width=True, key=f"conf_send_{gen}",
    ):
        uid   = _current_uid()
        rname = (recipient_username or "").strip()

        if not uid:
            st.error("Not logged in.")
            return
        if not rname:
            st.error("Enter a recipient username.")
            return
        if rname.lower() == _current_username().lower():
            st.error("You can't send a confession to yourself.")
            return

        errs = _validate_questions(questions)
        if errs:
            for e in errs:
                st.error(e)
            return

        recipient = _db_get_user_by_username(rname)
        if not recipient:
            st.error(f"No user found with username '{rname}'.")
            return

        code    = _gen_code()
        success = _db_save_confession(uid, recipient["id"], code, questions)

        if success:
            st.session_state.conf_form_gen += 1
            st.session_state.conf_sent_to  = rname
            st.rerun()
        else:
            st.error("Something went wrong. Try again.")


# ─── INBOX ───────────────────────────────────────────────────────────────────

def _render_inbox():
    inject_css()
    _section_label("Inbox — Confessions sent to you")

    items = _db_load_inbox(_current_uid())

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
    code        = item["code"]
    sender_name = item.get("sender_username", "Someone")
    status      = item["status"]
    num_q       = len(item.get("sender_questions", []))
    ts          = str(item.get("created_at", ""))[:16]

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
    {num_q} question{'s' if num_q != 1 else ''} — but you can't see them yet
  </div>
</div>
""")

    _status_badge(status, sender_name, _current_username(), is_sender=False)

    # ── STEP 1: Write your questions BLIND before seeing theirs ──────────────
    if status == "sent":
        with st.expander(
            f"Step 1 / 2 — Write your {num_q} question{'s' if num_q != 1 else ''} for {sender_name}",
            expanded=True,
        ):
            st.html(f"""
<div style="padding:14px 16px; background:var(--surface); border-radius:4px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:6px;">
    You haven't seen their questions. That's the point.
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    Commit to your <strong style="color:var(--text);">{num_q} question{'s' if num_q != 1 else ''}</strong>
    for <strong style="color:var(--text);">{sender_name}</strong> before you see what they asked you.
    The moment you submit, their questions unlock — and you answer them.
    <br><br>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">
      Must end with ? or start with a question word. No duplicates.
    </span>
  </div>
</div>
""")

            recipient_questions = _question_fields(
                f"inbox_rq_{code}", num_q, sender_name=sender_name
            )

            st.html("<div style='height:8px'></div>")

            if st.button(
                f"Lock in my questions & see {sender_name}'s →",
                key=f"inbox_step1_{code}",
                type="primary",
                use_container_width=True,
            ):
                errs = _validate_questions(recipient_questions)
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    if _db_recipient_submit_questions(code, recipient_questions):
                        st.success(f"Locked in. {sender_name}'s questions are now visible below.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    # ── STEP 2: Questions committed — now answer sender's ────────────────────
    elif status == "questioning":
        sender_questions = item.get("sender_questions", [])

        with st.expander(
            f"Step 2 / 2 — Answer {sender_name}'s questions",
            expanded=True,
        ):
            st.html(f"""
<div style="padding:14px 16px; background:var(--surface); border-radius:4px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:6px;">
    Your questions are locked. No going back.
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    Answer <strong style="color:var(--text);">{sender_name}'s questions</strong> honestly.
    When you submit, they'll answer yours — and the exchange reveals for both of you simultaneously.
  </div>
</div>
""")

            recipient_answers = []
            for i, q in enumerate(sender_questions):
                st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
            padding:10px 14px; background:var(--surface);
            border-left:2px solid var(--magenta); border-radius:0 3px 3px 0;
            margin-bottom:6px; line-height:1.6;">{q}</div>
""")
                ans = st.text_area(
                    "Your answer",
                    placeholder="Be honest…",
                    key=f"inbox_ans_{code}_{i}",
                    height=80,
                    label_visibility="collapsed",
                )
                recipient_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:8px'></div>")

            if st.button(
                f"Submit answers — {sender_name} answers yours next →",
                key=f"inbox_step2_{code}",
                type="primary",
                use_container_width=True,
            ):
                blank = [i+1 for i, a in enumerate(recipient_answers) if not a.strip()]
                if blank:
                    nums = ', '.join(str(b) for b in blank)
                    plural = 'are' if len(blank) > 1 else 'is'
                    st.error(f"Answer{'s' if len(blank) > 1 else ''} {nums} {plural} empty.")
                else:
                    if _db_recipient_answer(code, recipient_answers):
                        st.success(
                            f"Done. Waiting for {sender_name} to answer your questions. "
                            "Everything reveals the moment they submit."
                        )
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "responded":
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You've done your part. {sender_name} is answering your questions now.
    <br>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--cyan);">
      The exchange reveals the moment they submit.
    </span>
  </div>
</div>
""")

    elif status == "revealed":
        _render_revealed(item, is_sender=False)

    st.html("<div style='height:12px'></div>")


# ─── OUTBOX ──────────────────────────────────────────────────────────────────

def _render_outbox():
    inject_css()
    _section_label("Sent — Confessions you started")

    items = _db_load_outbox(_current_uid())

    if not items:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">NOTHING SENT YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Start one from the Compose tab.
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
    ts             = str(item.get("created_at", ""))[:16]

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
    {recipient_name} must write their own questions first — before they can even see yours.
  </div>
</div>
""")

    elif status == "questioning":
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    {recipient_name} locked in their questions and is now answering yours.
  </div>
</div>
""")

    elif status == "responded":
        recipient_questions = item.get("recipient_questions", [])

        with st.expander(
            f"{recipient_name} answered — final step: answer their questions to reveal everything",
            expanded=True,
        ):
            st.html(f"""
<div style="padding:14px 16px; background:var(--surface); border-radius:4px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:6px;">
    Final step — submit and everything unlocks simultaneously.
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    <strong style="color:var(--text);">{recipient_name}</strong> answered your questions.
    Answer theirs — then both sides reveal at the exact same time.
  </div>
</div>
""")

            sender_answers = []
            for i, q in enumerate(recipient_questions):
                st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
            padding:10px 14px; background:var(--surface);
            border-left:2px solid var(--lime); border-radius:0 3px 3px 0;
            margin-bottom:6px; line-height:1.6;">{q}</div>
""")
                ans = st.text_area(
                    "Your answer",
                    placeholder="Be honest…",
                    key=f"outbox_ans_{code}_{i}",
                    height=80,
                    label_visibility="collapsed",
                )
                sender_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:8px'></div>")

            if st.button(
                "Submit — reveal the exchange →",
                key=f"outbox_submit_{code}",
                type="primary",
                use_container_width=True,
            ):
                blank = [i+1 for i, a in enumerate(sender_answers) if not a.strip()]
                if blank:
                    nums   = ', '.join(str(b) for b in blank)
                    plural = 'are' if len(blank) > 1 else 'is'
                    st.error(f"Answer{'s' if len(blank) > 1 else ''} {nums} {plural} empty.")
                else:
                    if _db_sender_answer(code, sender_answers):
                        st.success("Exchange revealed. Check the Revealed tab.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "revealed":
        _render_revealed(item, is_sender=True)

    st.html("<div style='height:12px'></div>")


# ─── REVEALED VIEW ───────────────────────────────────────────────────────────

def _render_revealed(item, is_sender: bool):
    sender_name    = item.get("sender_username",    "Sender")
    recipient_name = item.get("recipient_username", "Recipient")

    st.html("""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--lime); border-radius:4px;
            padding:16px 20px; margin-bottom:16px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime);
              letter-spacing:2px; margin-bottom:4px;">EXCHANGE REVEALED</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);">
    Every step done. Here's everything.
  </div>
</div>
""")

    sq = item.get("sender_questions",    [])
    ra = item.get("recipient_answers",   [])
    rq = item.get("recipient_questions", [])
    sa = item.get("sender_answers",      [])

    if is_sender:
        _exchange_card(f"Your questions → {recipient_name}'s answers", "#c6ff00", sq, ra)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"{recipient_name}'s questions → Your answers", "#ff2d78", rq, sa)
    else:
        _exchange_card(f"{sender_name}'s questions → Your answers", "#ff2d78", sq, ra)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"Your questions → {sender_name}'s answers", "#c6ff00", rq, sa)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def confessions_page():
    inject_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">CONFESSIONS</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Mutual. Blind. Nobody blinks first — because neither of you can.
  </div>
</div>
""")

    uid = _current_uid()
    if not uid:
        st.error("Log in to use Confessions.")
        return

    if "conf_tab" not in st.session_state:
        st.session_state.conf_tab = "compose"

    inbox_items  = _db_load_inbox(uid)
    outbox_items = _db_load_outbox(uid)

    inbox_action  = sum(1 for i in inbox_items  if i["status"] in ("sent", "questioning"))
    outbox_action = sum(1 for i in outbox_items if i["status"] == "responded")
    revealed_all  = [i for i in inbox_items + outbox_items if i["status"] == "revealed"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "◈  Compose", use_container_width=True,
            type="primary" if st.session_state.conf_tab == "compose" else "secondary",
            key="tab_compose",
        ):
            st.session_state.conf_tab = "compose"; st.rerun()

    with col2:
        b2 = f"  ({inbox_action})" if inbox_action else ""
        if st.button(
            f"↓  Inbox{b2}", use_container_width=True,
            type="primary" if st.session_state.conf_tab == "inbox" else "secondary",
            key="tab_inbox",
        ):
            st.session_state.conf_tab = "inbox"; st.rerun()

    with col3:
        b3 = f"  ({outbox_action})" if outbox_action else ""
        if st.button(
            f"↑  Sent{b3}", use_container_width=True,
            type="primary" if st.session_state.conf_tab == "sent" else "secondary",
            key="tab_sent",
        ):
            st.session_state.conf_tab = "sent"; st.rerun()

    with col4:
        b4 = f"  ({len(revealed_all)})" if revealed_all else ""
        if st.button(
            f"⚡  Revealed{b4}", use_container_width=True,
            type="primary" if st.session_state.conf_tab == "revealed" else "secondary",
            key="tab_revealed",
        ):
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
            seen, unique = set(), []
            for item in revealed_all:
                if item["code"] not in seen:
                    seen.add(item["code"])
                    unique.append(item)
            for item in unique:
                is_s  = item.get("sender_id") == uid
                other = item.get("recipient_username") if is_s else item.get("sender_username")
                ts    = str(item.get("created_at", ""))[:16]
                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s)
