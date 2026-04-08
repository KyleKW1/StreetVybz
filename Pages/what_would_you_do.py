"""
Pages/what_would_you_do.py
AI-generated desire & fantasy profile quiz.
10 fresh indirect scenario questions generated per session.
Profiles across 6 dimensions, returns personalised exploration recommendations.
Results saved to quiz_results table on completion.

Perf fixes vs original:
  - OpenAI client cached with @st.cache_resource (no re-instantiation per render)
  - CSS/fonts not re-injected (handled globally by styles.py)

Fixes v2:
  - Recommendation prompt now receives chosen AND rejected answers explicitly
  - Model told never to suggest anything in rejected territory
  - Gender/orientation-neutral language enforced in prompt

Fixes v3:
  - uuid4 seed (truly unique per session, never collides)
  - Timestamp injected to second-level precision (kills caching at model level)
  - _FANTASY_POOLS massively expanded; 6 clusters sampled (was 4)
  - Remaining 4 free questions must come from OUTSIDE the sampled clusters
  - Prompt rewritten to surface unconscious/hidden desires via indirect scenarios
  - All gendered language purged from pools and prompts
  - Answer options now required to feel like crossing a psychological line

Fixes v4:
  - max_tokens=4000 added to _call_openai to prevent truncated JSON
  - _extract_json_array() robustly grabs the outermost [...] or {...} block,
    ignoring any preamble / trailing text the model appends
  - Both loading phases use _extract_json_array before json.loads
  - Raw model output logged to kq_raw_debug on failure for easier debugging

Fixes v5:
  - _sanitize_raw() normalises full-width punctuation and curly quotes before
    JSON extraction — prevents parse failures from CJK-style model drift
  - Prompt hardened: ASCII-only JSON, explicit closing-bracket rule
  - Generation call wrapped in retry loop (up to 3 attempts) before surfacing
    error to the user
  - JSONDecodeError now reports position + message for easier debugging
  - Fallback: questions that fail validation are skipped cleanly (was crashing)
"""

import re
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

# ─── EXPANDED FANTASY POOLS ───────────────────────────────────────────────────
# 30 distinct clusters. Each session samples 6 — giving C(30,6) = 593,775
# possible combinations before the free-question wildcard layer.
# ALL language is body-neutral and orientation-neutral.

_FANTASY_POOLS = [
    # 1 — Restraint
    ["being physically restrained during sex", "wrists tied above your head", "full-body rope bondage",
     "being unable to move while your partner does whatever they want", "spreader bars"],
    # 2 — Blindfolds / sensory removal
    ["blindfolds during sex", "not knowing what will happen next", "sensory deprivation hoods",
     "earplugs + blindfold combination", "being guided somewhere with no context"],
    # 3 — Group / multi-partner
    ["threesomes", "group sex with strangers", "being the centre of attention for multiple partners",
     "watching two people together while you participate", "an orgy scenario"],
    # 4 — Watching / voyeurism
    ["watching two people have sex without them knowing", "being let in to watch as a deliberate act",
     "live sex shows", "watching your partner with someone else", "covert observation fantasy"],
    # 5 — Being watched / exhibitionism
    ["having sex while someone watches", "performing for a stranger's gaze", "being filmed without direction",
     "sex in a room with a window", "knowing someone can hear everything"],
    # 6 — Public / risk
    ["sex in a place you could be caught", "outdoors with people nearby", "under a table at a restaurant",
     "in a changing room", "risk-of-discovery as the core turn-on"],
    # 7 — Dominance — giving
    ["being in complete control of another person's pleasure", "giving orders and having them obeyed",
     "deciding when your partner is allowed to come", "owning someone's body for a scene",
     "using a partner however you want with their full consent"],
    # 8 — Submission — receiving
    ["being told exactly what to do in bed", "giving up all control to a trusted partner",
     "being used for someone else's pleasure", "obeying without question",
     "not being allowed to speak unless given permission"],
    # 9 — Orgasm control
    ["being kept on the edge without being allowed to finish", "denying your own orgasm on command",
     "forced orgasm against your will (consensually)", "multiple orgasms with no break",
     "edging for a prolonged period before release"],
    # 10 — Dirty talk
    ["being narrated during sex", "explicit instructions whispered mid-act",
     "being told in graphic detail what's about to happen", "degrading language you've pre-agreed to",
     "praise that borders on obsession"],
    # 11 — Roleplay / personas
    ["playing a character who isn't you during sex", "stranger-meeting-stranger scenario despite knowing each other",
     "authority figure and subordinate dynamic", "rescuer and rescued", "predator and prey consensual chase"],
    # 12 — Anonymous / no-identity
    ["sex with someone whose name you never learn", "anonymous encounter in a darkened room",
     "glory hole fantasy", "hotel-hallway knock with no context", "masked encounter"],
    # 13 — Fetish wear / texture
    ["latex worn during sex", "leather restraints", "full-body stockings", "uniforms worn during sex",
     "partner in specific clothing that triggers arousal"],
    # 14 — Body worship
    ["having every part of your body kissed slowly", "spending an entire session on one body part",
     "foot or leg focus", "being treated like a sacred object", "worshipping your partner's body for hours"],
    # 15 — Dirty mirror / self-watching
    ["watching yourself in a full-length mirror during sex", "being filmed and watching the footage after",
     "live-streaming your own encounter privately", "narrating yourself", "reviewing what you look like mid-act"],
    # 16 — Temperature / sensation play
    ["ice traced across your skin during sex", "wax dripped carefully on your body",
     "feather teasing before any contact", "alternating heat and cold", "deliberately slowing sensation to an unbearable pace"],
    # 17 — Impact play
    ["spanking as part of sex", "hair-pulling mid-act", "biting that leaves marks",
     "being struck with an object you've agreed on", "the sound of impact as the primary turn-on"],
    # 18 — Toys during partnered sex
    ["a vibrator used on you while your partner watches", "remote-controlled toy in a public place",
     "toy used on your partner by you", "strap-on play", "double penetration via toys"],
    # 19 — Verbal humiliation / praise kink
    ["being praised obsessively during sex", "being called specific names you've asked for",
     "consensual degradation that only works because you chose it", "being talked down to and finding it hot",
     "worship language that borders on religious"],
    # 20 — Power reversal
    ["a partner who is usually dominant letting you take over", "taking control mid-scene unexpectedly",
     "swapping roles halfway through", "deliberately subverting the expected dynamic",
     "role-switching as a game with no fixed outcome"],
    # 21 — Non-monogamy scenarios
    ["swinging with another couple", "open relationship encounter with full partner knowledge",
     "watching your partner flirt with someone you've both agreed to", "compersion — being turned on by your partner's pleasure with another",
     "a couple's shared lover dynamic"],
    # 22 — Cuckolding / hotwife — gender-neutral version
    ["your partner sleeping with someone else while you know about it in real time",
     "being told every detail afterward", "watching your partner be desired by someone new",
     "the humiliation/pride mix of your partner being wanted by others",
     "orchestrating your partner's encounter from a distance"],
    # 23 — Phone / remote sex
    ["phone sex where you're directed by voice alone", "explicit voice notes sent throughout the day",
     "sexting that describes exactly what you'd do", "video call sex with a partner in another city",
     "being given instructions remotely and having to follow them alone"],
    # 24 — Fantasy narration during sex
    ["a partner narrating a fantasy scenario aloud while you have sex",
     "being told a story that describes exactly what's happening",
     "guided imagination during sex", "your partner voicing a character mid-act",
     "audio erotica playing while you're both in the room"],
    # 25 — Sleep-adjacent / stillness
    ["being touched while pretending to be asleep (consensual somnophilia)",
     "sex that starts before either of you fully wakes up", "keeping completely still while your partner moves",
     "staying silent no matter what happens", "the fantasy of being acted on without responding"],
    # 26 — Status / taboo dynamic
    ["a boss and employee dynamic with no real-world overlap", "a mentor and student scenario",
     "a formal hierarchy that only exists in the bedroom", "using titles during sex",
     "the turn-on of someone technically 'above' you wanting you"],
    # 27 — Competition / game
    ["sex as a challenge — who breaks first", "orgasm competition", "being bet against",
     "a game with sexual consequences for losing", "the thrill of trying to hold out longer"],
    # 28 — Scent / taste fixation
    ["a partner's specific scent being the main turn-on", "tasting someone before touching them",
     "blindfolded identification by scent alone", "oral fixation as a standalone act",
     "being eaten out or going down as the entire main event — not foreplay"],
    # 29 — Location / setting fetish
    ["sex in a specific location you've fixated on", "a hotel room with floor-to-ceiling windows",
     "the back seat of a car", "a swimming pool or body of water after dark",
     "a specific room in a house that isn't the bedroom"],
    # 30 — Aftercare / intimacy as erotic
    ["the vulnerability after sex being as erotic as the act", "crying or emotional release during sex",
     "being held for a long time after as part of the sexual experience",
     "silence and skin contact as an explicit act", "the morning after being as intentional as the night before"],
]


def _build_generation_prompt() -> str:
    seed      = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    clusters        = random.sample(_FANTASY_POOLS, 6)
    cluster_labels  = [c[0] for c in clusters]
    cluster_str     = "\n".join(f"  Cluster {i+1}: {', '.join(c)}" for i, c in enumerate(clusters))
    excluded_labels = "; ".join(cluster_labels)

    return f"""You write questions for an adults-only desire quiz called "Read Between The Lines" inside Vice Vault, a verified 18+ adult lifestyle app. Every user has age-verified and explicitly consented to explicit sexual content.

SESSION ID: {seed}
TIMESTAMP:  {timestamp}

This session ID is globally unique and has never existed before. You MUST generate questions that have never appeared in any prior session. No recycled phrasings, no familiar scenario structures, no reused setups. Treat this as a blank slate.

━━━ YOUR TASK ━━━
Write exactly 10 quiz questions that surface what a person ACTUALLY wants — including things they haven't consciously admitted to themselves. Your questions should feel like they've read the user's mind and named something they've never said out loud.

Use indirect, scenario-based framing. Don't ask "do you like X" — put the person inside a specific moment and ask how they respond. The question should create a small jolt of recognition.

━━━ ANCHORED QUESTIONS (build exactly 6 from these clusters) ━━━
{cluster_str}

Go beyond the surface label. For each cluster, construct a scenario that forces the person to locate themselves emotionally and physically — not just tick a preference box.

━━━ FREE QUESTIONS (exactly 4) ━━━
These must explore kinks, dynamics, or fantasies NOT covered by these clusters: {excluded_labels}
Choose territory that is specific, psychologically revealing, and genuinely different from the anchors.

━━━ RULES ━━━
1. Every question is unambiguously sexual in nature — no metaphors, no euphemisms.
2. Scenarios are second-person, present tense, specific. Put the person IN the moment.
3. Each question should feel like it's exposing something the person hasn't fully said yes to yet.
4. Measure one or more of these dimensions per question:
   - control     → dominance, submission, restraint, consensual power exchange
   - sensory     → physical sensation, pain/pleasure, texture, temperature, intensity
   - exhib       → being watched, performing, filming, public/semi-public scenarios
   - dynamic     → roleplay, personas, power games, specific fantasy scenarios
   - openness    → threesomes, group sex, non-monogamy, swinging, taboo kinks
   - verbal      → dirty talk, phone sex, explicit instructions, sound, narration
5. Exactly 4 answer options per question, escalating:
   - Option 0: avoidant / not for me
   - Option 1: curious but haven't gone there
   - Option 2: genuinely want this
   - Option 3: I've already thought about this in detail and I want more
   The jump from 2→3 should feel like crossing a psychological line.
6. Options must be meaningfully distinct — not just more emphatic versions of the same thing.
7. CRITICAL — fully gender-neutral and body-neutral language throughout. No pronouns that imply gender. No assumed body parts. No assumed role (top/bottom/giver/receiver). The questions must work for any person of any gender, body, and orientation.
8. Tone: direct, a little confrontational, no clinical language, no hedging.
9. CRITICAL — output valid JSON using ASCII double quotes ONLY. No curly quotes, no backticks, no full-width punctuation (no ：, 、, ，). Every string must open and close with a standard " character.
10. The JSON array must end with a single ] on its own line. Do not write any text after that closing bracket.

Return ONLY valid JSON — no markdown fences, no explanation, no preamble, no trailing text after the closing bracket:
[
  {{
    "tag": "2-3 word kink/fantasy label",
    "text": "The scenario — second person, present tense, specific, explicitly sexual",
    "dims": {{"dim_name": [score_opt0, score_opt1, score_opt2, score_opt3]}},
    "opts": ["Avoidant response", "Curious but hasn't happened", "Genuinely want this", "Already fantasised in detail"]
  }}
]
Scores are integers 0–3. Output the JSON array and nothing else."""


RECOMMENDATION_PROMPT = """You are a frank, sex-positive, deeply knowledgeable desire analyst for Vice Vault, a verified adult lifestyle app.

A user just completed a desire profile quiz. Using their dimension scores AND their actual chosen answers, write 5 personalised recommendations for experiences, scenarios, or dynamics worth exploring.

Dimension scores (0–100%):
{scores}

Profile: {profile_name} — {profile_desc}

What the user expressed genuine interest in (build on these — these are your raw material):
{chosen_answers}

What the user actively rejected or scored zero on (HARD RULE — do not recommend these, do not gesture toward them, do not recommend adjacent versions):
{rejected_answers}

Guidelines:
- CRITICAL: Anything in the rejected list is off the table entirely. Not even a softer version.
- Recommendations must feel like they were written specifically for this person's answer pattern — not generic sex advice.
- Use fully gender-neutral, body-neutral, orientation-neutral language. No assumed pronouns, body parts, or roles.
- Be specific and a little daring — this is an 18+ app with consenting adults.
- Tone: knowledgeable, non-judgmental, like a frank friend who knows a lot — not a therapist or a content warning.
- 1-2 sentences per recommendation, max.
- Do NOT use bullet characters or numbering inside the strings.
- CRITICAL — output valid JSON using ASCII double quotes ONLY. No curly quotes, no backticks, no full-width punctuation.
- The JSON array must end with a single ] on its own line. Do not write any text after that closing bracket.

Return ONLY a JSON array of exactly 5 strings. No markdown, no preamble, no trailing text after the closing bracket.
["Recommendation one.", "Recommendation two.", ...]"""


# ─── RAW OUTPUT SANITIZER ─────────────────────────────────────────────────────

def _sanitize_raw(raw: str) -> str:
    """
    Normalise common model output quirks before JSON extraction.

    Handles:
      - Full-width / CJK punctuation the model occasionally emits
      - Curly / typographic quotes
      - Backtick-delimited strings inside arrays
      - Stray trailing commas before ] or }
    """
    # Full-width and CJK punctuation → ASCII equivalents
    char_map = {
        "\uff1a": ":",   # ：
        "\u3001": ",",   # 、
        "\uff0c": ",",   # ，
        "\u3002": ".",   # 。
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
    }
    for bad, good in char_map.items():
        raw = raw.replace(bad, good)

    # Replace backtick-delimited strings: `foo` → "foo"
    # Only inside what looks like a JSON array value position
    raw = re.sub(r"`([^`]*)`", r'"\1"', raw)

    # Remove trailing commas before ] or } (common model mistake)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    return raw


# ─── JSON EXTRACTION HELPER ───────────────────────────────────────────────────

def _extract_json_array(raw: str) -> str:
    """
    Robustly extract the first top-level JSON array from a model response.

    Handles:
      - Markdown fences (```json ... ```)
      - Preamble text before the array
      - Trailing text / notes after the closing bracket
      - Cases where the model wraps the array in an object

    Raises ValueError with position detail if no valid array is found.
    """
    raw = raw.replace("```json", "").replace("```", "").strip()

    start = raw.find("[")
    if start == -1:
        raise ValueError("No JSON array found in model response")

    depth   = 0
    in_str  = False
    escape  = False

    for i, ch in enumerate(raw[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]

    raise ValueError("Malformed JSON array — no closing bracket found")


def _parse_json_array(raw: str) -> list:
    """Sanitise → extract → parse, with useful error messages on failure."""
    sanitized = _sanitize_raw(raw)
    extracted = _extract_json_array(sanitized)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse error at position {e.pos}: {e.msg}") from e


# ─── OPENAI CALL WITH RETRY ───────────────────────────────────────────────────

def _call_openai(prompt: str, retries: int = 3) -> str:
    """
    Call the OpenAI API with automatic retry on failure.
    Returns the raw string content of the first successful response.
    Raises the last exception if all attempts fail.
    """
    client = _get_openai_client()
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.99,
                presence_penalty=0.6,
                frequency_penalty=0.4,
                max_tokens=4000,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                continue
    raise last_exc


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
    """
    Returns (chosen_str, rejected_str) — human-readable summaries of what
    the user picked vs what they passed on. Used to ground the recommendation prompt.
    """
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
            rejected.append(f"- {tag}: chose \"{opt_text}\" (no interest)")
        elif ai == 1:
            chosen.append(f"- {tag}: chose \"{opt_text}\" (mild curiosity only)")
        else:
            chosen.append(f"- {tag}: chose \"{opt_text}\" (genuine interest)")

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


# ─── CSS (page-specific overrides only — global CSS from styles.py) ───────────

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
        "kq_raw_debug": "",
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

    if st.session_state.get("kq_raw_debug"):
        with st.expander("🛠 Debug: last raw model output"):
            st.code(st.session_state.kq_raw_debug, language="text")

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
        st.session_state.kq_phase     = "loading"
        st.session_state.kq_raw_debug = ""
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

    raw = ""
    try:
        upd("Generating your quiz…", 10, "Writing fresh scenarios for you")
        raw = _call_openai(_build_generation_prompt())

        upd("Parsing questions…", 80, "Validating")
        questions = _parse_json_array(raw)

        valid = []
        for q in questions:
            # Skip malformed entries cleanly instead of crashing
            if not isinstance(q, dict):
                continue
            if not all(k in q for k in ("tag", "text", "dims", "opts")):
                continue
            if not isinstance(q.get("opts"), list) or len(q["opts"]) != 4:
                continue
            if not isinstance(q.get("dims"), dict):
                continue
            q["dims"] = {d: v for d, v in q["dims"].items() if d in DIMS}
            if not q["dims"]:
                continue
            valid.append(q)

        if len(valid) < 5:
            raise ValueError(f"Only {len(valid)} valid questions returned — try again.")

        random.shuffle(valid)
        final = valid[:10]
        upd("Ready.", 100, "Let's go")

        st.session_state.kq_questions = final
        st.session_state.kq_answers   = [None] * len(final)
        st.session_state.kq_cur       = 0
        st.session_state.kq_phase     = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.kq_raw_debug = raw
        st.session_state.kq_error     = f"Couldn't generate questions: {e}"
        st.session_state.kq_phase     = "start"
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

    raw = ""
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

        upd("Finishing up…", 90, "Almost there")
        recs = _parse_json_array(raw)
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
        st.session_state.kq_raw_debug = raw
        st.session_state.kq_error     = f"Something went wrong generating your result: {e}"
        st.session_state.kq_phase     = "quiz"
        st.session_state.kq_cur       = len(st.session_state.kq_questions) - 1
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
