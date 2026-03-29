"""
Pages/analytics.py — Vice analytics & trends
"""
import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict


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
section.main .block-container { padding-top:2rem !important; max-width:900px !important; }
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
  color:var(--lime) !important; box-shadow:none !important; transform:none !important;
}
.stButton > button {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important; border-radius:3px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1.5px !important; text-transform:uppercase !important;
  transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover {
  border-color:var(--lime) !important; color:var(--lime) !important;
  box-shadow:none !important; transform:none !important;
}
.stSelectbox > div > div {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:3px !important; color:var(--text) !important;
}
.stSelectbox label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important; color:var(--muted) !important;
}
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")


VICE_META = {
    "weed":    {"label": "Weed",      "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol",   "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Sex",       "icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other",     "icon": "💊", "color": "#00e5ff"},
}


def get_log():
    return st.session_state.get("vice_log", [])


def entries_in_range(days: int):
    cutoff = datetime.now() - timedelta(days=days)
    return [
        e for e in get_log()
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]


def analytics_page():
    inject_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">
    ANALYTICS
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Patterns don't lie.
  </div>
</div>
""")

    log = get_log()

    if not log:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">NO DATA YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Log some sessions on the dashboard first.
  </div>
</div>
""")
        return

    # ── Period selector ───────────────────────────────────────────────────────
    period = st.selectbox("Time period", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
                          index=1, key="analytics_period")
    days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": 9999}
    days = days_map[period]
    entries = entries_in_range(days)
    total = len(entries)

    if total == 0:
        st.info("No sessions in this period.")
        return

    # ── Summary cards ─────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Summary
</div>
""")

    counts = {vk: len([e for e in entries if e["vice"] == vk]) for vk in VICE_META}
    cols = st.columns(4)
    for i, (vk, meta) in enumerate(VICE_META.items()):
        with cols[i]:
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid {meta['color']}; border-radius:4px; padding:16px 18px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">{meta['label']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:38px; color:{meta['color']};
              line-height:1;">{counts[vk]}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--soft);">sessions</div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Weekly frequency chart (ASCII-style bars) ─────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Weekly Frequency
</div>
""")

    # Group entries by week
    week_counts = defaultdict(int)
    for e in entries:
        dt = datetime.fromisoformat(e["timestamp"])
        week_start = (dt - timedelta(days=dt.weekday())).date()
        week_counts[week_start] += 1

    if week_counts:
        max_wk = max(week_counts.values(), default=1)
        sorted_weeks = sorted(week_counts.keys())[-8:]  # last 8 weeks max

        bars_html = '<div style="display:flex; align-items:flex-end; gap:8px; height:120px; margin-bottom:8px;">'
        for wk in sorted_weeks:
            cnt = week_counts.get(wk, 0)
            h = max(4, int((cnt / max_wk) * 100))
            bars_html += f"""
<div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:4px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--lime);">{cnt}</div>
  <div style="width:100%; height:{h}px; background:var(--lime); opacity:0.7; border-radius:2px 2px 0 0;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
              text-align:center; white-space:nowrap; overflow:hidden; max-width:36px;">
    {wk.strftime('%m/%d')}
  </div>
</div>"""
        bars_html += '</div>'

        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:20px;">
  {bars_html}
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Vice share pie (CSS-based) ────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Share of Sessions
</div>
""")

    col_pie, col_legend = st.columns([1, 2])
    with col_pie:
        # conic-gradient pie
        stops, pct_acc = [], 0
        for vk, meta in VICE_META.items():
            pct = (counts[vk] / total * 100) if total else 0
            stops.append(f"{meta['color']} {pct_acc:.1f}% {pct_acc + pct:.1f}%")
            pct_acc += pct
        conic = ", ".join(stops)
        st.html(f"""
<div style="width:120px; height:120px; border-radius:50%;
            background:conic-gradient({conic});
            margin:0 auto;"></div>
""")

    with col_legend:
        for vk, meta in VICE_META.items():
            pct = (counts[vk] / total * 100) if total else 0
            st.html(f"""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
  <div style="width:10px; height:10px; background:{meta['color']}; border-radius:2px; flex-shrink:0;"></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); flex:1;">{meta['icon']} {meta['label']}</div>
  <div style="font-family:'Space Mono',monospace; font-size:11px; color:{meta['color']};">{pct:.0f}%</div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Streak / cadence insights ─────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Insights
</div>
""")

    # Most active day of week
    dow_counts = defaultdict(int)
    for e in entries:
        dow = datetime.fromisoformat(e["timestamp"]).strftime("%A")
        dow_counts[dow] += 1
    busiest_day = max(dow_counts, key=dow_counts.get) if dow_counts else "—"

    # Most logged vice
    top_vice_key = max(counts, key=counts.get) if counts else None
    top_vice = VICE_META[top_vice_key]["label"] if top_vice_key else "—"
    top_vice_icon = VICE_META[top_vice_key]["icon"] if top_vice_key else ""
    top_vice_color = VICE_META[top_vice_key]["color"] if top_vice_key else "var(--lime)"

    # Days with any activity
    active_days = len({datetime.fromisoformat(e["timestamp"]).date() for e in entries})

    insights = [
        ("Busiest day",    busiest_day,                      "var(--cyan)"),
        ("Top vice",       f"{top_vice_icon} {top_vice}",    top_vice_color),
        ("Active days",    str(active_days),                 "var(--amber)"),
        ("Total sessions", str(total),                       "var(--lime)"),
    ]

    cols2 = st.columns(4)
    for i, (label, value, color) in enumerate(insights):
        with cols2[i]:
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">{label}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:{color};
              line-height:1.1;">{value}</div>
</div>
""")
