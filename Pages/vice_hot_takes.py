"""
Pages/vice_hot_takes.py

NOT a standalone page — a component injected into the logging flow.

Usage in dashboard.py, immediately after a successful session save:

    from Pages.vice_hot_takes import maybe_render_hot_take
    maybe_render_hot_take(vice=logged_vice, user_id=user_id)

How it works:
- One contextual scenario card appears inline after each log.
- Vice-matched: logging alcohol → alcohol scenario, etc.
- Response time is captured server-side (time.time() delta).
- Result writes to interactions table:
    { scenario_id, scenario_text, vice, heat, answer (bool), ms_elapsed }
- compute_freak_score(user_id) can be called anywhere to surface the
  running Freak Score + Conflict Index from accumulated responses.
"""

import time
import random
import streamlit as st

# ─── SCENARIO BANK ────────────────────────────────────────────────────────────

_SCENARIOS = {
    "alcohol": [
        {"id": "alc_01", "text": "You've kept drinking after you told yourself you were done.", "heat": 2},
        {"id": "alc_02", "text": "You've pre-drank alone because it was cheaper.", "heat": 1},
        {"id": "alc_03", "text": "You've lied about how much you had so someone wouldn't worry.", "heat": 2},
        {"id": "alc_04", "text": "You've made a drunk decision you'd never make sober — and stood by it.", "heat": 3},
        {"id": "alc_05", "text": "You've woken up and checked your phone with genuine anxiety.", "heat": 3},
        {"id": "alc_06", "text": "You've used alcohol to get through something you were dreading.", "heat": 2},
    ],
    "weed": [
        {"id": "wd_01", "text": "You've shown up to something important still a little high.", "heat": 2},
        {"id": "wd_02", "text": "You smoke to sleep most nights.", "heat": 2},
        {"id": "wd_03", "text": "You've been more productive high than sober on at least one occasion.", "heat": 1},
        {"id": "wd_04", "text": "You've turned down plans because you'd rather stay in and smoke.", "heat": 2},
        {"id": "wd_05", "text": "You've driven when you probably shouldn't have.", "heat": 3},
        {"id": "wd_06", "text": "You've gone longer than a week without it and genuinely felt it.", "heat": 2},
    ],
    "sex": [
        {"id": "sx_01", "text": "You've hooked up with someone you actively disliked as a person.", "heat": 2},
        {"id": "sx_02", "text": "You've faked enthusiasm in bed to speed things up.", "heat": 2},
        {"id": "sx_03", "text": "You've thought about someone else during sex and it worked.", "heat": 3},
        {"id": "sx_04", "text": "You've kept a hookup secret from your closest friend.", "heat": 2},
        {"id": "sx_05", "text": "You've done something in bed that surprised even yourself.", "heat": 3},
        {"id": "sx_06", "text": "You've said yes when no was the honest answer.", "heat": 3},
    ],
    "other": [
        {"id": "ot_01", "text": "You've combined things in ways you'd never admit to a doctor.", "heat": 3},
        {"id": "ot_02", "text": "You've talked someone else out of something you do yourself.", "heat": 2},
        {"id": "ot_03", "text": "You've used something to get through a social situation you'd normally avoid.", "heat": 2},
        {"id": "ot_04", "text": "You've done it more than once this week and told yourself it was still occasional.", "heat": 3},
        {"id": "ot_05", "text": "You've been more honest with a substance in your system than without.", "heat": 2},
    ],
}

_FALLBACK = [
    {"id": "meta_01", "text": "You've judged someone for a habit you share privately.", "heat": 2},
    {"id": "meta_02", "text": "You've thought 'I should probably slow down' and immediately didn't.", "heat": 3},
    {"id": "meta_03", "text": "You've lied to someone who cares about you about what you got up to.", "heat": 2},
]

_HEAT_COLOR = {1: "var(--lime)", 2: "var(--amber)", 3: "var(--magenta)"}
_HEAT_LABEL = {1: "MILD", 2: "SPICY", 3: "ATOMIC"}

_CSS = """
<style>
@keyframes ht-slide {
  from { opacity:0; transform:translateY(10px); }
  to   { opacity:1; transform:translateY(0); }
}
.ht-interrupt {
  animation: ht-slide 0.3s cubic-bezier(0.22,1,0.36,1) both;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 24px 22px;
  margin-top: 20px;
}
.ht-eyebrow {
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ht-question {
  font-family: 'DM Sans', sans-serif;
  font-size: 16px;
  color: var(--text);
  line-height: 1.65;
  margin-bottom: 20px;
  font-style: italic;
}
.ht-speed-note {
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--muted);
  text-align: center;
  margin-top: 10px;
}
</style>
"""


# ─── DB HELPERS ───────────────────────────────────────────────────────────────

def _seen_ids(user_id: int) -> set:
    try:
        import database as db
        rows = db.load_interactions(user_id, "hot_take")
        return {r["payload"].get("scenario_id") for r in rows if r.get("payload")}
    except Exception:
        return set()


def _save(user_id: int, scenario: dict, answer: bool, ms: int):
    try:
        import database as db
        db.save_interaction(user_id, "hot_take", {
            "scenario_id":   scenario["id"],
            "scenario_text": scenario["text"],
            "vice":          scenario.get("vice", ""),
            "heat":          scenario["heat"],
            "answer":        answer,
            "ms_elapsed":    ms,
        })
    except Exception:
        pass


def _pick(vice: str, seen: set) -> dict | None:
    pool = _SCENARIOS.get(vice, _FALLBACK)
    available = [s for s in pool if s["id"] not in seen]
    if not available:
        available = pool
    return random.choice(available) if available else None


# ─── FREAK SCORE ─────────────────────────────────────────────────────────────

def compute_freak_score(user_id: int) -> dict | None:
    """
    Returns score dict if >= 5 responses exist, else None.
    Persists conflict_idx + freak_score to shadow_scores table.
    Safe to call on every analytics/dashboard render.
    """
    try:
        import database as db
        rows = db.load_interactions(user_id, "hot_take")
    except Exception:
        return None

    if len(rows) < 5:
        return None

    yes_pts = max_pts = yes_count = hesitation_yes = conflict_pts = 0

    for r in rows:
        p    = r.get("payload", {})
        heat = p.get("heat", 1)
        ans  = p.get("answer", False)
        ms   = p.get("ms_elapsed", 0)
        max_pts += heat * 3
        if ans:
            yes_count += 1
            yes_pts   += heat
            if ms > 5000:
                hesitation_yes += 1
                conflict_pts   += heat
        else:
            if ms > 5000 and heat >= 2:
                conflict_pts += 1

    freak_pct    = round((yes_pts / max(max_pts, 1)) * 100)
    hes_pct      = round((hesitation_yes / max(yes_count, 1)) * 100) if yes_count else 0
    conflict_idx = min(100, round((conflict_pts / max(len(rows), 1)) * 10))

    try:
        db.upsert_shadow_score(user_id, conflict_idx=conflict_idx, freak_score=freak_pct)
    except Exception:
        pass

    thresholds = [
        (20,  "The Innocent",   "var(--lime)"),
        (40,  "The Curious",    "var(--lime)"),
        (60,  "The Candid",     "var(--amber)"),
        (78,  "The Unfiltered", "var(--amber)"),
        (101, "The Unhinged",   "var(--magenta)"),
    ]
    label, color = next(
        ((l, c) for ceiling, l, c in thresholds if freak_pct <= ceiling),
        ("The Unhinged", "var(--magenta)")
    )

    return {
        "freak_pct":      freak_pct,
        "conflict_idx":   conflict_idx,
        "hesitation_pct": hes_pct,
        "yes_count":      yes_count,
        "total":          len(rows),
        "label":          label,
        "color":          color,
    }


# ─── MAIN COMPONENT ──────────────────────────────────────────────────────────

def maybe_render_hot_take(vice: str, user_id: int):
    """
    Call immediately after a successful session save.
    Renders one contextual scenario card inline.
    Clears itself after response or skip.
    """
    # Reset state when a new log just happened
    # (caller should set st.session_state.ht_fresh = True before calling)
    if st.session_state.get("ht_fresh"):
        st.session_state.ht_dismissed  = False
        st.session_state.ht_answered   = False
        st.session_state.ht_scenario   = None
        st.session_state.ht_show_start = None
        st.session_state.ht_fresh      = False

    if st.session_state.get("ht_dismissed"):
        return

    if st.session_state.get("ht_answered"):
        st.html("""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-top:12px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime);">✓ Captured. Your response time is part of your profile.</div>
</div>
""")
        return

    # Pick scenario on first render
    if not st.session_state.get("ht_scenario"):
        seen     = _seen_ids(user_id)
        scenario = _pick(vice, seen)
        if not scenario:
            return
        st.session_state.ht_scenario   = {**scenario, "vice": vice}
        st.session_state.ht_show_start = time.time()

    scenario  = st.session_state.ht_scenario
    heat      = scenario["heat"]
    heat_col  = _HEAT_COLOR[heat]
    heat_lbl  = _HEAT_LABEL[heat]
    show_time = st.session_state.get("ht_show_start") or time.time()

    st.html(_CSS)
    st.html(f"""
<div class="ht-interrupt" style="border-top:2px solid {heat_col};">
  <div class="ht-eyebrow">
    <span>While you're being honest —</span>
    <span style="color:{heat_col};">{heat_lbl}</span>
  </div>
  <div class="ht-question">"{scenario['text']}"</div>
</div>
""")

    col_yes, col_no, col_skip = st.columns([3, 3, 2])
    sid = scenario["id"]

    with col_yes:
        if st.button("That's me", use_container_width=True, type="primary", key=f"ht_yes_{sid}"):
            ms = round((time.time() - show_time) * 1000)
            _save(user_id, scenario, True, ms)
            st.session_state.ht_answered = True
            st.rerun()
    with col_no:
        if st.button("Nah", use_container_width=True, key=f"ht_no_{sid}"):
            ms = round((time.time() - show_time) * 1000)
            _save(user_id, scenario, False, ms)
            st.session_state.ht_answered = True
            st.rerun()
    with col_skip:
        if st.button("Skip", use_container_width=True, key=f"ht_skip_{sid}"):
            st.session_state.ht_dismissed = True
            st.rerun()

    st.html('<div class="ht-speed-note">Your response time is part of the data.</div>')
