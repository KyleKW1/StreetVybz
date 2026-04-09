"""
Pages/confession.py — Mutual blind confession exchange.

Auto-delete: The DB function delete_expired_confessions() runs at the top of
every page load. It deletes ALL confessions where status='revealed' and
revealed_at < NOW() - 60 seconds. This is purely server-side — no JS needed.

The JS countdown banner is cosmetic only (shows the timer). When it hits zero
it reloads the page, which triggers the server-side cleanup. If the user
refreshes manually the cleanup still runs.

Screenshot detection: Desktop PrintScreen key only.
iOS/Android screenshots CANNOT be detected from a browser — no API exists for
this. visibilitychange and blur fire constantly on mobile from normal usage.

NEW (v2):
- Glitch CSS animation on CONFESSIONS header
- Pulsing screen-edge countdown glow (magenta → amber → lime → white)
- Staggered card flip reveal animation
- Emoji reaction stamps (😳 👀 💀 🫣) during the revealed window
- Emotional step labels
- Email invite on compose — deep-link for non-users
- Typing indicator pulse when waiting
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
.stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important; color:var(--muted) !important;
}
.stSelectbox > div > div { background:var(--card) !important; border:1px solid var(--border) !important; color:var(--text) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }

/* ── Glitch animation for CONFESSIONS header ── */
@keyframes glitch-clip {
  0%   { clip-path:inset(0 0 95% 0); transform:translate(-3px, 0); }
  10%  { clip-path:inset(30% 0 55% 0); transform:translate(3px, 0); }
  20%  { clip-path:inset(60% 0 15% 0); transform:translate(-2px, 0); }
  30%  { clip-path:inset(80% 0 5% 0);  transform:translate(2px, 0); }
  40%  { clip-path:inset(10% 0 80% 0); transform:translate(-3px, 0); }
  50%  { clip-path:inset(0 0 0 0);     transform:translate(0, 0); opacity:0; }
  100% { clip-path:inset(0 0 0 0);     transform:translate(0, 0); opacity:0; }
}
.glitch-wrap { position:relative; display:inline-block; }
.glitch-wrap::before,
.glitch-wrap::after {
  content: attr(data-text);
  position:absolute; top:0; left:0;
  font-family:'Bebas Neue',sans-serif;
  font-size:48px; letter-spacing:3px; line-height:0.95;
  pointer-events:none;
}
.glitch-wrap::before {
  color:var(--cyan);
  animation: glitch-clip 4s infinite linear;
  animation-delay: 0.5s;
}
.glitch-wrap::after {
  color:var(--magenta);
  animation: glitch-clip 4s infinite linear;
  animation-delay: 1.2s;
}

/* ── Staggered card entrance ── */
@keyframes card-enter {
  from { opacity:0; transform:translateY(18px) scale(0.97); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}
.reveal-card {
  animation: card-enter 0.45s cubic-bezier(0.19,1,0.22,1) both;
}

/* ── Reaction stamp button ── */
.reaction-btn {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 6px 14px !important;
  font-size: 18px !important;
  cursor: pointer !important;
  transition: all 0.15s !important;
  display: inline-block !important;
  letter-spacing: 0 !important;
}
.reaction-btn:hover {
  border-color: var(--magenta) !important;
  transform: scale(1.15) !important;
  box-shadow: 0 0 12px rgba(255,45,120,0.3) !important;
}

/* ── Typing indicator ── */
@keyframes typing-pulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40%           { opacity: 1;   transform: scale(1); }
}
.typing-dot {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--magenta);
  animation: typing-pulse 1.4s infinite ease-in-out;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
</style>
""")


# ─── COUNTDOWN BANNER (pulsing screen-edge glow) ─────────────────────────────

def inject_countdown_banner(confession_code: str, revealed_at_iso: str):
    """
    Fixed bottom banner + pulsing screen-edge border.
    Color shifts: magenta (60s) → amber (15s) → lime (5s) → white (3s).
    At 10s the whole screen border glows. At 3s it flickers.
    Also catches desktop PrintScreen key.
    """
    st.html(f"""
<style>
@keyframes border-pulse {{
  0%, 100% {{ opacity:1; }}
  50%       {{ opacity:0.4; }}
}}
@keyframes border-flicker {{
  0%,100% {{ opacity:1; }}
  25%     {{ opacity:0.1; }}
  50%     {{ opacity:0.8; }}
  75%     {{ opacity:0.2; }}
}}
#vv-screen-glow {{
  position:fixed; inset:0; pointer-events:none; z-index:9998;
  border:3px solid var(--magenta);
  box-shadow: inset 0 0 40px rgba(255,45,120,0.08), 0 0 0 0 transparent;
  transition: border-color 0.6s, box-shadow 0.6s;
  animation: border-pulse 2s infinite;
}}
#vv-screen-glow.amber {{
  border-color: var(--amber);
  box-shadow: inset 0 0 60px rgba(255,179,0,0.12), 0 0 30px rgba(255,179,0,0.18);
  animation: border-pulse 1.2s infinite;
}}
#vv-screen-glow.lime {{
  border-color: var(--lime);
  box-shadow: inset 0 0 80px rgba(198,255,0,0.18), 0 0 50px rgba(198,255,0,0.22);
  animation: border-pulse 0.7s infinite;
}}
#vv-screen-glow.white {{
  border-color: #fff;
  box-shadow: inset 0 0 100px rgba(255,255,255,0.2), 0 0 80px rgba(255,255,255,0.3);
  animation: border-flicker 0.3s infinite;
}}
</style>
<script>
(function() {{
  var code       = {repr(confession_code)};
  var revealedAt = new Date({repr(revealed_at_iso)}).getTime();
  var DELETE_MS  = 60 * 1000;

  // Screen glow element
  if (!document.getElementById("vv-screen-glow")) {{
    var glow = document.createElement("div");
    glow.id = "vv-screen-glow";
    document.body.appendChild(glow);
  }}

  if (!document.getElementById("vv-countdown-banner")) {{
    var banner = document.createElement("div");
    banner.id = "vv-countdown-banner";
    banner.style.cssText = "position:fixed;bottom:0;left:0;right:0;background:#0a0a0b;border-top:2px solid #ff2d78;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;z-index:9999;font-family:'Space Mono',monospace;";
    banner.innerHTML = '<div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#5a5a72;">DELETES IN</div><div id="vv-timer" style="font-size:22px;color:#ff2d78;font-weight:700;letter-spacing:3px;">1:00</div><div style="font-size:10px;letter-spacing:1px;color:#5a5a72;text-transform:uppercase;">Desktop PrintScreen = logged out</div>';
    document.body.appendChild(banner);
  }}

  var timerEl = document.getElementById("vv-timer");
  var glowEl  = document.getElementById("vv-screen-glow");
  var bannerEl = document.getElementById("vv-countdown-banner");

  // Desktop PrintScreen detection
  document.addEventListener("keyup", function(e) {{
    if (e.key === "PrintScreen" || e.keyCode === 44) {{
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code", code);
      window.location.href = url.toString();
    }}
  }});

  var iv = setInterval(function() {{
    var remaining = Math.max(0, Math.ceil((DELETE_MS - (Date.now() - revealedAt)) / 1000));
    if (timerEl) {{
      var m = Math.floor(remaining / 60);
      var s = remaining % 60;
      timerEl.textContent = m + ":" + (s < 10 ? "0" + s : s);
    }}

    // Color shifts
    if (glowEl && bannerEl) {{
      if (remaining <= 3) {{
        glowEl.className = "white";
        timerEl.style.color = "#ffffff";
        bannerEl.style.borderTopColor = "#ffffff";
      }} else if (remaining <= 5) {{
        glowEl.className = "lime";
        timerEl.style.color = "#c6ff00";
        bannerEl.style.borderTopColor = "#c6ff00";
      }} else if (remaining <= 15) {{
        glowEl.className = "amber";
        timerEl.style.color = "#ffb300";
        bannerEl.style.borderTopColor = "#ffb300";
      }} else {{
        glowEl.className = "";
        timerEl.style.color = "#ff2d78";
        bannerEl.style.borderTopColor = "#ff2d78";
      }}
    }}

    if (remaining <= 0) {{
      clearInterval(iv);
      window.location.reload();
    }}
  }}, 500);
}})();
</script>
""")


def inject_printscreen_guard(confession_code: str):
    """Desktop PrintScreen guard for non-revealed phases."""
    st.html(f"""
<script>
(function() {{
  var code = {repr(confession_code)};
  var done = false;
  document.addEventListener("keyup", function(e) {{
    if (!done && (e.key === "PrintScreen" || e.keyCode === 44)) {{
      done = true;
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code", code);
      window.location.href = url.toString();
    }}
  }});
}})();
</script>
""")


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _revealed_at_iso(item: dict) -> str:
    ra = item.get("revealed_at")
    if ra is None:
        ra = item.get("updated_at") or item.get("created_at")
    if ra is None:
        from datetime import datetime
        return datetime.now().isoformat()
    if hasattr(ra, "isoformat"):
        return ra.isoformat()
    return str(ra)


# ─── QUESTION VALIDATION ─────────────────────────────────────────────────────

QUESTION_WORDS = {
    "what", "why", "how", "when", "where", "who", "whom", "which", "whose",
    "would", "could", "should", "do", "did", "does", "have", "has", "had",
    "are", "is", "was", "were", "will", "can", "may", "might", "shall",
    "if", "tell", "describe", "explain", "name",
}


def _validate_questions(questions: list) -> list:
    errors, seen = [], {}
    for i, raw in enumerate(questions):
        q = raw.strip()
        num = i + 1
        if not q:
            errors.append(f"Question {num} is empty.")
            continue
        if len(q) < 8:
            errors.append(f"Question {num} is too short.")
            continue
        first_word = re.split(r'\W+', q.lower())[0]
        if not q.endswith("?") and first_word not in QUESTION_WORDS:
            errors.append(f"Question {num} doesn't look like a question. End with '?' or start with a question word.")
            continue
        norm = re.sub(r'[^\w\s]', '', q.lower()).strip()
        if norm in seen:
            errors.append(f"Question {num} is a duplicate of question {seen[norm]}.")
        else:
            seen[norm] = num
    return errors


# ─── DB WRAPPERS ─────────────────────────────────────────────────────────────

def _db(fn, *args, default=None, **kwargs):
    try:
        import database as db
        return getattr(db, fn)(*args, **kwargs)
    except Exception:
        return default


# ─── SESSION HELPERS ─────────────────────────────────────────────────────────

def _uid():
    u = st.session_state.get("user", {})
    return u.get("id") if u else None


def _username():
    u = st.session_state.get("user", {})
    return u.get("username", "You")


def _force_logout():
    _db("invalidate_user_sessions", _uid())
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


def _gen_code(n=8):
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(n))


# ─── QUERY PARAM HANDLER ─────────────────────────────────────────────────────

def _handle_query_params():
    params = st.query_params

    delete_code = params.get("delete_code")
    if delete_code:
        _db("delete_confession", delete_code)
        st.query_params.clear()
        st.rerun()

    ss_code = params.get("screenshot_code")
    if ss_code:
        uid      = _uid()
        username = _username()
        try:
            import database as db
            item = db.get_confession_by_code(ss_code)
        except Exception:
            item = None

        other = ""
        if item:
            other = item.get("recipient_username") if item.get("sender_id") == uid else item.get("sender_username", "")

        if uid and other:
            _db("save_screenshot_alert", ss_code, uid, username, other)

        st.query_params.clear()
        st.error(f"⚠️  Screenshot detected. You've been logged out. {other or 'The other person'} has been notified.")
        time.sleep(2)
        _force_logout()


# ─── SCREENSHOT ALERTS ───────────────────────────────────────────────────────

def _render_screenshot_alerts():
    alerts = _db("load_screenshot_alerts", _uid(), default=[])
    for alert in alerts:
        screenshotter = alert.get("screenshotter_username", "Someone")
        ts            = str(alert.get("created_at", ""))[:16]
        alert_id      = alert.get("id")
        st.html(f"""
<div style="background:#1a0a0e;border:1px solid var(--magenta);border-left:4px solid var(--magenta);
            border-radius:4px;padding:14px 18px;margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
              text-transform:uppercase;color:var(--magenta);margin-bottom:4px;">⚠  Screenshot Alert</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--text);line-height:1.6;">
    <strong style="color:var(--magenta);">{screenshotter}</strong> pressed PrintScreen during your exchange.
    <span style="color:var(--muted);font-size:11px;margin-left:8px;">{ts}</span>
  </div>
</div>
""")
        col_d, _ = st.columns([1, 4])
        with col_d:
            if st.button("Dismiss", key=f"dismiss_{alert_id}"):
                _db("dismiss_screenshot_alert", alert_id)
                st.rerun()


# ─── UI COMPONENTS ───────────────────────────────────────────────────────────

def _section_label(text):
    st.html(f'<div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-bottom:12px;">{text}</div>')


def _status_badge(status, sender, recipient, is_sender):
    cfg = {
        "sent":        {True: ("var(--amber)", "WAITING",   f"Waiting for {recipient} to send their questions first"),
                        False: ("var(--magenta)", "YOUR MOVE", f"Write your questions before you can see {sender}'s")},
        "questioning": {True: ("var(--amber)", "WAITING",   f"{recipient} sent their questions — waiting for them to answer yours"),
                        False: ("var(--cyan)",  "YOUR TURN", f"Your questions are locked in — now answer {sender}'s")},
        "responded":   {True: ("var(--cyan)",  "YOUR TURN", f"{recipient} answered — now answer their questions to reveal"),
                        False: ("var(--amber)", "WAITING",   f"Waiting for {sender} to answer your questions")},
        "revealed":    {True: ("var(--lime)",  "REVEALED",  "Exchange unlocked — deletes in 60 seconds"),
                        False: ("var(--lime)", "REVEALED",  "Exchange unlocked — deletes in 60 seconds")},
    }
    color, label, detail = cfg.get(status, {}).get(is_sender, ("var(--muted)", status.upper(), ""))
    st.html(f"""
<div style="display:inline-flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;
              color:{color};border:1px solid {color};border-radius:2px;padding:4px 10px;">{label}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--muted);">{detail}</div>
</div>
""")


def _typing_indicator(name: str):
    """Show a pulsing 'they're writing...' indicator."""
    st.html(f"""
<div style="display:flex;align-items:center;gap:10px;padding:10px 0 14px 0;">
  <span style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
               text-transform:uppercase;color:var(--muted);">{name} is writing</span>
  <span class="typing-dot"></span>
  <span class="typing-dot"></span>
  <span class="typing-dot"></span>
</div>
""")


def _question_fields(prefix, count, sender_name=None):
    ph = f"Ask {sender_name} something real…" if sender_name else "Ask them something you actually want to know…"
    return [st.text_area(f"Question {i+1}", placeholder=ph, key=f"{prefix}_{i}", height=80) for i in range(count)]


def _exchange_card(label, color, questions, answers, delay_base=0):
    """Renders exchange cards with staggered entrance animation."""
    st.html(f'<div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:{color};margin-bottom:8px;">{label}</div>')
    for i, (q, a) in enumerate(zip(questions, answers)):
        delay = delay_base + i * 0.12
        st.html(f"""
<div class="reveal-card" style="animation-delay:{delay}s;background:var(--card);border:1px solid var(--border);
            border-left:2px solid {color};border-radius:4px;padding:16px 18px;margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);
              letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Q{i+1}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:var(--text);
              line-height:1.6;margin-bottom:10px;">{q}</div>
  <div style="height:1px;background:var(--border);margin-bottom:10px;"></div>
  <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);
              letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Answer</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:{color};
              line-height:1.7;font-style:italic;">"{a}"</div>
</div>
""")


def _reaction_stamps(confession_code: str):
    """
    Emoji reaction stamps during the revealed window.
    Reactions are stored in DB (save_reaction) and shown live.
    Falls back gracefully if DB doesn't support reactions yet.
    """
    EMOJIS = ["😳", "👀", "💀", "🫣"]
    st.html("""
<div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
            text-transform:uppercase;color:var(--muted);margin-bottom:10px;">React</div>
""")
    cols = st.columns(len(EMOJIS))
    existing = _db("load_reactions", confession_code, _uid(), default=[])
    reacted = {r.get("emoji") for r in (existing or [])}

    for i, emoji in enumerate(EMOJIS):
        count = _db("count_reactions", confession_code, emoji, default=0) or 0
        with cols[i]:
            already = emoji in reacted
            label = f"{emoji}  {count}" if count else emoji
            border_color = "var(--magenta)" if already else "var(--border)"
            if st.button(label, key=f"react_{confession_code}_{emoji}",
                         help="React" if not already else "Already reacted"):
                if not already:
                    _db("save_reaction", confession_code, _uid(), emoji)
                    st.rerun()


# ─── EMAIL INVITE HELPERS ─────────────────────────────────────────────────────

def _send_invite_email(sender_username: str, recipient_email: str, confession_code: str) -> bool:
    """
    Send an email invite with a deep-link to the confession exchange.
    Requires: save_pending_invite(code, sender_id, email) in DB
              send_transactional_email(to, subject, html) in email module.
    Returns True on success.
    """
    base_url = st.secrets.get("APP_URL", "https://yourvicevault.app")
    link = f"{base_url}/?invite={confession_code}"

    html_body = f"""
<div style="background:#0a0a0b;color:#f0f0f5;font-family:'DM Sans',sans-serif;max-width:520px;margin:0 auto;padding:32px;">
  <div style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#5a5a72;margin-bottom:8px;">Vice Vault</div>
  <div style="font-size:36px;font-weight:900;letter-spacing:2px;color:#fff;margin-bottom:20px;">CONFESSIONS</div>
  <div style="font-size:15px;color:#9090aa;line-height:1.8;margin-bottom:28px;">
    <strong style="color:#f0f0f5;">{sender_username}</strong> wants to exchange confessions with you.
    Blind. Mutual. Auto-deletes after reveal.<br><br>
    Before you can read their questions, you write your own back.
    Then you both answer. Everything reveals at once.
  </div>
  <a href="{link}" style="display:inline-block;background:#ff2d78;color:#fff;text-decoration:none;
     font-family:'Space Mono',monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;
     padding:14px 28px;border-radius:3px;">Accept &amp; Write Back →</a>
  <div style="margin-top:24px;font-size:11px;color:#5a5a72;">This link is one-time use. Don't share it.</div>
</div>
"""
    try:
        import database as db
        db.save_pending_invite(confession_code, _uid(), recipient_email)
    except Exception:
        pass

    try:
        import email_service
        return email_service.send_transactional_email(
            to=recipient_email,
            subject=f"{sender_username} sent you a confession on Vice Vault",
            html=html_body
        )
    except Exception:
        return False


# ─── COMPOSE ─────────────────────────────────────────────────────────────────

def _render_compose():
    inject_css()
    _section_label("New Confession Exchange")

    st.session_state.setdefault("conf_form_gen", 0)
    st.session_state.setdefault("conf_sent_to", None)
    st.session_state.setdefault("conf_invite_mode", False)
    gen = st.session_state.conf_form_gen

    if st.session_state.conf_sent_to:
        st.success(f"Sent. {st.session_state.conf_sent_to} must write their own questions first.")
        st.session_state.conf_sent_to = None

    st.html("""
<div style="background:var(--card);border:1px solid var(--border);border-top:2px solid var(--magenta);
            border-radius:4px;padding:20px 22px;margin-bottom:24px;">
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--soft);line-height:1.9;">
    Write questions for someone. Before they can see a single one, they write their own back — blind.
    Then they answer yours. Then you answer theirs. Everything reveals at once.
    Auto-deletes 60 seconds after reveal.
  </div>
</div>
""")

    # ── Recipient input: username or email invite toggle ──
    invite_mode = st.toggle("Recipient isn't on ViceVault? Invite by email", key=f"conf_invite_toggle_{gen}",
                             value=st.session_state.conf_invite_mode)
    st.session_state.conf_invite_mode = invite_mode

    if invite_mode:
        recipient_email = st.text_input("Recipient email", placeholder="their@email.com", key=f"conf_email_{gen}")
        recipient_username = None
        st.html("""
<div style="background:#0f1a10;border:1px solid #1e3a20;border-radius:4px;padding:12px 16px;margin-bottom:16px;">
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:#5a7a5a;line-height:1.7;">
    They'll get a one-time link. If they don't have an account, they sign up first and land straight in the exchange.
  </div>
</div>
""")
    else:
        recipient_username = st.text_input("Send to (username)", placeholder="Their ViceVault username", key=f"conf_recipient_{gen}")
        recipient_email = None

    n = int(st.number_input("Number of questions", min_value=1, max_value=10, value=3, step=1, key=f"conf_n_{gen}"))
    st.html("<div style='height:8px'></div>")
    _section_label(f"Your {n} question{'s' if n != 1 else ''}")
    questions = _question_fields(f"conf_q_{gen}", n)
    st.html("<div style='height:12px'></div>")

    btn_label = "Send Invite →" if invite_mode else "Send Confession →"
    if st.button(btn_label, type="primary", use_container_width=True, key=f"conf_send_{gen}"):
        uid = _uid()
        if not uid:
            st.error("Not logged in."); return

        errs = _validate_questions(questions)
        if errs:
            [st.error(e) for e in errs]; return

        code = _gen_code()

        if invite_mode:
            # Email invite path
            email = (recipient_email or "").strip()
            if not email or "@" not in email:
                st.error("Enter a valid email address."); return
            # Save as pending invite confession (recipient_id=None until they sign up)
            if _db("save_confession_invite", uid, email, code, questions):
                sent = _send_invite_email(_username(), email, code)
                if sent:
                    st.session_state.conf_form_gen += 1
                    st.session_state.conf_sent_to = email
                    st.rerun()
                else:
                    st.warning("Confession saved but email failed to send. Share the invite link manually.")
                    st.code(f"{st.secrets.get('APP_URL','https://yourvicevault.app')}/?invite={code}")
            else:
                st.error("Something went wrong.")
        else:
            # Username path (original flow)
            rname = (recipient_username or "").strip()
            if not rname:
                st.error("Enter a recipient username."); return
            if rname.lower() == _username().lower():
                st.error("You can't send a confession to yourself."); return
            recipient = _db("get_user_by_username", rname)
            if not recipient:
                st.error(f"No user found: '{rname}'. Use the email invite toggle if they're not on the app."); return
            if _db("save_confession", uid, recipient["id"], code, questions):
                st.session_state.conf_form_gen += 1
                st.session_state.conf_sent_to = rname
                st.rerun()
            else:
                st.error("Something went wrong.")


# ─── INBOX ───────────────────────────────────────────────────────────────────

def _render_inbox():
    inject_css()
    _section_label("Inbox — Confessions sent to you")
    items = _db("load_confessions_inbox", _uid(), default=[])
    if not items:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:28px;letter-spacing:3px;color:var(--muted);">NOTHING YET</div></div>')
        return
    for item in items:
        _render_inbox_item(item)


def _render_inbox_item(item):
    code        = item["code"]
    sender_name = item.get("sender_username", "Someone")
    status      = item["status"]
    num_q       = len(item.get("sender_questions", []))
    ts          = str(item.get("created_at", ""))[:16]

    inject_printscreen_guard(code)

    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid var(--magenta);
            border-radius:4px;padding:18px 20px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;color:var(--text);">From {sender_name}</div>
    <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--soft);">{num_q} question{'s' if num_q != 1 else ''} — hidden until you write yours</div>
</div>
""")
    _status_badge(status, sender_name, _username(), is_sender=False)

    if status == "sent":
        # Emotional label: "Your move. They're waiting."
        with st.expander(f"Your move — write your {num_q} question{'s' if num_q != 1 else ''} for {sender_name}", expanded=True):
            st.html(f"""
<div style="padding:10px 14px;background:var(--surface);border-radius:4px;margin-bottom:14px;
            font-family:'DM Sans',sans-serif;font-size:13px;color:var(--soft);line-height:1.7;">
  {sender_name} already sent theirs — sealed and waiting. Write yours back before either of you sees anything.
</div>
""")
            rqs = _question_fields(f"inbox_rq_{code}", num_q, sender_name=sender_name)
            if st.button(f"Lock in — now see {sender_name}'s questions →", key=f"inbox_step1_{code}", type="primary", use_container_width=True):
                errs = _validate_questions(rqs)
                if errs:
                    [st.error(e) for e in errs]
                elif _db("confession_recipient_submit_questions", code, rqs):
                    st.success("Locked in."); st.rerun()
                else:
                    st.error("Something went wrong.")

    elif status == "questioning":
        sender_questions = item.get("sender_questions", [])
        # Emotional label: "They blinked first. Now answer."
        with st.expander(f"They showed their hand — answer {sender_name}'s questions", expanded=True):
            st.html(f"""
<div style="padding:10px 14px;background:var(--surface);border-radius:4px;margin-bottom:14px;
            font-family:'DM Sans',sans-serif;font-size:13px;color:var(--soft);line-height:1.7;">
  Both sets of questions are locked in. Answer honestly — {sender_name} can't see your questions until they answer yours too.
</div>
""")
            recipient_answers = []
            for i, q in enumerate(sender_questions):
                st.html(f'<div style="font-family:\'DM Sans\',sans-serif;font-size:14px;color:var(--text);padding:10px 14px;background:var(--surface);border-left:2px solid var(--magenta);border-radius:0 3px 3px 0;margin-bottom:6px;line-height:1.6;">{q}</div>')
                recipient_answers.append(st.text_area("Your answer", placeholder="Be honest…", key=f"inbox_ans_{code}_{i}", height=80, label_visibility="collapsed"))
            if st.button("Submit answers — trigger the reveal →", key=f"inbox_step2_{code}", type="primary", use_container_width=True):
                blank = [i+1 for i, a in enumerate(recipient_answers) if not a.strip()]
                if blank:
                    st.error(f"Answer{'s' if len(blank)>1 else ''} {', '.join(map(str,blank))} {'are' if len(blank)>1 else 'is'} empty.")
                elif _db("confession_recipient_answer", code, recipient_answers):
                    st.success("Done. Waiting for them to answer your questions."); st.rerun()
                else:
                    st.error("Something went wrong.")

    elif status == "responded":
        _typing_indicator(sender_name)
        st.html(f'<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:16px 18px;margin-bottom:12px;font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);">{sender_name} is answering your questions. Exchange reveals when they submit.</div>')

    elif status == "revealed":
        inject_countdown_banner(code, _revealed_at_iso(item))
        _render_revealed(item, is_sender=False)
        _reaction_stamps(code)

    st.html("<div style='height:12px'></div>")


# ─── OUTBOX ──────────────────────────────────────────────────────────────────

def _render_outbox():
    inject_css()
    _section_label("Sent — Confessions you started")
    items = _db("load_confessions_outbox", _uid(), default=[])
    if not items:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:28px;letter-spacing:3px;color:var(--muted);">NOTHING SENT YET</div></div>')
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
<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid var(--lime);
            border-radius:4px;padding:18px 20px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;color:var(--text);">To {recipient_name}</div>
    <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--soft);">{num_q} question{'s' if num_q != 1 else ''} sent</div>
</div>
""")
    _status_badge(status, _username(), recipient_name, is_sender=True)

    if status == "sent":
        _typing_indicator(recipient_name)
        st.html(f'<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:16px 18px;margin-bottom:12px;font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);">{recipient_name} must write their own questions before they can see yours.</div>')

    elif status == "questioning":
        _typing_indicator(recipient_name)
        st.html(f'<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:16px 18px;margin-bottom:12px;font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);">{recipient_name} locked in their questions and is now answering yours.</div>')

    elif status == "responded":
        recipient_questions = item.get("recipient_questions", [])
        # Emotional label: "They answered. Your move."
        with st.expander(f"They answered. Seal the deal — answer {recipient_name}'s questions", expanded=True):
            st.html(f"""
<div style="padding:14px 16px;background:var(--surface);border-radius:4px;margin-bottom:16px;
            font-family:'DM Sans',sans-serif;font-size:13px;color:var(--soft);line-height:1.7;">
  {recipient_name} answered your questions. The moment you submit, both sides reveal simultaneously.
  <strong style="color:var(--magenta);">Auto-deletes 60 seconds after reveal.</strong>
</div>
""")
            sender_answers = []
            for i, q in enumerate(recipient_questions):
                st.html(f'<div style="font-family:\'DM Sans\',sans-serif;font-size:14px;color:var(--text);padding:10px 14px;background:var(--surface);border-left:2px solid var(--lime);border-radius:0 3px 3px 0;margin-bottom:6px;line-height:1.6;">{q}</div>')
                sender_answers.append(st.text_area("Your answer", placeholder="Be honest…", key=f"outbox_ans_{code}_{i}", height=80, label_visibility="collapsed"))
            if st.button("Submit — reveal everything →", key=f"outbox_submit_{code}", type="primary", use_container_width=True):
                blank = [i+1 for i, a in enumerate(sender_answers) if not a.strip()]
                if blank:
                    st.error(f"Answer{'s' if len(blank)>1 else ''} {', '.join(map(str,blank))} {'are' if len(blank)>1 else 'is'} empty.")
                elif _db("confession_sender_answer", code, sender_answers):
                    st.success("Revealed. Auto-deletes in 60 seconds."); st.rerun()
                else:
                    st.error("Something went wrong.")

    elif status == "revealed":
        inject_countdown_banner(code, _revealed_at_iso(item))
        _render_revealed(item, is_sender=True)
        _reaction_stamps(code)

    st.html("<div style='height:12px'></div>")


# ─── REVEALED VIEW ───────────────────────────────────────────────────────────

def _render_revealed(item, is_sender: bool):
    sender_name    = item.get("sender_username", "Sender")
    recipient_name = item.get("recipient_username", "Recipient")

    st.html("""
<div style="background:var(--card);border:1px solid var(--border);border-top:2px solid var(--lime);
            border-radius:4px;padding:16px 20px;margin-bottom:16px;text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--lime);
              letter-spacing:2px;margin-bottom:4px;">EXCHANGE REVEALED</div>
  <div style="font-family:'Space Mono',monospace;font-size:10px;color:var(--magenta);">⏱  Auto-deletes in 60 seconds</div>
</div>
""")

    sq = item.get("sender_questions", [])
    ra = item.get("recipient_answers", [])
    rq = item.get("recipient_questions", [])
    sa = item.get("sender_answers", [])

    if is_sender:
        _exchange_card(f"Your questions → {recipient_name}'s answers", "#c6ff00", sq, ra, delay_base=0)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"{recipient_name}'s questions → Your answers", "#ff2d78", rq, sa, delay_base=len(sq) * 0.12)
    else:
        _exchange_card(f"{sender_name}'s questions → Your answers", "#ff2d78", sq, ra, delay_base=0)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"Your questions → {sender_name}'s answers", "#c6ff00", rq, sa, delay_base=len(sq) * 0.12)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def confessions_page():
    inject_css()

    # ── 1. Delete ALL expired revealed confessions (server-side, runs every load) ──
    try:
        import database as db
        db.delete_expired_confessions()
    except Exception:
        pass

    # ── 2. Handle JS signals (PrintScreen redirect, countdown reload) ──────────
    _handle_query_params()

    # ── 3. Glitch header ────────────────────────────────────────────────────────
    st.html("""
<div style="border-bottom:1px solid var(--border);padding-bottom:20px;margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:4px;
              text-transform:uppercase;color:var(--muted);margin-bottom:6px;">Vice Vault</div>
  <div class="glitch-wrap" data-text="CONFESSIONS"
       style="font-family:'Bebas Neue',sans-serif;font-size:48px;color:var(--text);
              letter-spacing:3px;line-height:0.95;">CONFESSIONS</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--muted);margin-top:6px;">
    Mutual. Blind. Nobody blinks first — because neither of you can.
  </div>
</div>
""")

    uid = _uid()
    if not uid:
        st.error("Log in to use Confessions.")
        return

    _render_screenshot_alerts()

    st.session_state.setdefault("conf_tab", "compose")

    inbox_items  = _db("load_confessions_inbox",  uid, default=[])
    outbox_items = _db("load_confessions_outbox", uid, default=[])

    inbox_action  = sum(1 for i in inbox_items  if i["status"] in ("sent", "questioning"))
    outbox_action = sum(1 for i in outbox_items if i["status"] == "responded")
    revealed_all  = [i for i in inbox_items + outbox_items if i["status"] == "revealed"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("◈  Compose", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "compose" else "secondary", key="tab_compose"):
            st.session_state.conf_tab = "compose"; st.rerun()
    with col2:
        b2 = f" ({inbox_action})" if inbox_action else ""
        if st.button(f"↓  Inbox{b2}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "inbox" else "secondary", key="tab_inbox"):
            st.session_state.conf_tab = "inbox"; st.rerun()
    with col3:
        b3 = f" ({outbox_action})" if outbox_action else ""
        if st.button(f"↑  Sent{b3}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "sent" else "secondary", key="tab_sent"):
            st.session_state.conf_tab = "sent"; st.rerun()
    with col4:
        b4 = f" ({len(revealed_all)})" if revealed_all else ""
        if st.button(f"⚡  Revealed{b4}", use_container_width=True,
                     type="primary" if st.session_state.conf_tab == "revealed" else "secondary", key="tab_revealed"):
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
            st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:24px;letter-spacing:3px;color:var(--muted);">NOTHING REVEALED YET</div></div>')
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
                inject_countdown_banner(item["code"], _revealed_at_iso(item))
                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s)
                    _reaction_stamps(item["code"])
