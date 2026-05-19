"""
Pages/what_would_you_do.py
Read Between The Lines — 3-phase desire profile quiz.
"""

import streamlit as st
import json
import random
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

SUBREDDITS = [
    "sex", "nonmonogamy", "confessions", "trueoffmychest",
]

TABOO_KEYWORDS = [
    "threesome", "3some", "open relationship", "swinger", "polyamory",
    "fantasy", "attracted to", "cheated", "affair", "tempted",
    "another person", "someone else", "bring someone", "experiment",
    "never told anyone", "taboo", "forbidden", "want to try",
    "nonmonogamy", "open marriage", "group", "voyeur",
    "fmf", "mfm", "confession", "told my partner",
    "we tried", "we talked about",
]

MIN_SCORE   = 30
MIN_LENGTH  = 100
POST_COUNT  = 7
TEXT_CUTOFF = 200

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

FALLBACK_POSTS = [
    {"sub": "r/relationship_advice", "avatar": "T", "user": "throwaway_82947",
     "title": "My partner and I accidentally started a conversation we can't take back",
     "text": "We talked for two hours about things we'd never said out loud before. I don't know what we're doing but I don't feel scared about it.",
     "upvotes": "14.2k", "comments": "832", "time": "6 hours ago",
     "url": "https://reddit.com/r/relationship_advice", "flair": "Long Post"},
    {"sub": "r/confessions", "avatar": "A", "user": "anon_user_2291",
     "title": "I described what happens in our bedroom to my best friend — my partner walked in halfway through",
     "text": "She asked if I'd describe what it's actually like. I did. In detail. My partner walked in and just sat down and listened. When she left, my partner said: 'I didn't mind that.'",
     "upvotes": "9.7k", "comments": "1.2k", "time": "2 days ago",
     "url": "https://reddit.com/r/confessions", "flair": "True Story"},
    {"sub": "r/trueoffmychest", "avatar": "S", "user": "strangebutreal",
     "title": "My partner and I spent four hours talking about a hypothetical last night",
     "text": "'If you could add anyone to our relationship for one night, who?' They didn't laugh it off. They answered. With a name. So I answered too. I feel like I know them more than yesterday.",
     "upvotes": "18.3k", "comments": "976", "time": "5 hours ago",
     "url": "https://reddit.com/r/trueoffmychest", "flair": "Personal"},
    {"sub": "r/sex", "avatar": "M", "user": "maybe_mistakes",
     "title": "My girlfriend said my fantasy made her feel like she wasn't enough",
     "text": "I told her about a recurring fantasy — nothing I planned to act on. She got quiet and said it made her feel inadequate. I said that's not what fantasies mean. We're still in this argument three days later.",
     "upvotes": "22.1k", "comments": "3.4k", "time": "1 day ago",
     "url": "https://reddit.com/r/sex", "flair": "Advice"},
    {"sub": "r/nonmonogamy", "avatar": "L", "user": "late_night_post_88",
     "title": "My friend accidentally sent my partner my text about wanting an open relationship",
     "text": "He texted me three seconds later. I thought I was about to have the worst conversation of my life. He said: 'Why haven't you just told me this?'",
     "upvotes": "31.5k", "comments": "2.1k", "time": "3 days ago",
     "url": "https://reddit.com/r/nonmonogamy", "flair": "Story"},
    {"sub": "r/confessions", "avatar": "W", "user": "wontusemyname",
     "title": "UPDATE: We did it. Here's the honest version.",
     "text": "The hardest part was the three days before, not the night itself. The morning after we made breakfast and laughed a lot. If someone asked me today whether I'd do it again — yes.",
     "upvotes": "19.4k", "comments": "1.1k", "time": "2 days ago",
     "url": "https://reddit.com/r/confessions", "flair": "Update"},
    {"sub": "r/sex", "avatar": "N", "user": "nightowl_anon",
     "title": "Most couples don't discuss threesomes because they're scared of the answer",
     "text": "If they're excited, now you know something. If they're horrified, now you know something else. Either answer changes things. So most people carry the question for years and call it loyalty.",
     "upvotes": "8.9k", "comments": "2.3k", "time": "12 hours ago",
     "url": "https://reddit.com/r/sex", "flair": "Discussion"},
]

RESULT_TYPES = [
    {"min": 0,  "max": 10,  "icon": "🔒", "name": "Closed Garden",
     "meta": "Yours. Only yours. Period.",
     "desc": "You're wired for exclusivity and not apologising for it. Every scenario triggered a protective instinct. You believe some things stay between two people — no amount of 'communication' changes that. That's not fear. That's a value."},
    {"min": 11, "max": 22,  "icon": "🌿", "name": "Quietly Curious",
     "meta": "The thought has crossed your mind. More than once.",
     "desc": "You'd never bring it up unprompted, but these scenarios stirred something. You're more open than your defaults suggest. Given the right relationship and the right conversation, you'd hear someone out. Not closed — just careful about who gets the key."},
    {"min": 23, "max": 35,  "icon": "🌙", "name": "The Open Door",
     "meta": "You've thought this through. Seriously.",
     "desc": "You're past the theoretical phase. These scenarios didn't make you uncomfortable — they made you think. You understand the dynamics, you've processed the jealousy question. The only thing between you and yes is the right moment."},
    {"min": 36, "max": 44,  "icon": "🔺", "name": "Already Decided",
     "meta": "The question isn't whether. It's when.",
     "desc": "No internal conflict left. You read these scenarios and recognised yourself — not as observer but as someone who's been in a version of these situations or is clearly ready. You know what you want."},
    {"min": 45, "max": 999, "icon": "⚡", "name": "The Third Is Already Picked",
     "meta": "You know exactly who. They probably know too.",
     "desc": "You're not curious — you're experienced, or so ready it's the same thing. These scenarios felt like reading your own diary. You've had the late-night conversations. You've made the decision."},
]

HIDDEN_DESIRE_QUESTIONS = [
    {"id": "hd_01", "signal": "power_dynamic_latent",
     "text": "You're watching a film. A scene with a specific power dynamic between two characters makes you shift in your seat — nothing explicit, just the energy."},
    {"id": "hd_02", "signal": "hidden_fantasy_present",
     "text": "You've had a fantasy you've never told anyone. Not because it's wrong — just because saying it out loud would feel exposing."},
    {"id": "hd_03", "signal": "archetype_attraction",
     "text": "There's a specific energy in a person — not necessarily a look — that makes you immediately wonder what they'd be like in bed."},
    {"id": "hd_04", "signal": "shame_adjacent_arousal",
     "text": "You've read or watched something you'd be embarrassed to admit turned you on."},
    {"id": "hd_05", "signal": "desired_intensity",
     "text": "Someone wanting you so much they lose a little control — that does something for you."},
    {"id": "hd_06", "signal": "dom_latent",
     "text": "You've thought about being completely in charge — every decision, every pace, every permission."},
    {"id": "hd_07", "signal": "sub_latent",
     "text": "You've thought about having zero say — someone else deciding everything, and you just going with it."},
    {"id": "hd_08", "signal": "exhib_latent",
     "text": "The thought of someone watching you — even hypothetically — is more interesting than you usually admit."},
    {"id": "hd_09", "signal": "group_latent",
     "text": "You've wondered what it would be like with more than one person involved."},
    {"id": "hd_10", "signal": "unnamed_fixation",
     "text": "There's something specific you've never done but think about more than you'd expect."},
    {"id": "hd_11", "signal": "taboo_draw",
     "text": "A certain kind of taboo — not harmful, just forbidden — is quietly compelling to you."},
    {"id": "hd_12", "signal": "elaborated_fantasy",
     "text": "You've fantasised about a scenario so specific and detailed it surprised you when you noticed how mapped-out it was."},
    {"id": "hd_13", "signal": "authentic_exposure",
     "text": "You're drawn to the idea of being fully seen — no performance, no holding back — and having that be enough."},
    {"id": "hd_14", "signal": "stranger_context",
     "text": "A stranger in a specific setting — a hotel, a flight, a party — and the fantasy almost writes itself."},
    {"id": "hd_15", "signal": "verbal_latent",
     "text": "Words matter to you in bed. The right thing said at the right moment does more than most physical acts."},
]

HD_OPTS = [
    ("nope",     "That's not me",             0),
    ("maybe",    "Maybe, a little",           1),
    ("yes",      "Yeah, that lands",          2),
    ("strongly", "More than I usually admit", 3),
]
HD_OPT_LABELS = [label for _, label, _ in HD_OPTS]
HD_OPT_IDS    = [oid   for oid, _, _ in HD_OPTS]


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
.stButton > button:disabled, .stButton > button[disabled] {
  opacity:0.35 !important; cursor:not-allowed !important;
}
.stProgress > div > div > div { background:var(--magenta) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
div[data-testid="stRadio"] > label { display:none !important; }
div[data-testid="stRadio"] > div { gap:8px !important; flex-direction:column !important; }
div[data-testid="stRadio"] > div > label {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:3px !important; padding:10px 14px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1px !important; color:var(--soft) !important;
  cursor:pointer !important; transition:all 0.15s !important; width:100% !important;
}
div[data-testid="stRadio"] > div > label:hover {
  border-color:var(--lime) !important; color:var(--lime) !important;
}
div[data-testid="stRadio"] > div > label[data-checked="true"] {
  background:var(--magenta) !important; border-color:var(--magenta) !important; color:#fff !important;
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
</style>
""")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_client():
    key = st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in Streamlit secrets.")
    return OpenAI(api_key=key)


def _uid():
    u = st.session_state.get("user", {})
    return u.get("id") if u else None


def _fmt_num(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def _time_ago(ts):
    diff = int(time.time() - ts)
    if diff < 3600:  return f"{diff // 60}m ago"
    if diff < 86400: return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


def _is_taboo(title, body):
    text = (title + " " + body).lower()
    return any(kw in text for kw in TABOO_KEYWORDS)


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
            lines.append(f"{q['signal']}:{'strong' if oid=='strongly' else 'yes'}")
    return ", ".join(lines) if lines else "none"


# ─── REDDIT FETCH ─────────────────────────────────────────────────────────────

def _fetch_one(sub):
    import requests
    url     = f"https://www.reddit.com/r/{sub}/hot.json?limit=20"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuizApp/1.0)", "Accept": "application/json"}

    for fetch_url in [url, "https://api.allorigins.win/raw?url=" + url]:
        try:
            r = requests.get(fetch_url, headers=headers, timeout=4)
            if not r.ok: continue
            data = r.json()
            if "contents" in data:
                data = json.loads(data["contents"])
            children = data.get("data", {}).get("children", [])
            posts = []
            for item in children:
                pd    = item.get("data", {})
                body  = pd.get("selftext", "")
                title = pd.get("title", "")
                if not body or len(body) < MIN_LENGTH:     continue
                if pd.get("score", 0) < MIN_SCORE:         continue
                if pd.get("stickied") or pd.get("pinned"): continue
                if body in ("[deleted]", "[removed]"):      continue
                if not _is_taboo(title, body):             continue
                snippet = body[:TEXT_CUTOFF].strip()
                if len(body) > TEXT_CUTOFF:
                    snippet += "…"
                posts.append({
                    "sub":      f"r/{sub}",
                    "avatar":   (pd.get("author") or "A")[0].upper(),
                    "user":     pd.get("author", "anonymous"),
                    "title":    title[:120],
                    "text":     snippet,
                    "upvotes":  _fmt_num(pd.get("score", 0)),
                    "comments": _fmt_num(pd.get("num_comments", 0)),
                    "time":     _time_ago(pd.get("created_utc", time.time())),
                    "url":      "https://reddit.com" + pd.get("permalink", ""),
                    "flair":    pd.get("link_flair_text") or sub.replace("_", " ").title(),
                })
            if posts: return posts
        except Exception:
            continue
    return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_posts():
    all_posts = []
    try:
        with ThreadPoolExecutor(max_workers=len(SUBREDDITS)) as pool:
            futures = {pool.submit(_fetch_one, sub): sub for sub in SUBREDDITS}
            for future in as_completed(futures, timeout=8):
                try:
                    all_posts.extend(future.result())
                except Exception:
                    pass
    except Exception:
        pass

    if all_posts:
        random.shuffle(all_posts)
        seen, unique = set(), []
        for p in all_posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique.append(p)
        return unique[:POST_COUNT * 2]

    pool = FALLBACK_POSTS.copy()
    random.shuffle(pool)
    return pool[:POST_COUNT]


# ─── QUESTION GENERATION ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _generate_question_cached(post_url: str, post_title: str, post_text: str,
                                post_sub: str, api_key: str) -> dict:
    client = OpenAI(api_key=api_key)
    prompt = (
        f'Reddit post from {post_sub}:\n'
        f'TITLE: {post_title}\n'
        f'EXCERPT: {post_text[:TEXT_CUTOFF]}\n\n'
        f'Write ONE punchy question putting the reader DIRECTLY in this scenario.\n'
        f'Rules:\n'
        f'- Reference a SPECIFIC detail from this post\n'
        f'- Ask about gut reaction, not what they "think about" it\n'
        f'- Must feel personal and slightly uncomfortable to answer honestly\n'
        f'- 4 answer options: closed/protective (pts:0), neutral (pts:2), open/curious (pts:3), fully on-board (pts:5)\n'
        f'- Each option should be 1 vivid sentence\n\n'
        f'Return ONLY JSON: {{"prompt":"...","opts":[{{"t":"...","pts":0}},{{"t":"...","pts":2}},{{"t":"...","pts":3}},{{"t":"...","pts":5}}]}}'
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, dict) or not data.get("prompt") or len(data.get("opts", [])) < 4:
        raise ValueError(f"Bad response: {raw[:80]}")
    return data


def _make_fallback_question(post):
    title = post.get("title", "this scenario")
    short = title[:60] + ("…" if len(title) > 60 else "")
    return {
        "prompt": f'Reading about "{short}" — where does your gut land?',
        "opts": [
            {"t": "Hard no — this kind of thing isn't something I'd ever want near my relationship.", "pts": 0},
            {"t": "I get why people do it, but I'd need a lot more trust before even discussing it.", "pts": 2},
            {"t": "Honestly? The idea is more interesting to me than I'd usually admit out loud.", "pts": 3},
            {"t": "This sounds exactly like a conversation I've already had — or want to have soon.", "pts": 5},
        ],
    }


def generate_all_questions_parallel(posts, api_key):
    results = [None] * len(posts)

    def _gen(idx, post):
        try:
            data = _generate_question_cached(
                post_url=post["url"],
                post_title=post["title"],
                post_text=post["text"],
                post_sub=post["sub"],
                api_key=api_key,
            )
            return idx, data
        except Exception:
            return idx, None

    with ThreadPoolExecutor(max_workers=min(len(posts), 8)) as pool:
        futures = {pool.submit(_gen, i, p): i for i, p in enumerate(posts)}
        try:
            for future in as_completed(futures, timeout=25):
                try:
                    idx, data = future.result()
                    results[idx] = data
                except Exception:
                    pass
        except Exception:
            pass

    questions, failed = [], 0
    for post, q_data in zip(posts, results):
        if q_data:
            questions.append({**post, **q_data})
        else:
            failed += 1
            questions.append({**post, **_make_fallback_question(post)})

    return questions, failed


# ─── PROFILE + CATEGORY SCORING ───────────────────────────────────────────────

def generate_profile_and_categories(result_type, openness_pct, hd_answers,
                                     questions, answers, client) -> dict:
    hd_str = _hd_signal_str(hd_answers)

    pos, neg = [], []
    for qi, ai in enumerate(answers):
        if ai is None or qi >= len(questions): continue
        q   = questions[qi]
        opt = q.get("opts", [])
        if ai >= len(opt): continue
        pts  = opt[ai].get("pts", 0) if isinstance(opt[ai], dict) else 0
        text = (opt[ai].get("t", "") if isinstance(opt[ai], dict) else "")[:60]
        if pts >= 3: pos.append(f'"{q.get("title","")[:40]}": {text}')
        elif pts == 0: neg.append(f'"{q.get("title","")[:40]}": {text}')
    pos_str = "; ".join(pos[:4]) or "none"
    neg_str = "; ".join(neg[:4]) or "none"

    categories_json = json.dumps(ALL_PLATFORM_CATEGORIES)

    prompt = f"""You are a desire profile analyst for an 18+ adult platform.

User profile:
- Openness result: {result_type['name']} ({openness_pct}%)
- Hidden desire signals: {hd_str}
- Resonated with: {pos_str}
- Rejected (DO NOT recommend): {neg_str}

Your tasks — return ONE JSON object with exactly these keys:

1. "ranked_categories": Score EVERY category in this list from 0-10 based on match to this user's profile.
   Higher = stronger match. Rejected items get 0. Be specific — not everything should score 5.
   Categories: {categories_json}

2. "recommendations": Write 5 personalised, frank recommendations (1-2 sentences each).
   Weave in their signals. Respect rejected items strictly. Gender-neutral. Non-judgmental.

Return ONLY valid JSON, no markdown:
{{
  "ranked_categories": {{"CategoryName": score, ...}},
  "recommendations": ["...", "...", "...", "...", "..."]
}}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)

    if not isinstance(data, dict):
        raise ValueError("Profile generation returned invalid JSON")

    raw_scores = data.get("ranked_categories", {})
    scored = []
    for cat in ALL_PLATFORM_CATEGORIES:
        score = int(raw_scores.get(cat, 0))
        scored.append({"name": cat, "score": score})
    scored.sort(key=lambda x: -x["score"])

    top25 = [c["name"] for c in scored[:25]]

    return {
        "ranked_categories": scored,
        "top25_names":       top25,
        "recommendations":   data.get("recommendations", [])[:5],
    }


# ─── STATE ────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "wwyd_phase":         "start",
    "wwyd_load_errors":   0,
    "wwyd_questions":     [],
    "wwyd_answers":       [],
    "wwyd_cur":           0,
    "wwyd_error":         "",
    "wwyd_source":        "live",
    "wwyd_hd_cur":        0,
    "wwyd_hd_answers":    {},
    "wwyd_result_type":   {},
    "wwyd_openness_pct":  0,
    "wwyd_total_pts":     0,
    "wwyd_recs":          [],
    "wwyd_ranked_cats":   [],
    "wwyd_top25":         [],
    "wwyd_selected_cats": [],
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
    fetch_posts.clear()
    init_state()
    st.rerun()


# ─── DB SAVE ──────────────────────────────────────────────────────────────────

def _save_to_db(phase: str):
    """Insert a full result row. Called at profile_complete."""
    uid = _uid()
    if not uid:
        return
    try:
        import database as db
        db.save_read_between_lines_v4(
            user_id=uid,
            phase=phase,
            result_name=st.session_state.get("wwyd_result_type", {}).get("name", ""),
            result_meta=st.session_state.get("wwyd_result_type", {}).get("meta", ""),
            openness_pct=st.session_state.get("wwyd_openness_pct", 0),
            total_pts=st.session_state.get("wwyd_total_pts", 0),
            questions=st.session_state.get("wwyd_questions", []),
            answers=st.session_state.get("wwyd_hd_answers", {}),
            dim_scores={
                "ranked_cats": st.session_state.get("wwyd_ranked_cats", [])[:25],
                "top25":       st.session_state.get("wwyd_top25", []),
                "selected":    st.session_state.get("wwyd_selected_cats", []),
                "hd_signals":  _hd_signal_str(st.session_state.get("wwyd_hd_answers", {})),
            },
            recommendations=st.session_state.get("wwyd_recs", []),
        )
    except Exception:
        pass


def _update_selections_in_db(selected_cats: list):
    """
    Update the existing DB row with the user's confirmed category picks.
    Called when the user clicks 'See My Full Profile →' — after they've
    toggled categories, so what's stored reflects their actual choices.
    """
    uid = _uid()
    if not uid:
        return
    try:
        import database as db
        db.update_rbtl_selected_categories(uid, selected_cats)
    except Exception:
        pass


# ─── HEADER ──────────────────────────────────────────────────────────────────

def _render_header():
    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Desire Quiz</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(44px,9vw,68px);
              color:var(--text); letter-spacing:3px; line-height:0.92; margin-bottom:6px;">
    READ BETWEEN<br><span style="color:var(--magenta);">THE LINES</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:4px;">
    Real Reddit scenarios. Hidden desires. Your full profile.
  </div>
</div>
""")


# ─── PHASE: START ─────────────────────────────────────────────────────────────

def render_start():
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    subs_html = "".join(
        f'<span style="display:inline-block; padding:3px 10px; margin:3px 3px 0 0; '
        f'border:1px solid var(--border); border-radius:2px; '
        f'font-family:\'Space Mono\',monospace; font-size:9px; color:var(--muted);">r/{s}</span>'
        for s in SUBREDDITS
    )

    st.html(f"""
<div class="enter-card">
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--magenta); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:6px;">
      <span class="live-dot"></span>Phase 1 · Reddit Scenarios
    </div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0 0 10px 0;">
      7 real posts. All questions generated in parallel — cached for speed.
    </p>
    <div>{subs_html}</div>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--amber); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber); margin-bottom:6px;">Phase 2 · Hidden Desires</div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0;">
      15 statements designed to surface what you don't usually name out loud.
    </p>
  </div>
  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--cyan); border-radius:4px;
              padding:16px 18px; margin-bottom:20px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--cyan); margin-bottom:6px;">Phase 3 · Your Category Fingerprint</div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.75; margin:0;">
      Every real platform category scored against your profile. Top 25 highlighted — you pick what fits.
    </p>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted); text-align:center; margin-bottom:14px;">
    18+ only · Results saved to your profile
  </div>
</div>
""")

    if st.button("Begin →", use_container_width=True, type="primary", key="start_btn"):
        _wipe()
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

    def upd(pct, status):
        ph_bar.progress(pct)
        ph_status.caption(status)

    try:
        upd(5, "Fetching live scenarios…")
        posts = fetch_posts()
        upd(20, f"{len(posts)} scenarios loaded — generating questions in parallel…")

        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            st.session_state.wwyd_error = "OPENAI_API_KEY not found in secrets."
            st.session_state.wwyd_phase = "start"
            st.rerun()
            return

        selected = posts[:POST_COUNT]
        questions, failed_count = generate_all_questions_parallel(selected, api_key)

        upd(95, "Finalising…")
        time.sleep(0.1)
        upd(100, "Ready.")

        st.session_state.wwyd_questions   = questions
        st.session_state.wwyd_answers     = [None] * len(questions)
        st.session_state.wwyd_cur         = 0
        st.session_state.wwyd_load_errors = failed_count
        st.session_state.wwyd_source      = (
            "live" if any("reddit.com/r/" in p.get("url", "") for p in posts) else "curated"
        )
        st.session_state.wwyd_phase = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Failed to load: {e}. Please try again."
        st.session_state.wwyd_phase = "start"
        st.rerun()


# ─── PHASE: QUIZ ─────────────────────────────────────────────────────────────

def render_quiz():
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

    q        = questions[cur]
    total    = len(questions)
    is_last  = (cur == total - 1)

    segs = "".join(
        f'<div style="flex:1; height:3px; border-radius:2px; background:'
        f'{"var(--magenta)" if i < cur else "rgba(255,45,120,0.4)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 1 · Reddit Scenarios · {cur + 1} / {total}
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
                font-family:'DM Sans',sans-serif; font-size:12px; font-weight:700; flex-shrink:0;">
      {q['avatar']}
    </div>
    <div style="flex:1; min-width:0;">
      <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">{q['sub']}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">u/{q['user']} · {q['time']}</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                padding:3px 8px; border:1px solid var(--border); color:var(--muted);
                text-transform:uppercase; border-radius:2px; white-space:nowrap; flex-shrink:0;">
      {q.get('flair','Post')}
    </div>
  </div>
  <div style="padding:14px 16px 10px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:15px; font-weight:500;
                color:var(--text); line-height:1.5; margin-bottom:8px;">{q['title']}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
                line-height:1.75;">{q['text']}</div>
  </div>
  <div style="padding:8px 16px 10px; border-top:1px solid var(--border);
              display:flex; align-items:center; gap:14px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">▲ {q['upvotes']}</span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">💬 {q['comments']}</span>
    <a href="{q['url']}" target="_blank"
       style="margin-left:auto; font-family:'Space Mono',monospace; font-size:9px;
              color:var(--cyan); text-decoration:none; letter-spacing:1px; text-transform:uppercase;">
      View on Reddit ↗
    </a>
  </div>
</div>
<div style="font-family:'DM Sans',sans-serif; font-size:14px; font-style:italic;
            color:var(--amber); border-left:2px solid var(--amber); padding-left:12px;
            margin-bottom:14px; line-height:1.55;">{q['prompt']}</div>
""")

    opt_labels  = [(opt["t"] if isinstance(opt, dict) else opt) for opt in q["opts"]]
    radio_key   = f"quiz_radio_{cur}"
    current_sel = answers[cur]

    chosen = st.radio(
        label="Your answer",
        options=list(range(len(opt_labels))),
        format_func=lambda i: opt_labels[i],
        index=current_sel,
        key=radio_key,
        horizontal=False,
    )

    if chosen != current_sel:
        a = list(st.session_state.wwyd_answers)
        a[cur] = chosen
        st.session_state.wwyd_answers = a

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
                st.session_state.wwyd_phase  = "hidden_desires"
            else:
                st.session_state.wwyd_cur += 1
            st.rerun()


# ─── PHASE: HIDDEN DESIRES ────────────────────────────────────────────────────

def render_hidden_desires():
    total   = len(HIDDEN_DESIRE_QUESTIONS)
    answers = st.session_state.wwyd_hd_answers
    cur     = max(0, min(st.session_state.wwyd_hd_cur, total - 1))
    st.session_state.wwyd_hd_cur = cur

    q       = HIDDEN_DESIRE_QUESTIONS[cur]
    sel_id  = answers.get(q["id"])
    is_last = (cur == total - 1)

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
            border-top:2px solid var(--amber); border-radius:4px; padding:24px; margin-bottom:14px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:3px;
              text-transform:uppercase; color:var(--amber); margin-bottom:10px;">How much does this resonate?</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; font-style:italic;
              color:var(--text); line-height:1.65;">{q['text']}</div>
</div>
""")

    current_idx = HD_OPT_IDS.index(sel_id) if sel_id in HD_OPT_IDS else None
    radio_key   = f"hd_radio_{cur}"
    chosen_idx  = st.radio(
        label="Resonance",
        options=list(range(len(HD_OPT_LABELS))),
        format_func=lambda i: HD_OPT_LABELS[i],
        index=current_idx,
        key=radio_key,
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
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:20px;">BUILDING YOUR PROFILE</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, s): ph_bar.progress(pct); ph_status.caption(s)

    try:
        upd(10, "Computing your Phase 1 score…")

        questions = st.session_state.wwyd_questions
        answers   = st.session_state.wwyd_answers
        hd_ans    = st.session_state.wwyd_hd_answers

        total_pts = sum(
            (q.get("opts", [])[a].get("pts", 0) if isinstance(q.get("opts", [])[a], dict) else 0)
            for q, a in zip(questions, answers)
            if a is not None and a < len(q.get("opts", []))
        )
        max_pts = sum(
            max((o.get("pts", 0) if isinstance(o, dict) else 0 for o in (q.get("opts") or [])), default=0)
            for q in questions
        )
        pct         = round((total_pts / max_pts) * 100) if max_pts else 0
        result_type = next((r for r in RESULT_TYPES if r["min"] <= total_pts <= r["max"]), RESULT_TYPES[-1])

        upd(30, "Scoring every platform category against your profile…")

        client       = _get_client()
        profile_data = generate_profile_and_categories(
            result_type, pct, hd_ans, questions, answers, client
        )

        upd(100, "Done.")
        time.sleep(0.15)

        st.session_state.wwyd_result_type   = result_type
        st.session_state.wwyd_openness_pct  = pct
        st.session_state.wwyd_total_pts     = total_pts
        st.session_state.wwyd_ranked_cats   = profile_data["ranked_categories"]
        st.session_state.wwyd_top25         = profile_data["top25_names"]
        st.session_state.wwyd_recs          = profile_data["recommendations"]
        # Pre-select AI top 25 as the starting point
        st.session_state.wwyd_selected_cats = list(profile_data["top25_names"])
        st.session_state.wwyd_phase         = "category_selector"

        # Save initial result row (selected = AI top 25 defaults at this point)
        _save_to_db("profile_complete")
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Couldn't build your profile: {e}"
        st.session_state.wwyd_phase = "start"
        st.rerun()


# ─── PHASE: CATEGORY SELECTOR ────────────────────────────────────────────────

def render_category_selector():
    ranked_cats = st.session_state.wwyd_ranked_cats
    top25_names = set(st.session_state.wwyd_top25)
    selected    = set(st.session_state.wwyd_selected_cats)

    pct         = st.session_state.get("wwyd_openness_pct", 0)
    result_type = st.session_state.get("wwyd_result_type", {})

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Phase 3 · Your Category Fingerprint</div>
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--cyan); border-radius:4px; padding:18px 20px; margin-bottom:16px;">
  <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--text);
                  letter-spacing:2px;">{result_type.get('icon','')} {result_type.get('name','')}</div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--magenta);
                  letter-spacing:1px; text-transform:uppercase; margin-top:2px;">{result_type.get('meta','')}</div>
    </div>
    <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
                padding:8px 14px; text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--text);">{pct}</div>
      <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">openness %</div>
    </div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); margin-top:12px; line-height:1.7;">
    Every real platform category scored against your signals.
    <span style="color:var(--lime); font-weight:600;">Lime = AI top 25 picks for you.</span>
    Toggle anything you want — or don't.
  </div>
</div>
<div style="display:flex; gap:16px; align-items:center; margin-bottom:14px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted);">
    {len(selected)} selected
  </div>
  <div style="display:flex; gap:8px; margin-left:auto;">
    <div style="display:flex; align-items:center; gap:5px;">
      <div style="width:10px; height:10px; border:1px solid var(--lime); border-radius:2px;"></div>
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">AI top 25</span>
    </div>
    <div style="display:flex; align-items:center; gap:5px;">
      <div style="width:10px; height:10px; border:1px solid var(--border); border-radius:2px;
                  background:var(--magenta);"></div>
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">selected</span>
    </div>
  </div>
</div>
""")

    cols = st.columns(3)
    for idx, cat_info in enumerate(ranked_cats):
        cat_name  = cat_info["name"]
        cat_score = cat_info["score"]
        is_top25  = cat_name in top25_names
        is_sel    = cat_name in selected

        if is_sel:
            btn_label = f"✓ {cat_name}"
        elif is_top25:
            btn_label = f"◆ {cat_name}"
        else:
            btn_label = cat_name

        with cols[idx % 3]:
            if st.button(
                btn_label,
                key=f"cat_{idx}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                new_sel = set(st.session_state.wwyd_selected_cats)
                if is_sel:
                    new_sel.discard(cat_name)
                else:
                    new_sel.add(cat_name)
                st.session_state.wwyd_selected_cats = list(new_sel)
                st.rerun()

            if cat_score > 0:
                bar_color = "var(--lime)" if is_top25 else "var(--border)"
                fill_pct  = min(100, cat_score * 10)
                st.html(f"""
<div style="height:2px; background:var(--border); border-radius:1px; margin:-6px 0 8px;">
  <div style="width:{fill_pct}%; height:100%; background:{bar_color}; border-radius:1px;"></div>
</div>
""")

    st.html("<br>")
    sel_count = len(selected)
    if st.button("See My Full Profile →", use_container_width=True, type="primary",
                 disabled=(sel_count == 0), key="cat_next"):
        # ── SAVE USER'S ACTUAL SELECTIONS TO DB ──────────────────────────────
        # This updates the row created at profile_complete so the stored record
        # reflects what the user actually chose, not just the AI defaults.
        _update_selections_in_db(list(selected))
        # ─────────────────────────────────────────────────────────────────────
        st.session_state.wwyd_phase = "result"
        st.rerun()


# ─── PHASE: RESULT ────────────────────────────────────────────────────────────

def render_result():
    result_type = st.session_state.get("wwyd_result_type") or RESULT_TYPES[0]
    pct         = st.session_state.get("wwyd_openness_pct", 0)
    sel_cats    = st.session_state.get("wwyd_selected_cats", [])
    recs        = st.session_state.get("wwyd_recs", [])
    ranked_cats = st.session_state.get("wwyd_ranked_cats", [])
    hd_ans      = st.session_state.get("wwyd_hd_answers", {})

    st.html(f"""
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--magenta); border-radius:4px;
            padding:28px 24px; text-align:center; margin-bottom:14px;">
  <div style="font-size:48px; margin-bottom:10px;">{result_type['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(28px,6vw,46px);
              letter-spacing:3px; color:var(--text); line-height:1.05; margin-bottom:4px;">
    {result_type['name'].upper()}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--magenta); text-transform:uppercase; margin-bottom:16px;">
    {result_type['meta']}
  </div>
  <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
             line-height:1.85; margin-bottom:20px; max-width:480px; margin-left:auto; margin-right:auto;">
    {result_type['desc']}
  </p>
  <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px; padding:14px;">
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

    strong = [q for q in HIDDEN_DESIRE_QUESTIONS if hd_ans.get(q["id"]) in ("yes", "strongly")]
    if strong:
        sigs_html = "".join(
            f'<div style="display:flex; gap:10px; align-items:flex-start; padding:8px 0; '
            f'border-bottom:1px solid var(--border);">'
            f'<span style="color:var(--amber); flex-shrink:0; margin-top:2px;">'
            f'{"★" if hd_ans.get(q["id"])=="strongly" else "◆"}</span>'
            f'<div style="font-family:\'DM Sans\',sans-serif; font-size:12px; color:var(--soft); '
            f'line-height:1.65; font-style:italic;">{q["text"]}</div></div>'
            for q in strong
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:10px;">
    Hidden Desire Signals · {len(strong)}
  </div>
  {sigs_html}
</div>
""")

    if ranked_cats:
        top10     = [c for c in ranked_cats[:10] if c["score"] > 0]
        max_score = ranked_cats[0]["score"] if ranked_cats else 1
        bars_html = "".join(
            f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">'
            f'<div style="font-family:\'Space Mono\',monospace; font-size:9px; '
            f'color:{"var(--lime)" if c["name"] in sel_cats else "var(--soft)"}; '
            f'width:150px; flex-shrink:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; '
            f'text-transform:uppercase; letter-spacing:1px;">'
            f'{"✓ " if c["name"] in sel_cats else ""}{c["name"]}</div>'
            f'<div style="flex:1; height:3px; background:var(--border); border-radius:2px;">'
            f'<div style="width:{min(100, round(c["score"]/max_score*100))}%; height:100%; '
            f'background:{"var(--lime)" if c["name"] in sel_cats else "var(--muted)"}; border-radius:2px;"></div>'
            f'</div>'
            f'<div style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--muted); '
            f'width:20px; text-align:right;">{c["score"]}</div>'
            f'</div>'
            for c in top10
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:12px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:4px;">
    Your Content Fingerprint · Top 10
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:11px; color:var(--muted);
              margin-bottom:14px; line-height:1.6;">
    Scored against your desire signals and openness tier.
    {len(sel_cats)} categories selected.
  </div>
  {bars_html}
</div>
""")

    if recs:
        recs_html = "".join(
            f'<div style="background:var(--surface); border:1px solid var(--border); '
            f'border-left:2px solid var(--magenta); border-radius:0 4px 4px 0; '
            f'padding:12px 16px; margin-bottom:8px; font-family:\'DM Sans\',sans-serif; '
            f'font-size:13px; color:var(--soft); line-height:1.75;">{r}</div>'
            for r in recs
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:18px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:12px;">Things Worth Exploring</div>
  {recs_html}
</div>
""")

    share = (
        f"Read Between The Lines — Vice Vault\n\n"
        f"Result: {result_type['name']}\n\"{result_type['meta']}\"\n"
        f"Openness Index: {pct}%\n\n{result_type['desc']}\n\n"
    )
    if strong:
        share += "Signals: " + ", ".join(q["signal"] for q in strong[:5]) + "\n\n"
    if sel_cats:
        share += "My categories: " + ", ".join(sel_cats[:10]) + "\n\n"
    if recs:
        share += "Recommendations:\n" + "\n".join(f"· {r}" for r in recs[:3])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Try Again", use_container_width=True, key="try_again"):
            hard_reset()
    with col2:
        st.download_button(
            "↓ Save Result",
            data=share, file_name="rbtl_result.txt",
            mime="text/plain", use_container_width=True, key="save_result"
        )


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()
    _render_header()

    phase = st.session_state.wwyd_phase

    if   phase == "start":              render_start()
    elif phase == "loading":            render_loading()
    elif phase == "quiz":               render_quiz()
    elif phase == "hidden_desires":     render_hidden_desires()
    elif phase == "generating_profile": render_generating_profile()
    elif phase == "category_selector":  render_category_selector()
    elif phase == "result":             render_result()
    else:
        _wipe()
        init_state()
        st.rerun()
