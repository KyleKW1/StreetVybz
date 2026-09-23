"""
Pages/analytics.py — Vice analytics & trends.
Added: combined timeline view showing all vices per day as colour-coded bars.
"""
import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict
from styles import inject_page_css

VICE_META = {
    "weed":    {"label": "Weed",    "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol", "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Sex",     "icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other",   "icon": "💊", "color": "#00e5ff"},
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
    inject_page_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Hidden</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">ANALYTICS</div>
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
    period   = st.selectbox("Time period",
                            ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
                            index=1, key="analytics_period")
    days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": 9999}
    days     = days_map[period]
    entries  = entries_in_range(days)
    total    = len(entries)

    if total == 0:
        st.info("No sessions in this period.")
        return

    # ── Summary cards ─────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Summary</div>
""")
    counts = {vk: len([e for e in entries if e["vice"] == vk]) for vk in VICE_META}
    cols   = st.columns(4)
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

    # ── Daily timeline — stacked per-vice bars ─────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Daily Timeline
</div>
""")

    display_days = min(days, 30)  # cap at 30 days for readability
    day_vice_counts: dict = defaultdict(lambda: defaultdict(int))
    for e in entries_in_range(min(days, 30)):
        d  = datetime.fromisoformat(e["timestamp"]).date()
        vk = e["vice"]
        day_vice_counts[d][vk] += 1

    day_list = [(datetime.now() - timedelta(days=i)).date() for i in range(display_days - 1, -1, -1)]
    max_day  = max((sum(day_vice_counts[d].values()) for d in day_list), default=1)

    bars_html = '<div style="display:flex; align-items:flex-end; gap:2px; height:120px; margin-bottom:8px;">'
    for d in day_list:
        day_total = sum(day_vice_counts[d].values())
        if day_total == 0:
            bars_html += f"""
<div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; gap:1px;">
  <div style="width:100%; height:2px; background:var(--border); border-radius:1px;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:6px; color:var(--border);
              text-align:center; margin-top:3px;">{d.strftime('%d')}</div>
</div>"""
            continue

        # Stack per-vice segments proportionally
        segments = ""
        for vk, meta in VICE_META.items():
            cnt = day_vice_counts[d].get(vk, 0)
            if cnt == 0:
                continue
            seg_h = max(4, int((cnt / max_day) * 100))
            segments += f'<div style="width:100%; height:{seg_h}px; background:{meta["color"]}; opacity:0.85;"></div>'

        bars_html += f"""
<div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:1px;">
  <div style="font-family:'Space Mono',monospace; font-size:6px; color:var(--lime); margin-bottom:2px;">{day_total}</div>
  <div style="width:100%; display:flex; flex-direction:column; align-items:center; justify-content:flex-end; gap:1px;">
    {segments}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:6px; color:var(--muted);
              text-align:center; margin-top:3px; white-space:nowrap; overflow:hidden; max-width:20px;">
    {d.strftime('%d') if d.day % 5 == 0 or d == day_list[0] or d == day_list[-1] else ''}
  </div>
</div>"""

    bars_html += "</div>"

    # Legend
    legend = "".join(
        f'<div style="display:inline-flex; align-items:center; gap:5px; margin-right:14px;">'
        f'<div style="width:10px; height:10px; background:{meta["color"]}; border-radius:2px;"></div>'
        f'<div style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--muted);">{meta["icon"]} {meta["label"]}</div>'
        f'</div>'
        for vk, meta in VICE_META.items() if counts.get(vk, 0) > 0
    )

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:20px;">
  {bars_html}
  <div style="margin-top:8px;">{legend}</div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Weekly frequency ──────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Weekly Frequency
</div>
""")
    week_counts: dict = defaultdict(int)
    for e in entries:
        dt         = datetime.fromisoformat(e["timestamp"])
        week_start = (dt - timedelta(days=dt.weekday())).date()
        week_counts[week_start] += 1

    if week_counts:
        max_wk       = max(week_counts.values(), default=1)
        sorted_weeks = sorted(week_counts.keys())[-8:]
        bars2        = '<div style="display:flex; align-items:flex-end; gap:8px; height:120px; margin-bottom:8px;">'
        for wk in sorted_weeks:
            cnt = week_counts.get(wk, 0)
            h   = max(4, int((cnt / max_wk) * 100))
            bars2 += f"""
<div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:4px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--lime);">{cnt}</div>
  <div style="width:100%; height:{h}px; background:var(--lime); opacity:0.7; border-radius:2px 2px 0 0;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
              text-align:center; white-space:nowrap; overflow:hidden; max-width:36px;">
    {wk.strftime('%m/%d')}
  </div>
</div>"""
        bars2 += "</div>"
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:20px;">
  {bars2}
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Vice share pie ────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Share of Sessions
</div>
""")
    col_pie, col_legend = st.columns([1, 2])
    with col_pie:
        stops, pct_acc = [], 0
        for vk, meta in VICE_META.items():
            pct = (counts[vk] / total * 100) if total else 0
            stops.append(f"{meta['color']} {pct_acc:.1f}% {pct_acc + pct:.1f}%")
            pct_acc += pct
        conic = ", ".join(stops)
        st.html(f"""
<div style="width:120px; height:120px; border-radius:50%;
            background:conic-gradient({conic}); margin:0 auto;"></div>
""")
    with col_legend:
        for vk, meta in VICE_META.items():
            pct = (counts[vk] / total * 100) if total else 0
            st.html(f"""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
  <div style="width:10px; height:10px; background:{meta['color']}; border-radius:2px; flex-shrink:0;"></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); flex:1;">
    {meta['icon']} {meta['label']}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:11px; color:{meta['color']};">{pct:.0f}%</div>
</div>
""")

    st.html("<div style='height:1.5rem'></div>")

    # ── Insights ──────────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Insights</div>
""")
    dow_counts: dict = defaultdict(int)
    for e in entries:
        dow = datetime.fromisoformat(e["timestamp"]).strftime("%A")
        dow_counts[dow] += 1
    busiest_day    = max(dow_counts, key=dow_counts.get) if dow_counts else "—"
    top_vice_key   = max(counts, key=counts.get) if counts else None
    top_vice       = VICE_META[top_vice_key]["label"] if top_vice_key else "—"
    top_vice_icon  = VICE_META[top_vice_key]["icon"]  if top_vice_key else ""
    top_vice_color = VICE_META[top_vice_key]["color"] if top_vice_key else "var(--lime)"
    active_days    = len({datetime.fromisoformat(e["timestamp"]).date() for e in entries})

    avg_per_week = round(total / max(1, days / 7), 1)

    insights = [
        ("Busiest day",    busiest_day,                   "var(--cyan)"),
        ("Top vice",       f"{top_vice_icon} {top_vice}", top_vice_color),
        ("Active days",    str(active_days),              "var(--amber)"),
        ("Avg / week",     str(avg_per_week),             "var(--lime)"),
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
