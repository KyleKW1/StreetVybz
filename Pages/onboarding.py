"""
Pages/onboarding.py
3-step first-time user flow shown when a user has no vice log entries.
Completion sets st.session_state.onboarding_done = True and redirects to dashboard.
"""

import streamlit as st
from datetime import datetime
from styles import inject_page_css

VICES = {
    "weed":    {"label": "Weed / Smoking", "icon": "🌿", "color": "#c6ff00"},
    "alcohol": {"label": "Alcohol",        "icon": "🥃", "color": "#ffb300"},
    "sex":     {"label": "Unprotected Sex","icon": "🔥", "color": "#ff2d78"},
    "other":   {"label": "Other Substances","icon": "💊","color": "#00e5ff"},
}

STEPS = ["Welcome", "First Log", "You're in"]


def _progress(step: int):
    segs = "".join(
        f'<div style="flex:1; height:3px; border-radius:2px; background:'
        f'{"var(--lime)" if i <= step else "var(--border)"}"></div>'
        for i in range(len(STEPS))
    )
    labels = "".join(
        f'<div style="flex:1; text-align:center; font-family:\'Space Mono\',monospace;'
        f' font-size:8px; letter-spacing:1px; text-transform:uppercase;'
        f' color:{"var(--lime)" if i <= step else "var(--muted)"};">{STEPS[i]}</div>'
        for i in range(len(STEPS))
    )
    st.html(f"""
<div style="margin-bottom:28px;">
  <div style="display:flex; gap:4px; margin-bottom:6px;">{segs}</div>
  <div style="display:flex;">{labels}</div>
</div>
""")


def _step_0():
    inject_page_css()
    _progress(0)
    st.html("""
<div style="text-align:center; padding:20px 0 32px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:56px; color:var(--lime);
              letter-spacing:4px; line-height:0.9; margin-bottom:12px;">
    VICE<span style="color:var(--text);">VAULT</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; color:var(--soft);
              line-height:1.8; max-width:420px; margin:0 auto 28px;">
    No judgement. No sharing. Just data about yourself that you never had before.
  </div>
</div>

<div style="display:flex; flex-direction:column; gap:10px; max-width:480px; margin:0 auto 32px;">
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--lime); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--lime); margin-bottom:4px;">Log</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Track what you actually do — weed, alcohol, sex, other substances. One tap, no form required.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--amber); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber); margin-bottom:4px;">Find out how freaky you are</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Answer hot takes after each log. Build your Freak Score. At 60+ unlock Shadow Mode — a darker tier of questions.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--magenta); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:4px;">Find like-minded people</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Freak Match shows anonymous profiles at your level. Drop a Compatibility Code after the desire quiz to compare results with someone.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--soft); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--soft); margin-bottom:4px;">Play</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Do or Drink, Confessions, Read Between The Lines — the vault feeds all of it.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid #00e5ff; border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:#00e5ff; margin-bottom:4px;">Track your patterns</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      History logs every session. Analytics surfaces patterns — your peak days, streaks, and habits you haven't noticed yet.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--lime); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--lime); margin-bottom:4px;">Where To Go Tonight</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Find venues and spots near you based on your vice. Real places, filtered to what you're actually into.
    </div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--amber); border-radius:4px; padding:14px 18px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber); margin-bottom:4px;">Profile</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
      Your full picture — vice breakdown, Freak Score, RBTL history, and a shareable stats card.
    </div>
  </div>
</div>
""")

    _, c, _ = st.columns([1, 2, 1])
    with c:
        if st.button("Let's go →", use_container_width=True, type="primary", key="ob_step0"):
            st.session_state.ob_step = 1
            st.rerun()

    st.html("""
<div style="text-align:center; margin-top:16px; font-family:'Space Mono',monospace;
            font-size:8px; letter-spacing:1px; text-transform:uppercase; color:var(--muted);">
  Everything stays private · Nothing is shared without your consent
</div>
""")


def _step_1():
    inject_page_css()
    _progress(1)
    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:18px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px; line-height:1;">LOG YOUR FIRST SESSION</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Pick something from the last 7 days. Be honest — nobody else can see this.
  </div>
</div>
""")

    st.session_state.setdefault("ob_vice", "weed")

    cols = st.columns(4)
    for i, (vk, v) in enumerate(VICES.items()):
        with cols[i]:
            is_sel = st.session_state.ob_vice == vk
            st.html(f"""
<div style="background:var(--card); border:1px solid {'var(--lime)' if is_sel else 'var(--border)'};
            border-top:3px solid {v['color']}; border-radius:4px; padding:14px 10px 10px;
            text-align:center; margin-bottom:4px;">
  <div style="font-size:22px; margin-bottom:4px;">{v['icon']}</div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:{v['color']};">
    {v['label'].split('/')[0].strip()}
  </div>
</div>
""")
            if st.button("Select", key=f"ob_pick_{vk}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.ob_vice = vk
                st.rerun()

    st.html("<div style='height:16px'></div>")

    from Pages.dashboard import render_log_form
    render_log_form(st.session_state.ob_vice)

    # Override the submit button behaviour — after logging, go to step 2
    if st.session_state.get("vice_log") and len(st.session_state.vice_log) > 0:
        st.session_state.ob_step = 2
        st.rerun()

    _, c2, _ = st.columns([2, 1, 2])
    with c2:
        if st.button("Skip →", use_container_width=True, key="ob_skip1"):
            st.session_state.ob_step = 2
            st.rerun()


def _step_2():
    inject_page_css()
    _progress(2)
    st.html("""
<div style="text-align:center; padding:40px 0;">
  <div style="font-size:52px; margin-bottom:16px;">⚡</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--lime);
              letter-spacing:3px; margin-bottom:12px;">YOU'RE IN</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
              line-height:1.8; max-width:400px; margin:0 auto 32px;">
    Your vault is open. Log whenever, as honest as you like.
  </div>
</div>

<div style="display:flex; flex-direction:column; gap:8px; max-width:420px; margin:0 auto 32px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:4px;">What happens next</div>
  <div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
              padding:12px 16px; font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
    🔥 After each log a <strong style="color:var(--text);">hot take card</strong> drops — answer honestly to build your Freak Score
  </div>
  <div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
              padding:12px 16px; font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
    ⬡ Hit 5 hot takes to unlock <strong style="color:var(--text);">Freak Match</strong> — anonymous profiles at your level
  </div>
  <div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
              padding:12px 16px; font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
    ⚡ <strong style="color:var(--text);">Read Between The Lines</strong> — desire profile quiz, drop a code to compare with someone
  </div>
  <div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
              padding:12px 16px; font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
    🃏 <strong style="color:var(--text);">Do or Drink</strong> — AI turns your vault into personalised dares
  </div>
</div>
""")

    _, c, _ = st.columns([1, 2, 1])
    with c:
        if st.button("Go to Dashboard →", use_container_width=True, type="primary", key="ob_done"):
            st.session_state.onboarding_done = True
            st.session_state.selected_feature = "stats"
            st.rerun()


def onboarding_page():
    st.session_state.setdefault("ob_step", 0)
    step = st.session_state.ob_step

    if step == 0:
        _step_0()
    elif step == 1:
        _step_1()
    else:
        _step_2()


def should_show_onboarding() -> bool:
    """
    Show onboarding if the user has never completed it and has no vice log entries.
    Once dismissed it won't show again for this session.
    """
    if st.session_state.get("onboarding_done"):
        return False
    log = st.session_state.get("vice_log", [])
    return len(log) == 0
