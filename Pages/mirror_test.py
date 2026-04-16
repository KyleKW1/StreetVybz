"""
Pages/mirror_test.py
The Mirror Test — rate anonymous strangers' logged habits.
Classic projection mechanic. People reveal their own shame thresholds
most clearly when judging others.

Hypocrisy Index = (what you judge harshly) vs (what you log yourself).
The bigger the gap, the higher the hypocrisy.
"""

import streamlit as st
import json
import random
import math
from styles import inject_page_css

_MIRROR_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d;
  --border:#2a2a35; --lime:#c6ff00; --magenta:#ff2d78;
  --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}

.mt-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 28px 24px;
  margin-bottom: 12px;
}

.mt-profile-chip {
  display: inline-block;
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 2px;
  border: 1px solid var(--border);
  color: var(--muted);
  margin: 2px;
}

.mt-judge-label {
  font-family: 'Space Mono', monospace;
  font-size: 9px;
  letter-spacing: 3px;
  text-transform: uppercase;
  text-align: center;
  margin-bottom: 10px;
}

.mt-rating-bar {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin: 10px 0;
}

.mt-verdict-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 18px 20px;
  margin-bottom: 10px;
  text-align: center;
}

.mt-hyp-bar {
  height: 8px;
  border-radius: 4px;
  background: var(--border);
  margin: 8px 0;
  overflow: hidden;
}

.mt-hyp-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.mt-progress-dots {
  display: flex;
  gap: 4px;
  justify-content: center;
  margin-bottom: 20px;
}

.mt-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border);
  transition: background 0.2s;
}

.mt-dot.done    { background: var(--lime); }
.mt-dot.current { background: var(--amber); }
</style>
"""

# ─── ANONYMOUS PERSONA GENERATOR ──────────────────────────────────────────────
# These are synthetic composites — no real user data, just plausible patterns
# that mirror what a real user might have in their vice log.

_HANDLE_PREFIXES = [
    "Anonymous", "User", "Vault", "Guest", "Profile",
]
_HANDLE_SUFFIXES = [str(i).zfill(3) for i in range(100, 999, 7)]

_PERSONAS = [
    {
        "handle_seed": "A",
        "tagline": "Drinks most weekends. Has a type.",
        "habits": ["alcohol", "alcohol", "alcohol", "sex"],
        "details": {
            "alcohol": "5-7 drinks on a night out, usually rum or beer. Pre-drinks alone sometimes.",
            "sex": "Active. Keeps their roster private.",
        },
        "frequency": "2–3 nights a week",
        "vice_vice": "alcohol",
    },
    {
        "handle_seed": "B",
        "tagline": "Daily smoker. Functional.",
        "habits": ["weed", "weed", "weed", "weed", "alcohol"],
        "details": {
            "weed": "Smokes to wind down every night. Says it helps them focus.",
            "alcohol": "Social only, rarely more than two drinks.",
        },
        "frequency": "Daily weed, occasional alcohol",
        "vice_vice": "weed",
    },
    {
        "handle_seed": "C",
        "tagline": "Doesn't drink. Does other things.",
        "habits": ["sex", "sex", "other", "other"],
        "details": {
            "sex": "Multiple partners, no labels. Very intentional about it.",
            "other": "Selective use of substances for specific experiences. Won't say more.",
        },
        "frequency": "Irregular but deliberate",
        "vice_vice": "sex",
    },
    {
        "handle_seed": "D",
        "tagline": "One drink becomes five. Every time.",
        "habits": ["alcohol", "alcohol", "alcohol", "alcohol", "alcohol"],
        "details": {
            "alcohol": "Started at 18. Works full-time. Never misses work. Weekend sessions run long.",
        },
        "frequency": "Thursdays through Sundays",
        "vice_vice": "alcohol",
    },
    {
        "handle_seed": "E",
        "tagline": "Weekend warrior. Keeps it separate.",
        "habits": ["alcohol", "weed", "sex", "other"],
        "details": {
            "alcohol": "Social drinker. Buys rounds.",
            "weed": "After sex sometimes. Or before. Depends.",
            "sex": "In a relationship. Has an arrangement.",
            "other": "Festival-only. One or two times a year.",
        },
        "frequency": "Weekends only. Mostly.",
        "vice_vice": "sex",
    },
    {
        "handle_seed": "F",
        "tagline": "High-functioning. Nobody suspects.",
        "habits": ["weed", "weed", "alcohol", "other"],
        "details": {
            "weed": "Edibles at work events. Vapes discreetly.",
            "alcohol": "Drinks at lunch when they can.",
            "other": "Occasional stimulants for deadlines.",
        },
        "frequency": "More days than not",
        "vice_vice": "weed",
    },
    {
        "handle_seed": "G",
        "tagline": "Just here for the sex, honestly.",
        "habits": ["sex", "sex", "sex", "sex"],
        "details": {
            "sex": "Unattached. Multiple ongoing. Very clear about what they want.",
        },
        "frequency": "Several times a week",
        "vice_vice": "sex",
    },
    {
        "handle_seed": "H",
        "tagline": "Curious experimenter. No one's business.",
        "habits": ["other", "other", "alcohol", "weed"],
        "details": {
            "other": "Has tried most things at least once. Careful about it.",
            "alcohol": "Rarely. Prefers something that doesn't make them feel sick.",
            "weed": "Helps with the aftermath.",
        },
        "frequency": "Monthly, occasionally more",
        "vice_vice": "other",
    },
    {
        "handle_seed": "I",
        "tagline": "The one who says 'just one' and means fifteen.",
        "habits": ["alcohol", "alcohol", "sex", "alcohol"],
        "details": {
            "alcohol": "White wine in meetings. Red wine at dinner. 'One' at the bar.",
            "sex": "Impulsive. Sometimes overlapping.",
        },
        "frequency": "Multiple times a week",
        "vice_vice": "alcohol",
    },
    {
        "handle_seed": "J",
        "tagline": "Logged it. Doesn't regret it.",
        "habits": ["sex", "weed", "alcohol", "other"],
        "details": {
            "sex": "Varied. Keeps a mental log already, figured the app might as well too.",
            "weed": "Morning and evening. Like coffee.",
            "alcohol": "A bottle of wine with dinner.",
            "other": "Mushrooms, once a year, deliberately.",
        },
        "frequency": "Daily on most",
        "vice_vice": "sex",
    },
]

# ─── JUDGMENT SCALE ───────────────────────────────────────────────────────────

_RATINGS = [
    {"value": 1, "label": "Totally fine",    "color": "var(--lime)"},
    {"value": 2, "label": "A little much",   "color": "var(--amber)"},
    {"value": 3, "label": "Concerning",      "color": "#ff8800"},
    {"value": 4, "label": "That's a lot",    "color": "var(--magenta)"},
    {"value": 5, "label": "I judge this",    "color": "#ff0055"},
]

# ─── STATE ────────────────────────────────────────────────────────────────────

def _init():
    defaults = {
        "mt_phase":     "intro",
        "mt_deck":      [],
        "mt_cur":       0,
        "mt_judgments": [],   # [{persona_seed, vice_vice, rating, value}]
        "mt_error":     "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset():
    for k in list(st.session_state.keys()):
        if k.startswith("mt_"):
            del st.session_state[k]
    _init()
    st.rerun()


# ─── HANDLE GENERATION ────────────────────────────────────────────────────────

def _handle(seed: str) -> str:
    idx = ord(seed) % len(_HANDLE_SUFFIXES)
    return f"Anonymous · {_HANDLE_SUFFIXES[idx]}"


# ─── VICE LOG ─────────────────────────────────────────────────────────────────

def _my_vice_counts() -> dict:
    log = st.session_state.get("vice_log", [])
    counts = {}
    for e in log:
        v = e.get("vice", "")
        if v:
            counts[v] = counts.get(v, 0) + 1
    return counts

_VICE_LABELS = {
    "weed":    "weed/smoking",
    "alcohol": "alcohol",
    "sex":     "sex",
    "other":   "other substances",
}


# ─── HYPOCRISY SCORING ────────────────────────────────────────────────────────

def _compute_hypocrisy(judgments: list, log_counts: dict) -> dict:
    """
    For each judgment: if the person judged a vice harshly (rating >= 3)
    but has that same vice logged themselves, that's a hypocrisy point.

    Hypocrisy Index = (hypocrisy points / possible hypocrisy points) * 100
    """
    hyp_points   = 0
    max_hyp      = 0
    hyp_details  = []   # {vice, their_rating, my_count}

    for j in judgments:
        vice    = j.get("vice_vice", "")
        rating  = j.get("rating", 1)
        my_cnt  = log_counts.get(vice, 0)

        # Only counts as potential hypocrisy if I have this vice logged
        if my_cnt > 0:
            max_hyp += 5   # max possible per question
            if rating >= 3:
                pts = rating - 2   # 3→1pt, 4→2pt, 5→3pt
                hyp_points += pts
                hyp_details.append({
                    "vice":    vice,
                    "rating":  rating,
                    "my_cnt":  my_cnt,
                    "label":   _RATINGS[rating - 1]["label"],
                })

    hyp_pct = round((hyp_points / max(max_hyp, 1)) * 100) if max_hyp else None

    # Average judgment severity
    avg_rating = round(sum(j["rating"] for j in judgments) / max(len(judgments), 1), 1)

    # Most judged vice
    vice_ratings = {}
    for j in judgments:
        v = j.get("vice_vice", "")
        if v not in vice_ratings:
            vice_ratings[v] = []
        vice_ratings[v].append(j["rating"])
    vice_avg = {v: sum(rs) / len(rs) for v, rs in vice_ratings.items()}
    harshest_vice = max(vice_avg, key=vice_avg.get) if vice_avg else None

    # Self-judgment gap: do I log the harshest-judged vice?
    self_gap = None
    if harshest_vice and log_counts.get(harshest_vice, 0) > 0:
        self_gap = harshest_vice

    return {
        "hyp_pct":      hyp_pct,
        "hyp_details":  hyp_details,
        "avg_rating":   avg_rating,
        "harshest_vice": harshest_vice,
        "self_gap":      self_gap,
        "has_log":       bool(log_counts),
        "vice_avg":      vice_avg,
    }


def _hyp_label(pct: int) -> tuple:
    if pct is None: return "No data", "var(--muted)"
    if pct < 10:  return "Clean Conscience", "var(--lime)"
    if pct < 30:  return "Selective Awareness", "var(--amber)"
    if pct < 55:  return "Convenient Amnesia", "#ff8800"
    if pct < 75:  return "Glass House",  "var(--magenta)"
    return "Full Mirror Crack", "#ff0055"


# ─── PHASES ───────────────────────────────────────────────────────────────────

def _render_intro():
    inject_page_css()
    st.html(_MIRROR_CSS)

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · The Mirror</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">THE<br><span style="color:var(--magenta);">MIRROR TEST</span></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    Judge anonymous strangers. Then see how you compare.
  </div>
</div>
""")

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:24px 22px; margin-bottom:14px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">How it works</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.9;">
    You'll see anonymised profiles of real-ish vice patterns.
    Rate each one from <strong style="color:var(--lime);">totally fine</strong> to
    <strong style="color:var(--magenta);">I judge this</strong>.<br><br>
    At the end, we compare your judgments to what's already in your own vault.
    The gap between what you call out in others and what you quietly log yourself
    is the <strong style="color:var(--text);">Hypocrisy Index</strong> — and it's uncomfortably accurate.
  </div>
</div>
""")

    st.html("""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:12px 16px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted);">
    All profiles are anonymised composites. No real usernames or identifiable data are shown.
  </div>
</div>
""")

    if st.button("Start Judging →", use_container_width=True, type="primary", key="mt_start"):
        deck = random.sample(_PERSONAS, min(8, len(_PERSONAS)))
        st.session_state.mt_deck      = deck
        st.session_state.mt_cur       = 0
        st.session_state.mt_judgments = []
        st.session_state.mt_phase     = "judge"
        st.rerun()

    if st.session_state.get("mt_judgments"):
        st.html("<div style='height:8px'></div>")
        if st.button("See Last Result", use_container_width=True, key="mt_result_back"):
            st.session_state.mt_phase = "result"
            st.rerun()


def _render_judge():
    inject_page_css()
    st.html(_MIRROR_CSS)

    deck    = st.session_state.mt_deck
    cur_idx = st.session_state.mt_cur

    if cur_idx >= len(deck):
        st.session_state.mt_phase = "result"
        st.rerun()
        return

    persona = deck[cur_idx]
    total   = len(deck)

    # Progress dots
    dots_html = "".join(
        f'<div class="mt-dot {"done" if i < cur_idx else "current" if i == cur_idx else ""}"></div>'
        for i in range(total)
    )
    st.html(f'<div class="mt-progress-dots">{dots_html}</div>')

    # Header
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); text-align:right; margin-bottom:12px;">
  profile {cur_idx + 1} / {total}
</div>
""")

    # Persona card
    habit_counts = {}
    for h in persona["habits"]:
        habit_counts[h] = habit_counts.get(h, 0) + 1
    habit_chips = "".join(
        f'<span class="mt-profile-chip">{_VICE_LABELS.get(v, v)} × {c}</span>'
        for v, c in habit_counts.items()
    )

    st.html(f"""
<div class="mt-card" style="border-top:3px solid var(--border);">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; letter-spacing:2px;
                  color:var(--soft);">{_handle(persona['handle_seed'])}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);
                  font-style:italic; margin-top:2px;">"{persona['tagline']}"</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                text-transform:uppercase; color:var(--muted); text-align:right;">
      {persona['frequency']}
    </div>
  </div>
  <div style="margin-bottom:16px;">{habit_chips}</div>
  <div style="border-top:1px solid var(--border); padding-top:14px;">
""")

    for vice, detail in persona.get("details", {}).items():
        st.html(f"""
  <div style="margin-bottom:8px;">
    <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                 text-transform:uppercase; color:var(--lime);">{_VICE_LABELS.get(vice, vice)}</span>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
                line-height:1.7; margin-top:2px;">{detail}</div>
  </div>
""")

    st.html("</div></div>")

    # Rating prompt
    st.html("""
<div class="mt-judge-label" style="color:var(--muted); margin-top:4px;">
  Rate this honestly
</div>
""")

    # Rating buttons
    cols = st.columns(5)
    for i, rating in enumerate(_RATINGS):
        with cols[i]:
            if st.button(
                rating["label"],
                key=f"mt_rate_{cur_idx}_{rating['value']}",
                use_container_width=True,
            ):
                st.session_state.mt_judgments.append({
                    "persona_seed": persona["handle_seed"],
                    "vice_vice":    persona["vice_vice"],
                    "rating":       rating["value"],
                    "rating_label": rating["label"],
                    "habits":       list(habit_counts.keys()),
                })
                st.session_state.mt_cur += 1
                st.rerun()

    # Rating legend
    st.html("""
<div style="display:flex; justify-content:space-between; padding:0 2px; margin-top:4px;">
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--lime);">NO ISSUE</div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--magenta);">JUDGING HARD</div>
</div>
""")

    # Show previous judgment
    if st.session_state.mt_judgments:
        last = st.session_state.mt_judgments[-1]
        lbl  = last.get("rating_label", "")
        st.html(f"""
<div style="margin-top:16px; padding:8px 12px; border:1px solid var(--border);
            border-radius:3px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted);">Last verdict: {lbl}</div>
</div>
""")


def _render_result():
    inject_page_css()
    st.html(_MIRROR_CSS)

    judgments  = st.session_state.mt_judgments
    log_counts = _my_vice_counts()

    if not judgments:
        _reset()
        return

    h = _compute_hypocrisy(judgments, log_counts)
    hyp_name, hyp_col = _hyp_label(h["hyp_pct"])

    st.html(f"""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">THE MIRROR · <span style="color:var(--magenta);">RESULT</span></div>
</div>
""")

    # Hypocrisy Index — main display
    if h["has_log"] and h["hyp_pct"] is not None:
        st.html(f"""
<div class="mt-verdict-box" style="border-top:3px solid {hyp_col}; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Hypocrisy Index</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:72px; letter-spacing:2px;
              line-height:1; color:{hyp_col};">{h['hyp_pct']}</div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted); margin-bottom:8px;">/100</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:24px; letter-spacing:2px;
              color:{hyp_col};">{hyp_name.upper()}</div>
</div>
""")

        # Bar
        st.html(f"""
<div class="mt-hyp-bar">
  <div class="mt-hyp-fill" style="width:{h['hyp_pct']}%; background:{hyp_col};"></div>
</div>
""")
    else:
        st.html("""
<div class="mt-verdict-box" style="margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Hypocrisy Index</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; letter-spacing:2px;
              color:var(--muted);">NO DATA</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:8px;">
    Log some sessions to unlock your personal hypocrisy score.
    Right now you're just judging into the void.
  </div>
</div>
""")

    # Stats: avg judgment + harshest vice
    col_a, col_b = st.columns(2)
    with col_a:
        avg = h["avg_rating"]
        avg_col = "var(--lime)" if avg < 2 else "var(--amber)" if avg < 3.5 else "var(--magenta)"
        st.html(f"""
<div class="mt-verdict-box">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Avg Judgment</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:44px; color:{avg_col}; line-height:1;">
    {avg:.1f}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);">/5 severity</div>
</div>
""")
    with col_b:
        hv = h.get("harshest_vice")
        hv_label = _VICE_LABELS.get(hv, hv or "—") if hv else "—"
        hv_avg   = round(h["vice_avg"].get(hv, 0), 1) if hv else "—"
        st.html(f"""
<div class="mt-verdict-box">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Harshest On</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--magenta);
              letter-spacing:2px; line-height:1.2; margin:8px 0;">
    {hv_label.upper()}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);">avg {hv_avg}/5</div>
</div>
""")

    # Hypocrisy details — the good stuff
    hyp_details = h.get("hyp_details", [])
    if hyp_details:
        items_html = ""
        for d in hyp_details:
            lv = _VICE_LABELS.get(d["vice"], d["vice"])
            items_html += f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:10px 0; border-bottom:1px solid var(--border);">
  <div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
                text-transform:uppercase; color:var(--lime);">{lv}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:2px;">
      You said "{d['label']}" — you've logged this {d['my_cnt']} time{'s' if d['my_cnt'] != 1 else ''}
    </div>
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--magenta);">
    {d['rating']}/5
  </div>
</div>
"""
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--magenta); border-radius:4px;
            padding:18px 20px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:14px;">
    ⚠ Where You're Judging Yourself Without Knowing It
  </div>
  {items_html}
</div>
""")

    # Self-gap callout
    self_gap = h.get("self_gap")
    if self_gap and h["has_log"]:
        gap_label = _VICE_LABELS.get(self_gap, self_gap)
        my_cnt    = log_counts.get(self_gap, 0)
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:8px;">The Gap</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You were hardest on <strong style="color:var(--text);">{gap_label}</strong>.
    Your vault shows {my_cnt} session{'s' if my_cnt != 1 else ''} of the same.
    That gap between judgment and behaviour is exactly what this test was built to find.
  </div>
</div>
""")

    # If totally consistent
    if not hyp_details and h["has_log"]:
        st.html("""
<div style="background:var(--surface); border:1px solid var(--lime); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:8px;">✓ Consistent</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You didn't judge anything harshly that you do yourself. Either you're unusually self-aware,
    or you were generous to everyone. Either way — no contradictions found.
  </div>
</div>
""")

    # Judgment breakdown by vice
    if h["vice_avg"]:
        st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px; margin-top:4px;">Your Judgment By Vice</div>""")
        for vice, avg in sorted(h["vice_avg"].items(), key=lambda x: -x[1]):
            bar_pct = round((avg / 5) * 100)
            bar_col = "var(--lime)" if avg < 2 else "var(--amber)" if avg < 3.5 else "var(--magenta)"
            label   = _VICE_LABELS.get(vice, vice)
            st.html(f"""
<div style="margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft);">{label}</span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:{bar_col};">{avg:.1f}/5</span>
  </div>
  <div class="mt-hyp-bar">
    <div class="mt-hyp-fill" style="width:{bar_pct}%; background:{bar_col};"></div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Judge Again", use_container_width=True, type="primary", key="mt_again"):
            deck = random.sample(_PERSONAS, min(8, len(_PERSONAS)))
            st.session_state.mt_deck      = deck
            st.session_state.mt_cur       = 0
            st.session_state.mt_judgments = []
            st.session_state.mt_phase     = "judge"
            st.rerun()
    with col2:
        if st.button("Back", use_container_width=True, key="mt_back"):
            st.session_state.mt_phase = "intro"
            st.rerun()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def mirror_test_page():
    _init()
    phase = st.session_state.mt_phase
    if phase == "intro":
        _render_intro()
    elif phase == "judge":
        _render_judge()
    elif phase == "result":
        _render_result()
    else:
        _render_intro()
