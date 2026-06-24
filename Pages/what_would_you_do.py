"""
Pages/what_would_you_do.py
Read Between The Lines — 3-phase desire profile quiz.

Everything is AI-generated fresh every time. No Reddit. No external dependencies.
All scenarios, questions, and answers are gender-neutral and orientation-inclusive.
No he/she/him/her/boyfriend/girlfriend anywhere.

Community Pulse: after answering each question the user sees an anonymous
breakdown of how other ViceVault users responded.
"""

import hashlib
import streamlit as st
import json
import random
import time
import threading
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

SCENARIO_COUNT = 7

ALL_PLATFORM_CATEGORIES = [
    "18-25", "60FPS", "AI", "Amateur", "Anal", "Arab", "Asian", "Babe",
    "Babysitter (18+)", "BBW", "Behind The Scenes", "Big Ass", "Big Dick",
    "Big Tits", "Bisexual Male", "Blonde", "Blowjob", "Bondage", "Brazilian",
    "British", "Brunette", "Bukkake", "Cartoon", "Casting", "Celebrity",
    "College (18+)", "Compilation", "Cosplay", "Creampie", "Cuckold",
    "Cumshot", "Czech", "Deepthroat", "Double Penetration", "Ebony", "Euro",
    "Exclusive", "Feet", "Female Orgasm", "Fetish", "Fingering", "Fisting",
    "French", "Funny", "Gaming", "Gangbang", "German", "Handjob", "Hardcore",
    "HD Porn", "Hentai", "Indian", "Interactive", "Interracial", "Italian",
    "Japanese", "Korean", "Latina", "Lesbian", "Massage", "Masturbation",
    "Mature", "MILF", "Muscular Men", "Music", "Old/Young (18+)", "Orgy",
    "Parody", "Party", "Pissing", "Podcast", "Popular With Women", "Pornstar",
    "POV", "Public", "Pussy Licking", "Reaction", "Reality", "Red Head",
    "Role Play", "Romantic", "Rough Sex", "Russian", "School (18+)", "SFW",
    "Small Tits", "Smoking", "Solo Female", "Solo Male", "Squirt",
    "Step Fantasy", "Strap On", "Striptease", "Tattooed Women", "Threesome",
    "Toys", "Transgender", "Verified Amateurs", "Verified Couples",
    "Verified Models", "Vintage", "Virtual Reality", "Webcam",
]

RESULT_TYPES = [
    {
        "min": 0, "max": 10, "icon": "🔒", "name": "Closed Garden",
        "meta": "Yours. Only yours. Period.",
        "hook": "You answered every single one the same way. That consistency either means total clarity — or a story you haven't told yourself yet.",
        "signal": "You're not curious about the scenarios. You're protective of something.",
        "tell": "The question that probably landed hardest was one you dismissed fast.",
    },
    {
        "min": 11, "max": 22, "icon": "🌿", "name": "Quietly Curious",
        "meta": "The thought has crossed your mind. More than once.",
        "hook": "You played it safe on the ones that felt risky. But you didn't close the door all the way on any of them.",
        "signal": "There's a gap between what you'd say out loud and what you actually thought reading these.",
        "tell": "Someone who knows you well would not be entirely surprised by your score.",
    },
    {
        "min": 23, "max": 35, "icon": "🌙", "name": "The Open Door",
        "meta": "You've thought this through. Seriously.",
        "hook": "You've been here before — in your head, at least. These scenarios didn't shock you. They felt familiar.",
        "signal": "The gap between where you are and where you want to be is mostly just one honest conversation.",
        "tell": "You know which scenario you'd actually say yes to if the circumstances were right.",
    },
    {
        "min": 36, "max": 44, "icon": "🔺", "name": "Already Decided",
        "meta": "The question isn't whether. It's when.",
        "hook": "You didn't hesitate on the ones that matter. That's not impulsiveness — that's someone who's done the work already.",
        "signal": "You're past theory. The only thing between you and acting on this is logistics.",
        "tell": "You probably already know who you'd want in the room.",
    },
    {
        "min": 45, "max": 999, "icon": "⚡", "name": "The Third Is Already Picked",
        "meta": "You know exactly who. They probably know too.",
        "hook": "You read these like someone reading their own journal entries. Not recognition — confirmation.",
        "signal": "This isn't curiosity. This is inventory.",
        "tell": "The most interesting question for you isn't what — it's what you're still waiting for.",
    },
]

# Phase 2: escalating hidden desire statements
HIDDEN_DESIRE_QUESTIONS = [
    # Tier 1 — warming up
    {"id": "hd_01", "signal": "verbal_arousal", "tier": 1,
     "text": "Being told exactly what someone wants to do to you — in specific, graphic detail — turns you on more than the act itself sometimes."},
    {"id": "hd_02", "signal": "desired_intensity", "tier": 1,
     "text": "You want to be wanted badly enough that someone loses composure. Not politely wanted. Urgently."},
    {"id": "hd_03", "signal": "authentic_exposure", "tier": 1,
     "text": "Being completely naked — no performance, no held breath, no self-editing — and having someone look at you like that is something you actively think about."},

    # Tier 2 — getting specific
    {"id": "hd_04", "signal": "power_dynamic", "tier": 2,
     "text": "A specific power dynamic — one person clearly in charge, one clearly not — is what makes certain sexual scenarios stay in your head long after."},
    {"id": "hd_05", "signal": "archetype_attraction", "tier": 2,
     "text": "There's a specific type of person — not a look, an energy — whose presence makes you immediately wonder what they'd be like in bed."},
    {"id": "hd_06", "signal": "stranger_fantasy", "tier": 2,
     "text": "A stranger in a specific setting — hotel bar, late flight, someone else's party — and the scene writes itself before you consciously stop it."},

    # Tier 3 — dominant/submissive
    {"id": "hd_07", "signal": "dom_active", "tier": 3,
     "text": "You've fantasised about being completely in control of another person's pleasure — setting every pace, every permission, deciding when they get what they want."},
    {"id": "hd_08", "signal": "sub_active", "tier": 3,
     "text": "You've thought about having someone take over completely — pinning you down, deciding what happens to your body, and you just taking it."},
    {"id": "hd_09", "signal": "taboo_arousal", "tier": 3,
     "text": "You've gotten turned on by something you'd never say out loud — a video, a story, a thought — and your first instinct was to delete the browser history."},
    {"id": "hd_10", "signal": "exhib_active", "tier": 3,
     "text": "Being watched — someone seeing you during sex, or seeing you undress — is something you've thought about with more interest than you typically admit."},

    # Tier 4 — group, specific fantasy
    {"id": "hd_11", "signal": "secret_fantasy", "tier": 4,
     "text": "You have a sexual fantasy you've never told a partner. Not because it's wrong — because saying it out loud would mean you'd actually have to decide if you want it."},
    {"id": "hd_12", "signal": "group_sex", "tier": 4,
     "text": "You've imagined what sex with more than one person at the same time would actually feel like — not as a passing thought, as a detailed mental image."},
    {"id": "hd_13", "signal": "taboo_fixation", "tier": 4,
     "text": "There's a specific category of content — something you'd close if someone walked in — that you keep returning to even when you tell yourself you're not that interested."},

    # Tier 5 — the ones that catch people off guard
    {"id": "hd_14", "signal": "elaborated_fantasy", "tier": 5,
     "text": "You have a sexual fantasy so mapped out — the specific person or type, the setting, the sequence of what happens — that you surprised yourself when you noticed how detailed it already was."},
    {"id": "hd_15", "signal": "unnamed_fixation", "tier": 5,
     "text": "There's something specific you've never done sexually but think about more than makes sense — and the fact that you haven't done it yet is its own kind of answer."},
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
div[data-testid="stRadio"] > div { gap:8px !important; flex-direction:column !important; }
div[data-testid="stRadio"] > div > label {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:3px !important; padding:12px 16px !important;
  font-family:'DM Sans',sans-serif !important; font-size:13px !important;
  color:var(--soft) !important; cursor:pointer !important;
  transition:all 0.15s !important; width:100% !important; line-height:1.55 !important;
}
div[data-testid="stRadio"] > div > label:hover {
  border-color:var(--lime) !important; color:var(--text) !important; background:#1c1c22 !important;
}
div[data-testid="stRadio"] > div > label[data-checked="true"] {
  background:rgba(255,45,120,0.12) !important; border-color:var(--magenta) !important;
  color:var(--text) !important; border-left-width:3px !important;
}
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

_prefetch_lock   = threading.Lock()
_prefetch_result = None  # list[scenario] once done | "loading" | "error"

def _run_prefetch():
    global _prefetch_result
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if not key:
            with _prefetch_lock:
                _prefetch_result = "error"
            return
        scenarios = _generate_all_scenarios(key, {})
        with _prefetch_lock:
            _prefetch_result = scenarios
    except Exception:
        with _prefetch_lock:
            _prefetch_result = "error"

def _ensure_prefetch_started():
    global _prefetch_result
    with _prefetch_lock:
        if _prefetch_result is None:
            _prefetch_result = "loading"
            t = threading.Thread(target=_run_prefetch, daemon=True)
            t.start()

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
    
    themes = random.sample(_SCENARIO_THEMES, min(SCENARIO_COUNT, len(_SCENARIO_THEMES)))

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
    while len(scenarios) < SCENARIO_COUNT:
        scenarios.append(_fallback_scenario(len(scenarios)))

    return scenarios[:SCENARIO_COUNT]


def _fallback_scenario(idx: int) -> dict:
    """Static fallback if generation fails — gender-neutral."""
    fallbacks = [
        {
            "title": "The conversation that changed something",
            "text": "You and someone you're close to stayed up talking until 4am. At some point the conversation shifted — not explicitly, but both of you felt it. Nothing happened. But something was established.",
            "prompt": "What's the most honest thing you can say about what you wanted in that moment?",
            "opts": [
                {"t": "I wanted the conversation and nothing more. That was enough.", "pts": 0},
                {"t": "I was aware of the tension but told myself I was imagining it.", "pts": 2},
                {"t": "I knew exactly what was happening and I was waiting to see what they'd do.", "pts": 3},
                {"t": "I wanted it to go further and I made sure they knew that.", "pts": 5},
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
    ]
    return fallbacks[idx % len(fallbacks)]


def get_scenarios() -> list:
    """Return prefetched scenarios if ready, else generate now with user profile."""
    profile = st.session_state.get("wwyd_profile", {})
    global _prefetch_result
    deadline = time.time() + 8
    while time.time() < deadline:
        with _prefetch_lock:
            val = _prefetch_result
        if val not in (None, "loading"):
            break
        time.sleep(0.05)

    with _prefetch_lock:
        val = _prefetch_result

    if val and val not in ("loading", "error"):
        # Reset for next session
        _prefetch_result = None
        _ensure_prefetch_started()
        return val

    # Fallback: generate now with profile
    key = st.secrets.get("OPENAI_API_KEY", "")
    if key:
        try:
            return _generate_all_scenarios(key, profile)
        except Exception:
            pass
    return [_fallback_scenario(i) for i in range(SCENARIO_COUNT)]


# ─── PROFILE + CATEGORY SCORING ───────────────────────────────────────────────

def generate_profile_and_categories(result_type, openness_pct, hd_answers,
                                    questions, answers, client) -> dict:
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
        f"You are a desire profile analyst for an 18+ adult platform called Vice Vault.\n"
        f"Write a profile that feels uncomfortably accurate — like it was written specifically for this person.\n\n"
        f"User data:\n"
        f"- Openness archetype: {result_type['name']} ({openness_pct}% openness index)\n"
        f"- Strong hidden desire signals: {', '.join(strong_signals) or 'none'}\n"
        f"- Present hidden desire signals: {', '.join(mild_signals) or 'none'}\n"
        f"- Resonated with: {pos_str}\n"
        f"- Rejected (DO NOT recommend these themes): {neg_str}\n\n"
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
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, dict):
        raise ValueError("Profile generation returned invalid JSON")

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

def _render_community_pulse(q_hash: str, chosen_idx: int, opt_labels: list):
    try:
        import database as db
        db.record_community_answer(q_hash, chosen_idx)
        tallies = db.get_community_answers(q_hash)
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
    global _prefetch_result
    with _prefetch_lock:
        _prefetch_result = None
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
                        "insight": st.session_state.get("wwyd_insight","")},
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
    Vice Vault · Desire Quiz
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

def _render_drop_code_lookup():
    with st.expander("◈ Enter a Drop Code", expanded=False):
        code_input = st.text_input(
            "Drop Code",
            max_chars=8,
            key="wwyd_drop_code_input",
            label_visibility="collapsed",
            placeholder="Enter 6-character code…"
        ).strip().upper()

        if st.button("Compare →", key="wwyd_drop_compare"):
            if not code_input:
                return
            import database as db
            drop = db.get_compat_drop(code_input)
            if not drop:
                st.html("""
<div style="font-family:'Space Mono',monospace;font-size:9px;color:var(--magenta);
            letter-spacing:1px;text-transform:uppercase;margin-top:8px;">
  Code not found or expired.
</div>
""")
                return

            uid = _uid()
            if uid and drop.get("status") == "open" and drop.get("creator_id") != uid:
                latest = db.load_latest_rbtl_result(uid)
                if latest and latest.get("id"):
                    db.link_compat_drop(code_input, uid, latest["id"])
                    drop = db.get_compat_drop(code_input) or drop

            c_name   = drop.get("creator_result_name") or "—"
            c_open   = drop.get("creator_openness_pct") or 0
            c_ds     = drop.get("creator_dim_scores") or {}
            p_name   = drop.get("partner_result_name") or "—"
            p_open   = drop.get("partner_openness_pct") or 0
            p_ds     = drop.get("partner_dim_scores") or {}

            c_sigs = _extract_signals(c_ds)
            p_sigs = _extract_signals(p_ds)

            shared    = [s for s in c_sigs if s in p_sigs][:3]
            diverging = [s for s in c_sigs if s not in p_sigs][:3]

            open_diff   = abs(c_open - p_open)
            signal_overlap = len(shared)
            match_pct = max(0, min(100, round(100 - open_diff * 0.5 + signal_overlap * 8)))

            shared_html = "".join(
                f'<span style="background:rgba(198,255,0,0.1);border:1px solid var(--lime);border-radius:2px;'
                f'font-family:\'Space Mono\',monospace;font-size:7px;padding:2px 6px;margin:2px;color:var(--lime);">{s}</span>'
                for s in shared
            ) or '<span style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);">None</span>'

            div_html = "".join(
                f'<span style="background:rgba(255,45,120,0.1);border:1px solid var(--magenta);border-radius:2px;'
                f'font-family:\'Space Mono\',monospace;font-size:7px;padding:2px 6px;margin:2px;color:var(--magenta);">{s}</span>'
                for s in diverging
            ) or '<span style="font-family:\'Space Mono\',monospace;font-size:8px;color:var(--muted);">None</span>'

            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px 20px; margin-top:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:14px;">Compatibility Drop — Results</div>
  <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px; padding:12px;">
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Them</div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:var(--text);
                  letter-spacing:1px; margin-bottom:4px;">{c_name}</div>
      <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--amber);">{c_open}% open</div>
    </div>
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px; padding:12px;">
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">You</div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:var(--text);
                  letter-spacing:1px; margin-bottom:4px;">{p_name}</div>
      <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--amber);">{p_open}% open</div>
    </div>
  </div>
  <div style="text-align:center; margin-bottom:16px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--lime);
                letter-spacing:2px; line-height:1;">{match_pct}%</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                text-transform:uppercase; letter-spacing:2px;">Match</div>
  </div>
  <div style="margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--lime);
                letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Shared Signals</div>
    <div style="display:flex; flex-wrap:wrap; gap:4px;">{shared_html}</div>
  </div>
  <div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--magenta);
                letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Diverging</div>
    <div style="display:flex; flex-wrap:wrap; gap:4px;">{div_html}</div>
  </div>
</div>
""")


def _extract_signals(dim_scores: dict) -> list:
    hd = dim_scores.get("hd_signals", "")
    if hd:
        return [s.strip() for s in hd.split(",") if s.strip()]
    return []


# ─── PHASE: START ─────────────────────────────────────────────────────────────

def render_start():
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    if not _uid():
        st.warning("Not logged in — results won't save to your profile.")

    _render_drop_code_lookup()

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
      15 statements that escalate from curiosity to the specific fantasies most people
      have never said out loud. At least one will catch you off guard.
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
    18+ only · Anonymous · Scenarios change every time
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
        scenarios = get_scenarios()

        upd(100, "Ready.")
        time.sleep(0.1)
        st.session_state.wwyd_questions   = scenarios
        st.session_state.wwyd_answers     = [None] * len(scenarios)
        st.session_state.wwyd_cur         = 0
        st.session_state.wwyd_pulse_shown = {}
        st.session_state.wwyd_phase       = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Failed to load: {e}. Please try again."
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
      <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">Vice Vault</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">anonymous · now</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                padding:3px 8px; border:1px solid var(--border); color:var(--muted);
                text-transform:uppercase; border-radius:2px; flex-shrink:0;">Scenario</div>
  </div>
  <div style="padding:14px 16px 14px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:15px; font-weight:500;
                color:var(--text); line-height:1.5; margin-bottom:10px;">{q['title']}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
                line-height:1.85;">{q['text']}</div>
  </div>
</div>
<div style="font-family:'DM Sans',sans-serif; font-size:15px; font-style:italic;
            color:var(--amber); border-left:3px solid var(--amber); padding-left:14px;
            margin-bottom:18px; line-height:1.6;">{q['prompt']}</div>
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
        _render_community_pulse(q_hash, chosen, opt_labels)

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
              margin-bottom:32px;">15 statements. They escalate.</div>
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
    tier_labels = {1:"Warming up", 2:"Getting specific", 3:"The ones people don't say out loud", 4:"Deeper", 5:"The ones that catch people off guard"}
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
        result_type = next((r for r in RESULT_TYPES if r["min"] <= total_pts <= r["max"]), RESULT_TYPES[-1])

        upd(35, "Reading your hidden desire signals…")
        client = _get_client()

        upd(55, "Scoring every category against your profile…")
        profile_data = generate_profile_and_categories(result_type, pct, hd_ans, questions, answers, client)

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

    except Exception as e:
        st.session_state.wwyd_error = f"Couldn't build your profile: {e}"
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
        {result_type.get('icon','')} {result_type.get('name','')}
      </div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--magenta);
                  letter-spacing:1px; text-transform:uppercase; margin-top:2px;">
        {result_type.get('meta','')}
      </div>
    </div>
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
                padding:8px 14px; text-align:center; flex-shrink:0;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--text);">{pct}</div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">openness %</div>
    </div>
  </div>
  {f'<div style="font-family:\'DM Sans\',sans-serif; font-size:13px; color:var(--amber); font-style:italic; line-height:1.6; border-left:2px solid var(--amber); padding-left:12px; margin-bottom:12px;">{insight}</div>' if insight else ''}
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); line-height:1.65;">
    Every real platform category scored against your answers.
    <span style="color:var(--lime);">Lime = AI top 25 picks for you.</span>
    Toggle anything — this is your profile, not a recommendation.
  </div>
</div>
<div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); margin-bottom:14px;">
  {len(selected)} selected
</div>
""")

    cols = st.columns(3)
    for idx, cat_info in enumerate(ranked_cats):
        cat_name  = cat_info["name"]
        cat_score = cat_info["score"]
        is_top25  = cat_name in top25_names
        is_sel    = cat_name in selected
        btn_label = f"✓ {cat_name}" if is_sel else (f"◆ {cat_name}" if is_top25 else cat_name)

        with cols[idx % 3]:
            if st.button(btn_label, key=f"cat_{idx}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                new_sel = set(st.session_state.wwyd_selected_cats)
                if is_sel: new_sel.discard(cat_name)
                else:      new_sel.add(cat_name)
                st.session_state.wwyd_selected_cats = list(new_sel)
                st.rerun()

            if cat_score > 0:
                bar_color = "var(--lime)" if is_top25 else "var(--border)"
                st.html(f"""
<div style="height:2px; background:var(--border); border-radius:1px; margin:-6px 0 8px;">
  <div style="width:{min(100, cat_score * 10)}%; height:100%; background:{bar_color}; border-radius:1px;"></div>
</div>
""")

    st.html("<br>")
    if st.button("See My Full Profile →", use_container_width=True, type="primary",
                 disabled=(len(selected) == 0), key="cat_next"):
        _update_selections_in_db(list(selected))
        st.session_state.wwyd_phase = "result"
        st.rerun()


# ─── PHASE: RESULT ────────────────────────────────────────────────────────────

def render_result():
    _show_persistent_db_error()
    result_type = st.session_state.get("wwyd_result_type") or RESULT_TYPES[0]
    pct         = st.session_state.get("wwyd_openness_pct", 0)
    sel_cats    = st.session_state.get("wwyd_selected_cats", [])
    recs        = st.session_state.get("wwyd_recs", [])
    ranked_cats = st.session_state.get("wwyd_ranked_cats", [])
    hd_ans      = st.session_state.get("wwyd_hd_answers", {})
    insight     = st.session_state.get("wwyd_insight", "")

    st.html(f"""
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--magenta); border-radius:4px; padding:28px 24px; margin-bottom:14px;">
  <div style="font-size:42px; margin-bottom:10px;">{result_type['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,6vw,46px);
              letter-spacing:3px; color:var(--text); line-height:1.05; margin-bottom:4px;">
    {result_type['name'].upper()}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--magenta); text-transform:uppercase; margin-bottom:24px;">
    {result_type['meta']}
  </div>
  <div style="border-top:1px solid var(--border); padding-top:18px; margin-bottom:16px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
                line-height:1.75; margin-bottom:14px;">{result_type.get('hook','')}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
                line-height:1.75; margin-bottom:14px; border-left:2px solid var(--border);
                padding-left:12px;">{result_type.get('signal','')}</div>
    <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--amber);
                line-height:1.65; letter-spacing:0.5px;">{result_type.get('tell','')}</div>
  </div>
  {f'<div style="background:var(--surface); border:1px solid var(--amber); border-radius:3px; padding:14px 16px; margin-top:4px;"><div style="font-family:\'Space Mono\',monospace; font-size:8px; letter-spacing:2px; text-transform:uppercase; color:var(--amber); margin-bottom:6px;">One-line read</div><div style="font-family:\'DM Sans\',sans-serif; font-size:14px; color:var(--text); font-style:italic; line-height:1.65;">{insight}</div></div>' if insight else ''}
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
        f"Read Between The Lines — Vice Vault\n\n"
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

    _render_compat_drop_section()


def _render_compat_drop_section():
    uid = _uid()
    if not uid:
        return

    quiz_id = st.session_state.get("wwyd_last_quiz_id")

    st.html("""
<div style="border-top:1px solid var(--border); margin-top:28px; padding-top:24px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Compatibility Drop</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-bottom:16px;
              line-height:1.65;">
    Generate a 6-character code. Share it. Someone enters it and sees how your results compare.
  </div>
</div>
""")

    existing_code = st.session_state.get("wwyd_compat_code")

    if existing_code:
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--lime); border-radius:4px;
            padding:18px 20px; margin-bottom:12px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Your Drop Code</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:42px; color:var(--lime);
              letter-spacing:8px; line-height:1;">{existing_code}</div>
  <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
              margin-top:8px; letter-spacing:1px; text-transform:uppercase;">Valid for 7 days</div>
</div>
""")
    elif quiz_id:
        if st.button("◈ Drop Compatibility Code →", use_container_width=True, key="gen_compat_code"):
            import database as db
            code = db.create_compat_drop(uid, quiz_id)
            if code:
                st.session_state.wwyd_compat_code = code
                st.rerun()


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
