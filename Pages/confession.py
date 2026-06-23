# database.py
"""
Pages/confession.py — Mutual blind confession exchange + anonymous community board + Friends/Compare.
"""

import streamlit as st
import secrets
import string
import re
import time
from datetime import datetime
from styles import inject_page_css


# ─── VICE META ────────────────────────────────────────────────────────────────

_VICE_META = {
    "weed":    {"label": "Weed",    "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol", "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Sex",     "icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other",   "icon": "💊", "color": "#00e5ff"},
}

BOARD_VICE_META = {
    "weed":    {"label": "Weed",    "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol", "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Sex",     "icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other",   "icon": "💊", "color": "#00e5ff"},
}
BOARD_VICE_NONE = {"label": "General", "icon": "◈", "color": "#9090aa"}

_WINDOW_OPTIONS = {
    "1 minute":   60,
    "5 minutes":  300,
    "30 minutes": 1800,
    "1 hour":     3600,
}

QUESTION_WORDS = {
    "what","why","how","when","where","who","whom","which","whose",
    "would","could","should","do","did","does","have","has","had",
    "are","is","was","were","will","can","may","might","shall",
    "if","tell","describe","explain","name",
}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _revealed_at_iso(item):
    ra = item.get("revealed_at") or item.get("updated_at") or item.get("created_at")
    if ra is None:
        return datetime.now().isoformat()
    return ra.isoformat() if hasattr(ra, "isoformat") else str(ra)


def _db(fn, *args, default=None, **kwargs):
    try:
        import database as db
        return getattr(db, fn)(*args, **kwargs)
    except Exception:
        return default


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


def _time_ago(dt):
    if dt is None:
        return ""
    try:
        if hasattr(dt, "timestamp"):
            diff = int((datetime.now() - dt).total_seconds())
        else:
            diff = int((datetime.now() - datetime.fromisoformat(str(dt))).total_seconds())
        if diff < 3600:   return f"{diff // 60}m ago"
        if diff < 86400:  return f"{diff // 3600}h ago"
        return f"{diff // 86400}d ago"
    except Exception:
        return str(dt)[:10]


def _window_label(secs):
    for label, s in _WINDOW_OPTIONS.items():
        if s == secs:
            return label
    if secs < 60:
        return f"{secs} seconds"
    m = secs // 60
    return f"{m} minute{'s' if m != 1 else ''}"


def _section_label(text):
    st.html(
        f'<div style="font-family:\'Space Mono\',monospace; font-size:9px; letter-spacing:3px;'
        f' text-transform:uppercase; color:var(--muted); margin-bottom:12px;">{text}</div>'
    )


def _validate_questions(questions):
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
            errors.append(f"Question {num} doesn't look like a question.")
            continue
        norm = re.sub(r'[^\w\s]', '', q.lower()).strip()
        if norm in seen:
            errors.append(f"Question {num} is a duplicate of question {seen[norm]}.")
        else:
            seen[norm] = num
    return errors


def _question_fields(prefix, count, sender_name=None):
    ph = f"Ask {sender_name} something real…" if sender_name else "Ask them something you actually want to know…"
    return [
        st.text_area(f"Question {i + 1}", placeholder=ph, key=f"{prefix}_{i}", height=80)
        for i in range(count)
    ]


# ─── COUNTDOWN / PRINTSCREEN ──────────────────────────────────────────────────

def inject_countdown_banner(confession_code, revealed_at_iso, window_seconds=60):
    delete_ms = window_seconds * 1000
    m, s = divmod(window_seconds, 60)
    initial = f"{m}:{s:02d}"
    st.html(f"""
<style>
@keyframes border-pulse   {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
@keyframes border-flicker {{ 0%,100%{{opacity:1}} 25%{{opacity:0.1}} 50%{{opacity:0.8}} 75%{{opacity:0.2}} }}
#vv-screen-glow {{ position:fixed; inset:0; pointer-events:none; z-index:9998;
  border:3px solid var(--magenta); box-shadow:inset 0 0 40px rgba(255,45,120,0.08);
  animation:border-pulse 2s infinite; }}
#vv-screen-glow.amber {{ border-color:var(--amber); animation:border-pulse 1.2s infinite; }}
#vv-screen-glow.lime  {{ border-color:var(--lime);  animation:border-pulse 0.7s infinite; }}
#vv-screen-glow.white {{ border-color:#fff; animation:border-flicker 0.3s infinite; }}
</style>
<script>
(function() {{
  var revAt = new Date({repr(revealed_at_iso)}).getTime();
  var DELETE_MS = {delete_ms};
  if (!document.getElementById("vv-screen-glow")) {{
    var g = document.createElement("div"); g.id = "vv-screen-glow";
    document.body.appendChild(g);
  }}
  if (!document.getElementById("vv-countdown-banner")) {{
    var b = document.createElement("div"); b.id = "vv-countdown-banner";
    b.style.cssText = "position:fixed;bottom:0;left:0;right:0;background:#0a0a0b;border-top:2px solid #ff2d78;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;z-index:9999;font-family:'Space Mono',monospace;";
    b.innerHTML = '<div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#5a5a72;">DELETES IN</div><div id="vv-timer" style="font-size:22px;color:#ff2d78;font-weight:700;letter-spacing:3px;">{initial}</div><div style="font-size:10px;color:#5a5a72;text-transform:uppercase;">PrintScreen = logged out</div>';
    document.body.appendChild(b);
  }}
  var timerEl = document.getElementById("vv-timer");
  var glowEl  = document.getElementById("vv-screen-glow");
  var bannerEl = document.getElementById("vv-countdown-banner");
  document.addEventListener("keyup", function(e) {{
    if (e.key === "PrintScreen" || e.keyCode === 44) {{
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code", {repr(confession_code)});
      window.location.href = url.toString();
    }}
  }});
  var iv = setInterval(function() {{
    var remaining = Math.max(0, Math.ceil((DELETE_MS - (Date.now() - revAt)) / 1000));
    if (timerEl) {{ var m=Math.floor(remaining/60),s=remaining%60; timerEl.textContent=m+":"+(s<10?"0"+s:s); }}
    if (remaining<=3) {{ glowEl.className="white"; timerEl.style.color="#fff"; bannerEl.style.borderTopColor="#fff"; }}
    else if (remaining<=5)  {{ glowEl.className="lime";  timerEl.style.color="#c6ff00"; bannerEl.style.borderTopColor="#c6ff00"; }}
    else if (remaining<=15) {{ glowEl.className="amber"; timerEl.style.color="#ffb300"; bannerEl.style.borderTopColor="#ffb300"; }}
    else {{ glowEl.className=""; timerEl.style.color="#ff2d78"; bannerEl.style.borderTopColor="#ff2d78"; }}
    if (remaining<=0) {{ clearInterval(iv); window.location.reload(); }}
  }}, 500);
}})();
</script>
""")


def inject_printscreen_guard(confession_code):
    st.html(f"""
<script>
(function() {{
  var done = false;
  document.addEventListener("keyup", function(e) {{
    if (!done && (e.key === "PrintScreen" || e.keyCode === 44)) {{
      done = true;
      var url = new URL(window.location.href);
      url.searchParams.set("screenshot_code", {repr(confession_code)});
      window.location.href = url.toString();
    }}
  }});
}})();
</script>
""")


# ─── UI COMPONENTS ────────────────────────────────────────────────────────────

def _status_badge(status, sender, recipient, is_sender):
    cfg = {
        "sent":        {
            True:  ("var(--amber)",   "WAITING",   f"Waiting for {recipient} to send their questions first"),
            False: ("var(--magenta)", "YOUR MOVE", f"Write your questions before you can see {sender}'s"),
        },
        "questioning": {
            True:  ("var(--amber)",  "WAITING",   f"{recipient} sent their questions — waiting for them to answer yours"),
            False: ("var(--cyan)",   "YOUR TURN", f"Your questions are locked in — now answer {sender}'s"),
        },
        "responded": {
            True:  ("var(--cyan)",   "YOUR TURN", f"{recipient} answered — now answer their questions to reveal"),
            False: ("var(--amber)",  "WAITING",   f"Waiting for {sender} to answer your questions"),
        },
        "revealed": {
            True:  ("var(--lime)", "REVEALED", "Exchange unlocked — auto-deletes soon"),
            False: ("var(--lime)", "REVEALED", "Exchange unlocked — auto-deletes soon"),
        },
    }
    color, label, detail = cfg.get(status, {}).get(is_sender, ("var(--muted)", status.upper(), ""))
    st.html(f"""
<div style="display:inline-flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
              text-transform:uppercase;color:{color};border:1px solid {color};
              border-radius:2px;padding:4px 10px;">{label}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--muted);">{detail}</div>
</div>
""")


def _typing_indicator(name):
    st.html(f"""
<div style="display:flex;align-items:center;gap:10px;padding:10px 0 14px 0;">
  <span style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
               text-transform:uppercase;color:var(--muted);">{name} is writing</span>
  <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
</div>
""")


def _exchange_card(label, color, questions, answers, delay_base=0):
    st.html(f'<div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:{color};margin-bottom:8px;">{label}</div>')
    for i, (q, a) in enumerate(zip(questions, answers)):
        delay = delay_base + i * 0.12
        st.html(f"""
<div class="reveal-card" style="animation-delay:{delay}s;background:var(--card);
     border:1px solid var(--border);border-left:2px solid {color};
     border-radius:4px;padding:16px 18px;margin-bottom:10px;">
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


def _reaction_stamps(confession_code):
    EMOJIS = ["😳", "👀", "💀", "🫣"]
    st.html('<div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px;">React</div>')
    cols = st.columns(len(EMOJIS))
    existing = _db("load_reactions", confession_code, _uid(), default=[])
    reacted = {r.get("emoji") for r in (existing or [])}
    for i, emoji in enumerate(EMOJIS):
        count = _db("count_reactions", confession_code, emoji, default=0) or 0
        with cols[i]:
            label = f"{emoji}  {count}" if count else emoji
            if st.button(label, key=f"react_{confession_code}_{emoji}"):
                if emoji not in reacted:
                    _db("save_reaction", confession_code, _uid(), emoji)
                    st.rerun()


# ─── SCREENSHOT HANDLING ──────────────────────────────────────────────────────

def _render_screenshot_alerts():
    alerts = _db("load_screenshot_alerts", _uid(), default=[])
    for alert in alerts:
        screenshotter = alert.get("screenshotter_username", "Someone")
        ts = str(alert.get("created_at", ""))[:16]
        alert_id = alert.get("id")
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


def _handle_query_params():
    params = st.query_params
    delete_code = params.get("delete_code")
    if delete_code:
        _db("delete_confession", delete_code)
        st.query_params.clear()
        st.rerun()
    ss_code = params.get("screenshot_code")
    if ss_code:
        uid = _uid()
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
        st.error(f"⚠️ Screenshot detected. You've been logged out. {other or 'The other person'} has been notified.")
        time.sleep(2)
        _force_logout()


# ─── EMAIL INVITE ─────────────────────────────────────────────────────────────

def _send_invite_email(sender_username, recipient_email, confession_code):
    base_url = st.secrets.get("APP_URL", "https://yourvicevault.app")
    link = f"{base_url}/?invite={confession_code}"
    try:
        import email_service
        return email_service.send_transactional_email(
            to=recipient_email,
            subject=f"{sender_username} sent you a confession on Vice Vault",
            html=f'<p>{sender_username} wants to exchange confessions. <a href="{link}">Accept here</a></p>',
        )
    except Exception:
        return False


def _show_invite_link(confession_code):
    base_url = st.secrets.get("APP_URL", "https://yourvicevault.app")
    link = f"{base_url}/?invite={confession_code}"
    st.html(f"""
<div style="background:#0f1a10;border:1px solid var(--lime);border-radius:4px;padding:16px 18px;margin-top:12px;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
              text-transform:uppercase;color:var(--lime);margin-bottom:8px;">📋  Share this link instead</div>
  <div style="font-family:'Space Mono',monospace;font-size:11px;color:var(--text);word-break:break-all;margin-bottom:10px;">{link}</div>
</div>
""")
    st.code(link)


# ─── COMPOSE ──────────────────────────────────────────────────────────────────

def _render_compose():
    inject_page_css()
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
  </div>
</div>
""")

    invite_mode = st.toggle("Recipient isn't on ViceVault? Invite by email",
                             key=f"conf_invite_toggle_{gen}", value=st.session_state.conf_invite_mode)
    st.session_state.conf_invite_mode = invite_mode

    if invite_mode:
        recipient_email = st.text_input("Recipient email", placeholder="their@email.com", key=f"conf_email_{gen}")
        recipient_username = None
    else:
        _prefill = st.session_state.pop("conf_prefill", "") or ""
        recipient_username = st.text_input("Send to (username)", value=_prefill,
                                            placeholder="Their ViceVault username", key=f"conf_recipient_{gen}")
        recipient_email = None

    window_label = st.selectbox("Auto-delete after reveal", list(_WINDOW_OPTIONS.keys()),
                                 index=0, key=f"conf_window_{gen}")
    window_seconds = _WINDOW_OPTIONS[window_label]
    n = int(st.number_input("Number of questions", min_value=1, max_value=10, value=3, step=1, key=f"conf_n_{gen}"))
    st.html("<div style='height:8px'></div>")
    _section_label(f"Your {n} question{'s' if n != 1 else ''}")
    questions = _question_fields(f"conf_q_{gen}", n)
    st.html("<div style='height:12px'></div>")

    btn_label = "Send Invite →" if invite_mode else "Send Confession →"
    if st.button(btn_label, type="primary", use_container_width=True, key=f"conf_send_{gen}"):
        uid = _uid()
        if not uid:
            st.error("Not logged in.")
            return
        errs = _validate_questions(questions)
        if errs:
            for e in errs:
                st.error(e)
            return
        code = _gen_code()
        if invite_mode:
            email = (recipient_email or "").strip()
            if not email or "@" not in email:
                st.error("Enter a valid email address.")
                return
            result = _db("save_confession_invite", uid, email, code, questions, window_seconds)
            if result:
                sent = _send_invite_email(_username(), email, code)
                if sent:
                    st.session_state.conf_form_gen += 1
                    st.session_state.conf_sent_to = email
                    st.rerun()
                else:
                    st.warning("Confession saved but email couldn't be sent. Share the link below:")
                    _show_invite_link(code)
            else:
                st.error("Something went wrong saving the confession.")
        else:
            rname = (recipient_username or "").strip()
            if not rname:
                st.error("Enter a recipient username.")
                return
            if rname.lower() == _username().lower():
                st.error("You can't send a confession to yourself.")
                return
            recipient = _db("get_user_by_username", rname)
            if not recipient:
                st.error(f"No user found: '{rname}'.")
                return
            if _db("save_confession", uid, recipient["id"], code, questions, window_seconds):
                st.session_state.conf_form_gen += 1
                st.session_state.conf_sent_to = rname
                st.rerun()
            else:
                st.error("Something went wrong.")


# ─── INBOX ────────────────────────────────────────────────────────────────────

def _render_inbox():
    inject_page_css()
    _section_label("Inbox — Confessions sent to you")
    items = _db("load_confessions_inbox", _uid(), default=[])
    if not items:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:28px;letter-spacing:3px;color:var(--muted);">NOTHING YET</div></div>')
        return
    for item in items:
        _render_inbox_item(item)


def _render_inbox_item(item):
    code = item["code"]
    sender_name = item.get("sender_username", "Someone")
    status = item["status"]
    num_q = len(item.get("sender_questions", []))
    ts = str(item.get("created_at", ""))[:16]
    window_secs = item.get("reveal_window_secs", 60)
    inject_printscreen_guard(code)
    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid var(--magenta);
            border-radius:4px;padding:18px 20px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;color:var(--text);">From {sender_name}</div>
    <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--soft);">
    {num_q} question{'s' if num_q != 1 else ''} — hidden until you write yours
  </div>
</div>
""")
    _status_badge(status, sender_name, _username(), is_sender=False)

    if status == "sent":
        with st.expander(f"Your move — write your {num_q} question{'s' if num_q != 1 else ''} for {sender_name}", expanded=True):
            rqs = _question_fields(f"inbox_rq_{code}", num_q, sender_name=sender_name)
            if st.button(f"Lock in — now see {sender_name}'s questions →", key=f"inbox_step1_{code}", type="primary", use_container_width=True):
                errs = _validate_questions(rqs)
                if errs:
                    for e in errs: st.error(e)
                elif _db("confession_recipient_submit_questions", code, rqs):
                    st.success("Locked in."); st.rerun()
                else:
                    st.error("Something went wrong.")

    elif status == "questioning":
        sender_questions = item.get("sender_questions", [])
        with st.expander(f"They showed their hand — answer {sender_name}'s questions", expanded=True):
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

    elif status == "revealed":
        inject_countdown_banner(code, _revealed_at_iso(item), window_secs)
        _render_revealed(item, is_sender=False)
        _reaction_stamps(code)

    st.html("<div style='height:12px'></div>")


# ─── OUTBOX ───────────────────────────────────────────────────────────────────

def _render_outbox():
    inject_page_css()
    _section_label("Sent — Confessions you started")
    items = _db("load_confessions_outbox", _uid(), default=[])
    if not items:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:28px;letter-spacing:3px;color:var(--muted);">NOTHING SENT YET</div></div>')
        return
    for item in items:
        _render_outbox_item(item)


def _render_outbox_item(item):
    code = item["code"]
    recipient_name = item.get("recipient_username") or item.get("recipient_email", "them")
    status = item["status"]
    num_q = len(item.get("sender_questions", []))
    ts = str(item.get("created_at", ""))[:16]
    window_secs = item.get("reveal_window_secs", 60)
    inject_printscreen_guard(code)
    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid var(--lime);
            border-radius:4px;padding:18px 20px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;color:var(--text);">To {recipient_name}</div>
    <div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);">{ts}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:var(--soft);">
    {num_q} question{'s' if num_q != 1 else ''} sent
  </div>
</div>
""")
    _status_badge(status, _username(), recipient_name, is_sender=True)

    if status in ("sent", "questioning"):
        _typing_indicator(recipient_name)

    elif status == "responded":
        recipient_questions = item.get("recipient_questions", [])
        with st.expander(f"They answered. Seal the deal — answer {recipient_name}'s questions", expanded=True):
            st.html(f'<div style="padding:14px 16px;background:var(--surface);border-radius:4px;margin-bottom:16px;font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);line-height:1.7;">{recipient_name} answered. The moment you submit, both sides reveal simultaneously. <strong style="color:var(--magenta);">Auto-deletes {_window_label(window_secs)} after reveal.</strong></div>')
            sender_answers = []
            for i, q in enumerate(recipient_questions):
                st.html(f'<div style="font-family:\'DM Sans\',sans-serif;font-size:14px;color:var(--text);padding:10px 14px;background:var(--surface);border-left:2px solid var(--lime);border-radius:0 3px 3px 0;margin-bottom:6px;line-height:1.6;">{q}</div>')
                sender_answers.append(st.text_area("Your answer", placeholder="Be honest…", key=f"outbox_ans_{code}_{i}", height=80, label_visibility="collapsed"))
            if st.button("Submit — reveal everything →", key=f"outbox_submit_{code}", type="primary", use_container_width=True):
                blank = [i+1 for i, a in enumerate(sender_answers) if not a.strip()]
                if blank:
                    st.error(f"Answer{'s' if len(blank)>1 else ''} {', '.join(map(str,blank))} {'are' if len(blank)>1 else 'is'} empty.")
                elif _db("confession_sender_answer", code, sender_answers):
                    st.success(f"Revealed. Auto-deletes in {_window_label(window_secs)}."); st.rerun()
                else:
                    st.error("Something went wrong.")

    elif status == "revealed":
        inject_countdown_banner(code, _revealed_at_iso(item), window_secs)
        _render_revealed(item, is_sender=True)
        _reaction_stamps(code)

    st.html("<div style='height:12px'></div>")


# ─── REVEALED VIEW ────────────────────────────────────────────────────────────

def _render_revealed(item, is_sender):
    sender_name = item.get("sender_username", "Sender")
    recipient_name = item.get("recipient_username") or item.get("recipient_email", "Recipient")
    window_secs = item.get("reveal_window_secs", 60)
    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-top:2px solid var(--lime);
            border-radius:4px;padding:16px 20px;margin-bottom:16px;text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--lime);letter-spacing:2px;margin-bottom:4px;">EXCHANGE REVEALED</div>
  <div style="font-family:'Space Mono',monospace;font-size:10px;color:var(--magenta);">⏱  Auto-deletes in {_window_label(window_secs)}</div>
</div>
""")
    sq = item.get("sender_questions", [])
    ra = item.get("recipient_answers", [])
    rq = item.get("recipient_questions", [])
    sa = item.get("sender_answers", [])
    if is_sender:
        _exchange_card(f"Your questions → {recipient_name}'s answers", "#c6ff00", sq, ra, delay_base=0)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"{recipient_name}'s questions → Your answers", "#ff2d78", rq, sa, delay_base=len(sq)*0.12)
    else:
        _exchange_card(f"{sender_name}'s questions → Your answers", "#ff2d78", sq, ra, delay_base=0)
        st.html("<div style='height:12px'></div>")
        _exchange_card(f"Your questions → {sender_name}'s answers", "#c6ff00", rq, sa, delay_base=len(sq)*0.12)


# ─── COMMUNITY BOARD ──────────────────────────────────────────────────────────

def _render_board_post_form():
    inject_page_css()
    st.session_state.setdefault("pcb_gen", 0)
    gen = st.session_state.pcb_gen
    vice_choice = st.selectbox("Tag it (optional)", ["None", "Weed 🌿", "Alcohol 🥃", "Sex 🔥", "Other 💊"], key=f"pcb_vice_{gen}", index=0)
    vice_map = {"None": None, "Weed 🌿": "weed", "Alcohol 🥃": "alcohol", "Sex 🔥": "sex", "Other 💊": "other"}
    vice_key = vice_map[vice_choice]
    content = st.text_area("Your confession", placeholder="Say it. Nobody knows it's you.", key=f"pcb_content_{gen}", height=120, max_chars=1000)
    if st.button("Post anonymously →", type="primary", use_container_width=True, key=f"pcb_submit_{gen}"):
        uid = _uid()
        if not uid:
            st.error("Log in to post.")
            return
        text = (content or "").strip()
        if len(text) < 10:
            st.error("Write at least 10 characters.")
            return
        result = _db("save_public_confession", uid, text, vice_key)
        if result:
            st.session_state.pcb_gen += 1
            st.success("Posted.")
            st.rerun()
        else:
            st.error("Something went wrong — try again.")


def _render_board_card(item):
    cid = item["id"]
    content = item.get("content", "")
    vice = item.get("vice")
    replies = item.get("reply_count", 0)
    meta = BOARD_VICE_META.get(vice, BOARD_VICE_NONE)
    ago = _time_ago(item.get("created_at"))
    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid {meta['color']};
            border-radius:4px;padding:16px 18px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
    <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:1px;text-transform:uppercase;color:{meta['color']};">{meta['icon']} {meta['label']}</div>
    <div style="font-family:'Space Mono',monospace;font-size:8px;color:var(--muted);">{ago}</div>
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:14px;color:var(--text);line-height:1.7;margin-bottom:10px;font-style:italic;">"{content}"</div>
  <div style="font-family:'Space Mono',monospace;font-size:8px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;">Anonymous · {replies} {'reply' if replies==1 else 'replies'}</div>
</div>
""")
    with st.expander(f"{'Read & reply' if replies else 'Be the first to reply'} →", expanded=False):
        thread = _db("load_public_replies", cid, default=[])
        if thread:
            for reply in thread:
                reply_ago = _time_ago(reply.get("created_at"))
                st.html(f'<div style="background:var(--surface);border-left:2px solid var(--border);border-radius:0 3px 3px 0;padding:10px 14px;margin-bottom:8px;"><div style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);line-height:1.6;font-style:italic;">"{reply["content"]}"</div><div style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);margin-top:4px;letter-spacing:1px;text-transform:uppercase;">Anonymous · {reply_ago}</div></div>')
        else:
            st.html('<div style="font-family:\'DM Sans\',sans-serif;font-size:12px;color:var(--muted);padding:8px 0 4px;font-style:italic;">No replies yet. Be the first.</div>')
        uid = _uid()
        if uid:
            reply_text = st.text_area("Reply anonymously", placeholder="Say something…", key=f"pcb_reply_text_{cid}", height=72, label_visibility="collapsed")
            if st.button("Reply →", key=f"pcb_reply_btn_{cid}", use_container_width=True):
                text = (reply_text or "").strip()
                if len(text) < 5:
                    st.error("Write at least 5 characters.")
                elif _db("save_public_reply", cid, uid, text):
                    st.rerun()
                else:
                    st.error("Couldn't post reply.")
        else:
            st.info("Log in to reply.")
    st.html("<div style='height:8px'></div>")


def _render_board():
    inject_page_css()
    _section_label("Community Board — anonymous confessions")
    st.html("""
<div style="background:var(--card);border:1px solid var(--border);border-top:2px solid var(--magenta);
            border-radius:4px;padding:16px 20px;margin-bottom:20px;">
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--soft);line-height:1.85;">
    No usernames. No receipts. Post something you'd never say with your name on it.
  </div>
</div>
""")
    filter_options = {"All": None, "🌿 Weed": "weed", "🥃 Alcohol": "alcohol", "🔥 Sex": "sex", "💊 Other": "other"}
    st.session_state.setdefault("pcb_filter", None)
    fcols = st.columns(len(filter_options))
    for i, (label, val) in enumerate(filter_options.items()):
        with fcols[i]:
            active = st.session_state.pcb_filter == val
            if st.button(label, key=f"pcb_f_{i}", use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.pcb_filter = val
                st.rerun()
    st.html("<div style='height:1rem'></div>")
    with st.expander("◈  Post something", expanded=False):
        _render_board_post_form()
    st.html("<div style='height:1px;background:var(--border);margin:16px 0;'></div>")
    posts = _db("load_public_confessions", 30, 0, st.session_state.pcb_filter, default=[])
    if not posts:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:60px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:28px;letter-spacing:3px;color:var(--muted);margin-bottom:8px;">NOTHING YET</div><div style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--muted);">Be the first. Post something above.</div></div>')
        return
    for item in posts:
        _render_board_card(item)


# ─── FRIENDS / COMPARE ────────────────────────────────────────────────────────

def _vice_bar(vice, count, total):
    meta = _VICE_META.get(vice, {"label": vice.title(), "icon": "◈", "color": "var(--muted)"})
    pct = round(count / total * 100) if total else 0
    return f"""
<div style="margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <span style="font-family:'Space Mono',monospace;font-size:8px;letter-spacing:1px;text-transform:uppercase;color:{meta['color']};">{meta['icon']} {meta['label']}</span>
    <span style="font-family:'Bebas Neue',sans-serif;font-size:16px;color:{meta['color']};">{count}</span>
  </div>
  <div style="height:3px;background:var(--border);border-radius:2px;">
    <div style="width:{pct}%;height:100%;background:{meta['color']};border-radius:2px;"></div>
  </div>
</div>"""


def _days_clean_display(vice, last_per_vice):
    last_str = last_per_vice.get(vice)
    if not last_str:
        return "—"
    try:
        last = datetime.fromisoformat(str(last_str))
        days = (datetime.now() - last).days
        return "today" if days == 0 else f"{days}d"
    except Exception:
        return "—"


def _render_compare_panel(stats, label, is_me):
    col_accent = "var(--lime)" if is_me else "var(--cyan)"
    username = stats.get("username", label)
    initials = username[:2].upper()
    freak = stats.get("freak_score")
    freak_str = f"{freak}/100" if freak is not None else "—"
    total = stats.get("total_sessions", 0)
    vice_counts = stats.get("vice_counts", {})
    rbtl = stats.get("rbtl_name") or "—"
    rbtl_open = stats.get("rbtl_openness")
    last_per = stats.get("last_per_vice", {})
    bars_html = "".join(_vice_bar(v, vice_counts.get(v, 0), total) for v in ["weed", "alcohol", "sex", "other"]) if total else '<div style="font-family:\'DM Sans\',sans-serif;font-size:12px;color:var(--muted);font-style:italic;padding:8px 0;">No sessions logged (30d)</div>'
    clean_items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);">'
        f'<span style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;">{_VICE_META.get(v,{}).get("icon","◈")} {_VICE_META.get(v,{}).get("label",v)}</span>'
        f'<span style="font-family:\'Bebas Neue\',sans-serif;font-size:16px;color:{col_accent};">{_days_clean_display(v,last_per)}</span></div>'
        for v in ["weed", "alcohol", "sex", "other"]
    )
    st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-top:3px solid {col_accent};border-radius:4px;padding:20px;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
    <div style="width:40px;height:40px;border-radius:50%;background:{col_accent};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span style="font-family:'Bebas Neue',sans-serif;font-size:16px;color:#0a0a0b;">{initials}</span>
    </div>
    <div>
      <div style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--text);letter-spacing:1px;line-height:1;">{username}</div>
      <div style="font-family:'Space Mono',monospace;font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:2px;">{"You" if is_me else "Friend"}</div>
    </div>
  </div>
  <div style="font-family:'Space Mono',monospace;font-size:8px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px;">Sessions (30d)</div>
  {bars_html}
  <div style="margin-top:16px;margin-bottom:4px;font-family:'Space Mono',monospace;font-size:8px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);">Days Since Last</div>
  {clean_items}
  <div style="display:flex;gap:12px;margin-top:16px;padding-top:14px;border-top:1px solid var(--border);">
    <div style="flex:1;text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:32px;color:{col_accent};line-height:1;">{freak_str}</div>
      <div style="font-family:'Space Mono',monospace;font-size:7px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:2px;">Freak Score</div>
    </div>
    <div style="flex:1;text-align:center;">
      <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:{col_accent};line-height:1.3;font-style:italic;margin-top:4px;">{rbtl}</div>
      <div style="font-family:'Space Mono',monospace;font-size:7px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">RBTL Result</div>
      {f'<div style="font-family:Bebas Neue,sans-serif;font-size:18px;color:{col_accent};">{rbtl_open}%</div>' if rbtl_open else ''}
    </div>
  </div>
</div>
""")


def _render_friends():
    inject_page_css()
    uid = _uid()
    if not uid:
        st.error("Log in to use Friends.")
        return

    import database as _db_mod

    st.session_state.setdefault("friend_compare_id",    None)
    st.session_state.setdefault("friend_compare_stats", None)
    st.session_state.setdefault("friend_add_gen",       0)

    # ── Compare view ──────────────────────────────────────────────────────────
    if st.session_state.friend_compare_id and st.session_state.friend_compare_stats:
        friend_stats = st.session_state.friend_compare_stats
        try:
            my_stats = _db_mod.get_user_public_stats(uid) or {}
        except Exception:
            my_stats = {}

        st.html('<div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-bottom:16px;">Vault Compare</div>')
        col_me, col_them = st.columns(2)
        with col_me:
            _render_compare_panel(my_stats or {"username": _username()}, "You", is_me=True)
        with col_them:
            _render_compare_panel(friend_stats, friend_stats.get("username", "Friend"), is_me=False)

        st.html("<div style='height:16px'></div>")
        my_freak    = (my_stats or {}).get("freak_score") or 0
        their_freak = friend_stats.get("freak_score") or 0
        my_total    = (my_stats or {}).get("total_sessions", 0)
        their_total = friend_stats.get("total_sessions", 0)
        insights = []
        if my_freak and their_freak:
            diff = abs(my_freak - their_freak)
            if diff <= 8:
                insights.append(("◆ Aligned", f"Your freak scores are within {diff} points of each other.", "var(--lime)"))
            elif my_freak > their_freak:
                insights.append(("▲ You lead", f"Your freak score is {diff} points higher.", "var(--amber)"))
            else:
                insights.append(("▲ They lead", f"Their freak score is {diff} points higher.", "var(--cyan)"))
        if my_total and their_total:
            if my_total > their_total * 1.5:
                insights.append(("◎ More active", f"You've logged {my_total - their_total} more sessions this month.", "var(--lime)"))
            elif their_total > my_total * 1.5:
                insights.append(("◎ More active", f"They've logged {their_total - my_total} more sessions this month.", "var(--cyan)"))
        for icon_label, detail, color in insights:
            st.html(f'<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid {color};border-radius:4px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px;"><div style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:{color};flex-shrink:0;">{icon_label}</div><div style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--soft);">{detail}</div></div>')

        if st.button("← Back to Friends", use_container_width=True, key="compare_back"):
            st.session_state.friend_compare_id    = None
            st.session_state.friend_compare_stats = None
            st.rerun()
        return

    # ── Pending requests ──────────────────────────────────────────────────────
    try:
        requests = _db_mod.load_friend_requests(uid) or []
    except Exception as e:
        st.warning(f"Could not load friend requests: {e}")
        requests = []

    if requests:
        _section_label(f"Friend Requests — {len(requests)}")
        for req in requests:
            sender = req.get("sender_username", "Someone")
            req_id = req.get("id")
            ago    = _time_ago(req.get("created_at"))
            st.html(f'<div style="background:var(--card);border:1px solid var(--border);border-left:3px solid var(--amber);border-radius:4px;padding:14px 18px;margin-bottom:4px;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:18px;color:var(--text);">{sender}</div><div style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);">{ago}</div></div>')
            col_acc, col_dec, _ = st.columns([2, 2, 3])
            with col_acc:
                if st.button("Accept →", key=f"fr_acc_{req_id}", type="primary", use_container_width=True):
                    try:
                        _db_mod.respond_friend_request(req_id, uid, True)
                    except Exception as e:
                        st.error(f"Error: {e}")
                    st.rerun()
            with col_dec:
                if st.button("Decline", key=f"fr_dec_{req_id}", use_container_width=True):
                    try:
                        _db_mod.respond_friend_request(req_id, uid, False)
                    except Exception as e:
                        st.error(f"Error: {e}")
                    st.rerun()
            st.html("<div style='height:6px'></div>")
        st.html("<div style='height:1px;background:var(--border);margin:16px 0;'></div>")

    # ── Friends list ──────────────────────────────────────────────────────────
    try:
        friends = _db_mod.load_friends(uid) or []
    except Exception as e:
        st.warning(f"Could not load friends: {e}")
        friends = []

    _section_label(f"Friends — {len(friends)}")

    if friends:
        for f in friends:
            fname    = f.get("username", "?")
            freak    = f.get("freak_score")
            top_vice = f.get("top_vice")
            sessions = f.get("session_count", 0)
            rbtl     = f.get("rbtl_name") or "—"
            fid      = f.get("user_id")
            top_meta = _VICE_META.get(top_vice, {}) if top_vice else {}
            initials = fname[:2].upper()
            st.html(f"""
<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:16px 18px;margin-bottom:4px;">
  <div style="display:flex;align-items:center;gap:14px;">
    <div style="width:40px;height:40px;border-radius:50%;background:var(--border);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <span style="font-family:'Bebas Neue',sans-serif;font-size:16px;color:var(--soft);">{initials}</span>
    </div>
    <div style="flex:1;min-width:0;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:20px;color:var(--text);letter-spacing:1px;line-height:1;">{fname}</div>
      <div style="font-family:'Space Mono',monospace;font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-top:3px;">{f"{top_meta.get('icon','')} {top_meta.get('label','')} most · " if top_vice else ""}{sessions} sessions · {rbtl}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-family:'Bebas Neue',sans-serif;font-size:28px;color:var(--lime);">{f"{freak}" if freak is not None else "—"}</div>
      <div style="font-family:'Space Mono',monospace;font-size:7px;color:var(--muted);text-transform:uppercase;">freak</div>
    </div>
  </div>
</div>
""")
            col_cmp, col_conf, col_rm, _ = st.columns([2, 2, 1, 2])
            with col_cmp:
                if st.button("Compare →", key=f"cmp_{fid}", use_container_width=True, type="primary"):
                    try:
                        stats = _db_mod.get_user_public_stats(fid) or {}
                    except Exception:
                        stats = {}
                    st.session_state.friend_compare_id    = fid
                    st.session_state.friend_compare_stats = stats
                    st.rerun()
            with col_conf:
                if st.button("↑ Confess", key=f"conf_friend_{fid}", use_container_width=True):
                    st.session_state.conf_tab     = "compose"
                    st.session_state.conf_prefill = fname
                    st.rerun()
            with col_rm:
                if st.button("✕", key=f"rm_friend_{fid}", help="Remove friend"):
                    try:
                        _db_mod.remove_friend(uid, fid)
                    except Exception as e:
                        st.error(f"Error: {e}")
                    st.rerun()
            st.html("<div style='height:8px'></div>")
    else:
        st.html('<div style="background:var(--card);border:1px solid var(--border);border-radius:4px;padding:48px;text-align:center;"><div style="font-family:\'Bebas Neue\',sans-serif;font-size:24px;letter-spacing:3px;color:var(--muted);margin-bottom:8px;">NO FRIENDS YET</div><div style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--muted);">Add someone below — they\'ll see your vault stats once both sides accept.</div></div>')

    # ── Add friend ────────────────────────────────────────────────────────────
    st.html("<div style='height:1px;background:var(--border);margin:20px 0;'></div>")
    _section_label("Add a Friend")
    gen = st.session_state.friend_add_gen
    uname_input = st.text_input("Username", placeholder="Their ViceVault username", key=f"friend_add_input_{gen}")
    if st.button("Send Friend Request →", type="primary", use_container_width=True, key=f"friend_add_btn_{gen}"):
        uname = (uname_input or "").strip()
        if not uname:
            st.error("Enter a username.")
        elif uname.lower() == _username().lower():
            st.error("You can't add yourself.")
        else:
            try:
                target = _db_mod.get_user_by_username(uname)
            except Exception as e:
                st.error(f"Could not look up user: {e}")
                target = None

            if target is None:
                st.error(f"No user found: '{uname}'")
            else:
                try:
                    result = _db_mod.send_friend_request(uid, target["id"])
                except Exception as e:
                    st.error(f"Friend request failed: {e}")
                    result = "error"

                if result == "sent":
                    st.success(f"Request sent to {uname}!")
                    st.session_state.friend_add_gen += 1
                    st.rerun()
                elif result == "already_friends":
                    st.info(f"You and {uname} are already friends.")
                elif result == "already_sent":
                    st.info("Request already pending — they haven't accepted yet.")
                elif result == "error":
                    st.error("Friend request failed — see error above.")
                else:
                    st.error(f"Unexpected result: {result}")

    st.html('<div style="background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:12px 16px;margin-top:12px;"><div style="font-family:\'DM Sans\',sans-serif;font-size:12px;color:var(--muted);line-height:1.7;">Friends can see your freak score, vice breakdown (last 30 days), and RBTL result. Individual session details are never shared.</div></div>')


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def confessions_page():
    inject_page_css()

    st.html("""
<style>
@keyframes glitch-clip {
  0%   { clip-path:inset(0 0 95% 0); transform:translate(-3px,0); }
  10%  { clip-path:inset(30% 0 55% 0); transform:translate(3px,0); }
  20%  { clip-path:inset(60% 0 15% 0); transform:translate(-2px,0); }
  30%  { clip-path:inset(80% 0 5% 0);  transform:translate(2px,0); }
  40%  { clip-path:inset(10% 0 80% 0); transform:translate(-3px,0); }
  50%,100% { clip-path:inset(0 0 0 0); transform:translate(0,0); opacity:0; }
}
.glitch-wrap { position:relative; display:inline-block; }
.glitch-wrap::before, .glitch-wrap::after {
  content:attr(data-text); position:absolute; top:0; left:0;
  font-family:'Bebas Neue',sans-serif; font-size:48px; letter-spacing:3px; line-height:0.95; pointer-events:none;
}
.glitch-wrap::before { color:var(--cyan);    animation:glitch-clip 4s infinite linear; animation-delay:0.5s; }
.glitch-wrap::after  { color:var(--magenta); animation:glitch-clip 4s infinite linear; animation-delay:1.2s; }
@keyframes card-enter { from{opacity:0;transform:translateY(18px) scale(0.97)} to{opacity:1;transform:translateY(0) scale(1)} }
.reveal-card { animation:card-enter 0.45s cubic-bezier(0.19,1,0.22,1) both; }
@keyframes typing-pulse { 0%,80%,100%{opacity:0.2;transform:scale(0.8)} 40%{opacity:1;transform:scale(1)} }
.typing-dot { display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--magenta);animation:typing-pulse 1.4s infinite ease-in-out; }
.typing-dot:nth-child(2){animation-delay:0.2s}
.typing-dot:nth-child(3){animation-delay:0.4s}
</style>
""")

    try:
        import database as db
        db.delete_expired_confessions()
    except Exception:
        pass

    _handle_query_params()

    st.html("""
<div style="border-bottom:1px solid var(--border);padding-bottom:20px;margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:4px;text-transform:uppercase;color:var(--muted);margin-bottom:6px;">Vice Vault · Social</div>
  <div class="glitch-wrap" data-text="CONFESSIONS" style="font-family:'Bebas Neue',sans-serif;font-size:48px;color:var(--text);letter-spacing:3px;line-height:0.95;">CONFESSIONS</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:var(--muted);margin-top:6px;">Mutual. Blind. Nobody blinks first — because neither of you can.</div>
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

    try:
        import database as _db_mod
        pending_reqs = _db_mod.load_friend_requests(uid) or []
    except Exception:
        pending_reqs = []

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        if st.button("◈  Compose", use_container_width=True, key="tab_compose", type="primary" if st.session_state.conf_tab=="compose" else "secondary"):
            st.session_state.conf_tab = "compose"; st.rerun()
    with col2:
        b2 = f" ({inbox_action})" if inbox_action else ""
        if st.button(f"↓  Inbox{b2}", use_container_width=True, key="tab_inbox", type="primary" if st.session_state.conf_tab=="inbox" else "secondary"):
            st.session_state.conf_tab = "inbox"; st.rerun()
    with col3:
        b3 = f" ({outbox_action})" if outbox_action else ""
        if st.button(f"↑  Sent{b3}", use_container_width=True, key="tab_sent", type="primary" if st.session_state.conf_tab=="sent" else "secondary"):
            st.session_state.conf_tab = "sent"; st.rerun()
    with col4:
        b4 = f" ({len(revealed_all)})" if revealed_all else ""
        if st.button(f"⚡  Revealed{b4}", use_container_width=True, key="tab_revealed", type="primary" if st.session_state.conf_tab=="revealed" else "secondary"):
            st.session_state.conf_tab = "revealed"; st.rerun()
    with col5:
        if st.button("◉  Board", use_container_width=True, key="tab_board", type="primary" if st.session_state.conf_tab=="board" else "secondary"):
            st.session_state.conf_tab = "board"; st.rerun()
    with col6:
        b6 = f" ({len(pending_reqs)})" if pending_reqs else ""
        if st.button(f"👥  Friends{b6}", use_container_width=True, key="tab_friends", type="primary" if st.session_state.conf_tab=="friends" else "secondary"):
            st.session_state.conf_tab = "friends"; st.rerun()

    st.html("<div style='height:1.5rem'></div>")

    tab = st.session_state.conf_tab
    if tab == "compose":
        _render_compose()
    elif tab == "inbox":
        _render_inbox()
    elif tab == "sent":
        _render_outbox()
    elif tab == "board":
        _render_board()
    elif tab == "friends":
        _render_friends()
    elif tab == "revealed":
        inject_page_css()
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
                other = (item.get("recipient_username") or item.get("recipient_email")) if is_s else item.get("sender_username")
                ts    = str(item.get("created_at", ""))[:16]
                inject_countdown_banner(item["code"], _revealed_at_iso(item), item.get("reveal_window_secs", 60))
                with st.expander(f"Exchange with {other} · {ts}", expanded=False):
                    _render_revealed(item, is_sender=is_s)
                    _reaction_stamps(item["code"])
