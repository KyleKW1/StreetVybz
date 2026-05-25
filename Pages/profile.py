"""
Pages/profile.py — User identity page.
Shows: avatar, stats summary, RBTL result history, freak score, share card.
"""

import streamlit as st
from datetime import datetime
from styles import inject_page_css

VICE_META = {
    "weed":    {"label": "Weed",    "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol", "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Sex",     "icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other",   "icon": "💊", "color": "#00e5ff"},
}

RESULT_ICONS = {
    "Closed Garden":             "🔒",
    "Quietly Curious":           "🌿",
    "The Open Door":             "🌙",
    "Already Decided":           "🔺",
    "The Third Is Already Picked": "⚡",
}


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
    return u.get("username", "User")


def profile_page():
    inject_page_css()
    uid      = _uid()
    username = _username()
    log      = st.session_state.get("vice_log", [])

    # ── Masthead ──────────────────────────────────────────────────────────────
    initials = username[:2].upper()
    st.html(f"""
<div style="display:flex; align-items:center; gap:20px;
            border-bottom:1px solid var(--border); padding-bottom:24px; margin-bottom:28px;">
  <div style="width:72px; height:72px; border-radius:50%; background:var(--lime);
              display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <span style="font-family:'Bebas Neue',sans-serif; font-size:28px;
                 color:#0a0a0b; letter-spacing:2px;">{initials}</span>
  </div>
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
                letter-spacing:2px; line-height:1;">{username.upper()}</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-top:4px;">
      Vice Vault · {len(log)} sessions logged
    </div>
  </div>
</div>
""")

    # ── Vice breakdown ────────────────────────────────────────────────────────
    if log:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Vault</div>
""")
        counts = {}
        for e in log:
            counts[e["vice"]] = counts.get(e["vice"], 0) + 1
        total = sum(counts.values())

        cols = st.columns(4)
        for i, (vk, meta) in enumerate(VICE_META.items()):
            cnt = counts.get(vk, 0)
            pct = round(cnt / total * 100) if total else 0
            with cols[i]:
                st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid {meta['color']}; border-radius:4px; padding:14px 16px;">
  <div style="font-size:20px; margin-bottom:6px;">{meta['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; color:{meta['color']};
              line-height:1;">{cnt}</div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
              text-transform:uppercase; letter-spacing:1px; margin-top:2px;">
    {pct}% of sessions
  </div>
</div>
""")
        st.html("<div style='height:1.5rem'></div>")

    # ── Freak Score ───────────────────────────────────────────────────────────
    if uid:
        try:
            from Pages.vice_hot_takes import compute_freak_score
            freak = compute_freak_score(uid)
            if freak:
                col  = freak["color"]
                st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Freak Score
</div>
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {col}; border-radius:4px;
            padding:18px 20px; margin-bottom:20px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:{col};
                  letter-spacing:1px;">{freak['label'].upper()}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:2px;">
        Based on {freak['total']} hot takes · {freak['yes_count']} yes answers
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:{col};
                  line-height:1;">{freak['freak_pct']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase;">/100</div>
    </div>
  </div>
  <div style="display:flex; gap:16px; margin-top:12px; padding-top:12px;
              border-top:1px solid var(--border);">
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--amber);">
        {freak['conflict_idx']}
      </div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">Conflict</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--magenta);">
        {freak['hesitation_pct']}%
      </div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">Hesitated</div>
    </div>
  </div>
</div>
""")
        except Exception:
            pass

    # ── RBTL result history ───────────────────────────────────────────────────
    if uid:
        history = _db("load_rbtl_history", uid, default=[])
        if history:
            st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Read Between The Lines — History
</div>
""")
            for row in history:
                name  = row.get("result_name", "—")
                meta  = row.get("result_meta", "")
                pct   = row.get("openness_pct", 0)
                ts    = row.get("completed_at", "")[:10]
                icon  = RESULT_ICONS.get(name, "◈")

                # Top signals from dim_scores
                ds          = row.get("dim_scores", {})
                hd_full     = ds.get("hd_full", {}) if isinstance(ds, dict) else {}
                from Pages.do_or_drink_core import HD_ID_TO_SIGNAL, HD_SCORE_MAP
                sigs = sorted(
                    ((HD_ID_TO_SIGNAL.get(k, k), HD_SCORE_MAP.get(v, 0))
                     for k, v in hd_full.items() if HD_SCORE_MAP.get(v, 0) >= 2),
                    key=lambda x: -x[1]
                )[:3]
                sig_str = ", ".join(
                    f"{s.replace('_latent','').replace('_',' ')}"
                    for s, _ in sigs
                ) if sigs else "—"

                st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-radius:4px; padding:16px 18px; margin-bottom:8px;
            display:flex; align-items:center; gap:16px;">
  <div style="font-size:28px; flex-shrink:0;">{icon}</div>
  <div style="flex:1; min-width:0;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:var(--text);
                letter-spacing:1px;">{name}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);
                font-style:italic; margin-top:2px;">{meta}</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--soft);
                text-transform:uppercase; letter-spacing:1px; margin-top:4px;">
      Signals: {sig_str}
    </div>
  </div>
  <div style="text-align:right; flex-shrink:0;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--lime);">
      {pct}
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                text-transform:uppercase;">openness</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                margin-top:4px;">{ts}</div>
  </div>
</div>
""")

    # ── Share card ────────────────────────────────────────────────────────────
    if log:
        st.html("<div style='height:0.5rem'></div>")
        counts    = {}
        for e in log:
            counts[e["vice"]] = counts.get(e["vice"], 0) + 1
        top_vice  = max(counts, key=counts.get) if counts else None
        top_icon  = VICE_META.get(top_vice, {}).get("icon", "◈") if top_vice else "◈"

        share_text = f"ViceVault — {username}\n"
        share_text += f"Sessions logged: {len(log)}\n"
        if top_vice:
            share_text += f"Most logged: {top_icon} {VICE_META[top_vice]['label']}\n"
        try:
            from Pages.vice_hot_takes import compute_freak_score
            freak = compute_freak_score(uid) if uid else None
            if freak:
                share_text += f"Freak Score: {freak['freak_pct']}/100 · {freak['label']}\n"
        except Exception:
            pass

        st.download_button(
            "↓ Share my stats",
            data=share_text,
            file_name="vicevault_profile.txt",
            mime="text/plain",
            use_container_width=True,
        )

    if not log:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:48px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:24px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">NOTHING LOGGED YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Log a session first — then your profile fills in.
  </div>
</div>
""")
