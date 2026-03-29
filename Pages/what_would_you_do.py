"""
Pages/what_would_you_do.py
Kink & desire profile quiz — 10 indirect scenario questions, no Reddit needed.
Profiles across 6 dimensions and surfaces matched kink tags.
"""

import streamlit as st
import json

# ─── QUESTIONS ────────────────────────────────────────────────────────────────

QUESTIONS = [
    {
        "tag": "Power play",
        "text": "You're planning a surprise for someone you're deeply attracted to. Which direction do you take it?",
        "dims": {"control": [0, 1, 2, 3], "sensory": [0, 0, 1, 1]},
        "opts": [
            "A thoughtful note and their favourite meal — I like making people feel cared for.",
            "Something they've mentioned wanting but never asked for — I pay attention.",
            "Blindfold them, lead them somewhere unexpected — the not-knowing is the point.",
            "I tell them exactly what's going to happen, step by step, before it does.",
        ],
    },
    {
        "tag": "Atmosphere",
        "text": "Which setting makes you feel most… switched on?",
        "dims": {"exhib": [0, 1, 2, 3], "sensory": [1, 0, 2, 0]},
        "opts": [
            "Completely private. Just us, no possibility of interruption.",
            "Somewhere semi-public — a balcony, a quiet corner — where getting caught is theoretically possible.",
            "Honestly? An audience wouldn't bother me. The attention is part of it.",
            "Sensory overload: music, low light, textures — I want every sense involved.",
        ],
    },
    {
        "tag": "Fantasy check",
        "text": "A movie scene that unexpectedly does something for you usually involves:",
        "dims": {"control": [0, 2, 1, 3], "dynamic": [0, 1, 2, 3]},
        "opts": [
            "Two people completely equal — no one leads, no one follows, just chemistry.",
            "Someone taking charge in a way that's confident but not aggressive.",
            "Roleplay or a character dynamic — the 'character' part matters as much as the act.",
            "Clear power — one person completely in control, the other completely surrendered.",
        ],
    },
    {
        "tag": "Comfort zone",
        "text": "You're with someone you trust completely. They suggest something new. Your gut says:",
        "dims": {"openness": [0, 1, 2, 3], "control": [1, 0, 2, 0]},
        "opts": [
            "Hard pass — I know what I like and I'm not experimenting tonight.",
            "Tell me more first. I need to understand it before I decide.",
            "Curious. I'll try most things once if I'm comfortable with the person.",
            "Yes before they finish the sentence. That's what trust is for.",
        ],
    },
    {
        "tag": "The language of want",
        "text": "How do you prefer desire to be communicated?",
        "dims": {"verbal": [0, 3, 1, 2], "control": [0, 1, 2, 1]},
        "opts": [
            "Actions only — words kill the mood for me.",
            "Tell me exactly. Specific, explicit, no ambiguity.",
            "Whispered, close — tone matters more than content.",
            "I want to be asked permission. The asking is the thing.",
        ],
    },
    {
        "tag": "Slow burn or fast fire",
        "text": "Your ideal pace from first contact to peak intensity is:",
        "dims": {"sensory": [3, 1, 0, 2], "dynamic": [1, 0, 2, 1]},
        "opts": [
            "Agonisingly slow. I want anticipation that feels almost unbearable.",
            "Gradual. Let it build naturally without forcing it.",
            "Fast. The urgency is the turn-on.",
            "Unpredictable — slow then suddenly fast — I like losing the rhythm.",
        ],
    },
    {
        "tag": "Imagination",
        "text": "If you were writing the scenario in your head right now, the other person is:",
        "dims": {"dynamic": [0, 1, 3, 2], "control": [0, 2, 3, 1]},
        "opts": [
            "Completely equal — we're discovering it together.",
            "Slightly unpredictable — I don't know exactly what they'll do next.",
            "Dominant and deliberate — they know exactly what they want from me.",
            "Waiting for my lead — I decide everything.",
        ],
    },
    {
        "tag": "Sensation",
        "text": "Which physical element features most in what you find genuinely exciting?",
        "dims": {"sensory": [3, 2, 1, 0], "control": [1, 2, 0, 3]},
        "opts": [
            "Touch and texture — what things feel like against skin.",
            "Restraint — not necessarily literal, but the feeling of being held.",
            "Eye contact and presence — being completely seen.",
            "Pain-adjacent sensation — that line where pleasure gets complicated.",
        ],
    },
    {
        "tag": "The reveal",
        "text": "When it comes to being truly known by someone intimately, you:",
        "dims": {"openness": [0, 1, 2, 3], "verbal": [1, 0, 2, 3]},
        "opts": [
            "Keep a lot private — some things are just mine.",
            "Share selectively, over time, when trust is solid.",
            "Open book — I'd rather someone know everything and react honestly.",
            "Want to be figured out. I like someone reading me without being told.",
        ],
    },
    {
        "tag": "After everything",
        "text": "What matters most to you once the intensity fades?",
        "dims": {"dynamic": [0, 1, 2, 3], "openness": [2, 1, 0, 3]},
        "opts": [
            "Quiet — no processing, no talking, just being present.",
            "Closeness — physical, warm, uncomplicated.",
            "Conversation — I want to talk about what just happened.",
            "Honesty — even if something was unexpected or complicated, I want it said.",
        ],
    },
]

# ─── DIMENSIONS ───────────────────────────────────────────────────────────────

DIMS = {
    "control":  {"label": "Power & control",     "color": "#D85A30"},
    "sensory":  {"label": "Sensory depth",        "color": "#ff2d78"},
    "exhib":    {"label": "Exhibitionism",         "color": "#ffb300"},
    "dynamic":  {"label": "Role dynamics",         "color": "#7F77DD"},
    "openness": {"label": "Sexual openness",       "color": "#00e5ff"},
    "verbal":   {"label": "Verbal intensity",      "color": "#c6ff00"},
}

# ─── KINK TAGS ────────────────────────────────────────────────────────────────

KINK_MAP = [
    {"label": "Dominance / submission", "dims": {"control": 0.6, "dynamic": 0.4}, "threshold": 0.55},
    {"label": "Sensory play",           "dims": {"sensory": 0.8, "control": 0.2}, "threshold": 0.50},
    {"label": "Roleplay",               "dims": {"dynamic": 0.7, "verbal": 0.3},  "threshold": 0.45},
    {"label": "Exhibitionism",          "dims": {"exhib": 1.0},                   "threshold": 0.40},
    {"label": "Restraint",              "dims": {"control": 0.5, "sensory": 0.5}, "threshold": 0.50},
    {"label": "Verbal intensity",       "dims": {"verbal": 0.8, "dynamic": 0.2},  "threshold": 0.50},
    {"label": "Slow anticipation",      "dims": {"sensory": 0.4, "openness": 0.6},"threshold": 0.50},
    {"label": "Power exchange",         "dims": {"control": 0.7, "dynamic": 0.3}, "threshold": 0.60},
    {"label": "Emotional intimacy",     "dims": {"openness": 0.7, "verbal": 0.3}, "threshold": 0.45},
    {"label": "Unpredictability",       "dims": {"openness": 0.5, "dynamic": 0.5},"threshold": 0.50},
]

# ─── RESULT PROFILES ─────────────────────────────────────────────────────────

PROFILES = [
    {
        "range": [0, 20],
        "icon": "🌙",
        "name": "The Intimate Minimalist",
        "meta": "Real > elaborate.",
        "desc": "You don't need complexity. What you want is genuine, simple, and deeply felt. The fewer variables the better — you find more in a moment of authentic closeness than in any elaborate setup.",
    },
    {
        "range": [21, 42],
        "icon": "🌿",
        "name": "The Calibrated Explorer",
        "meta": "Trust unlocks everything.",
        "desc": "You know what you like but you're still curious about the edges. You don't chase novelty for its own sake — but with the right person and enough trust, you'll go further than most people realise.",
    },
    {
        "range": [43, 62],
        "icon": "🔺",
        "name": "The Dynamic Architect",
        "meta": "Power and pace are the whole thing.",
        "desc": "Structure, dynamic, and control matter to you enormously. You're drawn to clear roles — whether you're the one creating them or surrendering to them. The setup is part of the pleasure.",
    },
    {
        "range": [63, 999],
        "icon": "⚡",
        "name": "The Full-Spectrum Player",
        "meta": "You want all of it.",
        "desc": "You're not afraid of complexity. Sensation, dynamic, honesty, and edge — you want the full range. You've probably thought about this more than most people have, and you know exactly what that means.",
    },
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _dim_maxes() -> dict:
    mx = {d: 0 for d in DIMS}
    for q in QUESTIONS:
        for d, vals in q["dims"].items():
            mx[d] += max(vals)
    return mx

DIM_MAX = _dim_maxes()


def _compute_scores(answers: list) -> dict:
    sc = {d: 0 for d in DIMS}
    for qi, ai in enumerate(answers):
        if ai is None:
            continue
        for d, vals in QUESTIONS[qi]["dims"].items():
            sc[d] += vals[ai]
    return sc


def _total_pct(scores: dict) -> int:
    tot = sum(scores.values())
    mx  = sum(DIM_MAX.values())
    return round((tot / mx) * 100) if mx else 0


def _dim_pct(scores: dict, d: str) -> int:
    return round((scores[d] / DIM_MAX[d]) * 100) if DIM_MAX[d] else 0


def _kink_score(scores: dict, k: dict) -> float:
    s = 0.0
    for d, w in k["dims"].items():
        s += (scores[d] / DIM_MAX[d]) * w if DIM_MAX[d] else 0
    return s


def _active_kinks(scores: dict) -> list:
    return [k["label"] for k in KINK_MAP if _kink_score(scores, k) >= k["threshold"]]

# ─── CSS ─────────────────────────────────────────────────────────────────────

def inject_css():
    st.html("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d; --border:#2a2a35;
  --lime:#c6ff00; --magenta:#ff2d78; --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}
.stApp { background:var(--bg) !important; }
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container { padding-top:0.5rem !important; max-width:720px !important; }
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
  background:var(--card) !important; color:var(--text) !important;
  border:1px solid var(--border) !important; border-radius:3px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1.5px !important; text-transform:uppercase !important;
  padding:10px 16px !important; transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover {
  background:#222230 !important; border-color:var(--magenta) !important;
  color:var(--magenta) !important; box-shadow:none !important; transform:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--magenta) !important; color:#fff !important;
  border-color:var(--magenta) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#ff5590 !important; box-shadow:0 0 20px rgba(255,45,120,0.25) !important;
}
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"][disabled] {
  background:var(--border) !important; color:var(--muted) !important;
  border-color:var(--border) !important; box-shadow:none !important;
}
.stProgress > div > div > div { background:var(--magenta) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")

# ─── STATE ───────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "kq_phase":   "start",
        "kq_cur":     0,
        "kq_answers": [None] * len(QUESTIONS),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def hard_reset():
    for k in list(st.session_state.keys()):
        if k.startswith("kq_"):
            del st.session_state[k]
    init_state()
    st.rerun()

# ─── HEADER ──────────────────────────────────────────────────────────────────

def render_header():
    st.html("""
<div style="text-align:center; padding:32px 0 24px; border-bottom:1px solid var(--border); margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
    Vice Vault · Desire Profile
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(48px,11vw,76px);
              color:var(--text); letter-spacing:3px; line-height:0.9; margin-bottom:8px;">
    READ<br><span style="color:var(--magenta);">BETWEEN</span><br>THE LINES
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:2px; text-transform:uppercase;">10 questions · Your real profile</div>
</div>
""")

# ─── START ────────────────────────────────────────────────────────────────────

def render_start():
    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:28px; margin-bottom:16px;">
  <p style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:20px; font-style:italic;">
    No direct questions.<br>
    No obvious answers.<br>
    Just scenarios — and what your choices reveal.
  </p>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">What you get</div>
  <p style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); line-height:1.8; margin:0;">
    A desire profile across 6 dimensions — power, sensation, dynamic, openness, verbal intensity,
    and exhibitionism — plus a set of kink tags that match your pattern.
    Nothing is assumed. Everything is inferred.
  </p>
</div>
""")
    if st.button("Begin →", use_container_width=True, type="primary"):
        st.session_state.kq_phase = "quiz"
        st.rerun()

# ─── QUIZ ─────────────────────────────────────────────────────────────────────

def render_quiz():
    cur     = st.session_state.kq_cur
    answers = st.session_state.kq_answers
    q       = QUESTIONS[cur]
    total   = len(QUESTIONS)
    is_last = cur == total - 1
    sel     = answers[cur]

    # Progress segments
    segs = "".join(
        f'<div style="flex:1; height:2px; border-radius:1px; '
        f'background:{"var(--magenta)" if i < cur else "rgba(255,45,120,0.5)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )
    st.html(f"""
<div style="display:flex; gap:3px; margin-bottom:20px;">{segs}</div>
<div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
            text-align:right; margin-bottom:12px; letter-spacing:1px;">
  {cur + 1} / {total}
</div>
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:24px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:8px;">{q['tag']}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; color:var(--text);
              line-height:1.6; margin-bottom:0;">{q['text']}</div>
</div>
""")

    for i, opt in enumerate(q["opts"]):
        is_sel = sel == i
        label  = ("◆  " if is_sel else "") + opt
        if st.button(label, key=f"kq_{cur}_{i}", use_container_width=True,
                     type="primary" if is_sel else "secondary"):
            st.session_state.kq_answers[cur] = i
            st.rerun()

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="kq_back", use_container_width=True):
                st.session_state.kq_cur -= 1
                st.rerun()
    with col_next:
        label = "See My Profile →" if is_last else "Next →"
        if st.button(label, key="kq_next", disabled=(sel is None),
                     use_container_width=True, type="primary"):
            if is_last:
                st.session_state.kq_phase = "result"
            else:
                st.session_state.kq_cur += 1
            st.rerun()

# ─── RESULT ───────────────────────────────────────────────────────────────────

def render_result():
    answers = st.session_state.kq_answers
    scores  = _compute_scores(answers)
    tot     = _total_pct(scores)
    profile = next((p for p in PROFILES if p["range"][0] <= tot <= p["range"][1]), PROFILES[-1])
    active  = _active_kinks(scores)

    # Kink pills
    pills = "".join(
        f'<span style="font-family:\'Space Mono\',monospace; font-size:9px; '
        f'padding:4px 10px; border-radius:99px; '
        f'border:1px solid {"var(--magenta)" if k["label"] in active else "var(--border)"}; '
        f'color:{"var(--magenta)" if k["label"] in active else "var(--muted)"}; '
        f'background:{"rgba(255,45,120,0.08)" if k["label"] in active else "transparent"}; '
        f'margin:3px;">{k["label"]}</span>'
        for k in KINK_MAP
    )

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:32px 28px; margin-bottom:16px;">
  <div style="font-size:48px; text-align:center; margin-bottom:12px;">{profile['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(30px,6vw,48px);
              letter-spacing:3px; color:var(--text); text-align:center; line-height:1.05; margin-bottom:4px;">
    {profile['name'].upper()}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--magenta); text-transform:uppercase; text-align:center; margin-bottom:18px;">
    {profile['meta']}
  </div>
  <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:24px;">
    {profile['desc']}
  </p>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Your kink tags</div>
  <div style="display:flex; flex-wrap:wrap; gap:6px;">{pills}</div>
</div>
""")

    # Dimension bars
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Dimension breakdown</div>
""")

    sorted_dims = sorted(DIMS.keys(), key=lambda d: -_dim_pct(scores, d))
    for d in sorted_dims:
        pct   = _dim_pct(scores, d)
        color = DIMS[d]["color"]
        label = DIMS[d]["label"]
        st.html(f"""
<div style="margin-bottom:14px;">
  <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--soft);">{label}</span>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:{color};">{pct}%</span>
  </div>
  <div style="height:4px; background:var(--border); border-radius:2px;">
    <div style="width:{pct}%; height:100%; background:{color}; border-radius:2px;"></div>
  </div>
</div>
""")

    st.html("<br>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Try Again", use_container_width=True):
            hard_reset()
    with col2:
        share = (
            f'Took the Vice Vault desire quiz\n\n'
            f'Profile: {profile["name"]}\n'
            f'"{profile["meta"]}"\n\n'
            f'Active kinks: {", ".join(active) if active else "still figuring it out"}'
        )
        st.download_button("↓ Save Result", data=share, file_name="my_desire_profile.txt",
                           mime="text/plain", use_container_width=True)

# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()
    _, col, _ = st.columns([1, 5, 1])
    with col:
        render_header()
        phase = st.session_state.kq_phase
        if   phase == "start":  render_start()
        elif phase == "quiz":   render_quiz()
        elif phase == "result": render_result()
