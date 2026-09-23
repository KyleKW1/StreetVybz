"""
Pages/what_would_you_do.py
Read Between The Lines — 3-phase desire profile quiz.

Everything is AI-generated fresh every time. No Reddit. No external dependencies.
All scenarios, questions, and answers are gender-neutral and orientation-inclusive.
No he/she/him/her/boyfriend/girlfriend anywhere.

Community Pulse: after answering each question the user sees an anonymous
breakdown of how other Hidden users responded.
"""

import hashlib
import html as _html
import streamlit as st
import json
import random
import time
import threading
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

SCENARIO_COUNT = 7

# Real adult-platform categories, minus the ones built around people who could read as
# under 18 (school, babysitter, college, step, old/young): results are shown to real matches.
ALL_PLATFORM_CATEGORIES = [
    "18-25", "60FPS", "AI", "Amateur", "Anal", "Arab", "Asian", "Babe",
    "BBW", "Behind The Scenes", "Big Ass", "Big Dick",
    "Big Tits", "Bisexual Male", "Blonde", "Blowjob", "Bondage", "Brazilian",
    "British", "Brunette", "Bukkake", "Cartoon", "Casting", "Celebrity",
    "Compilation", "Cosplay", "Creampie", "Cuckold",
    "Cumshot", "Czech", "Deepthroat", "Dirty Talk", "Double Penetration", "Ebony", "Euro",
    "Exclusive", "Feet", "Female Orgasm", "Fetish", "Fingering", "Fisting",
    "French", "Funny", "Gaming", "Gangbang", "Gay", "German", "Handjob", "Hardcore",
    "HD Porn", "Hentai", "Indian", "Interactive", "Interracial", "Italian",
    "Japanese", "Korean", "Latina", "Lesbian", "Massage", "Masturbation",
    "Mature", "MILF", "Muscular Men", "Music", "Orgy",
    "Parody", "Party", "Pissing", "Podcast", "Popular With Women", "Pornstar",
    "POV", "Public", "Pussy Licking", "Reaction", "Reality", "Red Head",
    "Role Play", "Romantic", "Rough Sex", "Russian", "Sensual", "SFW",
    "Small Tits", "Smoking", "Solo Female", "Solo Male", "Squirt",
    "Strap On", "Striptease", "Tattooed Women", "Threesome",
    "Toys", "Transgender", "Verified Amateurs", "Verified Couples",
    "Verified Models", "Vintage", "Virtual Reality", "Voyeur", "Webcam",
]

# min/max are openness-index bands (0–100), so every tier is reachable
# whatever the number of scenarios.
RESULT_TYPES = [
    {
        "min": 0, "max": 20, "icon": "🔒", "name": "Closed Garden",
        "meta": "Yours. Only yours. Period.",
        "hook": "You kept the door shut on almost every one. That consistency either means total clarity — or a story you haven't told yourself yet.",
        "signal": "You're not curious about the scenarios. You're protective of something.",
        "tell": "The question that probably landed hardest was one you dismissed fast.",
    },
    {
        "min": 21, "max": 45, "icon": "🌿", "name": "Quietly Curious",
        "meta": "The thought has crossed your mind. More than once.",
        "hook": "You played it safe on the ones that felt risky. But you didn't close the door all the way on any of them.",
        "signal": "There's a gap between what you'd say out loud and what you actually thought reading these.",
        "tell": "Someone who knows you well would not be entirely surprised by your score.",
    },
    {
        "min": 46, "max": 70, "icon": "🌙", "name": "The Open Door",
        "meta": "You've thought this through. Seriously.",
        "hook": "You've been here before — in your head, at least. These scenarios didn't shock you. They felt familiar.",
        "signal": "The gap between where you are and where you want to be is mostly just one honest conversation.",
        "tell": "You know which scenario you'd actually say yes to if the circumstances were right.",
    },
    {
        "min": 71, "max": 89, "icon": "🔺", "name": "Already Decided",
        "meta": "The question isn't whether. It's when.",
        "hook": "You didn't hesitate on the ones that matter. That's not impulsiveness — that's someone who's done the work already.",
        "signal": "You're past theory. The only thing between you and acting on this is logistics.",
        "tell": "You probably already know who you'd want in the room.",
    },
    {
        "min": 90, "max": 100, "icon": "⚡", "name": "The Third Is Already Picked",
        "meta": "You know exactly who. They probably know too.",
        "hook": "You read these like someone reading their own journal entries. Not recognition — confirmation.",
        "signal": "This isn't curiosity. This is inventory.",
        "tell": "The most interesting question for you isn't what — it's what you're still waiting for.",
    },
]

# Phase 2: 10 statements that escalate from curiosity to your deepest fantasy.
# The signal names are stored with results and shown to matches (matching.DESIRE_LABELS),
# so keep them stable; retired ones stay in DESIRE_LABELS for older results.
HIDDEN_DESIRE_QUESTIONS = [
    # Tier 1 — curiosity
    {"id": "hd_02", "signal": "desired_intensity", "tier": 1,
     "text": "You want to be wanted so badly that someone stops being polite about it — hands on you before the door is even shut."},
    {"id": "hd_01", "signal": "verbal_arousal", "tier": 1,
     "text": "Someone telling you exactly what they're going to do to you — slowly, in detail — gets you going faster than being touched."},

    # Tier 2 — getting specific
    {"id": "hd_06", "signal": "stranger_fantasy", "tier": 2,
     "text": "A stranger, a specific place — a hotel bar, a dark dance floor, a late flight — and in your head it's already gone all the way before you've said a word."},
    {"id": "hd_10", "signal": "exhib_active", "tier": 2,
     "text": "The idea of being watched — someone seeing you undress, or seeing you mid-sex — turns you on more than you'd admit to anyone you know."},

    # Tier 3 — the ones people don't say out loud
    {"id": "hd_07", "signal": "dom_active", "tier": 3,
     "text": "You've fantasised about being completely in charge of someone's pleasure — setting the pace, making them wait, deciding when they finally get to finish."},
    {"id": "hd_08", "signal": "sub_active", "tier": 3,
     "text": "You've thought about someone taking over completely — pinning you down, deciding what happens to your body, and you just letting them."},
    {"id": "hd_12", "signal": "group_sex", "tier": 3,
     "text": "You've pictured sex with more than one person at once — not as a joke, as a detailed scene you've replayed."},

    # Tier 4 — deeper
    {"id": "hd_09", "signal": "taboo_arousal", "tier": 4,
     "text": "Something you'd never say out loud has turned you on — a video, a story, a thought — and you went straight back to it later."},
    {"id": "hd_11", "signal": "secret_fantasy", "tier": 4,
     "text": "There's a fantasy you've never told a single partner. Not because it's wrong — because saying it would mean admitting how much you want it."},

    # Tier 5 — your deepest fantasy
    {"id": "hd_14", "signal": "elaborated_fantasy", "tier": 5,
     "text": "Your deepest fantasy is already fully written — who it's with, where it happens, what happens first — and if the right person asked, you'd tell them tonight."},
]

HD_OPTS = [
    ("nope",     "Not me",                    0),
    ("maybe",    "A little, maybe",           1),
    ("yes",      "Yeah — that's accurate",    2),
    ("strongly", "More than I'd usually say", 3),
]
HD_OPT_LABELS = [label for _, label, _ in HD_OPTS]
HD_OPT_IDS    = [oid   for oid, _, _ in HD_OPTS]

PHASE_TRANSITIONS = {
    "to_hidden_desires": [
        "Phase 1 read how you react to situations. Phase 2 goes after what you actually want.",
        "The scenarios showed your surface. What comes next goes to what you haven't named.",
        "You answered the situations. Now it gets personal.",
    ],
    "to_profile": [
        "You answered everything. Now it gets put together.",
        "Reading your answers back against each other.",
        "The pattern is clearer than you probably expected.",
    ],
}

# Random angles — injected per scenario so every generation is different
_QUESTION_ANGLES = [
    "Focus on the physical tension in the moment — what the body does before the decision is made.",
    "Focus on the moment right before — the anticipation, not the act.",
    "Focus on what hasn't been said out loud yet but is clearly being thought.",
    "Focus on the honesty required to answer this truthfully.",
    "Focus on what giving in to this would actually feel like.",
    "Focus on the desire itself — specific, embodied, not abstract.",
    "Focus on the secret being kept and what keeping it costs.",
    "Focus on what it would feel like to finally stop pretending this isn't interesting.",
    "Focus on the gap between what was said and what was meant.",
    "Focus on the version of themselves they're not showing their partner.",
    "Focus on what saying yes to this would actually require.",
    "Focus on the arousal that hasn't been admitted to yet.",
]

# Scenario themes — 28 distinct themes, shuffled per session so order varies
_SCENARIO_THEMES = [
    # Attraction within existing relationships
    "a slow attraction developing toward someone in their social circle while in a committed relationship — the kind that builds over months before it's undeniable",
    "realising they're physically attracted to their partner's close friend — and noticing the feeling is mutual",
    "discovering their partner has been fantasising about someone specific — and being more turned on than upset",

    # Fantasy and desire
    "a recurring sexual fantasy they've never acted on but can't stop thinking about — specific enough that they know exactly how it would go",
    "wanting to be completely sexually dominated — or to completely dominate someone — and not knowing how to bring it up",
    "a kink they discovered accidentally that they now think about constantly",
    "watching a type of content they'd never admit to and realising it reveals something true about what they actually want",

    # Non-monogamy and openness
    "a couple who keeps having the same hypothetical conversation about opening their relationship — and both of them know it's not really hypothetical anymore",
    "being genuinely excited at the thought of their partner sleeping with someone else — and not knowing what to do with that feeling",
    "wanting to bring a third person into their sex life and not knowing how to start the conversation",
    "an open relationship arrangement that went further than either person expected — and both want it to happen again",

    # Encounters and temptation
    "a near-encounter with someone they'd been attracted to for years — it almost happened, and the fact that it didn't still comes back",
    "meeting someone and immediately, viscerally knowing exactly how this could go if both of them wanted it to",
    "a work trip where something almost happened — the line was never technically crossed but it came closer than they've admitted",
    "running into an ex who clearly still wants them — and realising the feeling isn't entirely gone",

    # Communication and honesty gaps
    "wanting something specific in bed they've never asked for — not because they're ashamed, but because asking would mean admitting how much they want it",
    "the sex life they actually want versus the one they've settled into — and the distance between the two",
    "a boundary that has shifted without either person formally acknowledging it",
    "something they said no to years ago that they'd say yes to now — and haven't told their partner",

    # Group and voyeurism
    "genuinely imagining what sex with multiple people at the same time would feel like — not as an abstract idea but as a specific scenario",
    "being watched during sex — by a third person who's there specifically to watch — and finding the idea more compelling than expected",
    "watching their partner with someone else and being turned on rather than threatened",

    # Identity and self-discovery
    "attraction to someone of a gender they haven't been with before — and not being sure what to do with that",
    "discovering something about their own desires from a single moment of arousal they didn't expect",
    "the version of themselves sexually that their partner has never seen — and whether they want to show it",

    # Specific charged situations
    "a massage that both people let go further than it should have — and neither has mentioned it since",
    "a moment during a group social situation where eye contact with someone said everything that wasn't said out loud",
    "a sexting conversation that escalated faster than intended — and they weren't actually trying to stop it",
]

# Single life — nobody assumed to have a partner
_SINGLE_THEMES = [
    "a casual link-up who asks, mid-kiss, what they've always wanted to try and never has",
    "a couple they met on a night out inviting them home — both of them, together",
    "a first date that skips dinner entirely because the texts beforehand already said everything",
    "someone across a party who hasn't stopped looking all night finally coming over to whisper exactly what they want",
    "a friend with benefits suggesting a blindfold, and the rules being that they can't ask what comes next",
    "a dating-app match who opens with the most specific, filthy message they've ever received — and it's exactly their type",
]

# Themes that assume the reader already has a partner
_PARTNER_WORDS = ("partner", "relationship", "couple who", "settled into", "either person formally")


def _audience(profile: dict | None) -> str:
    """Which scenarios fit: "single", "partnered", or "open" (poly: all of them)."""
    rel = (profile or {}).get("relationship_status", "")
    if rel in ("partnered", "married"):
        return "partnered"
    return "open" if rel == "poly" else "single"


def _themes_for(audience: str) -> list:
    if audience == "single":
        return [t for t in _SCENARIO_THEMES if not any(w in t for w in _PARTNER_WORDS)] + _SINGLE_THEMES
    if audience == "partnered":
        return list(_SCENARIO_THEMES)
    return _SCENARIO_THEMES + _SINGLE_THEMES


# Gender-neutral rule enforced in every 
_GENDER_NEUTRAL_RULE = """CRITICAL — gender-neutral and orientation-inclusive:
- Use ONLY: 'you', 'your partner', 'someone', 'they', 'them', 'their', 'this person', 'another person'
- NEVER use: he, she, him, her, his, hers, boyfriend, girlfriend, husband, wife, man, woman, guy, girl
- The scenario and question must feel equally personal to ANY reader regardless of their gender, their partner's gender, or their sexual orientation
- Read every sentence back and ask: could a gay person, a straight person, a bisexual person, a non-binary person all see themselves in this equally? If not, rewrite."""

_ANSWER_OPTION_RULE = """ANSWER OPTIONS — sexually honest, not sanitised:
- Each option must feel like a private admission someone would think but never say in public
- The reader should recognise themselves in exactly one option and feel slightly caught out
- Be specific about desire — not 'I'd be open to it' but 'I've already thought about exactly how it would go'
- Use first person: 'I' and 'me'
- Be sexual where the scenario calls for it — don't water it down
- Each option: one sentence, max 22 words
- Scale: pts 0 = firm honest boundary | pts 2 = turned on but holding back | pts 3 = already thinking about the specifics | pts 5 = decided, or has been here before"""


# ─── CSS ──────────────────────────────────────────────────────────────────────

def inject_css():
    st.html("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d; --border:#2a2a35;
  --lime:#c6ff00; --magenta:#ff2d78; --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}
.stApp { background:var(--bg) !important; }
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container { padding-top:2rem !important; max-width:820px !important; }
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
  color:var(--lime) !important; box-shadow:none !important;
}
.stButton > button {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important; border-radius:3px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1.5px !important; text-transform:uppercase !important;
  transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover { border-color:var(--lime) !important; color:var(--lime) !important; }
.stButton > button[kind="primary"] {
  background:var(--magenta) !important; color:#fff !important;
  border-color:var(--magenta) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#ff5590 !important; box-shadow:0 0 20px rgba(255,45,120,0.25) !important;
}
.stButton > button:disabled { opacity:0.35 !important; cursor:not-allowed !important; }
.stProgress > div > div > div { background:var(--magenta) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
div[data-testid="stRadio"] > label { display:none !important; }
div[data-testid="stRadioGroup"] { gap:8px !important; flex-direction:column !important; }
div[data-testid="stRadio"], div[data-testid="stRadioGroup"],
div[data-testid="stRadioGroup"] > div { width:100% !important; }
label[data-testid="stRadioOption"] {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:3px !important; padding:12px 16px !important; margin:0 !important;
  cursor:pointer !important; transition:all 0.15s !important; width:100% !important;
}
label[data-testid="stRadioOption"], label[data-testid="stRadioOption"] p {
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
  letter-spacing:normal !important; text-transform:none !important;
  color:var(--soft) !important; line-height:1.55 !important;
}
label[data-testid="stRadioOption"]:hover {
  border-color:var(--lime) !important; background:#1c1c22 !important;
}
label[data-testid="stRadioOption"]:hover p { color:var(--text) !important; }
label[data-testid="stRadioOption"]:has(input:checked) {
  background:rgba(255,45,120,0.12) !important; border-color:var(--magenta) !important;
  border-left-width:3px !important;
}
label[data-testid="stRadioOption"]:has(input:checked) p { color:var(--text) !important; }
@keyframes card-enter {
  from { opacity:0; transform:translateY(14px) scale(0.98); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}
.enter-card { animation:card-enter 0.3s cubic-bezier(0.19,1,0.22,1) both; }
.live-dot {
  display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--magenta); animation:pulse-dot 1.4s infinite;
  vertical-align:middle; margin-right:6px;
}
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }
@keyframes fade-in { from{opacity:0} to{opacity:1} }
.fade-in { animation:fade-in 0.5s ease both; }
</style>
""")


# ─── UID ──────────────────────────────────────────────────────────────────────

def _uid():
    u = st.session_state.get("user")
    if isinstance(u, dict):
        uid = u.get("id") or u.get("user_id")
        if uid:
            try: return int(uid)
            except (TypeError, ValueError): pass
    try:
        uid = st.session_state.get("user_id")
        if uid: return int(uid)
    except (TypeError, ValueError): pass
    return None

def _debug_uid_info():
    return (
        f"session_state['user']={repr(st.session_state.get('user'))} | "
        f"session_state['user_id']={repr(st.session_state.get('user_id'))} | "
        f"resolved={_uid()}"
    )

def _show_persistent_db_error():
    err = st.session_state.get("wwyd_db_error", "")
    if err:
        st.error(f"⚠️ DB: {err}")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_client():
    key = st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in Streamlit secrets.")
    return OpenAI(api_key=key)

def _safe_json(raw):
    try:
        return json.loads(raw.strip().replace("```json", "").replace("```", "").strip())
    except Exception:
        return None

def _hd_signal_str(hd_answers):
    lines = []
    for q in HIDDEN_DESIRE_QUESTIONS:
        oid = hd_answers.get(q["id"])
        if oid in ("yes", "strongly"):
            lines.append(f"{q['signal']}:{'strong' if oid == 'strongly' else 'yes'}")
    return ", ".join(lines) if lines else "none"

def _question_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


# ─── BACKGROUND PRE-GENERATION ────────────────────────────────────────────────
# Kick off scenario generation at module load so questions are ready
# before the user finishes reading the intro screen.

# One batch per audience (single / partnered / open), so nobody single gets partner scenarios.

_prefetch_lock   = threading.Lock()
_prefetch_result = {}  # audience → list[scenario] once done | "loading" | "error"
_AUDIENCES = ("single", "partnered", "open")
_AUDIENCE_PROFILE = {"single": {"relationship_status": "single"},
                     "partnered": {"relationship_status": "partnered"},
                     "open": {"relationship_status": "poly"}}

def _run_prefetch(audience: str):
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if not key:
            with _prefetch_lock:
                _prefetch_result[audience] = "error"
            return
        scenarios = _generate_all_scenarios(key, _AUDIENCE_PROFILE[audience])
        with _prefetch_lock:
            _prefetch_result[audience] = scenarios
    except Exception:
        with _prefetch_lock:
            _prefetch_result[audience] = "error"

def _ensure_prefetch_started(audiences=_AUDIENCES):
    with _prefetch_lock:
        todo = [a for a in audiences if a not in _prefetch_result]
        for a in todo:
            _prefetch_result[a] = "loading"
    for a in todo:
        threading.Thread(target=_run_prefetch, args=(a,), daemon=True).start()

_ensure_prefetch_started()


# ─── SCENARIO GENERATION ──────────────────────────────────────────────────────

def _generate_one_scenario(theme: str, slot: int, api_key: str, profile: dict = None) -> dict | None:
    """Generate a single scenario + question. Personalized to user profile."""
    if profile is None:
        profile = {}
    
    client = OpenAI(api_key=api_key)
    angle  = random.choice(_QUESTION_ANGLES)

    # Build profile context for personalization
    rel_status = profile.get("relationship_status", "")
    rel_length = profile.get("relationship_length", "")
    gender = profile.get("gender_identity", "")
    attraction = profile.get("attraction", "")
    
    profile_context = ""
    if rel_status:
        profile_context += f"- Relationship: {rel_status}"
        if rel_length:
            profile_context += f" ({rel_length})"
        profile_context += "\n"
    if attraction:
        profile_context += f"- Attraction: {attraction}\n"
    
    if profile_context:
        profile_context = f"User context (for personalization):\n{profile_context}\nMake this scenario feel specifically written for someone in this situation."
    else:
        profile_context = "Create a universally resonant scenario."
    if _audience(profile) == "single":
        profile_context += "\nThe reader is SINGLE: never mention their partner, relationship or spouse. Use a link-up, a date, a match, a stranger or a friend instead."

    prompt = f"""You write scenarios for an adult desire quiz on an 18+ platform. No filters.

{profile_context}

Create ONE scenario about: {theme}
Angle: {angle}

TONE: A recognisable real-life moment that crosses a line.
A Tuesday night that went somewhere it shouldn't. Not fantasy. Not fiction.

RULES — non-negotiable:
- EXACTLY 2 sentences. No more.
- Present tense. Second person ("you").
- Explicit. Say what happened or what was wanted. Don't imply, don't euphemise.
- Concrete nouns. Specific actions. Real locations (bedroom, car, office, hotel room, bathroom).
- BANNED WORDS: lingering, breathless, tension, electricity, pulse, warmth, waves, sensation, blur, wonder, dance, thicken
- No metaphors. No em-dashes for drama. No ellipses.
- Stop at the moment of decision — not before, not after.

EXAMPLES OF WHAT YOU'RE WRITING:
- "You've been sleeping with your partner's friend for six weeks and you just got invited to their birthday dinner together."
- "You told them to stop, they slowed down just enough to check your face, and you pulled them back in."
- "Your coworker texts you at midnight asking if you're awake and you know exactly what it means because it's happened before."
- "You're in the bathroom at a party and someone you've wanted for two years knocks and asks if they can come in."

{_GENDER_NEUTRAL_RULE}

{_ANSWER_OPTION_RULE}

Return ONLY valid JSON:
{{"title":"Max 7 words. A statement. Could be a text message subject line.","text":"Exactly 2 sentences. Explicit. Specific. Present tense. Second person.","prompt":"One blunt question. Max 15 words. About what they actually want or did.","opts":[{{"t":"...","pts":0}},{{"t":"...","pts":2}},{{"t":"...","pts":3}},{{"t":"...","pts":5}}]}}"""
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=480,
        temperature=0.95,
        messages=[{"role": "user", "content": prompt}],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, dict) or not data.get("prompt") or len(data.get("opts", [])) < 4:
        return None
    return {
        "title":    data.get("title", "A scenario"),
        "text":     data.get("text", ""),
        "prompt":   data["prompt"],
        "opts":     data["opts"],
        "flair":    "Scenario",
        "avatar":   "V",
        "source":   "ai",
    }


def _generate_all_scenarios(api_key: str, profile: dict = None) -> list:
    """Generate all SCENARIO_COUNT scenarios in parallel."""
    if profile is None:
        profile = {}
    
    pool   = _themes_for(_audience(profile))
    themes = random.sample(pool, min(SCENARIO_COUNT, len(pool)))

    results = [None] * SCENARIO_COUNT

    def _gen(idx, theme):
        try:
            s = _generate_one_scenario(theme, idx, api_key, profile)
            return idx, s
        except Exception:
            return idx, None

    with ThreadPoolExecutor(max_workers=SCENARIO_COUNT) as pool:
        futures = {pool.submit(_gen, i, t): i for i, t in enumerate(themes)}
        try:
            for future in as_completed(futures, timeout=30):
                try:
                    idx, s = future.result()
                    results[idx] = s
                except Exception:
                    pass
        except Exception:
            pass

    # Filter Nones, fill any gaps with a safe fallback
    scenarios = [s for s in results if s]
    scenarios += _fallback_scenarios(SCENARIO_COUNT - len(scenarios),
                                     exclude_titles=[s.get("title") for s in scenarios],
                                     audience=_audience(profile))

    return scenarios[:SCENARIO_COUNT]


# Used when AI generation is unavailable: enough distinct scenarios that a
# quiz never repeats one.
_FALLBACK_SCENARIOS = [
    {
        "title": "4am on the couch",
        "text": "You and someone you're close to have been talking until 4am, and their hand has been on your thigh for the last hour. Neither of you has mentioned it, and neither of you has moved.",
        "prompt": "What do you do next?",
        "opts": [
            {"t": "Stand up and say goodnight. Some lines stay uncrossed.", "pts": 0},
            {"t": "Stay exactly where I am and let them decide.", "pts": 2},
            {"t": "Put my hand on theirs so they know I've noticed.", "pts": 3},
            {"t": "Kiss them. I've been waiting an hour for an excuse.", "pts": 5},
        ],
    },
    {
        "title": "The fantasy that keeps coming back",
        "text": "There's a specific scenario you've thought about more than once. It involves a specific type of situation, a specific dynamic. You didn't choose it — it just keeps returning.",
        "prompt": "How far have you actually let yourself go with this in your head?",
        "opts": [
            {"t": "I shut it down when it comes up. It's not something I want to explore.", "pts": 0},
            {"t": "I've thought about it but kept it surface level — never the full scenario.", "pts": 2},
            {"t": "I've played it out in detail. More than once.", "pts": 3},
            {"t": "I've played it out in detail and I'm actively looking for a way to make it real.", "pts": 5},
        ],
    },
    {
        "title": "Someone you probably shouldn't want",
        "text": "There's someone in your life — not a stranger, someone you interact with — that you're more attracted to than you've admitted. You've thought about what it would be like. You haven't done anything about it.",
        "prompt": "What's the most accurate thing about where you actually are with this?",
        "opts": [
            {"t": "I recognise the attraction and I'm not going to act on it. That's settled.", "pts": 0},
            {"t": "I notice it but I'm mostly good at not thinking about it.", "pts": 2},
            {"t": "I think about it more than I should and I'm not really trying to stop.", "pts": 3},
            {"t": "I've already thought through how it could happen. The attraction is mutual and we both know it.", "pts": 5},
        ],
    },

    {
        "title": "The text you almost sent",
        "text": "It's late and you've typed out exactly what you want to say to someone you shouldn't be texting. Your thumb is over send. You've done this before and deleted it every time.",
        "prompt": "What happens this time?",
        "opts": [
            {"t": "I delete it. Some things are better left in drafts.", "pts": 0},
            {"t": "I delete it, then screenshot the draft so I don't lose it.", "pts": 2},
            {"t": "I send something softer and wait to see if they bite.", "pts": 3},
            {"t": "I send it exactly as written. I'm done pretending.", "pts": 5},
        ],
    },
    {
        "title": "Your partner asks what you really want", "who": "partnered",
        "text": "Your partner asks, sincerely, if there's anything you've always wanted to try and never said. They mean it. They're waiting for an answer.",
        "prompt": "What do you actually tell them?",
        "opts": [
            {"t": "Honestly, nothing. What we have is what I want.", "pts": 0},
            {"t": "Something small and safe, and I keep the real answer to myself.", "pts": 2},
            {"t": "A hint of the real thing, to see how they react.", "pts": 3},
            {"t": "The whole thing, in detail. I've been waiting for them to ask.", "pts": 5},
        ],
    },
    {
        "title": "The hotel bar, the last round",
        "text": "You're away for work and someone at the hotel bar has been talking to you for two hours. They mention their room number without being asked.",
        "prompt": "Where's your head when you get in the elevator?",
        "opts": [
            {"t": "On my own floor. It was a nice conversation and that's all.", "pts": 0},
            {"t": "Flattered, and replaying it more than I'd admit.", "pts": 2},
            {"t": "Doing the maths on what I'd say if I knocked.", "pts": 3},
            {"t": "I already pressed their floor.", "pts": 5},
        ],
    },
    {
        "title": "Someone wants to watch", "who": "partnered",
        "text": "Someone you trust tells you they'd love to just watch you with your partner. No touching, no pressure. They'd only be in the room.",
        "prompt": "What's your honest first reaction?",
        "opts": [
            {"t": "A clear no. That's not for me.", "pts": 0},
            {"t": "No, but I noticed I didn't hate the idea.", "pts": 2},
            {"t": "I've already pictured how it would go.", "pts": 3},
            {"t": "I'd want to set a date.", "pts": 5},
        ],
    },
    {
        "title": "The ex who still knows you",
        "text": "An ex messages out of nowhere: they still think about one specific night. You know exactly which one. You think about it too.",
        "prompt": "How do you reply?",
        "opts": [
            {"t": "I don't. That door is closed.", "pts": 0},
            {"t": "Something friendly and vague, and I reread their message twice.", "pts": 2},
            {"t": "I admit I remember it, and let them take the next step.", "pts": 3},
            {"t": "I ask when they're free.", "pts": 5},
        ],
    },
    {
        "title": "Three of you, one night", "who": "partnered",
        "text": "You and your partner have joked about a threesome for months. Tonight a friend you both like stays over, and the joke suddenly isn't one.",
        "prompt": "What do you want to happen?",
        "opts": [
            {"t": "Nothing. The joke was a joke.", "pts": 0},
            {"t": "I'd be curious, but I'd never be the one to start it.", "pts": 2},
            {"t": "I'd give my partner a look that says I'm in if they are.", "pts": 3},
            {"t": "I'd make the first move myself.", "pts": 5},
        ],
    },
    {
        "title": "Handing over control",
        "text": "Someone you're seeing asks if you'd let them take complete control for one night: what you wear, what you do, when you're allowed to finish.",
        "prompt": "What's your answer?",
        "opts": [
            {"t": "No. I don't hand over that kind of control.", "pts": 0},
            {"t": "Maybe, if we talked it through a lot first.", "pts": 2},
            {"t": "Yes, and I'm already thinking about what they'd make me do.", "pts": 3},
            {"t": "Yes. I've wanted someone to ask me that for years.", "pts": 5},
        ],
    },
    {
        "title": "The open-relationship conversation", "who": "partnered",
        "text": "Your partner brings up opening the relationship, very carefully, like they've rehearsed it. They say they'd only do it if you wanted to as well.",
        "prompt": "Where do you land?",
        "opts": [
            {"t": "It's a no. Monogamy matters to me.", "pts": 0},
            {"t": "I say I'll think about it, and I actually do.", "pts": 2},
            {"t": "I'm relieved, because I've been thinking the same thing.", "pts": 3},
            {"t": "I already have someone in mind.", "pts": 5},
        ],
    },
    {
        "title": "Two of them, one invitation", "who": "single",
        "text": "A couple you've been dancing with all night lean in and ask if you want to come home with them. They're both looking at you, and they've clearly talked about this already.",
        "prompt": "What's your honest answer?",
        "opts": [
            {"t": "No thanks. One person at a time is my limit.", "pts": 0},
            {"t": "I say no, but I think about it the whole way home.", "pts": 2},
            {"t": "I ask what exactly they have in mind.", "pts": 3},
            {"t": "I'm already calling the car.", "pts": 5},
        ],
    },
    {
        "title": "The first message", "who": "single",
        "text": "A new match skips hello and tells you, in detail, what they want to do to you on the first date. It's exactly your type of filthy.",
        "prompt": "How do you reply?",
        "opts": [
            {"t": "I unmatch. Say hi first.", "pts": 0},
            {"t": "Something playful that doesn't answer, and I read it twice.", "pts": 2},
            {"t": "I tell them what I'd add to their list.", "pts": 3},
            {"t": "I ask if they're free tonight.", "pts": 5},
        ],
    },
    {
        "title": "Dinner is cancelled", "who": "single",
        "text": "An hour before your first date they text: forget the restaurant, come straight to mine. You both know what that means.",
        "prompt": "What do you do?",
        "opts": [
            {"t": "Insist on the restaurant. I like to meet people first.", "pts": 0},
            {"t": "Go to the restaurant, but I'm not planning to stay long.", "pts": 2},
            {"t": "Go to theirs, and dress for it.", "pts": 3},
            {"t": "Go to theirs. I was going to suggest it myself.", "pts": 5},
        ],
    },
    {
        "title": "The blindfold rule", "who": "single",
        "text": "Your friend with benefits pulls out a blindfold and says tonight you don't get to see or ask what comes next. You only get to say stop.",
        "prompt": "What's your first reaction?",
        "opts": [
            {"t": "No. I need to see what's happening.", "pts": 0},
            {"t": "Nervous, but I let them put it on.", "pts": 2},
            {"t": "Already turned on before it's even tied.", "pts": 3},
            {"t": "I've been hoping someone would ask me this.", "pts": 5},
        ],
    },
    {
        "title": "Across the room", "who": "single",
        "text": "Someone at the party has been watching you all night. They finally walk over, lean in and whisper exactly what they want to do to you in the bathroom.",
        "prompt": "Where does this go?",
        "opts": [
            {"t": "Nowhere. I laugh it off and find my friends.", "pts": 0},
            {"t": "I tell them to get my number first.", "pts": 2},
            {"t": "I tell them to go first and I'll follow in a minute.", "pts": 3},
            {"t": "I take their hand and lead the way.", "pts": 5},
        ],
    },
    {
        "title": "What you watch when you're alone",
        "text": "You catch yourself watching the same kind of thing over and over, something that doesn't match how you'd describe yourself.",
        "prompt": "What do you make of it?",
        "opts": [
            {"t": "Nothing. It's fantasy and it stays fantasy.", "pts": 0},
            {"t": "It's a bit uncomfortable, so I try not to think about it.", "pts": 2},
            {"t": "It's telling me something, and I'm starting to listen.", "pts": 3},
            {"t": "I know exactly what it means, and I want to try it for real.", "pts": 5},
        ],
    },
]


def _fallback_scenarios(n: int, exclude_titles=(), audience: str = "open") -> list:
    """n distinct static scenarios (gender-neutral) that fit this person's situation."""
    pool = [f for f in _FALLBACK_SCENARIOS if f["title"] not in set(exclude_titles)
            and (audience == "open" or f.get("who", audience) == audience)]
    picked = random.sample(pool, min(n, len(pool)))
    return [{k: v for k, v in f.items() if k != "who"} for f in picked]


def get_scenarios() -> list:
    """Return prefetched scenarios for this person's situation if ready, else generate now."""
    profile  = st.session_state.get("wwyd_profile", {})
    audience = _audience(profile)
    deadline = time.time() + 8
    while time.time() < deadline:
        with _prefetch_lock:
            val = _prefetch_result.get(audience)
        if val not in (None, "loading"):
            break
        time.sleep(0.05)

    with _prefetch_lock:
        val = _prefetch_result.get(audience)
        if val and val not in ("loading", "error"):
            del _prefetch_result[audience]      # each batch is used once
    if val and val not in ("loading", "error"):
        _ensure_prefetch_started((audience,))
        return val

    # Fallback: generate now with profile
    key = st.secrets.get("OPENAI_API_KEY", "")
    if key:
        try:
            return _generate_all_scenarios(key, profile)
        except Exception:
            pass
    return _fallback_scenarios(SCENARIO_COUNT, audience=audience)


# ─── PROFILE + CATEGORY SCORING ───────────────────────────────────────────────

_SIGNAL_CATEGORY_MAP = {
    "verbal_arousal":       ["Dirty Talk", "POV", "Solo Female", "Solo Male"],
    "desired_intensity":    ["Hardcore", "Rough Sex", "Female Orgasm", "Romantic"],
    "authentic_exposure":   ["Amateur", "Verified Couples", "Sensual"],
    "power_dynamic":        ["Bondage", "Role Play"],
    "archetype_attraction": ["Muscular Men", "MILF", "Mature", "Babe"],
    "stranger_fantasy":     ["Public", "Massage", "Casting"],
    "dom_active":           ["Bondage", "Strap On", "Rough Sex"],
    "sub_active":           ["Bondage", "Rough Sex", "Deepthroat"],
    "taboo_arousal":        ["Fetish", "Cuckold", "Role Play"],
    "exhib_active":         ["Public", "Webcam", "Striptease", "Voyeur"],
    "secret_fantasy":       ["Fetish", "Role Play", "Cosplay", "Toys"],
    "group_sex":            ["Threesome", "Orgy", "Gangbang", "Party"],
    "taboo_fixation":       ["Fetish", "Feet"],
    "elaborated_fantasy":   ["Role Play", "Cosplay", "Virtual Reality", "Romantic"],
    "unnamed_fixation":     ["Fetish", "Toys"],
}

# Who you're into (and who you are) nudges the fingerprint, so it doesn't read the same for everyone
_INTO_CATEGORIES = {
    "men":    ["Muscular Men", "Big Dick", "Solo Male", "Blowjob", "Handjob"],
    "women":  ["Solo Female", "Babe", "Pussy Licking", "Big Tits", "Big Ass"],
    "all":    ["Bisexual Male", "Lesbian", "Threesome", "Transgender", "Solo Male", "Solo Female"],
    "varies": ["Bisexual Male", "Lesbian", "Threesome", "Transgender"],
    "unclear": ["Bisexual Male", "Lesbian", "Sensual", "Transgender"],
}
_SELF_CATEGORIES = {
    "f":  ["Female Orgasm", "Popular With Women", "Romantic", "Toys"],
    "nb": ["Transgender", "Strap On", "Toys"],
}


def _identity_boosts(profile: dict | None) -> dict:
    """Category → bonus from the quiz intake (gender, who they're into)."""
    profile = profile or {}
    me, into = profile.get("gender_identity", ""), profile.get("attraction", "")
    boosts = {}
    for c in _INTO_CATEGORIES.get(into, []):
        boosts[c] = boosts.get(c, 0) + 2
    for c in _SELF_CATEGORIES.get(me, []):
        boosts[c] = boosts.get(c, 0) + 1
    if into == "men" and me == "m":
        boosts["Gay"] = boosts.get("Gay", 0) + 3
    if into == "women" and me == "f":
        boosts["Lesbian"] = boosts.get("Lesbian", 0) + 3
    return boosts


def _local_profile_and_categories(result_type, openness_pct, hd_answers, profile=None) -> dict:
    """No-AI fallback: score categories from hidden-desire signals + openness.
    Deterministic per answer set so reruns give the same profile."""
    strong = [q["signal"] for q in HIDDEN_DESIRE_QUESTIONS if hd_answers.get(q["id"]) == "strongly"]
    mild   = [q["signal"] for q in HIDDEN_DESIRE_QUESTIONS if hd_answers.get(q["id"]) == "yes"]

    seed = hash(tuple(sorted(hd_answers.items()))) & 0xFFFF
    rng  = random.Random(seed)
    base = 2 + round(openness_pct / 33)          # 2–5 baseline from openness

    boosts = _identity_boosts(profile)
    scores = {}
    for cat in ALL_PLATFORM_CATEGORIES:
        s = base + rng.randint(-1, 1) + boosts.get(cat, 0)
        for sig in strong:
            if cat in _SIGNAL_CATEGORY_MAP.get(sig, []):
                s += 4
        for sig in mild:
            if cat in _SIGNAL_CATEGORY_MAP.get(sig, []):
                s += 2
        scores[cat] = max(0, min(10, s))

    scored = sorted(
        [{"name": c, "score": scores[c]} for c in ALL_PLATFORM_CATEGORIES],
        key=lambda x: -x["score"],
    )
    top = [c["name"] for c in scored[:5]]
    recs = [
        f"Your strongest pull is toward {top[0]} — lean into it instead of circling it.",
        f"{top[1]} keeps showing up in your answers. That's not an accident.",
        f"You'd probably enjoy {top[2]} more than you'd admit out loud.",
        f"There's a quieter interest in {top[3]} worth exploring on your own terms.",
        f"{top[4]} is your wildcard — the one you haven't fully named yet.",
    ]
    return {
        "ranked_categories": scored,
        "top25_names":       [c["name"] for c in scored[:25]],
        "recommendations":   recs,
        "insight":           f"You read as {result_type['name']}. {result_type['meta']} The pattern in your answers is more consistent than you think.",
    }


def generate_profile_and_categories(result_type, openness_pct, hd_answers,
                                    questions, answers, client, profile=None) -> dict:
    if client is None:
        return _local_profile_and_categories(result_type, openness_pct, hd_answers, profile)
    pos, neg = [], []
    for qi, ai in enumerate(answers):
        if ai is None or qi >= len(questions): continue
        q   = questions[qi]
        opt = q.get("opts", [])
        if ai >= len(opt): continue
        pts  = opt[ai].get("pts", 0) if isinstance(opt[ai], dict) else 0
        text = (opt[ai].get("t", "") if isinstance(opt[ai], dict) else "")[:60]
        if pts >= 3:
            pos.append(f'"{q.get("title","")[:40]}": {text}')
        elif pts == 0:
            neg.append(f'"{q.get("title","")[:40]}": {text}')

    pos_str = "; ".join(pos[:4]) or "none"
    neg_str = "; ".join(neg[:4]) or "none"

    strong_signals = [q["signal"] for q in HIDDEN_DESIRE_QUESTIONS if hd_answers.get(q["id"]) == "strongly"]
    mild_signals   = [q["signal"] for q in HIDDEN_DESIRE_QUESTIONS if hd_answers.get(q["id"]) == "yes"]

    prompt = (
        f"You are a desire profile analyst for an 18+ adult platform called Hidden.\n"
        f"Write a profile that feels uncomfortably accurate — like it was written specifically for this person.\n\n"
        f"User data:\n"
        f"- Openness archetype: {result_type['name']} ({openness_pct}% openness index)\n"
        f"- Strong hidden desire signals: {', '.join(strong_signals) or 'none'}\n"
        f"- Present hidden desire signals: {', '.join(mild_signals) or 'none'}\n"
        f"- Resonated with: {pos_str}\n"
        f"- Rejected (DO NOT recommend these themes): {neg_str}\n"
        f"- Their gender: {(profile or {}).get('gender_identity') or 'unknown'}; into: {(profile or {}).get('attraction') or 'unknown'}. "
        f"Score as someone of that gender who is into those people would actually watch — not a default straight-male list.\n\n"
        f"Tasks — return ONE JSON object with exactly these keys:\n\n"
        f'1. "ranked_categories": Score EVERY category 0-10 against this person\'s actual desires. '
        f"Rejected themes get 0. Be specific — not everything scores 5+.\n"
        f"   Categories: {json.dumps(ALL_PLATFORM_CATEGORIES)}\n\n"
        f'2. "recommendations": Exactly 5 items. Rules:\n'
        f"   - Write like you know them\n"
        f"   - Each rec should feel like something they're already turned on by but haven't named\n"
        f"   - Gender-neutral — no he/she/him/her/boyfriend/girlfriend\n"
        f"   - 1-2 sentences. The second should add something unexpected.\n"
        f"   - Don't recommend anything in the rejected list\n\n"
        f'3. "insight": One sentence, 15-25 words. The single most accurate thing about their desire profile. '
        f"Should feel like something they'd read twice and not share.\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{"ranked_categories":{{"CategoryName":score,...}},'
        f'"recommendations":["...","...","...","...","..."],'
        f'"insight":"..."}}'
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=2200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw  = resp.choices[0].message.content.strip()
        data = _safe_json(raw)
        if not isinstance(data, dict):
            raise ValueError("Profile generation returned invalid JSON")
    except Exception:
        return _local_profile_and_categories(result_type, openness_pct, hd_answers, profile)

    raw_scores = data.get("ranked_categories", {})
    scored = sorted(
        [{"name": cat, "score": int(raw_scores.get(cat, 0))} for cat in ALL_PLATFORM_CATEGORIES],
        key=lambda x: -x["score"],
    )
    return {
        "ranked_categories": scored,
        "top25_names":       [c["name"] for c in scored[:25]],
        "recommendations":   data.get("recommendations", [])[:5],
        "insight":           data.get("insight", ""),
    }


# ─── COMMUNITY PULSE ──────────────────────────────────────────────────────────

def _render_community_pulse(q_hash: str, chosen_idx: int, opt_labels: list, slots: list = None):
    """slots[i] is the stored slot of displayed option i (answers are shuffled)."""
    slots = slots or list(range(len(opt_labels)))
    try:
        import database as db
        # Streamlit reruns on every click, so only count the first answer per question
        recorded = st.session_state.setdefault("wwyd_pulse_shown", {})
        if q_hash not in recorded:
            db.record_community_answer(q_hash, slots[chosen_idx])
            recorded[q_hash] = slots[chosen_idx]
        stored = db.get_community_answers(q_hash)
        tallies = {i: stored.get(slot, 0) for i, slot in enumerate(slots)}
    except Exception:
        return

    total = sum(tallies.values())
    if total < 3:
        return

    percentages  = {i: round(tallies.get(i, 0) / total * 100) for i in range(len(opt_labels))}
    expected     = 100 // len(opt_labels)
    surprise_idx = max(percentages, key=lambda i: abs(percentages[i] - expected))
    surprise_pct = percentages[surprise_idx]

    if surprise_pct > 50:
        hook = f"More than half said: <em>{opt_labels[surprise_idx][:60]}…</em>"
    elif surprise_pct < 10:
        hook = f"Almost nobody said: <em>{opt_labels[surprise_idx][:60]}…</em>"
    elif surprise_idx == 0 and surprise_pct > 35:
        hook = f"{surprise_pct}% closed the door completely."
    elif surprise_idx == len(opt_labels) - 1 and surprise_pct > 35:
        hook = f"{surprise_pct}% were fully on board. Higher than you'd expect."
    else:
        hook = "The split here was more even than most questions."

    st.html(f"""
<div style="margin-top:20px; margin-bottom:6px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">
    How {total} others answered
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--amber);
              font-style:italic; margin-bottom:12px; line-height:1.5;">{hook}</div>
</div>
""")
    for i, label in enumerate(opt_labels):
        pct      = percentages[i]
        is_me    = (i == chosen_idx)
        is_surp  = (i == surprise_idx)
        color    = "var(--lime)" if is_me else ("var(--amber)" if is_surp else "var(--border)")
        lcolor   = "var(--lime)" if is_me else ("var(--amber)" if is_surp else "var(--soft)")
        st.html(f"""
<div style="margin-bottom:10px;">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px; gap:8px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:{lcolor};
                max-width:82%; line-height:1.4;">
      {'▶ ' if is_me else ''}{label[:80]}{'…' if len(label)>80 else ''}
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:10px; color:{lcolor};
                flex-shrink:0; font-weight:{'700' if is_me else '400'};">{pct}%</div>
  </div>
  <div style="height:3px; background:var(--border); border-radius:2px;">
    <div style="width:{pct}%; height:100%; background:{color}; border-radius:2px;"></div>
  </div>
</div>
""")


# ─── STATE ────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "wwyd_phase":         "start",
    "wwyd_questions":     [],
    "wwyd_answers":       [],
    "wwyd_cur":           0,
    "wwyd_error":         "",
    "wwyd_db_error":      "",
    "wwyd_hd_cur":        0,
    "wwyd_hd_answers":    {},
    "wwyd_result_type":   {},
    "wwyd_openness_pct":  0,
    "wwyd_total_pts":     0,
    "wwyd_recs":          [],
    "wwyd_ranked_cats":   [],
    "wwyd_top25":         [],
    "wwyd_selected_cats": [],
    "wwyd_pulse_shown":   {},
    "wwyd_insight":       "",
    "wwyd_profile":       {},
}

def init_state():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _wipe():
    for k in list(st.session_state.keys()):
        if k.startswith("wwyd_"):
            del st.session_state[k]

def hard_reset():
    _wipe()
    init_state()
    _ensure_prefetch_started()
    st.rerun()


# ─── DB SAVES ─────────────────────────────────────────────────────────────────

def _save_to_db(phase: str):
    uid = _uid()
    if not uid:
        st.session_state.wwyd_db_error = f"Not saved ({phase}): could not resolve user ID. {_debug_uid_info()}"
        return
    try:
        import database as db
        slim_q = [{"title": q.get("title",""), "prompt": q.get("prompt",""), "opts": q.get("opts",[])}
                  for q in st.session_state.get("wwyd_questions", [])]
        saved = db.save_read_between_lines_v4(
            user_id=uid, phase=phase,
            result_name=st.session_state.get("wwyd_result_type",{}).get("name",""),
            result_meta=st.session_state.get("wwyd_result_type",{}).get("meta",""),
            openness_pct=st.session_state.get("wwyd_openness_pct",0),
            total_pts=st.session_state.get("wwyd_total_pts",0),
            questions=slim_q,
            answers={"phase1": st.session_state.get("wwyd_answers",[]),
                     "phase2": st.session_state.get("wwyd_hd_answers",{})},
            dim_scores={"ranked_cats": st.session_state.get("wwyd_ranked_cats",[])[:25],
                        "top25": st.session_state.get("wwyd_top25",[]),
                        "selected": st.session_state.get("wwyd_selected_cats",[]),
                        "hd_signals": _hd_signal_str(st.session_state.get("wwyd_hd_answers",{})),
                        "insight": st.session_state.get("wwyd_insight",""),
                        "shown_to_matches": True},   # taken under "matches see your result"
            recommendations=st.session_state.get("wwyd_recs",[]),
        )
        st.session_state.wwyd_db_error = "" if saved else f"DB save returned False ({phase})."
        if saved and isinstance(saved, int):
            st.session_state.wwyd_last_quiz_id = saved
    except Exception as e:
        st.session_state.wwyd_db_error = f"DB exception ({phase}): {e}"

def _update_selections_in_db(selected_cats: list):
    uid = _uid()
    if not uid:
        st.session_state.wwyd_db_error = f"Selection not saved: no user ID. {_debug_uid_info()}"
        return
    try:
        import database as db
        saved = db.update_rbtl_selected_categories(uid, selected_cats)
        st.session_state.wwyd_db_error = "" if saved else f"Selection update failed uid={uid}."
    except Exception as e:
        st.session_state.wwyd_db_error = f"Selection update exception: {e}"


# ─── HEADER ───────────────────────────────────────────────────────────────────

def _render_header():
    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
    Hidden · Desire Quiz
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(44px,9vw,68px);
              color:var(--text); letter-spacing:3px; line-height:0.92; margin-bottom:6px;">
    READ BETWEEN<br><span style="color:var(--magenta);">THE LINES</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:4px;">
    Real scenarios. Hidden desires. Your full profile.
  </div>
</div>
""")
    _show_persistent_db_error()


# ─── COMPAT DROP LOOKUP ──────────────────────────────────────────────────────

# ─── PHASE: START ─────────────────────────────────────────────────────────────

def render_start():
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    if not _uid():
        st.warning("Not logged in — results won't save to your profile.")


    st.html("""
<div class="enter-card">
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--magenta); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:8px;">
      <span class="live-dot"></span>Phase 1 · Scenarios
    </div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0;">
      7 AI-generated scenarios — different every time, built fresh for each session.
      Each one puts you directly inside a moment of desire or decision.
      After you answer, you'll see how everyone else responded — anonymously.
    </p>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--amber); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber); margin-bottom:8px;">
      Phase 2 · Hidden Desires
    </div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0;">
      10 statements that escalate from curiosity to the specific fantasies most people
      have never said out loud. The last one is your deepest.
    </p>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--cyan); border-radius:4px;
              padding:16px 18px; margin-bottom:20px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--cyan); margin-bottom:8px;">
      Phase 3 · Your Category Fingerprint
    </div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0;">
      Every real platform category scored against your actual answers.
      A one-line insight. You pick what goes into your profile.
    </p>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted); text-align:center; margin-bottom:14px;">
    18+ only · Matches who took it too see your result · Scenarios change every time
  </div>
</div>
""")
    if st.button("Begin →", use_container_width=True, type="primary", key="start_btn"):
        _wipe()
        st.session_state.wwyd_phase = "profile_intake"
        st.rerun()


# ─── PHASE: PROFILE INTAKE ────────────────────────────────────────────────────

def render_profile_intake():
    """Conversational profile intake — dark, bold, intimate."""
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:32px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">
    One quick step
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(32px,7vw,52px);
              color:var(--text); letter-spacing:3px; line-height:0.95; margin-bottom:8px;">
    HELP US KNOW<br><span style="color:var(--magenta);">YOUR WORLD</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    These answers personalize what you see. Not stored beyond this session.
  </div>
</div>
""")

    profile = st.session_state.wwyd_profile or {}

    # Q1: Relationship Status
    st.html("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:12px;">
    Relationship Status
  </div>
""")
    rel_opts = [
        ("single", "Single"),
        ("dating", "Dating"),
        ("partnered", "In a relationship"),
        ("married", "Married / Life partner"),
        ("poly", "Poly / Non-monogamous"),
        ("complicated", "It's complicated"),
    ]
    rel_val = profile.get("relationship_status", "")
    rel_chosen = st.radio(
        label="relationship",
        options=[o[0] for o in rel_opts],
        format_func=lambda x: next(o[1] for o in rel_opts if o[0] == x),
        index=[o[0] for o in rel_opts].index(rel_val) if rel_val in [o[0] for o in rel_opts] else 0,
        key="intake_rel",
        horizontal=False,
    )
    if rel_chosen != rel_val:
        profile["relationship_status"] = rel_chosen
        st.session_state.wwyd_profile = profile
    st.html("</div>")

    # Q2: Gender Identity
    st.html("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:12px;">
    Your Gender
  </div>
""")
    gnd_opts = [
        ("m", "Man"),
        ("f", "Woman"),
        ("nb", "Non-binary"),
        ("other", "Something else"),
        ("prefer_not", "Prefer not to say"),
    ]
    gnd_val = profile.get("gender_identity", "")
    gnd_chosen = st.radio(
        label="gender",
        options=[o[0] for o in gnd_opts],
        format_func=lambda x: next(o[1] for o in gnd_opts if o[0] == x),
        index=[o[0] for o in gnd_opts].index(gnd_val) if gnd_val in [o[0] for o in gnd_opts] else 0,
        key="intake_gnd",
        horizontal=False,
    )
    if gnd_chosen != gnd_val:
        profile["gender_identity"] = gnd_chosen
        st.session_state.wwyd_profile = profile
    st.html("</div>")

    # Q3: Attraction
    st.html("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:12px;">
    Who You're Into
  </div>
""")
    att_opts = [
        ("men", "Men"),
        ("women", "Women"),
        ("all", "All genders"),
        ("varies", "It depends / varies"),
        ("unclear", "Still figuring it out"),
    ]
    att_val = profile.get("attraction", "")
    att_chosen = st.radio(
        label="attraction",
        options=[o[0] for o in att_opts],
        format_func=lambda x: next(o[1] for o in att_opts if o[0] == x),
        index=[o[0] for o in att_opts].index(att_val) if att_val in [o[0] for o in att_opts] else 0,
        key="intake_att",
        horizontal=False,
    )
    if att_chosen != att_val:
        profile["attraction"] = att_chosen
        st.session_state.wwyd_profile = profile
    st.html("</div>")

    # Q4: Relationship Length (conditional)
    if rel_chosen in ("dating", "partnered", "married"):
        st.html("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:12px;">
    How Long?
  </div>
""")
        rel_len_opts = [
            ("new", "New (under 6 months)"),
            ("medium", "A few years"),
            ("long", "Long-term (3+ years)"),
        ]
        rel_len_val = profile.get("relationship_length", "")
        rel_len_chosen = st.radio(
            label="rel_length",
            options=[o[0] for o in rel_len_opts],
            format_func=lambda x: next(o[1] for o in rel_len_opts if o[0] == x),
            index=[o[0] for o in rel_len_opts].index(rel_len_val) if rel_len_val in [o[0] for o in rel_len_opts] else 0,
            key="intake_rel_len",
            horizontal=False,
        )
        if rel_len_chosen != rel_len_val:
            profile["relationship_length"] = rel_len_chosen
            st.session_state.wwyd_profile = profile
        st.html("</div>")

    # Q5: Comfort with desire talk
    st.html("""
<div style="margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:12px;">
    Being Honest About Desire
  </div>
""")
    hon_opts = [
        ("private", "I keep it to myself"),
        ("sometimes", "I open up sometimes"),
        ("open", "I'm pretty open about it"),
        ("very_open", "I'm fully transparent"),
    ]
    hon_val = profile.get("honesty_level", "")
    hon_chosen = st.radio(
        label="honesty",
        options=[o[0] for o in hon_opts],
        format_func=lambda x: next(o[1] for o in hon_opts if o[0] == x),
        index=[o[0] for o in hon_opts].index(hon_val) if hon_val in [o[0] for o in hon_opts] else 0,
        key="intake_hon",
        horizontal=False,
    )
    if hon_chosen != hon_val:
        profile["honesty_level"] = hon_chosen
        st.session_state.wwyd_profile = profile
    st.html("</div>")

    st.html("<br>")
    if st.button("Start Quiz →", use_container_width=True, type="primary", key="profile_intake_btn"):
        st.session_state.wwyd_phase = "loading"
        st.rerun()


def _shuffle_opts(q: dict) -> dict:
    """Show answers in random order so the most guarded one isn't always on top.
    Each option keeps its original slot in "i" for the community tallies."""
    opts = [dict(o, i=k) if isinstance(o, dict) else {"t": str(o), "pts": 0, "i": k}
            for k, o in enumerate(q.get("opts") or [])]
    random.shuffle(opts)
    return {**q, "opts": opts}


# ─── PHASE: LOADING ───────────────────────────────────────────────────────────

def render_loading():
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:24px;">BUILDING YOUR QUIZ</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, msg):
        ph_bar.progress(pct)
        ph_status.caption(msg)

    try:
        upd(10, "Generating personalized scenarios…")
        scenarios = [_shuffle_opts(q) for q in get_scenarios()]

        upd(100, "Ready.")
        time.sleep(0.1)
        st.session_state.wwyd_questions   = scenarios
        st.session_state.wwyd_answers     = [None] * len(scenarios)
        st.session_state.wwyd_cur         = 0
        st.session_state.wwyd_pulse_shown = {}
        st.session_state.wwyd_phase       = "quiz"
        st.rerun()

    except Exception:
        st.session_state.wwyd_error = "Couldn't load the scenarios — give it another try."
        st.session_state.wwyd_phase = "start"
        st.rerun()


# ─── PHASE: QUIZ ─────────────────────────────────────────────────────────────

def render_quiz():
    _show_persistent_db_error()
    questions = st.session_state.wwyd_questions
    cur       = st.session_state.wwyd_cur
    answers   = st.session_state.wwyd_answers

    if not questions or cur >= len(questions):
        st.session_state.wwyd_phase = "start"
        st.rerun()
        return

    if len(answers) < len(questions):
        answers = answers + [None] * (len(questions) - len(answers))
        st.session_state.wwyd_answers = answers

    q       = questions[cur]
    total   = len(questions)
    is_last = (cur == total - 1)
    q_hash  = _question_hash(q.get("prompt", q.get("title", str(cur))))

    segs = "".join(
        f'<div style="flex:1; height:3px; border-radius:2px; background:'
        f'{"var(--magenta)" if i < cur else "rgba(255,45,120,0.4)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 1 · Scenarios · {cur + 1} / {total}
</div>
<div style="display:flex; gap:3px; margin-bottom:20px;">{segs}</div>
""")

    st.html(f"""
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-radius:4px; overflow:hidden; margin-bottom:14px;">
  <div style="display:flex; align-items:center; gap:10px; padding:11px 16px;
              border-bottom:1px solid var(--border);">
    <div style="width:28px; height:28px; border-radius:50%; background:var(--magenta);
                color:#fff; display:flex; align-items:center; justify-content:center;
                font-family:'DM Sans',sans-serif; font-size:12px; font-weight:700; flex-shrink:0;">V</div>
    <div style="flex:1; min-width:0;">
      <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">Hidden</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">anonymous · now</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                padding:3px 8px; border:1px solid var(--border); color:var(--muted);
                text-transform:uppercase; border-radius:2px; flex-shrink:0;">Scenario</div>
  </div>
  <div style="padding:14px 16px 14px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:15px; font-weight:500;
                color:var(--text); line-height:1.5; margin-bottom:10px;">{_html.escape(str(q['title']))}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
                line-height:1.85;">{_html.escape(str(q['text']))}</div>
  </div>
</div>
<div style="font-family:'DM Sans',sans-serif; font-size:15px; font-style:italic;
            color:var(--amber); border-left:3px solid var(--amber); padding-left:14px;
            margin-bottom:18px; line-height:1.6;">{_html.escape(str(q['prompt']))}</div>
""")

    opt_labels  = [(opt["t"] if isinstance(opt, dict) else opt) for opt in q["opts"]]
    current_sel = answers[cur]

    chosen = st.radio(
        label="Your answer",
        options=list(range(len(opt_labels))),
        format_func=lambda i: opt_labels[i],
        index=current_sel,
        key=f"quiz_radio_{cur}",
        horizontal=False,
    )

    if chosen != current_sel:
        a = list(st.session_state.wwyd_answers)
        a[cur] = chosen
        st.session_state.wwyd_answers = a

    if chosen is not None:
        slots = [opt.get("i", k) if isinstance(opt, dict) else k for k, opt in enumerate(q["opts"])]
        _render_community_pulse(q_hash, chosen, opt_labels, slots)

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="quiz_back", use_container_width=True):
                st.session_state.wwyd_cur -= 1
                st.rerun()
    with col_next:
        btn_label = "Next: Hidden Desires →" if is_last else "Next →"
        answered  = st.session_state.wwyd_answers[cur] is not None
        if st.button(btn_label, key="quiz_next", disabled=not answered,
                     use_container_width=True, type="primary"):
            if is_last:
                st.session_state.wwyd_hd_cur = 0
                st.session_state.wwyd_phase  = "phase_transition"
            else:
                st.session_state.wwyd_cur += 1
            st.rerun()


# ─── PHASE: TRANSITION ────────────────────────────────────────────────────────

def render_phase_transition():
    line = random.choice(PHASE_TRANSITIONS["to_hidden_desires"])
    st.html(f"""
<div class="enter-card fade-in" style="text-align:center; padding:60px 20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:20px;">
    Phase 1 complete
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:20px; color:var(--text);
              line-height:1.6; max-width:380px; margin:0 auto 32px; font-style:italic;">
    {line}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--amber); margin-bottom:8px;">
    Phase 2 · Hidden Desires
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
              margin-bottom:32px;">10 statements. They escalate.</div>
</div>
""")
    if st.button("Continue →", use_container_width=True, type="primary", key="transition_btn"):
        st.session_state.wwyd_phase = "hidden_desires"
        st.rerun()


# ─── PHASE: HIDDEN DESIRES ────────────────────────────────────────────────────

def render_hidden_desires():
    _show_persistent_db_error()
    total   = len(HIDDEN_DESIRE_QUESTIONS)
    answers = st.session_state.wwyd_hd_answers
    cur     = max(0, min(st.session_state.wwyd_hd_cur, total - 1))
    st.session_state.wwyd_hd_cur = cur

    q       = HIDDEN_DESIRE_QUESTIONS[cur]
    sel_id  = answers.get(q["id"])
    is_last = (cur == total - 1)
    tier    = q.get("tier", 1)

    tier_colors = {1:"var(--soft)", 2:"var(--amber)", 3:"var(--magenta)", 4:"var(--magenta)", 5:"var(--lime)"}
    tier_labels = {1:"Warming up", 2:"Getting specific", 3:"The ones people don't say out loud", 4:"Deeper", 5:"Your deepest fantasy"}
    accent      = tier_colors.get(tier, "var(--amber)")
    tier_label  = tier_labels.get(tier, "")

    segs = "".join(
        f'<div style="flex:1; height:3px; border-radius:2px; background:'
        f'{"var(--amber)" if i < cur else "rgba(255,179,0,0.4)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 2 · Hidden Desires · {cur + 1} / {total}
</div>
<div style="display:flex; gap:2px; margin-bottom:20px;">{segs}</div>
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid {accent}; border-radius:4px; padding:24px 24px 20px; margin-bottom:14px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:3px;
              text-transform:uppercase; color:{accent}; margin-bottom:12px; opacity:0.75;">
    {tier_label}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:17px; font-style:italic;
              color:var(--text); line-height:1.7; font-weight:300;">{q['text']}</div>
</div>
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px; text-align:center;">
  How much does this resonate?
</div>
""")

    current_idx = HD_OPT_IDS.index(sel_id) if sel_id in HD_OPT_IDS else None
    chosen_idx  = st.radio(
        label="Resonance",
        options=list(range(len(HD_OPT_LABELS))),
        format_func=lambda i: HD_OPT_LABELS[i],
        index=current_idx,
        key=f"hd_radio_{cur}",
        horizontal=False,
    )

    if chosen_idx is not None:
        new_id = HD_OPT_IDS[chosen_idx]
        if new_id != sel_id:
            hd = dict(st.session_state.wwyd_hd_answers)
            hd[q["id"]] = new_id
            st.session_state.wwyd_hd_answers = hd
            if not is_last:
                st.session_state.wwyd_hd_cur += 1
                st.rerun()

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="hd_back", use_container_width=True):
                st.session_state.wwyd_hd_cur -= 1
                st.rerun()
    with col_next:
        answered = q["id"] in st.session_state.wwyd_hd_answers
        if is_last:
            if st.button("Build My Profile →", key="hd_next_last",
                         disabled=not answered, use_container_width=True, type="primary"):
                st.session_state.wwyd_phase = "generating_profile"
                st.rerun()
        else:
            if st.button("Next →", key="hd_next_mid", disabled=not answered,
                         use_container_width=True,
                         type="primary" if answered else "secondary"):
                st.session_state.wwyd_hd_cur += 1
                st.rerun()


# ─── PHASE: GENERATING PROFILE ────────────────────────────────────────────────

def render_generating_profile():
    line = random.choice(PHASE_TRANSITIONS["to_profile"])
    st.html(f"""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:8px;">BUILDING YOUR PROFILE</div>
<div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);
            font-style:italic; margin-bottom:24px;">{line}</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, s):
        ph_bar.progress(pct)
        ph_status.caption(s)

    try:
        upd(10, "Computing your Phase 1 score…")
        questions = st.session_state.wwyd_questions
        answers   = st.session_state.wwyd_answers
        hd_ans    = st.session_state.wwyd_hd_answers

        total_pts = sum(
            (q.get("opts",[])[a].get("pts",0) if isinstance(q.get("opts",[])[a], dict) else 0)
            for q, a in zip(questions, answers)
            if a is not None and a < len(q.get("opts",[]))
        )
        max_pts = sum(
            max((o.get("pts",0) if isinstance(o, dict) else 0 for o in (q.get("opts") or [])), default=0)
            for q in questions
        )
        pct         = round((total_pts / max_pts) * 100) if max_pts else 0
        result_type = next((r for r in RESULT_TYPES if r["min"] <= pct <= r["max"]), RESULT_TYPES[-1])

        upd(35, "Reading your hidden desire signals…")
        try:
            client = _get_client()
        except Exception:
            client = None

        upd(55, "Scoring every category against your profile…")
        profile_data = generate_profile_and_categories(result_type, pct, hd_ans, questions, answers, client,
                                                       st.session_state.get("wwyd_profile") or {})

        upd(90, "Saving…")
        st.session_state.wwyd_result_type   = result_type
        st.session_state.wwyd_openness_pct  = pct
        st.session_state.wwyd_total_pts     = total_pts
        st.session_state.wwyd_ranked_cats   = profile_data["ranked_categories"]
        st.session_state.wwyd_top25         = profile_data["top25_names"]
        st.session_state.wwyd_recs          = profile_data["recommendations"]
        st.session_state.wwyd_insight       = profile_data.get("insight", "")
        st.session_state.wwyd_selected_cats = list(profile_data["top25_names"])

        _save_to_db("profile_complete")

        upd(100, "Done.")
        time.sleep(0.1)
        st.session_state.wwyd_phase = "category_selector"
        st.rerun()

    except Exception:
        st.session_state.wwyd_error = "Couldn't build your profile right now — give it another try in a minute."
        st.session_state.wwyd_phase = "start"
        st.rerun()


# ─── PHASE: CATEGORY SELECTOR ────────────────────────────────────────────────

def render_category_selector():
    _show_persistent_db_error()
    ranked_cats = st.session_state.wwyd_ranked_cats
    top25_names = set(st.session_state.wwyd_top25)
    selected    = set(st.session_state.wwyd_selected_cats)
    pct         = st.session_state.get("wwyd_openness_pct", 0)
    result_type = st.session_state.get("wwyd_result_type", {})
    insight     = st.session_state.get("wwyd_insight", "")

    insight_html = ('<div style="font-family:\'DM Sans\',sans-serif; font-size:13px; color:var(--amber); font-style:italic; line-height:1.6; border-left:2px solid var(--amber); padding-left:12px; margin-bottom:12px;">' + insight + '</div>') if insight else ''
    rt_icon = result_type.get('icon', '')
    rt_name = result_type.get('name', '')
    rt_meta = result_type.get('meta', '')
    sel_count = len(selected)
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 3 · Your Category Fingerprint
</div>
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--cyan); border-radius:4px; padding:18px 20px; margin-bottom:16px;">
  <div style="display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
    <div style="flex:1; min-width:200px;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--text); letter-spacing:2px;">
        {rt_icon} {rt_name}
      </div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--magenta);
                  letter-spacing:1px; text-transform:uppercase; margin-top:2px;">
        {rt_meta}
      </div>
    </div>
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
                padding:8px 14px; text-align:center; flex-shrink:0;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--text);">{pct}</div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">openness %</div>
    </div>
  </div>
  {insight_html}
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); line-height:1.65;">
    Every real platform category scored against your answers. Your top 25 are already picked —
    tap to add or remove. This is your profile, not a recommendation.
  </div>
</div>
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:14px;">
  Tap to add or remove
</div>
""")

    # Pills wrap on a phone, so the whole fingerprint fits instead of 100 stacked buttons
    top_names  = [c["name"] for c in ranked_cats if c["name"] in top25_names]
    rest_names = [c["name"] for c in ranked_cats if c["name"] not in top25_names]
    picked_top = st.pills("Your top picks", top_names, selection_mode="multi",
                          default=[n for n in top_names if n in selected], key="cat_pills_top")
    with st.expander(f"All {len(rest_names)} other categories"):
        picked_rest = st.pills("Other categories", rest_names, selection_mode="multi",
                               default=[n for n in rest_names if n in selected], key="cat_pills_rest",
                               label_visibility="collapsed")
    selected = set(picked_top or []) | set(picked_rest or [])
    st.session_state.wwyd_selected_cats = [n for n in top_names + rest_names if n in selected]

    st.html("<br>")
    if st.button("See My Full Profile →", use_container_width=True, type="primary",
                 disabled=(len(selected) == 0), key="cat_next"):
        _update_selections_in_db(list(selected))
        st.session_state.wwyd_phase = "result"
        st.rerun()


# ─── PHASE: RESULT ────────────────────────────────────────────────────────────

def _deepest_fantasy(hd_ans: dict, cats: list):
    """Name the one desire they owned most (strongest answer, then furthest into Phase 2)."""
    from matching import DESIRE_LABELS
    owned = [q for q in HIDDEN_DESIRE_QUESTIONS if hd_ans.get(q["id"]) in ("yes", "strongly")]
    if not owned:
        body = ('<div class="df-name">Still under lock</div>'
                '<div class="df-sub">You didn\'t own a single one. Either that\'s the truth, or your deepest '
                'fantasy is the one you\'re protecting. Retake it when you\'re ready to say it.</div>')
    else:
        # "An untold fantasy" and "a mapped-out fantasy" say one exists, not what it is,
        # so name a concrete desire whenever they owned one
        concrete = [q for q in owned if q["signal"] not in ("secret_fantasy", "elaborated_fantasy")] or owned
        top = max(concrete, key=lambda q: (hd_ans.get(q["id"]) == "strongly", q.get("tier", 1)))
        related = [c for c in cats if c in _SIGNAL_CATEGORY_MAP.get(top["signal"], [])] or cats
        leans = ", ".join(_html.escape(c) for c in related[:3])
        body = (f'<div class="df-name">{_html.escape(DESIRE_LABELS.get(top["signal"], "Unnamed"))}</div>'
                f'<div class="df-sub">It\'s the one you owned hardest: “{_html.escape(top["text"])}”</div>'
                + (f'<div class="df-leans">Leans toward · {leans}</div>' if leans else ""))
    st.html(f"""
<style>
.df-card {{ background:linear-gradient(160deg,#241018 0%,#131318 100%); border:1px solid rgba(255,45,120,.5);
  border-radius:4px; padding:20px; margin-bottom:12px; }}
.df-kicker {{ font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px; text-transform:uppercase;
  color:var(--magenta); margin-bottom:8px; }}
.df-name {{ font-family:'Bebas Neue',sans-serif; font-size:34px; letter-spacing:2px; color:var(--text); line-height:1; }}
.df-sub {{ font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.7; margin-top:8px; font-style:italic; }}
.df-leans {{ font-family:'Space Mono',monospace; font-size:10px; color:var(--amber); margin-top:10px; letter-spacing:.5px; }}
.df-private {{ font-family:'Space Mono',monospace; font-size:8px; color:var(--muted); margin-top:12px;
  letter-spacing:1px; text-transform:uppercase; }}
</style>
<div class="df-card enter-card">
  <div class="df-kicker">🔥 Your deepest fantasy</div>
  {body}
  <div class="df-private">Only you see this. A match only sees it if they said yes to it too.</div>
</div>""")


def render_result():
    _show_persistent_db_error()
    result_type = st.session_state.get("wwyd_result_type") or RESULT_TYPES[0]
    pct         = st.session_state.get("wwyd_openness_pct", 0)
    sel_cats    = st.session_state.get("wwyd_selected_cats", [])
    recs        = st.session_state.get("wwyd_recs", [])
    ranked_cats = st.session_state.get("wwyd_ranked_cats", [])
    hd_ans      = st.session_state.get("wwyd_hd_answers", {})
    insight     = st.session_state.get("wwyd_insight", "")

    one_line_read_html = (
        '<div style="background:var(--surface); border:1px solid var(--amber); border-radius:3px; padding:14px 16px; margin-top:4px;">'
        '<div style="font-family:\'Space Mono\',monospace; font-size:8px; letter-spacing:2px; text-transform:uppercase; color:var(--amber); margin-bottom:6px;">One-line read</div>'
        f'<div style="font-family:\'DM Sans\',sans-serif; font-size:14px; color:var(--text); font-style:italic; line-height:1.65;">{insight}</div>'
        '</div>'
    ) if insight else ''
    rt_icon = result_type['icon']
    rt_name = result_type['name'].upper()
    rt_meta = result_type['meta']
    rt_hook = result_type.get('hook', '')
    rt_signal = result_type.get('signal', '')
    rt_tell = result_type.get('tell', '')
    st.html(f"""
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--magenta); border-radius:4px; padding:28px 24px; margin-bottom:14px;">
  <div style="font-size:42px; margin-bottom:10px;">{rt_icon}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,6vw,46px);
              letter-spacing:3px; color:var(--text); line-height:1.05; margin-bottom:4px;">
    {rt_name}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--magenta); text-transform:uppercase; margin-bottom:24px;">
    {rt_meta}
  </div>
  <div style="border-top:1px solid var(--border); padding-top:18px; margin-bottom:16px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
                line-height:1.75; margin-bottom:14px;">{rt_hook}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
                line-height:1.75; margin-bottom:14px; border-left:2px solid var(--border);
                padding-left:12px;">{rt_signal}</div>
    <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--amber);
                line-height:1.65; letter-spacing:0.5px;">{rt_tell}</div>
  </div>
  {one_line_read_html}
  <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
              padding:14px; margin-top:16px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-bottom:8px;">Openness Index</div>
    <div style="height:4px; background:var(--border); border-radius:2px; margin-bottom:8px;">
      <div style="width:{pct}%; height:100%;
                  background:linear-gradient(90deg, var(--amber), var(--magenta)); border-radius:2px;"></div>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">Closed off</span>
      <span style="font-family:'Bebas Neue',sans-serif; font-size:32px; color:var(--text);">
        {pct}<span style="font-size:14px; color:var(--muted);"> / 100</span>
      </span>
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">Wide open</span>
    </div>
  </div>
</div>
""")

    _deepest_fantasy(hd_ans, sel_cats or [c["name"] for c in ranked_cats[:5]])

    strong = sorted(
        [q for q in HIDDEN_DESIRE_QUESTIONS if hd_ans.get(q["id"]) in ("yes","strongly")],
        key=lambda q: (-(3 if hd_ans.get(q["id"])=="strongly" else 2), q.get("tier",1)),
    )
    if strong:
        sigs_html = "".join(
            f'<div style="display:flex; gap:12px; align-items:flex-start; padding:10px 0; border-bottom:1px solid var(--border);">'
            f'<span style="color:{"var(--magenta)" if hd_ans.get(q["id"])=="strongly" else "var(--amber)"}; flex-shrink:0; margin-top:3px; font-size:10px;">{"★" if hd_ans.get(q["id"])=="strongly" else "◆"}</span>'
            f'<div style="font-family:\'DM Sans\',sans-serif; font-size:12px; color:var(--soft); line-height:1.7; font-style:italic;">{q["text"]}</div></div>'
            for q in strong
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber);">Hidden Desire Signals</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">
      {len([q for q in strong if hd_ans.get(q['id'])=='strongly'])} strong · {len([q for q in strong if hd_ans.get(q['id'])=='yes'])} present
    </div>
  </div>
  {sigs_html}
</div>
""")

    if ranked_cats:
        top10     = [c for c in ranked_cats[:10] if c["score"] > 0]
        max_score = ranked_cats[0]["score"] if ranked_cats else 1
        bars_html = "".join(
            f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">'
            f'<div style="font-family:\'Space Mono\',monospace; font-size:9px; color:{"var(--lime)" if c["name"] in sel_cats else "var(--soft)"}; width:150px; flex-shrink:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; text-transform:uppercase; letter-spacing:1px;">{"✓ " if c["name"] in sel_cats else ""}{c["name"]}</div>'
            f'<div style="flex:1; height:3px; background:var(--border); border-radius:2px;"><div style="width:{min(100, round(c["score"]/max_score*100))}%; height:100%; background:{"var(--lime)" if c["name"] in sel_cats else "var(--muted)"}; border-radius:2px;"></div></div>'
            f'<div style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--muted); width:20px; text-align:right;">{c["score"]}</div>'
            f'</div>'
            for c in top10
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--cyan);">Content Fingerprint · Top 10</div>
    <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">{len(sel_cats)} selected</div>
  </div>
  {bars_html}
</div>
""")

    if recs:
        recs_html = "".join(
            f'<div style="padding:14px 0; border-bottom:1px solid var(--border);">'
            f'<div style="font-family:\'Space Mono\',monospace; font-size:8px; letter-spacing:2px; text-transform:uppercase; color:var(--magenta); margin-bottom:6px;">0{i+1}</div>'
            f'<div style="font-family:\'DM Sans\',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">{r}</div></div>'
            for i, r in enumerate(recs)
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:4px;">Things Worth Exploring</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted); margin-bottom:12px;">
    Based on what you actually answered — not just your archetype.
  </div>
  {recs_html}
</div>
""")

    share = (
        f"Read Between The Lines — Hidden\n\n"
        f"Result: {result_type['name']}\n\"{result_type['meta']}\"\n"
        f"Openness Index: {pct}%\n\n"
        f"{result_type.get('hook','')}\n{result_type.get('signal','')}\n{result_type.get('tell','')}\n"
    )
    if insight: share += f"\nOne-line read: {insight}\n"
    if strong:  share += "\nSignals: " + ", ".join(q["signal"] for q in strong[:5]) + "\n"
    if sel_cats: share += "\nMy categories: " + ", ".join(sel_cats[:10]) + "\n"
    if recs:    share += "\nRecommendations:\n" + "\n".join(f"· {r}" for r in recs[:3])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Try Again", use_container_width=True, key="try_again"):
            hard_reset()
    with col2:
        st.download_button("↓ Save Result", data=share, file_name="rbtl_result.txt",
                           mime="text/plain", use_container_width=True, key="save_result")

    st.html('<div style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:var(--muted);'
            'text-align:center;margin-top:22px;line-height:1.6;">Matches who\'ve taken the quiz too see '
            'your result, your freak score (Openness Index) and the hidden desires you both said yes to. '
            'Never the rest.<br>To compare with anyone else, get a drop code in <b>Me › Quiz</b>.</div>')


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()
    _render_header()

    phase = st.session_state.wwyd_phase

    if   phase == "start":              render_start()
    elif phase == "profile_intake":     render_profile_intake()
    elif phase == "loading":            render_loading()
    elif phase == "quiz":               render_quiz()
    elif phase == "phase_transition":   render_phase_transition()
    elif phase == "hidden_desires":     render_hidden_desires()
    elif phase == "generating_profile": render_generating_profile()
    elif phase == "category_selector":  render_category_selector()
    elif phase == "result":             render_result()
    else:
        _wipe()
        init_state()
        st.rerun()
