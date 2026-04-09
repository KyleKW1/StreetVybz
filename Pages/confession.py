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

Security features:
  - Auto-delete revealed exchanges after 60 seconds
  - Viewer's username watermarked across ALL revealed content (traceable)
  - "Report screenshot" button at every step — saves a persistent notification to the other person
  - Screenshot alerts survive confession deletion
"""

import streamlit as st
import secrets
import string
import re
import time


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


# ─── WATERMARK ───────────────────────────────────────────────────────────────

def _watermark_svg(username: str) -> str:
    """
    Diagonal repeating SVG watermark stamped over revealed content.
    Uses a <pattern> so it tiles at any height automatically.
    Opacity is low enough to read content through it, but visible in screenshots.
    """
    safe = username.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"
     style="position:absolute;inset:0;pointer-events:none;z-index:10;border-radius:4px;"
     preserveAspectRatio="xMidYMid slice">
  <defs>
    <pattern id="wm-{safe}" x="0" y="0" width="280" height="130"
             patternUnits="userSpaceOnUse" patternTransform="rotate(-28)">
      <text x="10" y="52" font-family="Space Mono,monospace" font-size="13"
            font-weight="700" fill="rgba(255,45,120,0.15)" letter-spacing="3">
        {safe}
      </text>
      <text x="60" y="105" font-family="Space Mono,monospace" font-size="10"
            fill="rgba(198,255,0,0.10)" letter-spacing="2">
        ViceVault · {safe}
      </text>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#wm-{safe})" />
</svg>"""


def _watermarked_card(label: str, color: str, questions: list,
                      answers: list, viewer: str):
    """Each Q&A card rendered with the viewer's username tiled diagonally over it."""
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:{color}; margin-bottom:8px;">{label}</div>
""")
    wm = _watermark_svg(viewer)
    for i, (q, a) in enumerate(zip(questions, answers)):
        st.html(f"""
<div style="position:relative; overflow:hidden; background:var(--card);
            border:1px solid var(--border); border-left:2px solid {color};
            border-radius:4px; padding:16px 18px; margin-bottom:10px;
            user-select:none; -webkit-user-select:none;">
  {wm}
  <div style="position:relative; z-index:1;">
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
</div>
""")


# ─── AUTO-DELETE COUNTDOWN ───────────────────────────────────────────────────

def _inject_countdown(confession_code: str):
    """
    Fixed bottom banner: counts down 60 s.
    At zero appends ?delete_code=CODE to the URL → server deletes on next rerun.
    Safe to call multiple times — JS guards against duplicate banners.
    """
    st.html(f"""
<script>
(function() {{
  var code = "{confession_code}";
  if (document.getElementById("vv-countdown-banner")) return;

  var banner = document.createElement("div");
  banner.id = "vv-countdown-banner";
  banner.style.cssText = [
    "position:fixed","bottom:0","left:0","right:0",
    "background:#0a0a0b","border-top:2px solid #ff2d78",
    "padding:10px 24px","display:flex","align-items:center",
    "justify-content:space-between","z-index:9999",
    "font-family:'Space Mono',monospace","gap:12px","flex-wrap:wrap"
  ].join(";");
  banner.innerHTML = `
    <div style="font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#5a5a72;">
      EXCHANGE SELF-DESTRUCTS IN
    </div>
    <div id="vv-timer" style="font-size:24px;color:#ff2d78;font-weight:700;letter-spacing:4px;">
      1:00
    </div>
    <div style="font-size:9px;letter-spacing:1px;color:#5a5a72;text-transform:uppercase;">
      Your name is on every screenshot
    </div>
  `;
  document.body.appendChild(banner);

  var secondsLeft = 60;
  var timerEl = document.getElementById("vv-timer");

  var interval = setInterval(function() {{
    secondsLeft--;
    var m = Math.floor(secondsLeft / 60);
    var s = secondsLeft % 60;
    if (timerEl) {{
      timerEl.textContent = m + ":" + (s < 10 ? "0" + s : s);
      if (secondsLeft <= 10) timerEl.style.color = "#c6ff00";
      if (secondsLeft <= 5)  timerEl.style.color = "#ffffff";
    }}
    if (secondsLeft <= 0) {{
      clearInterval(interval);
      var url = new URL(window.location.href);
      url.searchParams.set("delete_code", code);
      window.location.href = url.toString();
    }}
  }}, 1000);
}})();
</script>
""")


# ─── QUESTION VALIDATION ─────────────────────────────────────────────────────

QUESTION_WORDS = {
    "what", "why", "how", "when", "where", "who", "whom", "which", "whose",
    "would", "could", "should", "do", "did", "does", "have", "has", "had",
    "are", "is", "was", "were", "will", "can", "may", "might", "shall",
    "if", "tell", "describe", "explain", "name",
}


def _validate_questions(questions: list) -> list:
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
    try:
        import database as db
        return db.confession_recipient_submit_questions(code, recipient_questions)
    except Exception:
        return False

def _db_recipient_answer(code, recipient_answers):
    try:
        import database as db
        return db.confession_recipient_answer(code, recipient_answers)
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

def _db_delete_confession(code):
    try:
        import database as db
        return db.delete_confession(code)
    except Exception:
        return False

def _db_save_screenshot_alert(code, reporter_id, reporter_username,
                               accused_username, alert_recipient_username):
    """
    Saves a screenshot report. Persists even after the confession is deleted.
    alert_recipient_username = the person who will SEE the alert in their banner.
    """
    try:
        import database as db
        return db.save_screenshot_alert(
            code, reporter_id, reporter_username,
            accused_username, alert_recipient_username
        )
    except Exception:
        return False

def _db_load_screenshot_alerts(user_id):
    try:
        import database as db
        return db.load_screenshot_alerts(user_id)
    except Exception:
        return []

def _db_dismiss_screenshot_alert(alert_id):
    try:
        import database as db
        return db.dismiss_screenshot_alert(alert_id)
    except Exception:
        return False


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


# ─── QUERY-PARAM SIGNAL HANDLER ──────────────────────────────────────────────

def _handle_query_params():
    """Reads signals posted by JS (auto-delete timer) and acts server-side."""
    params = st.query_params
    delete_code = params.get("delete_code")
    if delete_code:
        _db_delete_confession(delete_code)
        st.query_params.clear()
        st.rerun()


# ─── SCREENSHOT ALERTS BANNER ────────────────────────────────────────────────

def _render_screenshot_alerts():
    """
    Top-of-page persistent alerts.
    Written to a separate DB table — survive confession deletion.
    Shown to the person who was reported against (the accused's exchange partner).
    """
    uid    = _current_uid()
    alerts = _db_load_screenshot_alerts(uid)
    if not alerts:
        return

    for alert in alerts:
        accused  = alert.get("accused_username", "Someone")
        reporter = alert.get("reporter_username", "your exchange partner")
        ts       = str(alert.get("created_at", ""))[:16]
        alert_id = alert.get("id")

        st.html(f"""
<div style="background:#1a0a0e; border:1px solid var(--magenta);
            border-left:4px solid var(--magenta); border-radius:4px;
            padding:14px 18px; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:6px;">
    📸  Screenshot Report
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--text); line-height:1.7;">
    <strong style="color:var(--soft);">{reporter}</strong> reported that
    <strong style="color:var(--magenta);">{accused}</strong>
    may have screenshotted your confession exchange.
    <span style="color:var(--muted); font-size:11px; margin-left:6px;">{ts}</span>
    <br>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--muted);">
      Their username was watermarked on any screenshot they captured.
    </span>
  </div>
</div>
""")
        col_dismiss, _ = st.columns([1, 5])
        with col_dismiss:
            if st.button("Dismiss", key=f"dismiss_alert_{alert_id}"):
                _db_dismiss_screenshot_alert(alert_id)
                st.rerun()


# ─── REPORT SCREENSHOT BUTTON ────────────────────────────────────────────────

def _render_report_button(confession_code: str, accused_username: str,
                           alert_recipient_username: str):
    """
    Manual report button shown at every step.
    Pressing it saves a persistent alert to the accused person's banner.
    accused_username         = who you think took the screenshot
    alert_recipient_username = who gets notified (usually the accused themselves,
                               or their exchange partner depending on context)
    """
    col_btn, col_note = st.columns([3, 4])
    with col_btn:
        btn_key = f"report_ss_{confession_code}_{accused_username}"
        if st.button(f"📸  Report screenshot by {accused_username}", key=btn_key):
            uid      = _current_uid()
            reporter = _current_username()
            saved    = _db_save_screenshot_alert(
                confession_code,
                uid,
                reporter,
                accused_username,
                alert_recipient_username,
            )
            if saved:
                st.success(
                    f"Reported. {accused_username} has been notified. "
                    "Their username is watermarked on anything they captured."
                )
            else:
                st.error("Couldn't save the report. Try again.")
    with col_note:
        st.html(f"""
<div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);
            padding-top:8px; line-height:1.6;">
  Any screenshot <strong style="color:var(--soft);">{accused_username}</strong>
  took already has their username stamped on it.
</div>
""")


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
            True:  ("var(--lime)",    "REVEALED",   "Deletes in 60 s · your username is watermarked on every screenshot"),
            False: ("var(--lime)",    "REVEALED",   "Deletes in 60 s · your username is watermarked on every screenshot"),
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
      Revealed exchanges auto-delete in 60 seconds.
      Every screenshot has your username stamped on it — permanently traceable.
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
    viewer      = _current_username()

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

    _status_badge(status, sender_name, viewer, is_sender=False)

    # Report button available at every step (accuse the sender of screenshotting)
    _render_report_button(code, accused_username=sender_name,
                          alert_recipient_username=sender_name)

    # ── STEP 1 ───────────────────────────────────────────────────────────────
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
            recipient_questions = _question_fields(f"inbox_rq_{code}", num_q, sender_name=sender_name)
            st.html("<div style='height:8px'></div>")

            if st.button(
                f"Lock in my questions & see {sender_name}'s →",
                key=f"inbox_step1_{code}", type="primary", use_container_width=True,
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

    # ── STEP 2 ───────────────────────────────────────────────────────────────
    elif status == "questioning":
        sender_questions = item.get("sender_questions", [])
        with st.expander(f"Step 2 / 2 — Answer {sender_name}'s questions", expanded=True):
            st.html(f"""
<div style="padding:14px 16px; background:var(--surface); border-radius:4px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:6px;">
    Your questions are locked. No going back.
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    Answer <strong style="color:var(--text);">{sender_name}'s questions</strong> honestly.
    When you submit, they'll answer yours — and the exchange reveals simultaneously.
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
                    "Your answer", placeholder="Be honest…",
                    key=f"inbox_ans_{code}_{i}", height=80,
                    label_visibility="collapsed",
                )
                recipient_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:8px'></div>")
            if st.button(
                f"Submit answers — {sender_name} answers yours next →",
                key=f"inbox_step2_{code}", type="primary", use_container_width=True,
            ):
                blank = [i+1 for i, a in enumerate(recipient_answers) if not a.strip()]
                if blank:
                    nums   = ', '.join(str(b) for b in blank)
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
        _inject_countdown(code)
        _render_revealed(item, is_sender=False, viewer_username=viewer)
        _render_report_button(code, accused_username=sender_name,
                              alert_recipient_username=sender_name)

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
    viewer         = _current_username()

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

    _status_badge(status, viewer, recipient_name, is_sender=True)

    # Report button — accuse the recipient of screenshotting
    _render_report_button(code, accused_username=recipient_name,
                          alert_recipient_username=recipient_name)

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
    Answer theirs — both sides reveal at the exact same time.
    Exchange <strong style="color:var(--magenta);">auto-deletes in 60 seconds</strong> after reveal.
    Every screenshot carries your username as a permanent watermark.
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
                    "Your answer", placeholder="Be honest…",
                    key=f"outbox_ans_{code}_{i}", height=80,
                    label_visibility="collapsed",
                )
                sender_answers.append(ans)
                st.html("<div style='height:4px'></div>")

            st.html("<div style='height:8px'></div>")
            if st.button(
                "Submit — reveal the exchange →",
                key=f"outbox_submit_{code}", type="primary", use_container_width=True,
            ):
                blank = [i+1 for i, a in enumerate(sender_answers) if not a.strip()]
                if blank:
                    nums   = ', '.join(str(b) for b in blank)
                    plural = 'are' if len(blank) > 1 else 'is'
                    st.error(f"Answer{'s' if len(blank) > 1 else ''} {nums} {plural} empty.")
                else:
                    if _db_sender_answer(code, sender_answers):
                        st.success("Exchange revealed. It auto-deletes in 60 seconds.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "revealed":
        _inject_countdown(code)
        _render_revealed(item, is_sender=True, viewer_username=viewer)
        _render_report_button(code, accused_username=recipient_name,
                              alert_recipient_username=recipient_name)

    st.html("<div style='height:12px'></div>")


# ─── REVEALED VIEW ───────────────────────────────────────────────────────────

def _render_revealed(item, is_sender: bool, viewer_username: str):
    """
    Full exchange display with the viewer's username watermarked
    diagonally across every single card.
    """
    sender_name    = item.get("sender_username",    "Sender")
    recipient_name = item.get("recipient_username", "Recipient")

    st.html(f"""
<div style="position:relative; overflow:hidden; background:var(--card);
            border:1px solid var(--border); border-top:2px solid var(--lime);
            border-radius:4px; padding:16px 20px; margin-bottom:16px; text-align:center;">
  {_watermark_svg(viewer_username)}
  <div style="position:relative; z-index:1;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime);
                letter-spacing:2px; margin-bottom:6px;">EXCHANGE REVEALED</div>
    <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--muted);
                letter-spacing:1px; line-height:2;">
      ⏱ Auto-deletes in 60 s
      &nbsp;·&nbsp;
      🔏 <span style="color:var(--magenta);">{viewer_username}</span> watermarked on every screenshot
    </div>
  </div>
</div>
""")

    sq = item.get("sender_questions",    [])
    ra = item.get("recipient_answers",   [])
    rq = item.get("recipient_questions", [])
    sa = item.get("sender_answers",      [])

    if is_sender:
        _watermarked_card(
            f"Your questions → {recipient_name}'s answers",
            "#c6ff00", sq, ra, viewer_username
        )
        st.html("<div style='height:12px'></div>")
        _watermarked_card(
            f"{recipient_name}'s questions → Your answers",
            "#ff2d78", rq, sa, viewer_username
        )
    else:
        _watermarked_card(
            f"{sender_name}'s questions → Your answers",
            "#ff2d78", sq, ra, viewer_username
        )
        st.html("<div style='height:12px'></div>")
        _watermarked_card(
            f"Your questions → {sender_name}'s answers",
            "#c6ff00", rq, sa, viewer_username
        )


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def confessions_page():
    inject_css()
    _handle_query_params()

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

    # Persistent screenshot alert banner
    _render_screenshot_alerts()

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
            viewer = _current_username()
            seen, unique = set(), []
            for item in revealed_all:
                if item["code"] not in seen:
                    seen.add(item["code"])
                    unique.append(item)
            for item in unique:
                is_s  = item.get("sender_id") == uid
                other = item.get("recipient_username") if is_s else item.get("sender_username")
                ts    = str(item.get("created_at", ""))[:16]
                _inject_countdown(item["code"])
                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s, viewer_username=viewer)
                    _render_report_button(item["code"], accused_username=other,
                                          alert_recipient_username=other)
