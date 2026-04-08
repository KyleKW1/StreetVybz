"""
Pages/what_would_you_do.py
AI-generated desire & fantasy profile quiz.
GPT-4o-mini generates 10 fresh indirect scenario questions every session.
Profiles across 6 dimensions and returns personalised exploration recommendations.
Results are saved to the quiz_results table on completion.

Changes from original:
  - Question style rewritten: casual plain English, not dramatic fragments
  - Recommendation prompt now receives chosen AND rejected answers for specificity
  - OpenAI client cached with @st.cache_resource
  - max_tokens=8000 to prevent JSON truncation
"""

import streamlit as st
import json
import random
import datetime
import uuid
from openai import OpenAI


# ─── CACHED CLIENT ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_openai_client():
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


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

# ─── FANTASY POOLS ────────────────────────────────────────────────────────────

_FANTASY_POOLS = [
    ["bondage & restraint", "blindfolds", "handcuffs", "rope play", "sensory deprivation"],
    ["threesomes", "group sex", "watching your partner with someone else", "being shared"],
    ["dominance", "being in control", "giving orders", "deciding when your partner finishes"],
    ["submission", "being told what to do", "giving up control", "obeying without question"],
    ["exhibitionism", "being watched during sex", "performing for someone", "sex in public"],
    ["voyeurism", "watching others have sex", "observing without being seen"],
    ["dirty talk", "explicit instructions during sex", "being narrated", "verbal degradation"],
    ["impact play", "spanking", "hair pulling", "biting", "leaving marks"],
    ["orgasm control", "edging", "being denied", "forced orgasm"],
    ["roleplay", "power dynamic scenarios", "stranger fantasy", "authority figure dynamic"],
    ["anonymous sex", "no-name hookup", "glory hole", "masked encounter"],
    ["filming & watching", "being recorded", "watching footage back", "live streaming privately"],
    ["temperature play", "ice during sex", "wax play", "alternating heat and cold"],
    ["group dynamics", "swinging", "open relationship encounters", "shared partners"],
    ["praise & degradation kink", "being called names during sex", "humiliation play", "worship dynamic"],
]


def _build_generation_prompt() -> str:
    seed      = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    clusters    = random.sample(_FANTASY_POOLS, 6)
    cluster_str = "\n".join(f"  - {', '.join(c)}" for c in clusters)
    excluded    = "; ".join(c[0] for c in clusters)

    return f"""You write questions for an adults-only desire quiz inside Vice Vault, a verified 18+ adult lifestyle app.

SESSION ID: {seed}
TIMESTAMP:  {timestamp}

Write exactly 10 quiz questions. 6 must come from these clusters:
{cluster_str}

The other 4 can cover any sexual fantasy or kink NOT in: {excluded}

STYLE — MOST IMPORTANT:
Questions must sound like something a friend would casually say out loud.
Plain, direct, no drama. Just the scenario in one sentence.

GOOD examples — match this energy exactly:
"Having sex with your partner and inviting a friend to join."
"Having sex somewhere you could easily get caught."
"Being blindfolded during sex and not knowing what comes next."
"Being tied up and completely unable to move."
"Hooking up with someone whose name you never find out."
"Being told exactly what to do in bed."
"Filming yourself having sex and watching it back."
"Having your partner watch while you're with someone else."

BAD — do not write like this:
"Wrists pinned. You can't move. They take their time."
"You're in a darkened room and someone you trust has blindfolded you..."

CRITICAL LANGUAGE RULES — violations will break the quiz:
- NEVER imply penetration, giving or receiving, top or bottom, or any specific sex act that assumes a body part
- NEVER use phrases like "getting it on", "riding", "taking it", "giving it" — these imply specific bodies/roles
- Every question must work equally for any gender, any body, any orientation
- Use: "having sex", "being touched", "hooking up", "being with someone" — not act-specific language
- Bad: "Getting it on in the back seat of a car" (implies penetrative sex)
- Good: "Having sex in the back seat of a car with someone watching"

Rules:
- "text": one plain sentence, 8-14 words, present participle style ("Having sex...", "Being tied...")
- "opts": 4-7 words each, casual and honest
- "tag": 2-3 words
- Explicitly sexual, no euphemisms, but body/role neutral
- EXACTLY 4 answer options per question, escalating 0-3
- Score each option 0-3 across relevant dims: control, sensory, exhib, dynamic, openness, verbal
- You MUST write all 10 questions. Do not stop early.
- Return ONLY valid JSON. No markdown, no preamble, no text after the closing bracket.

[
  {{
    "tag": "short label",
    "text": "One plain casual sentence.",
    "dims": {{"dim_name": [0,1,2,3]}},
    "opts": ["Not my thing","Kind of curious","Would actually do this","Already thought about this a lot"]
  }}
]"""


RECOMMENDATION_PROMPT = """You are a sex-positive, frank, and knowledgeable desire analyst for Vice Vault, an adult lifestyle app.

A user just completed a desire profile quiz. Write 5 personalised recommendations based on their scores AND their actual answers.

Dimension scores (0-100%):
{scores}

Profile: {profile_name} — {profile_desc}

What they showed genuine interest in (build on these):
{chosen_answers}

What they actively rejected (do NOT recommend these or anything adjacent):
{rejected_answers}

Guidelines:
- Rejected items are completely off the table — not even a softer version.
- Recommendations must feel written specifically for this person, not generic advice.
- Gender-neutral, body-neutral, orientation-neutral language throughout.
- Tone: a knowledgeable, non-judgmental friend — not a therapist.
- 1-2 sentences per recommendation, max.
- Do NOT use bullet characters or numbering inside the strings.
- Return ONLY a JSON array of exactly 5 strings. No markdown, no preamble.

["Recommendation one.", "Recommendation two.", ...]"""


# ─── OPENAI CALL ──────────────────────────────────────────────────────────────

def _call_openai(prompt: str) -> str:
    response = _get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.97,
        max_tokens=8000,
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


def _build_answer_context(questions: list, answers: list) -> tuple[str, str]:
    chosen   = []
    rejected = []
    for qi, ai in enumerate(answers):
        if ai is None or qi >= len(questions):
            continue
        q        = questions[qi]
        tag      = q.get("tag", "")
        opts     = q.get("opts", [])
        opt_text = opts[ai] if ai < len(opts) else ""
        if ai == 0:
            rejected.append(f"- {tag}: \"{opt_text}\"")
        else:
            chosen.append(f"- {tag}: \"{opt_text}\" ({'mild curiosity' if ai == 1 else 'genuine interest'})")
    chosen_str   = "\n".join(chosen)   if chosen   else "Nothing stood out strongly."
    rejected_str = "\n".join(rejected) if rejected else "Nothing explicitly rejected."
    return chosen_str, rejected_str


# ─── DB SAVE ──────────────────────────────────────────────────────────────────

def _save_result_to_db(profile, dim_scores_pct, recs, total_pct, questions, answers):
    user    = st.session_state.get("user")
    user_id = user.get("id") if user else None
    if not user_id:
        return
    try:
        import database as db
        db.save_read_between_lines_result(
            user_id=user_id,
            profile_name=profile.get("name", ""),
            profile_meta=profile.get("meta", ""),
            dim_scores=dim_scores_pct,
            recommendations=recs,
            total_pct=total_pct,
            questions=questions,
            answers=answers,
        )
    except Exception:
        pass


# ─── CSS ──────────────────────────────────────────────────────────────────────

def _inject_page_css():
    st.html("""
<style>
section.main .block-container { padding-top:0.5rem !important; max-width:720px !important; }
.stButton > button[kind="primary"] {
  background:var(--magenta) !important;
  color:#fff !important;
  border-color:var(--magenta) !important;
}
.stButton > button[kind="primary"]:hover {
  background:#ff5590 !important;
  box-shadow:0 0 20px rgba(255,45,120,0.25) !important;
}
.stProgress > div > div > div { background:var(--magenta) !important; }
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

def _render_header():
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

def _render_start():
    if st.session_state.kq_error:
        st.warning(st.session_state.kq_error)
        st.session_state.kq_error = ""

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:28px; margin-bottom:16px;">
  <p style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:20px; font-style:italic;">
    No obvious questions.<br>No sanitised answers.<br>
    Just scenarios — and what your instincts say about what you actually want.
  </p>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">What happens</div>
  <p style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); line-height:1.8; margin:0;">
    10 fresh scenarios generated every time — no two quizzes are identical.
    Your answers build a desire profile across 6 dimensions. Then AI writes
    recommendations tailored specifically to your pattern.
  </p>
</div>
""")
    if st.button("Generate My Quiz →", use_container_width=True, type="primary"):
        st.session_state.kq_phase = "loading"
        st.rerun()


# ─── LOADING ──────────────────────────────────────────────────────────────────

def _render_loading():
    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(t, p, s):
        ph_title.markdown(f"**{t}**")
        ph_bar.progress(p)
        ph_status.caption(s)

    def _parse_questions(raw: str) -> list:
        raw = raw.replace("```json", "").replace("```", "").strip()
        questions = json.loads(raw)
        defaults = ["Not my thing", "Kind of curious", "Would actually do this", "Already thought about this a lot"]
        valid = []
        for q in questions:
            if not all(k in q for k in ("tag", "text", "dims", "opts")):
                continue
            if not isinstance(q["opts"], list) or len(q["opts"]) < 2:
                continue
            while len(q["opts"]) < 4:
                q["opts"].append(defaults[len(q["opts"])])
            q["opts"] = q["opts"][:4]
            if isinstance(q.get("dims"), dict):
                q["dims"] = {d: v for d, v in q["dims"].items() if d in DIMS}
            if not q.get("dims"):
                q["dims"] = {"dynamic": [0, 1, 2, 3]}
            valid.append(q)
        return valid

    try:
        valid = []
        for attempt in range(3):
            pct = 10 + attempt * 20
            upd("Generating your quiz…", pct, f"Writing fresh scenarios{'  (retry)' if attempt else ''}")
            raw = _call_openai(_build_generation_prompt())
            valid = _parse_questions(raw)
            if len(valid) >= 8:
                break

        if not valid:
            raise ValueError("No valid questions returned — please try again.")

        upd("Parsing questions…", 80, "Validating and shuffling")
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

@st.cache_data(show_spinner=False)
def _question_card_html(cur: int, total: int, tag: str, text: str) -> str:
    segs = "".join(
        f'<div style="flex:1; height:2px; border-radius:1px; '
        f'background:{"var(--magenta)" if i < cur else "rgba(255,45,120,0.5)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )
    return f"""
<div style="display:flex; gap:3px; margin-bottom:20px;">{segs}</div>
<div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
            text-align:right; margin-bottom:12px; letter-spacing:1px;">{cur+1} / {total}</div>
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:24px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:8px;">{tag}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; color:var(--text);
              line-height:1.6;">{text}</div>
</div>
"""


def _render_quiz():
    cur       = st.session_state.kq_cur
    answers   = st.session_state.kq_answers
    questions = st.session_state.kq_questions

    if not questions or cur >= len(questions):
        hard_reset(); return

    q       = questions[cur]
    total   = len(questions)
    is_last = cur == total - 1
    sel     = answers[cur] if cur < len(answers) else None

    st.html(_question_card_html(cur, total, q["tag"], q["text"]))

    for i, opt in enumerate(q["opts"]):
        is_sel = sel == i
        if st.button(
            ("◆  " if is_sel else "") + opt,
            key=f"kq_{cur}_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            st.session_state.kq_answers[cur] = i
            if not is_last:
                st.session_state.kq_cur += 1
            st.rerun()

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="kq_back", use_container_width=True):
                st.session_state.kq_cur -= 1; st.rerun()
    with col_next:
        if is_last:
            if st.button(
                "See My Profile →", key="kq_next",
                disabled=(sel is None), use_container_width=True, type="primary",
            ):
                st.session_state.kq_phase = "generating_result"; st.rerun()


# ─── GENERATING RESULT ────────────────────────────────────────────────────────

def _render_generating_result():
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
            f'  {DIMS[d]["label"]}: {_dim_pct(scores, dim_max, d)}%' for d in DIMS
        )

        chosen_str, rejected_str = _build_answer_context(questions, answers)

        upd("Generating recommendations…", 55, "Writing your personalised profile")
        raw = _call_openai(RECOMMENDATION_PROMPT.format(
            scores=score_str,
            profile_name=profile["name"],
            profile_desc=profile["desc"],
            chosen_answers=chosen_str,
            rejected_answers=rejected_str,
        ))
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

def _render_result():
    profile = st.session_state.get("kq_profile", PROFILES[0])
    scores  = st.session_state.get("kq_scores",  {d: 0 for d in DIMS})
    dim_max = st.session_state.get("kq_dimmax",  {d: 1 for d in DIMS})
    recs    = st.session_state.get("kq_recs",    [])

    if not st.session_state.get("kq_saved"):
        _save_result_to_db(
            profile=profile,
            dim_scores_pct=st.session_state.get("kq_dim_pct", {}),
            recs=recs,
            total_pct=st.session_state.get("kq_total_pct", 0),
            questions=st.session_state.get("kq_questions", []),
            answers=st.session_state.get("kq_answers", []),
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

    st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Dimension breakdown</div>""")

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
        st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin:20px 0 12px;">Things worth exploring</div>""")
        dim_colors = [v["color"] for v in DIMS.values()]
        for i, rec in enumerate(recs):
            color = dim_colors[i % len(dim_colors)]
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {color}; border-radius:0 4px 4px 0;
            padding:14px 16px; margin-bottom:8px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75;">{rec}</div>
</div>
""")

    st.html("""<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:center; margin-top:8px;">
  ✓ Result saved to your profile</div>""")

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
    _inject_page_css()
    init_state()
    _, col, _ = st.columns([1, 5, 1])
    with col:
        _render_header()
        phase = st.session_state.kq_phase
        if   phase == "start":             _render_start()
        elif phase == "loading":           _render_loading()
        elif phase == "quiz":              _render_quiz()
        elif phase == "generating_result": _render_generating_result()
        elif phase == "result":            _render_result()
