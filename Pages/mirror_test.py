"""
Pages/mirror_test.py
The Mirror Test — rate anonymised composite habit profiles.
Projection mechanic: people reveal shame thresholds when judging others.

DB writes:
  - Each judgment → interactions table (type='mirror_judgment')
  - On completion → quiz_results (quiz_type='mirror_test') + shadow_scores.hypocrisy_idx

Shadow score surfaces on dashboard/analytics via get_shadow_score().
"""

import streamlit as st
import json
import random
from styles import inject_page_css

# ─── COMPOSITE PERSONAS ───────────────────────────────────────────────────────
# Synthetic — no real user data. Plausible patterns that mirror real vault logs.

_PERSONAS = [
    {
        "seed": "A",
        "tagline": "Drinks most weekends. Has a type.",
        "habits": {"alcohol": 3, "sex": 1},
        "detail": {
            "alcohol": "5–7 drinks on a night out, usually rum or beer. Pre-drinks alone sometimes.",
            "sex": "Active. Keeps the roster private.",
        },
        "frequency": "2–3 nights a week",
        "primary_vice": "alcohol",
    },
    {
        "seed": "B",
        "tagline": "Daily smoker. Fully functional.",
        "habits": {"weed": 4, "alcohol": 1},
        "detail": {
            "weed": "Smokes to wind down every night. Says it helps them focus during the day.",
            "alcohol": "Social only. Rarely more than two drinks.",
        },
        "frequency": "Daily weed, occasional alcohol",
        "primary_vice": "weed",
    },
    {
        "seed": "C",
        "tagline": "Doesn't drink. Does other things.",
        "habits": {"sex": 3, "other": 2},
        "detail": {
            "sex": "Multiple partners, no labels. Very intentional about it.",
            "other": "Selective use for specific experiences. Won't elaborate.",
        },
        "frequency": "Irregular but deliberate",
        "primary_vice": "sex",
    },
    {
        "seed": "D",
        "tagline": "One drink becomes five. Every time.",
        "habits": {"alcohol": 5},
        "detail": {
            "alcohol": "Started at 18. Works full time. Never misses work. Weekend sessions run long.",
        },
        "frequency": "Thursdays through Sundays",
        "primary_vice": "alcohol",
    },
    {
        "seed": "E",
        "tagline": "Weekend warrior. Keeps it separate.",
        "habits": {"alcohol": 2, "weed": 1, "sex": 1, "other": 1},
        "detail": {
            "alcohol": "Social drinker. Buys rounds.",
            "weed": "After sex sometimes. Or before. Depends.",
            "sex": "In a relationship. Has an arrangement.",
            "other": "Festival-only. Once or twice a year.",
        },
        "frequency": "Weekends only. Mostly.",
        "primary_vice": "sex",
    },
    {
        "seed": "F",
        "tagline": "High-functioning. Nobody suspects.",
        "habits": {"weed": 3, "alcohol": 1, "other": 1},
        "detail": {
            "weed": "Edibles at work events. Vapes discreetly.",
            "alcohol": "Drinks at lunch when they can get away with it.",
            "other": "Occasional stimulants for deadlines.",
        },
        "frequency": "More days than not",
        "primary_vice": "weed",
    },
    {
        "seed": "G",
        "tagline": "Just here for the sex, honestly.",
        "habits": {"sex": 4},
        "detail": {
            "sex": "Unattached. Multiple ongoing. Very clear about what they want and don't want.",
        },
        "frequency": "Several times a week",
        "primary_vice": "sex",
    },
    {
        "seed": "H",
        "tagline": "Curious experimenter. No one's business.",
        "habits": {"other": 3, "alcohol": 1, "weed": 1},
        "detail": {
            "other": "Has tried most things at least once. Careful about it.",
            "alcohol": "Rarely — prefers something that doesn't make them feel sick the next day.",
            "weed": "Helps with the aftermath.",
        },
        "frequency": "Monthly, occasionally more",
        "primary_vice": "other",
    },
    {
        "seed": "I",
        "tagline": "Says 'just one' and means fifteen.",
        "habits": {"alcohol": 4, "sex": 1},
        "detail": {
            "alcohol": "White wine in meetings. Red at dinner. 'One more' at the bar.",
            "sex": "Impulsive. Sometimes overlapping.",
        },
        "frequency": "Multiple times a week",
        "primary_vice": "alcohol",
    },
    {
        "seed": "J",
        "tagline": "Logged it. Doesn't regret it.",
        "habits": {"sex": 2, "weed": 2, "alcohol": 1, "other": 1},
        "detail": {
            "sex": "Varied. Keeps a mental log already.",
            "weed": "Morning and evening. Like coffee.",
            "alcohol": "A bottle of wine with dinner.",
            "other": "Mushrooms, once a year, deliberately.",
        },
        "frequency": "Daily on most",
        "primary_vice": "sex",
    },
]

_SUFFIXES = [str(i).zfill(3) for i in range(100, 999, 7)]
_VICE_LABELS = {"weed": "weed/smoking", "alcohol": "alcohol", "sex": "sex", "other": "other substances"}

_RATINGS = [
    {"value": 1, "label": "Totally fine"},
    {"value": 2, "label": "A little much"},
    {"value": 3, "label": "Concerning"},
    {"value": 4, "label": "That's a lot"},
    {"value": 5, "label": "I judge this"},
]

_RATING_COLORS = {1: "var(--lime)", 2: "var(--amber)", 3: "#ff8800", 4: "var(--magenta)", 5: "#ff0055"}

_CSS = """
<style>
.mt-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 26px 22px;
  margin-bottom: 12px;
}
.mt-chip {
  display: inline-block;
  font-family: 'Space Mono', monospace;
  font-size: 8px;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 2px;
  border: 1px solid var(--border);
  color: var(--muted);
  margin: 2px 2px 2px 0;
}
.mt-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--border);
  margin: 6px 0 14px;
  overflow: hidden;
}
.mt-fill { height: 100%; border-radius: 3px; }
.mt-dots {
  display: flex;
  gap: 5px;
  justify-content: center;
  margin-bottom: 18px;
}
.mt-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--border);
}
.mt-dot.done    { background: var(--lime); }
.mt-dot.current { background: var(--amber); }
</style>
"""


# ─── HANDLE ───────────────────────────────────────────────────────────────────

def _handle(seed: str) -> str:
    return f"Anonymous · {_SUFFIXES[ord(seed) % len(_SUFFIXES)]}"


# ─── STATE ────────────────────────────────────────────────────────────────────

def _init():
    for k, v in {
        "mt_phase":     "intro",
        "mt_deck":      [],
        "mt_cur":       0,
        "mt_judgments": [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─── DB ───────────────────────────────────────────────────────────────────────

def _my_vice_counts() -> dict:
    log = st.session_state.get("vice_log", [])
    counts = {}
    for e in log:
        v = e.get("vice")
        if v:
            counts[v] = counts.get(v, 0) + 1
    return counts


def _save_judgment(user_id: int, persona_seed: str, primary_vice: str,
                   habits: dict, rating: int, rating_label: str):
    try:
        import database as db
        db.save_interaction(user_id, "mirror_judgment", {
            "persona_seed":   persona_seed,
            "primary_vice":   primary_vice,
            "habits_judged":  habits,
            "rating":         rating,
            "rating_label":   rating_label,
        })
    except Exception:
        pass


def _save_result_to_db(user_id: int, hyp_pct: int, results: dict):
    """Write to quiz_results and upsert shadow_scores."""
    try:
        import database as db
        db.save_read_between_lines_result(
            user_id=user_id,
            profile_name=results.get("hyp_label", ""),
            profile_meta=f"Hypocrisy Index: {hyp_pct}",
            dim_scores={"hypocrisy": hyp_pct, "avg_judgment": results.get("avg_rating", 0)},
            recommendations=[],
            total_pct=hyp_pct,
            questions=[],
            answers=[],
        )
        # Override quiz_type — raw SQL needed since save_read_between_lines_result
        # hardcodes 'read_between_lines'. We patch via a second call.
        conn = db.create_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """UPDATE quiz_results SET quiz_type='mirror_test'
                       WHERE user_id=%s AND quiz_type='read_between_lines'
                       ORDER BY completed_at DESC LIMIT 1""",
                    (user_id,)
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()

        db.upsert_shadow_score(user_id, hypocrisy_idx=hyp_pct)
    except Exception:
        pass


# ─── HYPOCRISY SCORING ────────────────────────────────────────────────────────

def _compute(judgments: list, log_counts: dict) -> dict:
    hyp_pts = max_hyp = 0
    hyp_details = []
    vice_ratings = {}

    for j in judgments:
        vice   = j.get("primary_vice", "")
        rating = j.get("rating", 1)
        my_cnt = log_counts.get(vice, 0)
        vice_ratings.setdefault(vice, []).append(rating)

        if my_cnt > 0:
            max_hyp += 5
            if rating >= 3:
                pts = rating - 2
                hyp_pts += pts
                hyp_details.append({"vice": vice, "rating": rating,
                                     "label": j.get("rating_label", ""), "my_cnt": my_cnt})

    hyp_pct  = round((hyp_pts / max(max_hyp, 1)) * 100) if max_hyp else None
    avg_rat  = round(sum(j["rating"] for j in judgments) / max(len(judgments), 1), 1)
    vice_avg = {v: round(sum(rs) / len(rs), 1) for v, rs in vice_ratings.items()}
    harshest = max(vice_avg, key=vice_avg.get) if vice_avg else None
    self_gap = harshest if (harshest and log_counts.get(harshest, 0) > 0) else None

    labels = [
        (10,  "Clean Conscience",    "var(--lime)"),
        (30,  "Selective Awareness", "var(--amber)"),
        (55,  "Convenient Amnesia",  "#ff8800"),
        (75,  "Glass House",         "var(--magenta)"),
        (101, "Full Mirror Crack",   "#ff0055"),
    ]
    hyp_label, hyp_col = next(
        ((l, c) for ceil, l, c in labels if (hyp_pct or 0) <= ceil),
        ("Full Mirror Crack", "#ff0055")
    )

    return {
        "hyp_pct":     hyp_pct,
        "hyp_label":   hyp_label,
        "hyp_col":     hyp_col,
        "hyp_details": hyp_details,
        "avg_rating":  avg_rat,
        "vice_avg":    vice_avg,
        "harshest":    harshest,
        "self_gap":    self_gap,
        "has_log":     bool(log_counts),
    }


# ─── PHASES ───────────────────────────────────────────────────────────────────

def _render_intro():
    inject_page_css()
    st.html(_CSS)

    user    = st.session_state.get("user", {})
    user_id = user.get("id")

    # Surface previous hypocrisy score if it exists
    shadow = {}
    if user_id:
        try:
            import database as db
            shadow = db.get_shadow_score(user_id) or {}
        except Exception:
            pass

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">THE<br><span style="color:var(--magenta);">MIRROR TEST</span></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    Judge anonymous strangers. Then see yourself in the verdict.
  </div>
</div>
""")

    if shadow.get("hypocrisy_idx") is not None:
        hidx = shadow["hypocrisy_idx"]
        hcol = "var(--lime)" if hidx < 30 else "var(--amber)" if hidx < 55 else "var(--magenta)"
        st.html(f"""
<div style="background:var(--card); border:1px solid {hcol}; border-radius:4px;
            padding:16px 20px; margin-bottom:16px; display:flex;
            justify-content:space-between; align-items:center;">
  <div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-bottom:4px;">Your Hypocrisy Index</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
      From your last run. Retake to update it.
    </div>
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:{hcol};
              letter-spacing:2px; line-height:1;">{hidx}</div>
</div>
""")

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:22px 20px; margin-bottom:14px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">How it works</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.9;">
    8 anonymised habit profiles. Rate each one honestly — from <em>totally fine</em> to <em>I judge this</em>.<br><br>
    At the end we cross-reference your verdicts against what's in your own vault.
    The gap between what you condemn in strangers and what you quietly log yourself
    is your <strong style="color:var(--text);">Hypocrisy Index</strong> — saved to your profile and woven into your shadow score.
  </div>
</div>
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted);">
    All profiles are synthetic composites. No real user data is displayed.
  </div>
</div>
""")

    if st.button("Start →", use_container_width=True, type="primary", key="mt_start"):
        st.session_state.mt_deck      = random.sample(_PERSONAS, min(8, len(_PERSONAS)))
        st.session_state.mt_cur       = 0
        st.session_state.mt_judgments = []
        st.session_state.mt_phase     = "judge"
        st.rerun()


def _render_judge():
    inject_page_css()
    st.html(_CSS)

    deck    = st.session_state.mt_deck
    cur_idx = st.session_state.mt_cur
    total   = len(deck)

    if cur_idx >= total:
        st.session_state.mt_phase = "result"
        st.rerun()
        return

    persona = deck[cur_idx]

    # Dots
    dots = "".join(
        f'<div class="mt-dot {"done" if i < cur_idx else "current" if i == cur_idx else ""}"></div>'
        for i in range(total)
    )
    st.html(f"""
<div class="mt-dots">{dots}</div>
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:right; margin-bottom:12px;">
  {cur_idx + 1} / {total}
</div>
""")

    # Persona card
    chips = "".join(
        f'<span class="mt-chip">{_VICE_LABELS.get(v, v)} × {cnt}</span>'
        for v, cnt in persona["habits"].items()
    )
    detail_rows = "".join(
        f"""<div style="margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime);">{_VICE_LABELS.get(v, v)}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
              line-height:1.7; margin-top:2px;">{detail}</div>
</div>"""
        for v, detail in persona.get("detail", {}).items()
    )

    st.html(f"""
<div class="mt-card">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; letter-spacing:2px;
                  color:var(--soft);">{_handle(persona['seed'])}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
                  font-style:italic; margin-top:2px;">"{persona['tagline']}"</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                text-align:right; text-transform:uppercase; letter-spacing:1px;">
      {persona['frequency']}
    </div>
  </div>
  <div style="margin-bottom:14px;">{chips}</div>
  <div style="border-top:1px solid var(--border); padding-top:14px;">{detail_rows}</div>
</div>
""")

    # Rating prompt
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); text-align:center; margin-bottom:10px;">
  Rate this honestly
</div>
""")

    cols = st.columns(5)
    user_id = st.session_state.get("user", {}).get("id")

    for i, rating in enumerate(_RATINGS):
        with cols[i]:
            if st.button(rating["label"], key=f"mt_r_{cur_idx}_{rating['value']}",
                         use_container_width=True):
                if user_id:
                    _save_judgment(
                        user_id=user_id,
                        persona_seed=persona["seed"],
                        primary_vice=persona["primary_vice"],
                        habits=persona["habits"],
                        rating=rating["value"],
                        rating_label=rating["label"],
                    )
                st.session_state.mt_judgments.append({
                    "persona_seed":  persona["seed"],
                    "primary_vice":  persona["primary_vice"],
                    "rating":        rating["value"],
                    "rating_label":  rating["label"],
                })
                st.session_state.mt_cur += 1
                st.rerun()

    st.html("""
<div style="display:flex; justify-content:space-between; padding:0 2px; margin-top:4px;">
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--lime);">NO ISSUE</div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--magenta);">JUDGING HARD</div>
</div>
""")


def _render_result():
    inject_page_css()
    st.html(_CSS)

    judgments  = st.session_state.mt_judgments
    log_counts = _my_vice_counts()
    user       = st.session_state.get("user", {})
    user_id    = user.get("id")

    if not judgments:
        st.session_state.mt_phase = "intro"
        st.rerun()
        return

    r = _compute(judgments, log_counts)

    # Save to DB on first render
    if not st.session_state.get("mt_saved") and user_id and r["hyp_pct"] is not None:
        _save_result_to_db(user_id, r["hyp_pct"], r)
        st.session_state.mt_saved = True

    hyp_col   = r["hyp_col"]
    hyp_label = r["hyp_label"]
    hyp_pct   = r["hyp_pct"]

    st.html(f"""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">THE MIRROR · <span style="color:var(--magenta);">RESULT</span></div>
</div>
""")

    # Main score
    if r["has_log"] and hyp_pct is not None:
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {hyp_col}; border-radius:4px;
            padding:28px; text-align:center; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Hypocrisy Index</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:80px; color:{hyp_col};
              letter-spacing:2px; line-height:1;">{hyp_pct}</div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted); margin-bottom:8px;">/100</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:26px; color:{hyp_col};
              letter-spacing:2px;">{hyp_label.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted); margin-top:6px;">
    Saved to your profile · Feeds your shadow score
  </div>
</div>
""")
        st.html(f"""
<div class="mt-bar">
  <div class="mt-fill" style="width:{hyp_pct}%; background:{hyp_col};"></div>
</div>
""")
    else:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:28px; text-align:center; margin-bottom:12px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--muted);">NO VAULT DATA</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:8px;">
    Log some sessions to unlock your personal hypocrisy score.
    Right now you're judging into the void.
  </div>
</div>
""")

    # Stats row
    col_a, col_b = st.columns(2)
    with col_a:
        avg     = r["avg_rating"]
        avg_col = "var(--lime)" if avg < 2 else "var(--amber)" if avg < 3.5 else "var(--magenta)"
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:16px; text-align:center; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Avg Judgment</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:44px; color:{avg_col}; line-height:1;">
    {avg}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);">/5 severity</div>
</div>
""")
    with col_b:
        hv      = r.get("harshest")
        hv_lbl  = _VICE_LABELS.get(hv, hv or "—") if hv else "—"
        hv_avg  = r["vice_avg"].get(hv, 0) if hv else 0
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:16px; text-align:center; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Harshest On</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--magenta);
              letter-spacing:2px; line-height:1.2; margin:6px 0;">{hv_lbl.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);">avg {hv_avg}/5</div>
</div>
""")

    # Contradiction callouts
    hyp_details = r.get("hyp_details", [])
    if hyp_details:
        rows_html = ""
        for d in hyp_details:
            lv = _VICE_LABELS.get(d["vice"], d["vice"])
            rows_html += f"""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:10px 0; border-bottom:1px solid var(--border);">
  <div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
                text-transform:uppercase; color:var(--lime);">{lv}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:2px;">
      You said "{d['label']}" — your vault has {d['my_cnt']} session{'s' if d['my_cnt'] != 1 else ''}
    </div>
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:30px; color:var(--magenta);
              flex-shrink:0; margin-left:12px;">{d['rating']}/5</div>
</div>
"""
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--magenta); border-radius:4px;
            padding:18px 20px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:14px;">
    Where You're Judging Yourself Without Knowing It
  </div>
  {rows_html}
</div>
""")

    # Self-gap
    if r.get("self_gap") and r["has_log"]:
        gap_lbl = _VICE_LABELS.get(r["self_gap"], r["self_gap"])
        my_cnt  = log_counts.get(r["self_gap"], 0)
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:8px;">The Gap</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You were hardest on <strong style="color:var(--text);">{gap_lbl}</strong>.
    Your vault shows {my_cnt} session{'s' if my_cnt != 1 else ''} of the same.
    That gap is exactly what this test was built to find.
  </div>
</div>
""")

    if not hyp_details and r["has_log"]:
        st.html("""
<div style="background:var(--surface); border:1px solid var(--lime); border-radius:4px;
            padding:16px 18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:6px;">Consistent</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    You didn't judge anything harshly that you do yourself.
    Either you're unusually self-aware, or you were generous to everyone.
  </div>
</div>
""")

    # Vice-by-vice breakdown
    if r["vice_avg"]:
        st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px; margin-top:4px;">Judgment By Vice</div>""")
        for vice, avg in sorted(r["vice_avg"].items(), key=lambda x: -x[1]):
            bar_pct = round((avg / 5) * 100)
            bar_col = "var(--lime)" if avg < 2 else "var(--amber)" if avg < 3.5 else "var(--magenta)"
            label   = _VICE_LABELS.get(vice, vice)
            st.html(f"""
<div style="margin-bottom:11px;">
  <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft);">{label}</span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:{bar_col};">{avg}/5</span>
  </div>
  <div class="mt-bar">
    <div class="mt-fill" style="width:{bar_pct}%; background:{bar_col};"></div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Judge Again", use_container_width=True, type="primary", key="mt_again"):
            st.session_state.mt_deck      = random.sample(_PERSONAS, min(8, len(_PERSONAS)))
            st.session_state.mt_cur       = 0
            st.session_state.mt_judgments = []
            st.session_state.mt_saved     = False
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
