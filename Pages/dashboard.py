"""
Pages/dashboard.py
Vice tracker — stats, log, and history as separate standalone pages.
DB-backed: entries are saved to vice_log table on add, deleted on clear.
"""

import streamlit as st
import time
from datetime import datetime, timedelta, date

# ─── BRAND CSS ────────────────────────────────────────────────────────────────

def inject_css():
    st.html("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #0a0a0b;
  --surface:  #111114;
  --card:     #18181d;
  --border:   #2a2a35;
  --lime:     #c6ff00;
  --magenta:  #ff2d78;
  --cyan:     #00e5ff;
  --amber:    #ffb300;
  --text:     #f0f0f5;
  --muted:    #5a5a72;
  --soft:     #9090aa;
}

.stApp { background: var(--bg) !important; }
section[data-testid="stMain"] { background: var(--bg) !important; }
section.main .block-container {
  padding-top: 2rem !important;
  padding-bottom: 3rem !important;
  max-width: 900px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: #0d0d10 !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: #c8c8d8 !important; }
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: #c8c8d8 !important;
  border-radius: 4px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 11px !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
  transition: all 0.2s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #1a1a20 !important;
  border-color: var(--lime) !important;
  color: var(--lime) !important;
  box-shadow: none !important; transform: none !important;
}

/* Buttons */
.stButton > button {
  background: var(--lime) !important;
  color: #0a0a0b !important;
  border: none !important;
  border-radius: 3px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  padding: 10px 20px !important;
  transition: all 0.15s ease !important;
  box-shadow: none !important;
}
.stButton > button:hover {
  background: #d4ff1a !important;
  box-shadow: 0 0 20px rgba(198,255,0,0.25) !important;
  transform: none !important;
}
.stButton > button[kind="secondary"] {
  background: transparent !important;
  color: var(--soft) !important;
  border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--soft) !important;
  color: var(--text) !important;
  box-shadow: none !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 14px !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--lime) !important;
  box-shadow: 0 0 0 2px rgba(198,255,0,0.12) !important;
}
.stTextInput label, .stNumberInput label,
.stTextArea label, .stSelectbox label,
.stSlider label, .stDateInput label,
.stTimeInput label {
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}

/* Date / Time inputs */
.stDateInput > div > div,
.stTimeInput > div > div {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  color: var(--text) !important;
}

/* Selectbox */
.stSelectbox > div > div {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
  color: var(--text) !important;
}

/* Slider */
.stSlider > div > div > div > div { background: var(--lime) !important; }

/* Alerts */
.stAlert {
  border-radius: 4px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
}
.stSuccess { border-left: 3px solid var(--lime) !important; }
.stError   { border-left: 3px solid var(--magenta) !important; }

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""")

# ─── VICE DEFINITIONS ─────────────────────────────────────────────────────────

VICES = {
    "weed": {
        "label": "Weed / Smoking",
        "icon": "🌿",
        "color": "#c6ff00",
        "unit": "sessions",
        "fields": [
            {"key": "method", "label": "Method", "type": "select",
             "options": ["Joint", "Blunt", "Bong", "Vape", "Edible", "Other"]},
            {"key": "amount", "label": "Amount (g / units)", "type": "number", "min": 0.1, "step": 0.1},
            {"key": "intensity", "label": "Intensity (1–10)", "type": "slider", "min": 1, "max": 10},
            {"key": "solo", "label": "Alone or with others?", "type": "select",
             "options": ["Solo", "With 1 person", "Group (3+)"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ]
    },
    "alcohol": {
        "label": "Alcohol",
        "icon": "🥃",
        "color": "#ffb300",
        "unit": "standard drinks",
        "fields": [
            {"key": "drink_type", "label": "Type", "type": "select",
             "options": ["Beer", "Wine", "Spirits", "Cocktails", "Shots", "Mixed"]},
            {"key": "drinks", "label": "No. of standard drinks", "type": "number", "min": 1, "step": 1},
            {"key": "over_hours", "label": "Over how many hours?", "type": "number", "min": 0.5, "step": 0.5},
            {"key": "setting", "label": "Setting", "type": "select",
             "options": ["Home alone", "Home with others", "Bar / Club", "Party", "Restaurant", "Other"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ]
    },
    "sex": {
        "label": "Unprotected Sex",
        "icon": "🔥",
        "color": "#ff2d78",
        "unit": "encounters",
        "fields": [
            {"key": "partner_type", "label": "Partner", "type": "select",
             "options": ["Long-term partner", "Casual / Known", "New / Unknown", "Prefer not to say"]},
            {"key": "contraception", "label": "Any contraception used?", "type": "select",
             "options": ["None", "Pill / Hormonal", "IUD", "Pull-out", "Other"]},
            {"key": "sti_status", "label": "STI status known?", "type": "select",
             "options": ["Both tested", "One tested", "Neither tested", "Unknown"]},
            {"key": "regret", "label": "Regret level (1 = none, 10 = major)", "type": "slider", "min": 1, "max": 10},
            {"key": "notes", "label": "Notes (private)", "type": "text"},
        ]
    },
    "other": {
        "label": "Other Substances",
        "icon": "💊",
        "color": "#00e5ff",
        "unit": "uses",
        "fields": [
            {"key": "substance", "label": "Substance", "type": "text"},
            {"key": "amount", "label": "Amount / Dose", "type": "text"},
            {"key": "intensity", "label": "Intensity (1–10)", "type": "slider", "min": 1, "max": 10},
            {"key": "setting", "label": "Setting", "type": "select",
             "options": ["Solo", "Social", "Party", "Other"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ]
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
    """Add a vice entry to session_state AND persist to DB."""
    log = get_log()
    local_id = int(time.time() * 1000)

    entry = {
        "id":        local_id,
        "vice":      vice_key,
        "timestamp": timestamp.isoformat(),
        "data":      data,
    }
    log.append(entry)
    st.session_state.vice_log = log

    # ── DB persist ────────────────────────────────────────────────────────────
    user_id = _current_user_id()
    if user_id:
        try:
            import database as db
            db_id = db.save_vice_entry(user_id, vice_key, timestamp, data)
            if db_id:
                entry["id"] = db_id   # update local entry with real DB id
        except Exception:
            pass   # offline — local copy is the fallback


def entries_for(vice_key: str, days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    return [
        e for e in get_log()
        if e["vice"] == vice_key
        and datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]


def all_entries(days: int = 30):
    cutoff = datetime.now() - timedelta(days=days)
    return [
        e for e in get_log()
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]

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

# ─── STATS PAGE ───────────────────────────────────────────────────────────────

def stats_page():
    inject_css()
    page_masthead("DASHBOARD", "No judgement. Just data.")

    log = all_entries(30)
    total = len(log)

    # Summary cards
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
        return

    # 14-day activity heatmap
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  14-Day Activity
</div>
""")
    days_list = [(datetime.now() - timedelta(days=i)).date() for i in range(13, -1, -1)]
    day_counts = {}
    for e in all_entries(14):
        d = datetime.fromisoformat(e["timestamp"]).date()
        day_counts[d] = day_counts.get(d, 0) + 1

    max_count = max(day_counts.values(), default=1)
    cols_heat = st.columns(14)
    for i, d in enumerate(days_list):
        cnt = day_counts.get(d, 0)
        intensity = cnt / max_count if max_count else 0
        opacity = 0.15 + intensity * 0.85
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

    # Per-vice breakdown
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Breakdown</div>
""")
    for vk, v in VICES.items():
        count = len([e for e in log if e["vice"] == vk])
        pct = (count / total * 100) if total else 0
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
        log_date = st.date_input(
            "Date",
            value=date.today(),
            max_value=date.today(),
            key=f"log_{vice_key}_date",
        )
    with col_time:
        log_time = st.time_input(
            "Time",
            value=datetime.now().time(),
            key=f"log_{vice_key}_time",
        )

    st.html("<div style='height:4px'></div>")

    form_data = {}
    for field in v["fields"]:
        key = f"log_{vice_key}_{field['key']}"
        if field["type"] == "select":
            form_data[field["key"]] = st.selectbox(field["label"], field["options"], key=key)
        elif field["type"] == "number":
            form_data[field["key"]] = st.number_input(
                field["label"],
                min_value=float(field.get("min", 0)),
                step=float(field.get("step", 1)),
                key=key,
            )
        elif field["type"] == "slider":
            form_data[field["key"]] = st.slider(
                field["label"],
                min_value=field["min"],
                max_value=field["max"],
                value=(field["min"] + field["max"]) // 2,
                key=key,
            )
        elif field["type"] == "text":
            form_data[field["key"]] = st.text_input(field["label"], key=key)

    st.html("<div style='height:8px'></div>")

    if st.button(f"Log {v['label']} →", key=f"submit_{vice_key}", type="primary", use_container_width=True):
        entry_dt = datetime.combine(log_date, log_time)
        add_entry(vice_key, form_data, entry_dt)
        st.success(f"Logged. {v['icon']}")
        st.rerun()


def log_session_page():
    inject_css()
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
    inject_css()
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
        v = VICES[e["vice"]]
        ts = datetime.fromisoformat(e["timestamp"])
        time_str = ts.strftime("%b %d, %Y · %H:%M")
        data_str = "  ·  ".join(
            f"{k}: {val}" for k, val in e["data"].items() if val and k != "notes"
        )
        notes = e["data"].get("notes", "")
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
        # ── Delete from DB ────────────────────────────────────────────────────
        user_id = _current_user_id()
        if user_id:
            try:
                import database as db
                db.delete_vice_log(user_id)
            except Exception:
                pass
        st.session_state.vice_log = []
        st.rerun()

# ─── LEGACY ENTRY POINT ───────────────────────────────────────────────────────

def dashboard_page():
    stats_page()
