"""
Pages/vice_hot_takes.py
Vice Hot Takes — swipe UI on spicy scenarios.
Response speed is tracked as a signal (hesitation = internal conflict).
Results are paired against the user's existing vice log to surface inconsistencies.
Outputs a Freak Score and a Conflict Index.
"""

import streamlit as st
import json
import time
import datetime
import random
from styles import inject_page_css

# ─── SCENARIO BANK ────────────────────────────────────────────────────────────

_SCENARIOS = [
    # alcohol
    {"id": "alc_01", "text": "You pre-drink alone before going out because it's cheaper.", "vice": "alcohol", "heat": 1},
    {"id": "alc_02", "text": "You've kept drinking after you said you were done for the night.", "vice": "alcohol", "heat": 2},
    {"id": "alc_03", "text": "You've lied about how much you drank so someone wouldn't worry.", "vice": "alcohol", "heat": 2},
    {"id": "alc_04", "text": "You've woken up and checked your phone with genuine anxiety.", "vice": "alcohol", "heat": 3},
    {"id": "alc_05", "text": "You've made a decision drunk that you'd never make sober and stood by it.", "vice": "alcohol", "heat": 3},
    # weed
    {"id": "weed_01", "text": "You've shown up to something important still a little high.", "vice": "weed", "heat": 2},
    {"id": "weed_02", "text": "You smoke to sleep most nights.", "vice": "weed", "heat": 2},
    {"id": "weed_03", "text": "You've driven while high — even just a little.", "vice": "weed", "heat": 3},
    {"id": "weed_04", "text": "You've turned down plans because you'd rather stay in and smoke.", "vice": "weed", "heat": 2},
    {"id": "weed_05", "text": "You've been more productive high than sober on more than one occasion.", "vice": "weed", "heat": 1},
    # sex
    {"id": "sex_01", "text": "You've hooked up with someone you actively disliked as a person.", "vice": "sex", "heat": 2},
    {"id": "sex_02", "text": "You've faked enthusiasm in bed to speed things up.", "vice": "sex", "heat": 2},
    {"id": "sex_03", "text": "You've had sex with someone while technically in a relationship.", "vice": "sex", "heat": 3},
    {"id": "sex_04", "text": "You've kept a hookup secret from your closest friend.", "vice": "sex", "heat": 2},
    {"id": "sex_05", "text": "You've thought about someone else during sex and it worked.", "vice": "sex", "heat": 3},
    {"id": "sex_06", "text": "You've done something in bed that surprised even yourself.", "vice": "sex", "heat": 3},
    # other
    {"id": "oth_01", "text": "You've combined substances in ways you'd never admit to a doctor.", "vice": "other", "heat": 3},
    {"id": "oth_02", "text": "You've talked someone else out of something you do yourself.", "vice": "other", "heat": 2},
    {"id": "oth_03", "text": "You've used something to get through a social situation you'd normally avoid.", "vice": "other", "heat": 2},
    # meta / social
    {"id": "soc_01", "text": "You've judged someone for a habit you share privately.", "vice": "meta", "heat": 2},
    {"id": "soc_02", "text": "You've felt genuine relief when a plan got cancelled.", "vice": "meta", "heat": 1},
    {"id": "soc_03", "text": "You've used a substance as a social crutch when you didn't actually want it.", "vice": "meta", "heat": 1},
    {"id": "soc_04", "text": "You've lied to someone who cares about you about what you got up to last weekend.", "vice": "meta", "heat": 2},
    {"id": "soc_05", "text": "You've thought 'I probably drink too much' and immediately poured another.", "vice": "meta", "heat": 3},
]

_SWIPE_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d;
  --border:#2a2a35; --lime:#c6ff00; --magenta:#ff2d78;
  --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}

.ht-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 32px 28px;
  margin-bottom: 12px;
  position: relative;
  transition: border-color 0.2s;
}

.ht-card-heat-1 { border-top: 3px solid var(--lime); }
.ht-card-heat-2 { border-top: 3px solid var(--amber); }
.ht-card-heat-3 { border-top: 3px solid var(--magenta); }

.ht-scenario {
  font-family: 'DM Sans', sans-serif;
  font-size: 18px;
  line-height: 1.65;
  color: var(--text);
  text-align: center;
  margin-bottom: 0;
}

.ht-meta {
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 3px;
  text-transform: uppercase;
  text-align: center;
  margin-bottom: 18px;
}

.ht-progress-bar {
  height: 2px;
  background: var(--border);
  border-radius: 1px;
  margin-bottom: 24px;
  overflow: hidden;
}
.ht-progress-fill {
  height: 100%;
  background: var(--lime);
  border-radius: 1px;
  transition: width 0.3s ease;
}

.ht-score-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 20px;
  text-align: center;
  margin-bottom: 10px;
}

.ht-score-number {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 64px;
  letter-spacing: 2px;
  line-height: 1;
}

.ht-conflict-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--border);
  margin: 8px 0;
  overflow: hidden;
}

.ht-conflict-fill {
  height: 100%;
  border-radius: 3px;
}

.ht-timer-track {
  height: 3px;
  background: var(--border);
  border-radius: 1.5px;
  overflow: hidden;
  margin-bottom: 20px;
}

@keyframes timer-drain {
  from { width: 100%; }
  to   { width: 0%; }
}

.ht-conflict-tag {
  display: inline-block;
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 2px;
  border: 1px solid;
  margin: 4px;
}

.ht-hesitation-badge {
  font-family: 'Space Mono', monospace;
  font-size: 7px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--amber);
  text-align: center;
  margin-top: 8px;
}
</style>
"""

# ─── HEAT COLORS ──────────────────────────────────────────────────────────────

_HEAT_COLOR = {1: "var(--lime)", 2: "var(--amber)", 3: "var(--magenta)"}
_HEAT_LABEL = {1: "mild", 2: "spicy", 3: "atomic"}

# ─── VICE LABELS ──────────────────────────────────────────────────────────────

_VICE_LABELS = {
    "weed":    "weed",
    "alcohol": "alcohol",
    "sex":     "sex",
    "other":   "other",
    "meta":    "self-awareness",
}

# ─── STATE ────────────────────────────────────────────────────────────────────

def _init():
    defaults = {
        "ht_phase":      "intro",
        "ht_deck":       [],
        "ht_cur":        0,
        "ht_responses":  [],   # [{scenario_id, answer, ms_elapsed, heat, vice}]
        "ht_card_start": None,
        "ht_error":      "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset():
    for k in list(st.session_state.keys()):
        if k.startswith("ht_"):
            del st.session_state[k]
    _init()
    st.rerun()


# ─── VICE LOG HELPERS ─────────────────────────────────────────────────────────

def _my_vice_counts() -> dict:
    """Returns {vice: count} from the user's logged sessions."""
    log = st.session_state.get("vice_log", [])
    counts = {}
    for e in log:
        v = e.get("vice", "")
        if v:
            counts[v] = counts.get(v, 0) + 1
    return counts


# ─── SCORING ─────────────────────────────────────────────────────────────────

_FAST_THRESHOLD_MS  = 1800   # < 1.8s = fast/confident
_SLOW_THRESHOLD_MS  = 5000   # > 5s   = hesitation

def _compute_results(responses: list) -> dict:
    """
    Freak Score  = weighted sum of YES answers by heat level (1/2/3 pts)
    Hesitation % = proportion of YES answers that took > 5s
    Conflict pts = YES answers that *also* took > 5s (knowing but slow) — internal conflict
    Log conflicts = vice categories in log but answered NO here — suppression signal
    """
    freak   = 0
    total_q = len(responses)
    yes_count = no_count = 0
    hesitation_yes = 0
    conflict_pts = 0
    yes_by_vice  = {}

    for r in responses:
        heat = r.get("heat", 1)
        ms   = r.get("ms_elapsed", 999)
        ans  = r.get("answer")   # True=yes, False=no
        vice = r.get("vice", "meta")

        if ans:
            yes_count += 1
            freak += heat
            yes_by_vice[vice] = yes_by_vice.get(vice, 0) + 1
            if ms > _SLOW_THRESHOLD_MS:
                hesitation_yes += 1
                conflict_pts += heat  # more weight for high-heat hesitations
        else:
            no_count += 1
            # Quick no on high-heat = consistent/genuinely doesn't do it
            # Slow no on high-heat = suppression signal
            if ms > _SLOW_THRESHOLD_MS and heat >= 2:
                conflict_pts += 1  # slight signal even on no

    max_freak     = sum(s["heat"] * 3 for s in _SCENARIOS)
    freak_pct     = round((freak / max(max_freak, 1)) * 100)
    hesitation_pct = round((hesitation_yes / max(yes_count, 1)) * 100) if yes_count else 0
    conflict_idx  = min(100, round((conflict_pts / max(total_q, 1)) * 10))

    # Compare vice log to yes_by_vice — suppression
    log_counts   = _my_vice_counts()
    suppressions = []
    for vice, log_cnt in log_counts.items():
        if log_cnt >= 2 and yes_by_vice.get(vice, 0) == 0:
            suppressions.append(vice)

    return {
        "freak_pct":      freak_pct,
        "hesitation_pct": hesitation_pct,
        "conflict_idx":   conflict_idx,
        "yes_count":      yes_count,
        "no_count":       no_count,
        "yes_by_vice":    yes_by_vice,
        "suppressions":   suppressions,
        "hesitation_yes": hesitation_yes,
        "total":          total_q,
    }


def _freak_label(pct: int) -> tuple:
    if pct < 20: return "The Innocent",  "var(--lime)"
    if pct < 40: return "The Curious",   "var(--lime)"
    if pct < 60: return "The Candid",    "var(--amber)"
    if pct < 78: return "The Unfiltered","var(--amber)"
    return "The Unhinged", "var(--magenta)"


# ─── PHASES ───────────────────────────────────────────────────────────────────

def _render_intro():
    inject_page_css()
    st.html(_SWIPE_CSS)

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Hot Takes</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">VICE<br><span style="color:var(--lime);">HOT TAKES</span></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    Swipe on scenarios. Your speed tells us what your answers won't.
  </div>
</div>
""")

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:24px 22px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">How it works</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.9;">
    You'll get 15 scenarios. Hit <strong style="color:var(--lime);">That's me</strong> or <strong style="color:var(--magenta);">Nah</strong>.
    We track how long you take on each one — hesitation on a yes means something.
    Slow on a no means something different.<br><br>
    At the end: a <strong style="color:var(--text);">Freak Score</strong>, a <strong style="color:var(--amber);">Conflict Index</strong>,
    and anywhere your answers contradict what's already in your vault.
  </div>
</div>
""")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start →", use_container_width=True, type="primary", key="ht_start"):
            deck = random.sample(_SCENARIOS, min(15, len(_SCENARIOS)))
            st.session_state.ht_deck      = deck
            st.session_state.ht_cur       = 0
            st.session_state.ht_responses = []
            st.session_state.ht_phase     = "quiz"
            st.session_state.ht_card_start = time.time()
            st.rerun()
    with col2:
        if st.session_state.get("ht_responses"):
            if st.button("See Last Result", use_container_width=True, key="ht_result_back"):
                st.session_state.ht_phase = "result"
                st.rerun()


def _render_quiz():
    inject_page_css()
    st.html(_SWIPE_CSS)

    deck    = st.session_state.ht_deck
    cur_idx = st.session_state.ht_cur

    if cur_idx >= len(deck):
        st.session_state.ht_phase = "result"
        st.rerun()
        return

    scenario  = deck[cur_idx]
    total     = len(deck)
    pct       = cur_idx / total
    heat      = scenario["heat"]
    heat_col  = _HEAT_COLOR[heat]
    heat_lbl  = _HEAT_LABEL[heat]

    # Progress
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px; text-align:right;">
  {cur_idx + 1} / {total}
</div>
<div class="ht-progress-bar">
  <div class="ht-progress-fill" style="width:{pct * 100:.0f}%"></div>
</div>
""")

    # Timer bar (JS, purely cosmetic — drains over 8s, resets on card change)
    st.html(f"""
<div id="ht-timer-track" class="ht-timer-track">
  <div id="ht-timer-fill" style="height:100%; width:100%; background:{heat_col};
       border-radius:1.5px; transition:width 0.1s linear;"></div>
</div>
<script>
(function() {{
  var el     = document.getElementById('ht-timer-fill');
  if (!el) return;
  var start  = Date.now();
  var dur    = 8000;
  function tick() {{
    var elapsed = Date.now() - start;
    var pct     = Math.max(0, 1 - elapsed / dur);
    if (el) el.style.width = (pct * 100) + '%';
    if (pct > 0) requestAnimationFrame(tick);
  }}
  requestAnimationFrame(tick);
}})();
</script>
""")

    # Card
    st.html(f"""
<div class="ht-card ht-card-heat-{heat}">
  <div class="ht-meta" style="color:{heat_col};">{heat_lbl} · {_VICE_LABELS.get(scenario['vice'], scenario['vice'])}</div>
  <p class="ht-scenario">"{scenario['text']}"</p>
</div>
""")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✓  That's me", use_container_width=True, type="primary", key=f"ht_yes_{cur_idx}"):
            _record(scenario, True)
    with col_no:
        if st.button("✗  Nah", use_container_width=True, key=f"ht_no_{cur_idx}"):
            _record(scenario, False)

    # Show previous if any
    responses = st.session_state.ht_responses
    if responses:
        last = responses[-1]
        ans_str = "That's me" if last["answer"] else "Nah"
        ms      = last["ms_elapsed"]
        spd_col = "var(--magenta)" if ms > _SLOW_THRESHOLD_MS else "var(--lime)" if ms < _FAST_THRESHOLD_MS else "var(--amber)"
        spd_lbl = "hesitated" if ms > _SLOW_THRESHOLD_MS else "fast" if ms < _FAST_THRESHOLD_MS else ""
        st.html(f"""
<div style="margin-top:16px; padding:8px 12px; border:1px solid var(--border);
            border-radius:3px; display:flex; justify-content:space-between; align-items:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted);">Last: {ans_str}</div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:{spd_col};">
    {ms / 1000:.1f}s{'  · ' + spd_lbl if spd_lbl else ''}
  </div>
</div>
""")


def _record(scenario: dict, answer: bool):
    elapsed_ms = round((time.time() - st.session_state.ht_card_start) * 1000)
    st.session_state.ht_responses.append({
        "scenario_id": scenario["id"],
        "text":        scenario["text"],
        "answer":      answer,
        "ms_elapsed":  elapsed_ms,
        "heat":        scenario["heat"],
        "vice":        scenario["vice"],
    })
    st.session_state.ht_cur += 1
    st.session_state.ht_card_start = time.time()

    if st.session_state.ht_cur >= len(st.session_state.ht_deck):
        st.session_state.ht_phase = "result"

    st.rerun()


def _render_result():
    inject_page_css()
    st.html(_SWIPE_CSS)

    responses = st.session_state.ht_responses
    if not responses:
        st.session_state.ht_phase = "intro"
        st.rerun()
        return

    r = _compute_results(responses)
    freak_name, freak_col = _freak_label(r["freak_pct"])

    st.html(f"""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">HOT TAKES · <span style="color:var(--lime);">RESULT</span></div>
</div>
""")

    # Freak Score
    st.html(f"""
<div class="ht-score-box" style="border-top:3px solid {freak_col}; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">Freak Score</div>
  <div class="ht-score-number" style="color:{freak_col};">{r['freak_pct']}</div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted); margin-bottom:8px;">/100</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; letter-spacing:2px;
              color:{freak_col};">{freak_name.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); margin-top:4px;">
    {r['yes_count']} owned · {r['no_count']} denied · out of {r['total']} scenarios
  </div>
</div>
""")

    # Stats row
    col_a, col_b = st.columns(2)
    with col_a:
        hes_col = "var(--magenta)" if r["hesitation_pct"] > 50 else "var(--amber)" if r["hesitation_pct"] > 25 else "var(--lime)"
        st.html(f"""
<div class="ht-score-box">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Hesitation Rate</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:{hes_col}; line-height:1;">
    {r['hesitation_pct']}%
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted); margin-top:4px;">
    of your YES answers took &gt;5s
  </div>
</div>
""")
    with col_b:
        conf_col = "var(--magenta)" if r["conflict_idx"] > 60 else "var(--amber)" if r["conflict_idx"] > 30 else "var(--lime)"
        st.html(f"""
<div class="ht-score-box">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Conflict Index</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:{conf_col}; line-height:1;">
    {r['conflict_idx']}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted); margin-top:4px;">
    hesitation-weighted tension score
  </div>
</div>
""")

    # Conflict bar
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px 20px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Internal Conflict Breakdown</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); margin-bottom:10px;">
    Hesitated before saying yes — knows it, but it took a moment.
  </div>
  <div class="ht-conflict-bar">
    <div class="ht-conflict-fill" style="width:{r['hesitation_pct']}%; background:var(--amber);"></div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); margin-top:10px; margin-bottom:10px;">
    Overall conflict pressure — heat-weighted.
  </div>
  <div class="ht-conflict-bar">
    <div class="ht-conflict-fill" style="width:{r['conflict_idx']}%; background:var(--magenta);"></div>
  </div>
</div>
""")

    # Vice log inconsistencies
    suppressions = r["suppressions"]
    log_counts   = _my_vice_counts()
    if log_counts and suppressions:
        sup_tags = "".join(
            f'<span class="ht-conflict-tag" style="color:var(--magenta); border-color:var(--magenta);">'
            f'{_VICE_LABELS.get(v, v).upper()}</span>'
            for v in suppressions
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--magenta); border-radius:4px;
            padding:18px 20px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:10px;">⚠ Vault Conflict</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8; margin-bottom:12px;">
    Your vice log has sessions in these categories, but you denied all related scenarios here.
    That's either a very selective memory — or the vault knows something you won't say out loud.
  </div>
  <div>{sup_tags}</div>
</div>
""")
    elif log_counts and not suppressions:
        st.html("""
<div style="background:var(--surface); border:1px solid var(--lime); border-radius:4px;
            padding:14px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:6px;">✓ Consistent</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
    Your answers align with what's in your vault. You own what you log. That's rare.
  </div>
</div>
""")

    # Hesitation breakdown — most conflicted scenario
    slow_yes = [r2 for r2 in responses if r2["answer"] and r2["ms_elapsed"] > _SLOW_THRESHOLD_MS]
    if slow_yes:
        worst = max(slow_yes, key=lambda x: x["ms_elapsed"])
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:8px;">Most Conflicted Moment</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              line-height:1.6; margin-bottom:6px; font-style:italic;">"{worst['text']}"</div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--amber);">
    {worst['ms_elapsed'] / 1000:.1f}s before you said yes
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Play Again", use_container_width=True, type="primary", key="ht_again"):
            deck = random.sample(_SCENARIOS, min(15, len(_SCENARIOS)))
            st.session_state.ht_deck       = deck
            st.session_state.ht_cur        = 0
            st.session_state.ht_responses  = []
            st.session_state.ht_phase      = "quiz"
            st.session_state.ht_card_start = time.time()
            st.rerun()
    with col2:
        if st.button("Back", use_container_width=True, key="ht_back"):
            st.session_state.ht_phase = "intro"
            st.rerun()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def vice_hot_takes_page():
    _init()
    phase = st.session_state.ht_phase
    if phase == "intro":
        _render_intro()
    elif phase == "quiz":
        _render_quiz()
    elif phase == "result":
        _render_result()
    else:
        _render_intro()
