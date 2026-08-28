import streamlit as st
from styles import inject_page_css


def freak_match_page(user_id: int):
    inject_page_css()

    if not user_id:
        st.html("""
<div style="padding:60px;text-align:center;font-family:'Bebas Neue',sans-serif;
            font-size:28px;letter-spacing:3px;color:var(--muted);">LOG IN TO USE FREAK MATCH</div>
""")
        return

    import database as db
    from Pages.vice_hot_takes import compute_freak_score

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
    Hidden · Anonymous Matching
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(40px,8vw,62px);
              color:var(--text); letter-spacing:3px; line-height:0.92; margin-bottom:6px;">
    FREAK<br><span style="color:var(--magenta);">MATCH</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:4px;">
    Anonymous. Opt-in. No names.
  </div>
</div>
""")

    freak_data = compute_freak_score(user_id)

    if not freak_data:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid var(--amber); border-radius:4px; padding:20px 22px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:8px;">NOT ENOUGH DATA YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text); line-height:1.65; margin-bottom:14px;">
    Your Freak Score needs at least 5 responses to activate.
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted); letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">How to unlock:</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); line-height:1.8;">
    1. Go to <strong style="color:var(--text);">Dashboard → Log Session</strong> (or hit the ＋ button)<br>
    2. Submit a log — a scenario card appears below it<br>
    3. Answer <strong style="color:var(--text);">That's me</strong> or <strong style="color:var(--text);">Nah</strong> — that's one hot take<br>
    4. Repeat across 5 sessions. Your Freak Score builds automatically.
  </div>
</div>
""")
        return

    freak_pct = freak_data["freak_pct"]
    freak_label = freak_data["label"]
    freak_color = freak_data["color"]

    shadow_row = db.get_shadow_score(user_id)
    is_visible = bool(shadow_row.get("match_visible", 0))

    toggle_label = "You're visible to matches" if is_visible else "Make your profile visible to matches"
    toggle_color = "var(--lime)" if is_visible else "var(--muted)"
    toggle_icon  = "◈" if is_visible else "○"

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid {toggle_color}; border-radius:4px;
            padding:18px 20px; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:{toggle_color}; margin-bottom:8px;">
    {toggle_icon} Visibility
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              margin-bottom:14px; line-height:1.6;">
    {toggle_label}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
              letter-spacing:1px; line-height:1.6;">
    Only your freak score range, tier label, and top signals are shown. No username. No identifiers.
  </div>
</div>
""")

    btn_label = "Go invisible" if is_visible else "Make me visible"
    if st.button(btn_label, key="fm_toggle_visible"):
        db.set_match_visible(user_id, not is_visible)
        db.get_shadow_score.clear()
        st.rerun()

    if not is_visible:
        return

    matches = db.load_freak_matches(user_id, freak_pct)

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin:24px 0 14px;">
  Profiles within ±20 of your score ({freak_pct})
</div>
""")

    if not matches:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:32px 20px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--muted);
              letter-spacing:3px; margin-bottom:8px;">NO MATCHES YET</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    No one at your level right now. Check back later.
  </div>
</div>
""")
    else:
        cols = st.columns(2)
        for i, m in enumerate(matches):
            col = cols[i % 2]
            with col:
                sigs_html = "".join(
                    f'<span style="background:var(--surface); border:1px solid var(--border); border-radius:2px; '
                    f'font-family:\'Space Mono\',monospace; font-size:7px; letter-spacing:1px; '
                    f'padding:3px 7px; margin-right:4px; color:var(--muted);">{s}</span>'
                    for s in (m["match_signals"] or [])
                ) if m["match_signals"] else '<span style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);">No signals</span>'
                st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {m['freak_color']}; border-radius:4px;
            padding:16px 16px 14px; margin-bottom:12px;">
  <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
    <div style="width:40px; height:40px; border-radius:50%; background:{m['freak_color']};
                display:flex; align-items:center; justify-content:center; flex-shrink:0;">
      <span style="font-family:'Bebas Neue',sans-serif; font-size:16px; color:#0a0a0b;">{m['initials']}</span>
    </div>
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:{m['freak_color']};
                  line-height:1;">{m['freak_score']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">{m['freak_label']}</div>
    </div>
  </div>
  <div style="margin-bottom:10px; display:flex; flex-wrap:wrap; gap:4px;">
    {sigs_html}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase;">
    Conflict index: {m['conflict_idx']}
  </div>
</div>
""")

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:7px; letter-spacing:1px;
            text-transform:uppercase; color:var(--muted); text-align:center; margin-top:16px;">
  Profiles refresh every 60 seconds. All data is anonymised.
</div>
""")
