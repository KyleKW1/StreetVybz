"""
Pages/dashboard.py
Vice tracker — stats, log, history, goals, and streak pages.
DB-backed. AI weekly reflection via Anthropic. Anonymous social feed.
"""

import streamlit as st
import time
from datetime import datetime, timedelta, date
from collections import defaultdict
from styles import inject_page_css

# ─── VICE DEFINITIONS ─────────────────────────────────────────────────────────

VICES = {
    "weed": {
        "label": "Weed / Smoking", "icon": "🌿", "color": "#c6ff00", "unit": "sessions",
        "fields": [
            {"key": "method",    "label": "Method",             "type": "select",
             "options": ["Joint", "Blunt", "Bong", "Vape", "Edible", "Other"]},
            {"key": "amount",    "label": "Amount (g / units)", "type": "number", "min": 0.1, "step": 0.1},
            {"key": "intensity", "label": "Intensity (1–10)",   "type": "slider", "min": 1, "max": 10},
            {"key": "solo",      "label": "Alone or with others?", "type": "select",
             "options": ["Solo", "With 1 person", "Group (3+)"]},
            {"key": "notes",     "label": "Notes",              "type": "text"},
        ],
    },
    "alcohol": {
        "label": "Alcohol", "icon": "🥃", "color": "#ffb300", "unit": "standard drinks",
        "fields": [
            {"key": "drink_type", "label": "Type", "type": "select",
             "options": ["Beer", "Wine", "Spirits", "Cocktails", "Shots", "Mixed"]},
            {"key": "drinks",     "label": "No. of standard drinks", "type": "number", "min": 1, "step": 1},
            {"key": "over_hours", "label": "Over how many hours?",   "type": "number", "min": 0.5, "step": 0.5},
            {"key": "setting",    "label": "Setting", "type": "select",
             "options": ["Home alone", "Home with others", "Bar / Club", "Party", "Restaurant", "Other"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ],
    },
    "sex": {
        "label": "Unprotected Sex", "icon": "🔥", "color": "#ff2d78", "unit": "encounters",
        "fields": [
            {"key": "partner_type",  "label": "Partner", "type": "select",
             "options": ["Long-term partner", "Casual / Known", "New / Unknown", "Prefer not to say"]},
            {"key": "contraception", "label": "Any contraception used?", "type": "select",
             "options": ["None", "Pill / Hormonal", "IUD", "Pull-out", "Other"]},
            {"key": "sti_status",    "label": "STI status known?", "type": "select",
             "options": ["Both tested", "One tested", "Neither tested", "Unknown"]},
            {"key": "regret", "label": "Regret level (1 = none, 10 = major)", "type": "slider", "min": 1, "max": 10},
            {"key": "notes", "label": "Notes (private)", "type": "text"},
        ],
    },
    "other": {
        "label": "Other Substances", "icon": "💊", "color": "#00e5ff", "unit": "uses",
        "fields": [
            {"key": "substance", "label": "Substance",     "type": "text"},
            {"key": "amount",    "label": "Amount / Dose", "type": "text"},
            {"key": "intensity", "label": "Intensity (1–10)", "type": "slider", "min": 1, "max": 10},
            {"key": "setting",   "label": "Setting", "type": "select",
             "options": ["Solo", "Social", "Party", "Other"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ],
    },
}

# ─── STORAGE HELPERS ──────────────────────────────────────────────────────────

def _current_user_id() -> int | None:
    user = st.session_state.get("user")
    return user.get("id") if user else None


def get_log():
    if "vice_log" not in st.session_state:
        st.session_state.vice_log = []
    return st.session_state.vice_log


def add_entry(vice_key: str, data: dict, timestamp: datetime):
    log      = get_log()
    local_id = int(time.time() * 1000)
    entry    = {"id": local_id, "vice": vice_key, "timestamp": timestamp.isoformat(), "data": data}
    log.append(entry)
    st.session_state.vice_log = log

    user_id = _current_user_id()
    if user_id:
        try:
            import database as db
            db_id = db.save_vice_entry(user_id, vice_key, timestamp, data)
            if db_id:
                entry["id"] = db_id
        except Exception:
            pass


def entries_for(vice_key: str, days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    return [
        e for e in get_log()
        if e["vice"] == vice_key and datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]


def all_entries(days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    return [e for e in get_log() if datetime.fromisoformat(e["timestamp"]) >= cutoff]


# ─── SHARED COMPONENTS ────────────────────────────────────────────────────────

def page_masthead(title, subtitle=""):
    st.html(f"""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">{title}</div>
  {'<div style="font-family:\'DM Sans\',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">' + subtitle + '</div>' if subtitle else ''}
</div>
""")


def stat_card(label, value, sublabel, color):
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-top:2px solid {color};
            border-radius:4px; padding:18px 20px; margin-bottom:0;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">{label}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:42px; color:{color};
              line-height:1; margin-bottom:4px;">{value}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--soft);">{sublabel}</div>
</div>
""")


# ─── AI WEEKLY REFLECTION ─────────────────────────────────────────────────────

def _generate_reflection(entries: list) -> str:
    try:
        import anthropic
        client  = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        counts  = defaultdict(int)
        details = {}
        for e in entries:
            v = e["vice"]
            counts[v] += 1
            if v not in details:
                details[v] = e.get("data", {})

        lines = []
        for v, c in counts.items():
            meta = VICES.get(v, {})
            lines.append(f"{meta.get('label', v)}: {c} session(s)")

        summary = ", ".join(lines) if lines else "no activity"

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=180,
            messages=[{
                "role": "user",
                "content": (
                    "You're a non-judgmental wellness companion inside a vice-tracking app. "
                    "Write 2-3 sentences reflecting on the past 7 days of logged activity. "
                    "Be warm, honest, and direct — not preachy. One specific observation, one small nudge.\n\n"
                    f"This week: {summary}\n\n"
                    "Keep it under 60 words. Conversational."
                ),
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        return ""


def _render_ai_reflection(entries_7d: list):
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Weekly Reflection
</div>
""")
    cached = st.session_state.get("_reflection_text")
    cached_at = st.session_state.get("_reflection_ts", 0)
    stale = (time.time() - cached_at) > 3600  # Re-generate after 1 hour

    if cached and not stale:
        text = cached
    else:
        text = ""

    if text:
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid var(--lime); border-radius:0 4px 4px 0;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
              line-height:1.8; font-style:italic;">{text}</div>
</div>
""")

    if st.button(
        "⟳  Generate Reflection" if not text else "⟳  Refresh Reflection",
        key="gen_reflection",
        type="secondary",
    ):
        with st.spinner("Reading your week…"):
            result = _generate_reflection(entries_7d)
        if result:
            st.session_state._reflection_text = result
            st.session_state._reflection_ts   = time.time()
            st.rerun()
        else:
            st.warning("Couldn't generate reflection — check your Anthropic API key.")


# ─── ANONYMOUS SOCIAL FEED ────────────────────────────────────────────────────

_VICE_ICONS = {"weed": "🌿", "alcohol": "🥃", "sex": "🔥", "other": "💊"}


def _render_social_feed():
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Live in Kingston
</div>
""")
    try:
        import database as db
        feed = db.load_social_feed(20)
    except Exception:
        feed = []

    if not feed:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:20px; text-align:center; font-family:'Space Mono',monospace;
            font-size:9px; color:var(--muted); letter-spacing:2px; text-transform:uppercase;">
  No community activity yet
</div>
""")
        return

    items_html = ""
    for row in feed[:12]:
        logged_at = row.get("logged_at")
        if hasattr(logged_at, "isoformat"):
            dt = logged_at
        else:
            try:
                dt = datetime.fromisoformat(str(logged_at))
            except Exception:
                dt = datetime.now()

        diff   = datetime.now() - dt
        mins   = int(diff.total_seconds() / 60)
        hrs    = mins // 60
        days   = hrs // 24
        if days >= 1:
            ago = f"{days}d ago"
        elif hrs >= 1:
            ago = f"{hrs}h ago"
        elif mins >= 1:
            ago = f"{mins}m ago"
        else:
            ago = "just now"

        vice  = row.get("vice", "other")
        icon  = _VICE_ICONS.get(vice, "◈")
        label = VICES.get(vice, {}).get("label", vice.title())
        color = VICES.get(vice, {}).get("color", "var(--muted)")

        items_html += f"""
<div style="display:flex; align-items:center; gap:10px; padding:8px 0;
            border-bottom:1px solid var(--border);">
  <div style="font-size:16px; flex-shrink:0;">{icon}</div>
  <div style="flex:1; min-width:0;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:{color};
                letter-spacing:1px; text-transform:uppercase;">Someone logged {label}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">Kingston</div>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
              flex-shrink:0;">{ago}</div>
</div>"""

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:12px 16px;">
  {items_html}
</div>
""")


# ─── STATS PAGE ───────────────────────────────────────────────────────────────

def stats_page():
    inject_page_css()
    page_masthead("DASHBOARD", "No judgement. Just data.")

    log   = all_entries(30)
    total = len(log)

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Last 30 days</div>
""")
    cols = st.columns(4)
    for i, (vk, v) in enumerate(VICES.items()):
        count = len([e for e in log if e["vice"] == vk])
        with cols[i]:
            stat_card(v["label"], count, v["unit"], v["color"])

    st.html("<div style='height:1.5rem'></div>")

    if total == 0:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:40px; text-align:center; color:var(--muted);
            font-family:'Space Mono',monospace; font-size:11px; letter-spacing:2px;">
  NO DATA YET — START LOGGING
</div>
""")
    else:
        # 14-day activity heatmap
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  14-Day Activity
</div>
""")
        days_list  = [(datetime.now() - timedelta(days=i)).date() for i in range(13, -1, -1)]
        day_counts = {}
        for e in all_entries(14):
            d = datetime.fromisoformat(e["timestamp"]).date()
            day_counts[d] = day_counts.get(d, 0) + 1

        max_count  = max(day_counts.values(), default=1)
        cols_heat  = st.columns(14)
        for i, d in enumerate(days_list):
            cnt       = day_counts.get(d, 0)
            intensity = cnt / max_count if max_count else 0
            opacity   = 0.15 + intensity * 0.85
            with cols_heat[i]:
                st.html(f"""
<div style="text-align:center;">
  <div style="width:100%; aspect-ratio:1; background:rgba(198,255,0,{opacity:.2f});
              border:1px solid rgba(198,255,0,0.2); border-radius:2px; margin-bottom:4px;
              display:flex; align-items:center; justify-content:center;
              font-family:'Space Mono',monospace; font-size:10px; color:var(--lime);">
    {cnt if cnt else ''}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">{d.strftime('%d')}</div>
</div>
""")

        st.html("<div style='height:1.5rem'></div>")

        # Breakdown bars
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Breakdown</div>
""")
        for vk, v in VICES.items():
            count = len([e for e in log if e["vice"] == vk])
            pct   = (count / total * 100) if total else 0
            st.html(f"""
<div style="margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--soft);">
      {v['icon']} {v['label']}
    </span>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:{v['color']};">
      {count} &nbsp;·&nbsp; {pct:.0f}%
    </span>
  </div>
  <div style="height:4px; background:var(--border); border-radius:2px;">
    <div style="width:{pct}%; height:100%; background:{v['color']}; border-radius:2px;"></div>
  </div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # AI weekly reflection
    _render_ai_reflection(all_entries(7))

    st.html("<div style='height:1.5rem'></div>")

    # Social feed
    _render_social_feed()


# ─── LOG SESSION PAGE ─────────────────────────────────────────────────────────

def render_log_form(vice_key: str):
    v = VICES[vice_key]
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-left:3px solid {v['color']};
            border-radius:4px; padding:20px 20px 4px; margin-bottom:16px;">
  <span style="font-size:22px;">{v['icon']}</span>
  <span style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:{v['color']};
               letter-spacing:2px; margin-left:8px;">{v['label']}</span>
</div>
""")
    col_date, col_time = st.columns(2)
    with col_date:
        log_date = st.date_input("Date", value=date.today(), max_value=date.today(),
                                 key=f"log_{vice_key}_date")
    with col_time:
        log_time = st.time_input("Time", value=datetime.now().time(), key=f"log_{vice_key}_time")

    st.html("<div style='height:4px'></div>")
    form_data = {}
    for field in v["fields"]:
        key = f"log_{vice_key}_{field['key']}"
        if field["type"] == "select":
            form_data[field["key"]] = st.selectbox(field["label"], field["options"], key=key)
        elif field["type"] == "number":
            form_data[field["key"]] = st.number_input(
                field["label"], min_value=float(field.get("min", 0)),
                step=float(field.get("step", 1)), key=key)
        elif field["type"] == "slider":
            form_data[field["key"]] = st.slider(
                field["label"], min_value=field["min"], max_value=field["max"],
                value=(field["min"] + field["max"]) // 2, key=key)
        elif field["type"] == "text":
            form_data[field["key"]] = st.text_input(field["label"], key=key)

    st.html("<div style='height:8px'></div>")
    if st.button(f"Log {v['label']} →", key=f"submit_{vice_key}", type="primary", use_container_width=True):
        entry_dt = datetime.combine(log_date, log_time)
        add_entry(vice_key, form_data, entry_dt)
        st.success(f"Logged. {v['icon']}")
        st.rerun()


def log_session_page():
    inject_page_css()
    page_masthead("LOG SESSION", "What happened?")
    vice_choice = st.selectbox(
        "Select vice",
        list(VICES.keys()),
        format_func=lambda k: f"{VICES[k]['icon']}  {VICES[k]['label']}",
        key="log_vice_choice",
    )
    st.html("<div style='height:4px'></div>")
    render_log_form(vice_choice)


# ─── HISTORY PAGE ─────────────────────────────────────────────────────────────

def history_page():
    inject_page_css()
    page_masthead("HISTORY", "All logged sessions")
    log = list(reversed(get_log()))

    if not log:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:40px; text-align:center; color:var(--muted);
            font-family:'Space Mono',monospace; font-size:11px; letter-spacing:2px;">
  NOTHING LOGGED YET
</div>
""")
        return

    for e in log[:50]:
        v        = VICES[e["vice"]]
        ts       = datetime.fromisoformat(e["timestamp"])
        time_str = ts.strftime("%b %d, %Y · %H:%M")
        data_str = "  ·  ".join(f"{k}: {val}" for k, val in e["data"].items()
                                 if val and k != "notes")
        notes    = e["data"].get("notes", "")
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {v['color']}; border-radius:4px;
            padding:14px 16px; margin-bottom:8px;">
  <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
    <span style="font-size:16px;">{v['icon']}</span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
                 letter-spacing:1px; text-transform:uppercase;">{time_str}</span>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; color:{v['color']};
              letter-spacing:1px; text-transform:uppercase; margin-bottom:4px;">{v['label']}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">{data_str}</div>
  {f'<div style="font-family:\'DM Sans\',sans-serif; font-size:11px; color:var(--muted); margin-top:4px; font-style:italic;">"{notes}"</div>' if notes else ''}
</div>
""")

    st.html("<div style='height:8px'></div>")
    if st.button("Clear all history", type="secondary"):
        user_id = _current_user_id()
        if user_id:
            try:
                import database as db
                db.delete_vice_log(user_id)
            except Exception:
                pass
        st.session_state.vice_log = []
        st.rerun()


# ─── GOALS PAGE ───────────────────────────────────────────────────────────────

def _this_week_counts() -> dict:
    """Count sessions per vice in the current calendar week."""
    today      = date.today()
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    counts     = defaultdict(int)
    for e in get_log():
        if datetime.fromisoformat(e["timestamp"]) >= week_start:
            counts[e["vice"]] += 1
    return dict(counts)


def _compute_streaks_simple(entries: list) -> dict:
    if not entries:
        return {"current": 0, "longest": 0}
    dates = sorted({datetime.fromisoformat(e["timestamp"]).date() for e in entries})
    today = date.today()

    current  = 0
    expected = today
    for d in reversed(dates):
        if d == expected or d == expected - timedelta(days=1):
            if d != expected:
                expected = d
            current += 1
            expected = expected - timedelta(days=1)
        elif d < expected:
            break

    longest = 1
    run     = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i - 1] + timedelta(days=1):
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    return {"current": current, "longest": longest}


def goals_page():
    inject_page_css()
    page_masthead("GOALS", "Set limits. Track progress.")

    user_id = _current_user_id()
    if not user_id:
        st.warning("Log in to use Goals.")
        return

    # Load saved goals
    try:
        import database as db
        saved_goals = db.get_vice_goals(user_id)
    except Exception:
        saved_goals = {}

    this_week = _this_week_counts()
    streaks   = _compute_streaks_simple(get_log())

    # ── Streak banner ─────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Streaks</div>
""")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--lime); border-radius:4px; padding:18px 20px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Current streak</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:42px; color:var(--lime); line-height:1;">
    {streaks['current']}<span style="font-size:18px; color:var(--muted);"> days</span>
  </div>
</div>
""")
    with sc2:
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--amber); border-radius:4px; padding:18px 20px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Longest streak</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:42px; color:var(--amber); line-height:1;">
    {streaks['longest']}<span style="font-size:18px; color:var(--muted);"> days</span>
  </div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Weekly limits ─────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Weekly Limits</div>
""")

    st.html("""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:4px;
            padding:12px 16px; margin-bottom:20px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); line-height:1.7;">
    Set a weekly session limit per vice. 0 means no limit set.
    Progress resets each Monday.
  </div>
</div>
""")

    updated = {}
    for vk, v in VICES.items():
        current_limit = saved_goals.get(vk, 0)
        used          = this_week.get(vk, 0)
        color         = v["color"]

        pct   = min(100, (used / current_limit * 100)) if current_limit else 0
        over  = current_limit and used > current_limit
        bar_c = "var(--magenta)" if over else color

        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {color}; border-radius:4px; padding:14px 16px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
    <div style="font-family:'Space Mono',monospace; font-size:10px; color:{color};
                letter-spacing:1px; text-transform:uppercase;">{v['icon']} {v['label']}</div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:{bar_c};">
      {used}{' / ' + str(current_limit) if current_limit else ''}
      <span style="font-size:11px; color:var(--muted);">{v['unit']}</span>
    </div>
  </div>
  {f'<div style="height:4px; background:var(--border); border-radius:2px; margin-bottom:8px;"><div style="width:{pct:.0f}%; height:100%; background:{bar_c}; border-radius:2px;"></div></div>' if current_limit else ''}
  {'<div style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--magenta); letter-spacing:1px; text-transform:uppercase; margin-bottom:4px;">⚠ Over limit this week</div>' if over else ''}
</div>
""")
        updated[vk] = st.number_input(
            f"Weekly limit for {v['label']}",
            min_value=0, max_value=100, value=int(current_limit), step=1,
            key=f"goal_{vk}",
            help="Set to 0 to remove the limit",
        )

    st.html("<div style='height:8px'></div>")
    if st.button("Save Goals →", type="primary", use_container_width=True):
        try:
            import database as db
            for vk, limit in updated.items():
                db.save_vice_goal(user_id, vk, limit)
            st.success("Goals saved.")
            st.rerun()
        except Exception:
            st.error("Couldn't save goals — please try again.")


# ─── LEGACY ENTRY POINT ───────────────────────────────────────────────────────

def dashboard_page():
    stats_page()
