"""
Pages/what_would_you_do.py
AI-generated desire & fantasy profile quiz.
GPT-4o-mini generates 10 fresh indirect scenario questions every session.
Profiles across 6 dimensions and returns personalised exploration recommendations.
Results are saved to the quiz_results table on completion.
"""

import streamlit as st
import json
import random
from openai import OpenAI


# ─── DIMENSIONS ───────────────────────────────────────────────────────────────

DIMS = {
    "control":  {"label": "Power & control",  "color": "#D85A30"},
    "sensory":  {"label": "Sensory depth",     "color": "#ff2d78"},
    "exhib":    {"label": "Exhibitionism",      "color": "#ffb300"},
    "dynamic":  {"label": "Role dynamics",      "color": "#7F77DD"},
    "openness": {"label": "Sexual openness",    "color": "#00e5ff"},
    "verbal":   {"label": "Verbal intensity",   "color": "#c6ff00"},
}

PROFILES = [
    {
        "range": [0, 20],
        "icon": "🌙",
        "name": "The Intimate Minimalist",
        "meta": "Real > elaborate.",
        "desc": "You don't need complexity. What you want is genuine, simple, and deeply felt. You find more in a moment of authentic closeness than in any elaborate setup.",
    },
    {
        "range": [21, 42],
        "icon": "🌿",
        "name": "The Calibrated Explorer",
        "meta": "Trust unlocks everything.",
        "desc": "You know what you like but you're still curious about the edges. With the right person and enough trust, you'll go further than most people realise.",
    },
    {
        "range": [43, 62],
        "icon": "🔺",
        "name": "The Dynamic Architect",
        "meta": "Power and pace are the whole thing.",
        "desc": "Structure, dynamic, and roles matter to you enormously. Whether you're creating that structure or surrendering to it — the setup is part of the pleasure.",
    },
    {
        "range": [63, 999],
        "icon": "⚡",
        "name": "The Full-Spectrum Player",
        "meta": "You want all of it.",
        "desc": "You're not afraid of complexity. Sensation, dynamic, honesty, and edge — you want the full range. You know exactly what that means.",
    },
]

# ─── PROMPTS ──────────────────────────────────────────────────────────────────

GENERATION_PROMPT = """You write questions for an adults-only desire quiz called "Read Between The Lines" inside a lifestyle app called Vice Vault. The audience is adults who have explicitly opted into this experience.

The quiz is EXPLICITLY sexual in nature. Every question must be about sex, desire, fantasy, or intimate preferences — just phrased as a scenario or gut-reaction rather than a blunt question.

The goal is to feel like a daring, cheeky quiz you'd find in a bold lifestyle magazine — the kind that makes you laugh, feel a little exposed, and want to show your partner.

Generate exactly 10 questions. Each must:
- Be clearly about sex eg. threesome, attraction, desire, or intimacy — not ambiguously lifestyle-coded
- Measure one or more of these dimensions:
    control — who leads, who follows, dominance and submission dynamics
    sensory — physical sensation, touch, texture, intensity of physical experience
    exhib — being watched, performing, public/semi-public desire, showing off
    dynamic — roleplay, personas, power games, fantasy scenarios
    openness — willingness to experiment sexually, taboo curiosity, non-monogamy
    verbal — dirty talk, explicit communication, sound, language during sex
- Have exactly 4 answer options, escalating from least adventurous (score 0) to most (score 3)
- Feel exciting, a little provocative, honest — not clinical or sanitised

Strong example questions (use as tone reference, not verbatim):
- "Your partner says they want to try something new tonight and hands you a blindfold. Your first reaction?"
- "You're in a hotel and realise the curtains are slightly open while you're with someone. You..."
- "Your partner wants to talk through exactly what they want to do to you before anything happens. You feel..."
- "Someone you're sleeping with suggests you both stay fully dressed for as long as possible. Your instinct is..."
- "You're in a new situationship. They send you a voice note describing exactly what they've been thinking about. You..."

Return ONLY valid JSON. No markdown fences, no explanation. Format:
[
  {
    "tag": "Short 2-3 word label (e.g. 'The Blindfold', 'Open Window', 'Say It Out Loud')",
    "text": "The question or scenario text",
    "dims": {"dim_name": [score_for_opt0, score_for_opt1, score_for_opt2, score_for_opt3]},
    "opts": ["Option A text", "Option B text", "Option C text", "Option D text"]
  }
]

Scores are integers 0-3. Each option should feel meaningfully different — not just "a little" vs "a lot".
Make every question feel like it sees through the person answering it.
"""

RECOMMENDATION_PROMPT = """You are a sex-positive, frank, and knowledgeable desire analyst for Vice Vault, an adult lifestyle app.

A user just completed a desire profile quiz. Based on their scores, write 5 personalised recommendations for things they might enjoy exploring — specific experiences, scenarios, or dynamics.

Dimension scores (0–100%):
{scores}

Profile: {profile_name} — {profile_desc}

Guidelines:
- Be specific, honest, and a little daring — this is an adults-only app
- Reference actual sexual dynamics, scenarios, or experiences where relevant
- Each rec should feel tailored to their exact score pattern, not generic
- Tone: a knowledgeable, non-judgmental friend who's been around — not a therapist
- 1-2 sentences per recommendation, max
- Do NOT use bullet characters or numbering inside the strings

Return ONLY a JSON array of exactly 5 strings. No markdown, no preamble.
["Recommendation one.", "Recommendation two.", ...]
"""

# ─── OPENAI CLIENT ────────────────────────────────────────────────────────────

def call_openai(prompt: str) -> str:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,
    )
    return response.choices[0].message.content.strip()

# ─── SCORING HELPERS ──────────────────────────────────────────────────────────

def _dim_maxes(questions: list) -> dict:
    mx = {d: 0 for d in DIMS}
    for q in questions:
        for d, vals in q.get("dims", {}).items():
            if d in mx:
                mx[d] += max(vals)
    return mx


def _compute_scores(questions: list, answers: list) -> dict:
    sc = {d: 0 for d in DIMS}
    for qi, ai in enumerate(answers):
        if ai is None or qi >= len(questions):
            continue
        for d, vals in questions[qi].get("dims", {}).items():
            if d in sc and ai < len(vals):
                sc[d] += vals[ai]
    return sc


def _total_pct(scores: dict, dim_max: dict) -> int:
    tot = sum(scores.values())
    mx  = sum(v for v in dim_max.values() if v > 0)
    return round((tot / mx) * 100) if mx else 0


def _dim_pct(scores: dict, dim_max: dict, d: str) -> int:
    return round((scores[d] / dim_max[d]) * 100) if dim_max.get(d) else 0

# ─── DB SAVE ──────────────────────────────────────────────────────────────────

def _save_result_to_db(profile, dim_scores_pct, recs, total_pct, questions, answers):
    """Persist quiz result. Silent fail — never blocks the UI."""
    user = st.session_state.get("user")
    user_id = user.get("id") if user else None
    if not user_id:
        return
    try:
        import database as db
        db.save_read_between_lines_result(
            user_id         = user_id,
            profile_name    = profile.get("name", ""),
            profile_meta    = profile.get("meta", ""),
            dim_scores      = dim_scores_pct,
            recommendations = recs,
            total_pct       = total_pct,
            questions       = questions,
            answers         = answers,
        )
    except Exception:
        pass

# ─── CSS ──────────────────────────────────────────────────────────────────────

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

# ─── STATE ────────────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "kq_phase":     "start",
        "kq_cur":       0,
        "kq_answers":   [],
        "kq_questions": [],
        "kq_scores":    {},
        "kq_dimmax":    {},
        "kq_profile":   {},
        "kq_recs":      [],
        "kq_error":     "",
        "kq_saved":     False,
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

# ─── HEADER ───────────────────────────────────────────────────────────────────

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
              letter-spacing:2px; text-transform:uppercase;">AI-generated · Different every time · 18+</div>
</div>
""")

# ─── START ────────────────────────────────────────────────────────────────────

def render_start():
    if st.session_state.kq_error:
        st.warning(st.session_state.kq_error)
        st.session_state.kq_error = ""

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:28px; margin-bottom:16px;">
  <p style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:20px; font-style:italic;">
    No obvious questions.<br>
    No sanitised answers.<br>
    Just scenarios — and what your instincts say about what you actually want.
  </p>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">What happens</div>
  <p style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); line-height:1.8; margin:0;">
    10 fresh scenarios generated every time — no two quizzes are identical.
    Your answers build a desire profile across 6 dimensions covering power, sensation,
    exhibitionism, roleplay, openness, and verbal intensity. Then AI writes
    recommendations tailored specifically to your pattern. Results are saved to your profile.
  </p>
</div>
""")

    if st.button("Generate My Quiz →", use_container_width=True, type="primary"):
        st.session_state.kq_phase = "loading"
        st.rerun()

# ─── LOADING ──────────────────────────────────────────────────────────────────

def render_loading():
    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(t, p, s):
        ph_title.markdown(f"**{t}**")
        ph_bar.progress(p)
        ph_status.caption(s)

    try:
        upd("Generating your quiz…", 10, "Writing fresh scenarios for you")

        raw = call_openai(GENERATION_PROMPT)
        raw = raw.replace("```json", "").replace("```", "").strip()

        upd("Parsing questions…", 80, "Validating and shuffling")

        questions = json.loads(raw)

        valid = []
        for q in questions:
            if not all(k in q for k in ("tag", "text", "dims", "opts")):
                continue
            if len(q["opts"]) != 4:
                continue
            q["dims"] = {d: v for d, v in q["dims"].items() if d in DIMS}
            if not q["dims"]:
                continue
            valid.append(q)

        if len(valid) < 5:
            raise ValueError(f"Only {len(valid)} valid questions — try again.")

        random.shuffle(valid)
        final = valid[:10]

        upd("Ready.", 100, "Let's go")

        st.session_state.kq_questions = final
        st.session_state.kq_answers   = [None] * len(final)
        st.session_state.kq_cur       = 0
        st.session_state.kq_phase     = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.kq_error = f"Couldn't generate questions: {e}"
        st.session_state.kq_phase = "start"
        st.rerun()

# ─── QUIZ ─────────────────────────────────────────────────────────────────────

def render_quiz():
    cur       = st.session_state.kq_cur
    answers   = st.session_state.kq_answers
    questions = st.session_state.kq_questions

    if not questions or cur >= len(questions):
        hard_reset()
        return

    q       = questions[cur]
    total   = len(questions)
    is_last = cur == total - 1
    sel     = answers[cur] if cur < len(answers) else None

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
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:24px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:8px;">{q['tag']}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; color:var(--text);
              line-height:1.6;">{q['text']}</div>
</div>
""")

    for i, opt in enumerate(q["opts"]):
        is_sel = sel == i
        if st.button(
            ("◆  " if is_sel else "") + opt,
            key=f"kq_{cur}_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
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
                st.session_state.kq_phase = "generating_result"
            else:
                st.session_state.kq_cur += 1
            st.rerun()

# ─── GENERATING RESULT ────────────────────────────────────────────────────────

def render_generating_result():
    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(t, p, s):
        ph_title.markdown(f"**{t}**")
        ph_bar.progress(p)
        ph_status.caption(s)

    try:
        upd("Reading between the lines…", 20, "Analysing your answers")

        questions = st.session_state.kq_questions
        answers   = st.session_state.kq_answers
        scores    = _compute_scores(questions, answers)
        dim_max   = _dim_maxes(questions)
        tot       = _total_pct(scores, dim_max)
        profile   = next(
            (p for p in PROFILES if p["range"][0] <= tot <= p["range"][1]),
            PROFILES[-1],
        )

        score_str = "\n".join(
            f'  {DIMS[d]["label"]}: {_dim_pct(scores, dim_max, d)}%'
            for d in DIMS
        )

        upd("Generating your recommendations…", 55, "Writing your personalised profile")

        rec_prompt = RECOMMENDATION_PROMPT.format(
            scores=score_str,
            profile_name=profile["name"],
            profile_desc=profile["desc"],
        )

        raw = call_openai(rec_prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()

        upd("Finishing up…", 90, "Almost there")

        recs = json.loads(raw)
        if not isinstance(recs, list):
            recs = []

        dim_scores_pct = {d: _dim_pct(scores, dim_max, d) for d in DIMS}

        st.session_state.kq_scores    = scores
        st.session_state.kq_dimmax    = dim_max
        st.session_state.kq_profile   = profile
        st.session_state.kq_recs      = recs
        st.session_state.kq_dim_pct   = dim_scores_pct
        st.session_state.kq_total_pct = tot
        st.session_state.kq_phase     = "result"
        st.session_state.kq_saved     = False
        st.rerun()

    except Exception as e:
        st.session_state.kq_error = f"Something went wrong building your profile: {e}"
        st.session_state.kq_phase = "quiz"
        st.session_state.kq_cur   = len(st.session_state.kq_questions) - 1
        st.rerun()

# ─── RESULT ───────────────────────────────────────────────────────────────────

def render_result():
    profile = st.session_state.get("kq_profile", PROFILES[0])
    scores  = st.session_state.get("kq_scores", {d: 0 for d in DIMS})
    dim_max = st.session_state.get("kq_dimmax", {d: 1 for d in DIMS})
    recs    = st.session_state.get("kq_recs", [])

    if not st.session_state.get("kq_saved"):
        _save_result_to_db(
            profile        = profile,
            dim_scores_pct = st.session_state.get("kq_dim_pct", {}),
            recs           = recs,
            total_pct      = st.session_state.get("kq_total_pct", 0),
            questions      = st.session_state.get("kq_questions", []),
            answers        = st.session_state.get("kq_answers", []),
        )
        st.session_state.kq_saved = True

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:32px 28px; margin-bottom:16px;">
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
             line-height:1.9; text-align:center; margin-bottom:0;">
    {profile['desc']}
  </p>
</div>
""")

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Dimension breakdown
</div>
""")
    for d in sorted(DIMS.keys(), key=lambda d: -_dim_pct(scores, dim_max, d)):
        pct   = _dim_pct(scores, dim_max, d)
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

    if recs:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin:20px 0 12px;">
  Things worth exploring
</div>
""")
        dim_colors = [v["color"] for v in DIMS.values()]
        for i, rec in enumerate(recs):
            color = dim_colors[i % len(dim_colors)]
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {color}; border-radius:0 4px 4px 0;
            padding:14px 16px; margin-bottom:8px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75;">
    {rec}
  </div>
</div>
""")

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:center; margin-top:8px;">
  ✓ Result saved to your profile
</div>
""")

    st.html("<br>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ New Quiz", use_container_width=True):
            hard_reset()
    with col2:
        share_recs = "\n".join(f"· {r}" for r in recs[:3])
        share = (
            f"Vice Vault — Desire Profile\n\n"
            f"Profile: {profile.get('name', '')}\n"
            f"\"{profile.get('meta', '')}\"\n\n"
            f"{profile.get('desc', '')}\n\n"
            f"Top suggestions:\n{share_recs}"
        )
        st.download_button(
            "↓ Save Result",
            data=share,
            file_name="my_desire_profile.txt",
            mime="text/plain",
            use_container_width=True,
        )

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()
    _, col, _ = st.columns([1, 5, 1])
    with col:
        render_header()
        phase = st.session_state.kq_phase
        if   phase == "start":             render_start()
        elif phase == "loading":           render_loading()
        elif phase == "quiz":              render_quiz()
        elif phase == "generating_result": render_generating_result()
        elif phase == "result":            render_result()
