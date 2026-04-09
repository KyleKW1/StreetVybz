"""
Pages/confessions.py — Mutual blind confession exchange.

Status machine (4 steps, nobody can cheat):
  sent        → Recipient must submit THEIR questions first (blind — sender's hidden)
  questioning → Recipient submitted their questions. Now they unlock sender's questions to answer.
  responded   → Recipient answered sender's questions. Sender must now answer recipient's.
  revealed    → Sender answered. Full exchange visible to both. Simultaneous unlock.

Auto-delete: revealed exchanges are deleted from DB after 60 seconds.
             This is enforced server-side on every page load — no JS required.

Screenshot detection: Desktop PrintScreen key only (reliable).
             visibilitychange / blur are NOT used — they fire on normal phone
             usage (lock screen, notification pull-down, app switch) and produce
             constant false positives. You cannot reliably detect screenshots in
             a browser. The PrintScreen key is the only genuinely trustworthy signal.
"""

import streamlit as st
import secrets
import string
import re
import time
from datetime import datetime, timedelta


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


# ─── COUNTDOWN BANNER (pure CSS/JS — no page-unload side effects) ─────────────

def inject_countdown_banner(confession_code: str, revealed_at_iso: str):
    """
    Shows a fixed bottom banner counting down to 0.
    When it hits 0 it sets a query param and reloads — server then deletes.
    Uses the server-recorded revealed_at time so the countdown is accurate
    even if the user refreshes.
    """
    st.html(f"""
<script>
(function() {{
  var code        = "{confession_code}";
  var revealedAt  = new Date("{revealed_at_iso}").getTime();
  var deleteAfter = 60 * 1000;  // 60 seconds in ms

  // Create banner if not already present
  var banner = document.getElementById("vv-countdown-banner");
  if (!banner) {{
    banner = document.createElement("div");
    banner.id = "vv-countdown-banner";
    banner.style.cssText = [
      "position:fixed","bottom:0","left:0","right:0",
      "background:#0a0a0b","border-top:2px solid #ff2d78",
      "padding:12px 24px","display:flex","align-items:center",
      "justify-content:space-between","z-index:9999",
      "font-family:'Space Mono',monospace"
    ].join(";");
    banner.innerHTML = `
      <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#5a5a72;">
        THIS EXCHANGE SELF-DESTRUCTS IN
      </div>
      <div id="vv-timer" style="font-size:22px;color:#ff2d78;font-weight:700;letter-spacing:3px;">
        1:00
      </div>
      <div style="font-size:10px;letter-spacing:1px;color:#5a5a72;text-transform:uppercase;">
        PrintScreen = logged out
      </div>
    `;
    document.body.appendChild(banner);
  }}

  var timerEl = document.getElementById("vv-timer");

  // Desktop PrintScreen detection (genuinely reliable)
  document.addEventListener("keyup", function(e) {{
    if (e.key === "PrintScreen" || e.keyCode === 44) {{
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code",  code);
      window.location.href = url.toString();
    }}
  }});

  var interval = setInterval(function() {{
    var elapsed   = Date.now() - revealedAt;
    var remaining = Math.max(0, Math.ceil((deleteAfter - elapsed) / 1000));

    if (timerEl) {{
      var m = Math.floor(remaining / 60);
      var s = remaining % 60;
      timerEl.textContent = m + ":" + (s < 10 ? "0" + s : s);
      if (remaining <= 10) timerEl.style.color = "#c6ff00";
      if (remaining <= 5)  timerEl.style.color = "#ffffff";
    }}

    if (remaining <= 0) {{
      clearInterval(interval);
      var url = new URL(window.location.href);
      url.searchParams.set("delete_code", code);
      window.location.href = url.toString();
    }}
  }}, 500);
}})();
</script>
""")


def inject_printscreen_guard(confession_code: str):
    """
    Inject desktop PrintScreen detection only (no visibilitychange/blur).
    Safe to use on non-revealed phases too.
    """
    st.html(f"""
<script>
(function() {{
  var code     = "{confession_code}";
  var reported = false;
  document.addEventListener("keyup", function(e) {{
    if (!reported && (e.key === "PrintScreen" || e.keyCode === 44)) {{
      reported = true;
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code", code);
      window.location.href = url.toString();
    }}
  }});
}})();
</script>
""")


# ─── SERVER-SIDE AUTO-DELETE CHECK ───────────────────────────────────────────

_DELETE_AFTER_SECONDS = 60


def _auto_delete_expired_revealed(items: list) -> list:
    """
    Called after loading inbox/outbox. For any item with status='revealed',
    check if it's been revealed for >60s. If so, delete it from DB and
    remove it from the list.
    Returns the filtered list.
    """
    kept = []
    for item in items:
        if item.get("status") != "revealed":
            kept.append(item)
            continue

        updated_at = item.get("updated_at")
        if updated_at is None:
            kept.append(item)
            continue

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except Exception:
                kept.append(item)
                continue

        age = (datetime.now() - updated_at).total_seconds()
        if age > _DELETE_AFTER_SECONDS:
            _db_delete_confession(item["code"])
            # Don't add to kept — it's gone
        else:
            kept.append(item)

    return kept


def _get_revealed_at_iso(item: dict) -> str:
    """Return the ISO string of when the exchange was revealed (updated_at)."""
    updated_at = item.get("updated_at")
    if updated_at is None:
        return datetime.now().isoformat()
    if hasattr(updated_at, "isoformat"):
        return updated_at.isoformat()
    return str(updated_at)


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


def _db_save_screenshot_alert(code, screenshotter_id, screenshotter_username, other_username):
    try:
        import database as db
        return db.save_screenshot_alert(
            code, screenshotter_id, screenshotter_username, other_username
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


def _db_logout_user(user_id):
    try:
        import database as db
        db.invalidate_user_sessions(user_id)
    except Exception:
        pass


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


def _force_logout():
    uid = _current_uid()
    if uid:
        _db_logout_user(uid)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ─── QUERY-PARAM SIGNAL HANDLERS ─────────────────────────────────────────────

def _handle_query_params():
    """
    Called once at the top of confessions_page().
    Handles:
      ?delete_code=XXXX          → delete the confession and rerun
      ?screenshot_code=XXXX      → save alert, log out user, rerun
    """
    params = st.query_params

    # ── Auto-delete signal (from countdown timer JS) ──────────────────────────
    delete_code = params.get("delete_code")
    if delete_code:
        _db_delete_confession(delete_code)
        st.query_params.clear()
        st.rerun()

    # ── Screenshot signal (PrintScreen key only) ──────────────────────────────
    ss_code = params.get("screenshot_code")
    if ss_code:
        uid      = _current_uid()
        username = _current_username()

        # Figure out the other party from the confession record
        try:
            import database as db
            item = db.get_confession_by_code(ss_code)
        except Exception:
            item = None

        other = ""
        if item:
            if item.get("sender_id") == uid:
                other = item.get("recipient_username", "")
            else:
                other = item.get("sender_username", "")

        if uid and other:
            _db_save_screenshot_alert(ss_code, uid, username, other)

        st.query_params.clear()

        st.error(
            f"⚠️  Screenshot detected (PrintScreen key). You've been logged out. "
            f"{other or 'The other person'} has been notified."
        )
        time.sleep(2)
        _force_logout()


# ─── SCREENSHOT ALERTS BANNER ─────────────────────────────────────────────────

def _render_screenshot_alerts():
    uid    = _current_uid()
    alerts = _db_load_screenshot_alerts(uid)
    if not alerts:
        return

    for alert in alerts:
        screenshotter = alert.get("screenshotter_username", "Someone")
        ts            = str(alert.get("created_at", ""))[:16]
        alert_id      = alert.get("id")

        st.html(f"""
<div style="background:#1a0a0e; border:1px solid var(--magenta);
            border-left:4px solid var(--magenta); border-radius:4px;
            padding:14px 18px; margin-bottom:10px; display:flex;
            align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
  <div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:4px;">
      ⚠  Screenshot Alert
    </div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--text); line-height:1.6;">
      <strong style="color:var(--magenta);">{screenshotter}</strong>
      pressed PrintScreen during your confession exchange.
      <span style="color:var(--muted); font-size:11px; margin-left:8px;">{ts}</span>
    </div>
  </div>
</div>
""")
        col_dismiss, _ = st.columns([1, 4])
        with col_dismiss:
            if st.button("Dismiss", key=f"dismiss_alert_{alert_id}"):
                _db_dismiss_screenshot_alert(alert_id)
                st.rerun()


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
            True:  ("var(--lime)",    "REVEALED",   "Exchange unlocked — deletes in 60 seconds"),
            False: ("var(--lime)",    "REVEALED",   "Exchange unlocked — deletes in 60 seconds"),
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
      The exchange auto-deletes 60 seconds after it's revealed.
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

    items = _auto_delete_expired_revealed(_db_load_inbox(_current_uid()))

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

    # PrintScreen guard on all phases
    inject_printscreen_guard(code)

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
    When you submit, they'll answer yours — and the exchange reveals for both simultaneously.
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
        inject_countdown_banner(code, _get_revealed_at_iso(item))
        _render_revealed(item, is_sender=False)

    st.html("<div style='height:12px'></div>")


# ─── OUTBOX ──────────────────────────────────────────────────────────────────

def _render_outbox():
    inject_css()
    _section_label("Sent — Confessions you started")

    items = _auto_delete_expired_revealed(_db_load_outbox(_current_uid()))

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

    inject_printscreen_guard(code)

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
    The exchange <strong style="color:var(--magenta);">auto-deletes 60 seconds after reveal</strong>.
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
                        st.success("Exchange revealed. It will auto-delete in 60 seconds.")
                        st.rerun()
                    else:
                        st.error("Something went wrong. Try again.")

    elif status == "revealed":
        inject_countdown_banner(code, _get_revealed_at_iso(item))
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
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:1px;
              color:var(--magenta);">
    ⏱  Auto-deletes in 60 seconds
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

    # Handle JS signals first
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

    _render_screenshot_alerts()

    if "conf_tab" not in st.session_state:
        st.session_state.conf_tab = "compose"

    # Load and auto-delete expired revealed items
    inbox_items  = _auto_delete_expired_revealed(_db_load_inbox(uid))
    outbox_items = _auto_delete_expired_revealed(_db_load_outbox(uid))

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
                inject_countdown_banner(item["code"], _get_revealed_at_iso(item))
                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s)
