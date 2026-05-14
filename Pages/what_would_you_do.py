"""
Pages/what_would_you_do.py
What Would You Do? — 3-phase desire profile quiz.

Phase 1: Reddit-powered scenario quiz (10 questions, AI-generated)
Phase 2: Hidden desires checklist (15 statements, self-report)
Phase 3: Fantasy category selector (25 AI-generated labels)
Result:  Full personalised profile + 5 recommendations via GPT

FIXES:
  - Backend: OpenAI (gpt-4o-mini) via OPENAI_API_KEY in secrets
  - Reddit fetch: parallel ThreadPoolExecutor + guaranteed fallback, never blocks
  - generate_question: robust JSON parsing, graceful per-question fallback
  - Phase transitions: clean state machine, no double-click bugs
  - generate_fantasies / generate_recommendations: explicit error surfaces
  - CSS: consolidated, no duplicate rules, sidebar styled consistently
  - All st.markdown(..., unsafe_allow_html=True) replaced with st.html()

BUG FIXES:
  - render_quiz(): safe list copy-reassign for wwyd_answers
  - render_hidden_desires():
      * wwyd_hd_cur clamped AND written back to session_state
      * re-clicking an already-selected option no longer auto-advances
      * explicit "Next →" button added for non-last questions (back-then-forward is now possible)
  - what_would_you_do_page(): removed unreachable duplicate _wipe/init_state/rerun
  - render_generating_fantasies(): max_pts uses max(..., default=0) — no crash on empty opts
  - fetch_posts(): TimeoutError from as_completed now caught at the outer level
  - UI text: "Claude writes" → "AI writes" (code uses gpt-4o-mini, not Claude)
"""

import streamlit as st
import json
import random
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

SUBREDDITS = [
    "sex", "nonmonogamy", "polyamory", "swingers",
    "confessions", "trueoffmychest", "relationship_advice",
    "openrelationships",
]

TABOO_KEYWORDS = [
    "threesome", "3some", "open relationship", "swinger", "polyamory",
    "fantasy", "attracted to", "cheated", "affair", "tempted", "curious about",
    "another person", "someone else", "bring someone", "invite", "experiment",
    "exploring", "never told anyone", "taboo", "forbidden", "secret",
    "want to try", "thinking about", "nonmonogamy", "ethical non",
    "open marriage", "group", "voyeur", "exhibitionist",
    "fmf", "mfm", "confession", "told my partner", "my partner told me",
    "we tried", "we talked about",
]

MIN_SCORE  = 50
MIN_LENGTH = 200
POST_COUNT = 10

FALLBACK_POSTS = [
    {"sub": "r/relationship_advice", "avatar": "T", "user": "throwaway_82947",
     "title": "My partner and I accidentally started a conversation we can't take back",
     "text": "We've been together three years. Last Saturday we had some friends over and after everyone left, one of them made a joke about how 'it's a shame you two are taken.' Nobody laughed it off. There was this long pause where we all just looked at each other. My partner and I talked about it after they left and it turned into a two-hour conversation about things we'd never said out loud before. I don't know what we're doing but I don't feel scared about it.",
     "upvotes": "14.2k", "comments": "832", "time": "6 hours ago",
     "url": "https://reddit.com/r/relationship_advice", "flair": "Long Post"},
    {"sub": "r/confessions", "avatar": "A", "user": "anon_user_2291",
     "title": "I told my best friend exactly what happens in our bedroom because she asked — my partner walked in halfway through",
     "text": "She's been single for a while and we were deep in a wine conversation when she said she was jealous — not of my relationship, specifically of the intimacy. She asked if I'd describe what it's actually like. I did. In detail. My partner walked in halfway through and just sat down and listened. Nobody was uncomfortable. Nobody said 'that's too much information.' When she left, my partner said, 'I didn't mind that.' We haven't talked about what that means yet.",
     "upvotes": "9.7k", "comments": "1.2k", "time": "2 days ago",
     "url": "https://reddit.com/r/confessions", "flair": "True Story"},
    {"sub": "r/trueoffmychest", "avatar": "S", "user": "strangebutreal",
     "title": "My partner and I spent four hours talking about a hypothetical last night and I've never felt closer to them",
     "text": "It started with a dumb hypothetical — I said 'if you could add anyone to our relationship for one night, no consequences, who would you say?' I expected them to laugh it off. They didn't. They answered. Thoughtfully. With a name. So I answered too. Then we started talking about how it would actually work, what the rules would be, whether we'd feel jealous. We never agreed to do anything. I feel like I know them more than I did yesterday.",
     "upvotes": "18.3k", "comments": "976", "time": "5 hours ago",
     "url": "https://reddit.com/r/trueoffmychest", "flair": "Personal"},
    {"sub": "r/nonmonogamy", "avatar": "M", "user": "maybe_mistakes",
     "title": "AITA for telling my girlfriend that her being bothered by my fantasy means she doesn't trust me?",
     "text": "I told her about a recurring fantasy — nothing I expected to act on, just something in my head. She got quiet for a while and then said it made her feel like she wasn't enough. I told her that's not what fantasies mean, and that being bothered by something I've never done makes me feel like she assumes the worst of me. She said I was being defensive. I said she was conflating imagination with intention. We're still in this argument three days later. The fantasy involved someone we both know.",
     "upvotes": "22.1k", "comments": "3.4k", "time": "1 day ago",
     "url": "https://reddit.com/r/nonmonogamy", "flair": "Advice"},
    {"sub": "r/polyamory", "avatar": "L", "user": "late_night_post_88",
     "title": "My close friend accidentally sent my partner a text I wrote about wanting to explore an open relationship",
     "text": "My close friend had been asking for advice on her relationship. I sent her this long message about how I think openness between partners is underrated, and I gave a specific example — that I'd thought about what it would be like if we ever brought someone else into things, and that my partner's reaction if I ever brought it up was the thing stopping me. She screenshotted it and sent it to my partner by accident. He texted me three seconds later. I thought I was about to have the worst conversation of my life. He said: 'Why haven't you just told me this?'",
     "upvotes": "31.5k", "comments": "2.1k", "time": "3 days ago",
     "url": "https://reddit.com/r/polyamory", "flair": "Story"},
    {"sub": "r/swingers", "avatar": "W", "user": "wontusemyname",
     "title": "UPDATE: We did it. Here's the honest version of what happened.",
     "text": "Original post was six months ago. Short version: my partner and I had been curious, we met someone we both trusted, and after a lot of conversations we stopped overthinking and made a decision. Here's what nobody tells you: the hardest part was the three days before, not the night itself. The night was calm. Everyone knew the agreement. Nobody felt left out. The morning after, we made breakfast together and laughed a lot. It wasn't perfect — there were small moments of awkwardness that we talked through over the next week. But if someone asked me today whether I'd do it again, the answer would be yes.",
     "upvotes": "19.4k", "comments": "1.1k", "time": "2 days ago",
     "url": "https://reddit.com/r/swingers", "flair": "Update"},
    {"sub": "r/sex", "avatar": "N", "user": "nightowl_anon",
     "title": "The reason most couples never talk about threesomes isn't morality — it's fear of the answer",
     "text": "Think about it. The hesitation isn't really about whether it's a good idea. It's about the moment after you ask, when you see their face — and you find out who they actually are. If they're excited, now you know something. If they're horrified, now you know something else. Either answer changes things. So instead of asking, most people just carry the question around for years and call that loyalty. I'm not saying it should always be asked. I'm saying the reason it isn't has nothing to do with morality.",
     "upvotes": "8.9k", "comments": "2.3k", "time": "12 hours ago",
     "url": "https://reddit.com/r/sex", "flair": "Discussion"},
    {"sub": "r/openrelationships", "avatar": "C", "user": "confessed_at_midnight",
     "title": "I've been in a situation most people would call complicated. I consider it the best year of my life.",
     "text": "About two years ago, my partner and I became very close with another person — someone we both trusted, liked, and were both, separately, attracted to. We never planned what happened. It evolved slowly over months. There were awkward conversations, check-ins, one moment where someone cried and we almost stopped everything. But we didn't stop. We spent a year navigating something that nobody gave us a map for and on the other side of it, my relationship with my partner is the strongest it's ever been.",
     "upvotes": "27.8k", "comments": "4.5k", "time": "4 days ago",
     "url": "https://reddit.com/r/openrelationships", "flair": "Experience"},
    {"sub": "r/relationship_advice", "avatar": "F", "user": "finally_saying_it",
     "title": "My partner told me they've always been curious about this and I said nothing. That was six months ago.",
     "text": "They brought it up casually, like it was just a thought, not a request. I panicked internally and changed the subject and they never brought it up again. But I think about it almost every week. Not because I'm angry or hurt — because I keep asking myself what I actually think about it, and I don't have a clean answer. Part of me is curious. Part of me is scared. Part of me wonders what would have happened if I'd just said 'tell me more' instead of going quiet. I don't know if I'm ready to reopen the conversation.",
     "upvotes": "12.6k", "comments": "889", "time": "8 hours ago",
     "url": "https://reddit.com/r/relationship_advice", "flair": "Serious"},
    {"sub": "r/confessions", "avatar": "B", "user": "burner_acct_now",
     "title": "People who've actually had a threesome — what happened to your relationship after?",
     "text": "Top comment: 'We talked about it for months before anything happened. The conversation itself changed our relationship — more honesty, more trust. We stopped performing for each other.' Second: 'We tried it. It was amazing and also complicated and also something I'd do again.' Third: 'The fact that we could have the conversation without falling apart told me more about our relationship than anything else ever had.' Fourth: 'We found out we wanted very different things. That was hard but also necessary to know.' Fifth: 'Still together four years later. No regrets.'",
     "upvotes": "41.2k", "comments": "7.8k", "time": "1 week ago",
     "url": "https://reddit.com/r/confessions", "flair": "Discussion"},
]

RESULT_TYPES = [
    {"min": 0,  "max": 10,  "icon": "🔒", "name": "Closed Garden",
     "meta": "Yours. Only yours. Period.",
     "desc": "You're wired for exclusivity and you're not apologizing for it. Every scenario made you want to protect something — and that instinct is real. You believe some things should stay between two people, and no amount of 'communication' changes what you fundamentally want. That's not fear. That's a value."},
    {"min": 11, "max": 22,  "icon": "🌿", "name": "Quietly Curious",
     "meta": "The thought has crossed your mind. More than once.",
     "desc": "You'd never bring it up unprompted, but these scenarios made something stir. You're more open than your default settings suggest. Given the right relationship, the right trust level, and the right conversation — you'd hear someone out. You're not closed. You're just careful about who gets the key."},
    {"min": 23, "max": 35,  "icon": "🌙", "name": "The Open Door",
     "meta": "You've thought this through. Seriously.",
     "desc": "You're past the theoretical phase. These scenarios didn't make you uncomfortable — they made you think. You understand the dynamics, you've processed the jealousy question, and you're emotionally equipped for complexity. The only thing between you and yes is finding the right moment and the right person."},
    {"min": 36, "max": 44,  "icon": "🔺", "name": "Already Decided",
     "meta": "The question isn't whether. It's when.",
     "desc": "There's no internal conflict left in you on this. You read these scenarios and recognized yourself — not as an observer but as someone who's either been in a version of these situations or is clearly ready. You know what you want. You manage the emotional complexity well. You're not waiting for permission."},
    {"min": 45, "max": 999, "icon": "⚡", "name": "The Third Is Already Picked",
     "meta": "You know exactly who. They probably know too.",
     "desc": "You're not curious — you're experienced or so ready it's the same thing. These scenarios felt like reading your own diary entries. You've had the late-night conversations, sat in the silence, made the decision. Whoever you send this quiz to will understand immediately why you sent it."},
]

FALLBACK_OPTS = [
    {"t": "This makes me uncomfortable — I'd want no part of it.", "pts": 0},
    {"t": "I understand it but it's not something I'd personally want.", "pts": 1},
    {"t": "I'm genuinely curious — this scenario has me thinking.", "pts": 3},
    {"t": "This resonates more than I'd admit out loud.", "pts": 5},
]

HIDDEN_DESIRE_QUESTIONS = [
    {"id": "hd_01", "signal": "power_dynamic_latent",
     "text": "You're watching a film. A scene comes on — nothing explicitly sexual — but something about the power dynamic between two characters makes you shift in your seat."},
    {"id": "hd_02", "signal": "hidden_fantasy_present",
     "text": "You've had a fantasy you've never told anyone. Not because it's wrong — just because you'd feel exposed saying it out loud."},
    {"id": "hd_03", "signal": "archetype_attraction",
     "text": "There's a type of person — a specific energy, not necessarily a look — that makes you immediately wonder what they'd be like in bed."},
    {"id": "hd_04", "signal": "shame_adjacent_arousal",
     "text": "You've read or watched something — a story, a scene, a clip — that you'd be embarrassed to admit turned you on."},
    {"id": "hd_05", "signal": "desired_intensity",
     "text": "The idea of someone wanting you so much they lose a little control — that does something for you."},
    {"id": "hd_06", "signal": "dom_latent",
     "text": "You've thought about being the one completely in charge — every decision, every pace, every permission."},
    {"id": "hd_07", "signal": "sub_latent",
     "text": "You've thought about having zero say — someone else making every call, and you just... going with it."},
    {"id": "hd_08", "signal": "exhib_latent",
     "text": "The thought of someone watching you — even hypothetically — is more interesting than you usually admit."},
    {"id": "hd_09", "signal": "group_latent",
     "text": "You've caught yourself wondering what it would be like with more than one person involved."},
    {"id": "hd_10", "signal": "unnamed_fixation",
     "text": "There's something specific you've never done but think about more than you'd expect."},
    {"id": "hd_11", "signal": "taboo_draw",
     "text": "You find a certain kind of taboo — not harmful, just forbidden — quietly compelling."},
    {"id": "hd_12", "signal": "elaborated_fantasy",
     "text": "You've fantasised about a scenario so specific and detailed that it surprised you when you realised how mapped-out it was."},
    {"id": "hd_13", "signal": "authentic_exposure",
     "text": "You're drawn to the idea of being seen exactly as you are — no performance, no holding back — and that being enough."},
    {"id": "hd_14", "signal": "stranger_context",
     "text": "A stranger in a specific setting — a hotel, a flight, a party — and the fantasy almost writes itself."},
    {"id": "hd_15", "signal": "verbal_latent",
     "text": "Words matter to you in bed — the right thing said at the right moment does more than most physical acts."},
]

HD_OPTS = [
    ("nope",     "That's not me",             0),
    ("maybe",    "Maybe, a little",           1),
    ("yes",      "Yeah, that lands",          2),
    ("strongly", "More than I usually admit", 3),
]


# ─── CSS ─────────────────────────────────────────────────────────────────────

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
.stButton > button:disabled,
.stButton > button[disabled] {
  opacity:0.4 !important; cursor:not-allowed !important;
}

.stProgress > div > div > div { background:var(--magenta) !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }

@keyframes card-enter {
  from { opacity:0; transform:translateY(12px); }
  to   { opacity:1; transform:translateY(0); }
}
.enter-card { animation:card-enter 0.35s ease both; }
</style>
""")


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _get_client():
    try:
        key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not found in Streamlit secrets.")
        return OpenAI(api_key=key)
    except Exception as e:
        raise RuntimeError(f"OpenAI client error: {e}")


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
    """Strip markdown fences and parse JSON. Returns None on failure."""
    try:
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return None


def _hd_signal_str(hd_answers):
    lines = []
    for q in HIDDEN_DESIRE_QUESTIONS:
        oid = hd_answers.get(q["id"])
        if oid in ("yes", "strongly"):
            lines.append(f"- {q['signal']}: {'strongly present' if oid == 'strongly' else 'present'}")
    return "\n".join(lines) if lines else "No strong signals detected."


def _quiz_context(questions, answers):
    positive, negative = [], []
    for qi, ai in enumerate(answers):
        if ai is None or qi >= len(questions):
            continue
        q    = questions[qi]
        opts = q.get("opts", [])
        if ai >= len(opts):
            continue
        pts   = opts[ai].get("pts", 0)
        text  = opts[ai].get("t", "")[:80]
        title = q.get("title", "")[:50]
        if pts >= 3:
            positive.append(f'- "{title}": {text}')
        elif pts == 0:
            negative.append(f'- "{title}": {text}')
    return (
        "\n".join(positive)  if positive  else "Nothing strongly resonated.",
        "\n".join(negative)  if negative  else "Nothing strongly rejected.",
    )


# ─── REDDIT FETCH ─────────────────────────────────────────────────────────────

def _fetch_one(args):
    import requests
    sub, sort = args
    url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit=25"
    if sort == "top":
        url += "&t=month"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; QuizApp/1.0)", "Accept": "application/json"}

    for fetch_url in [url, "https://api.allorigins.win/raw?url=" + url]:
        try:
            r = requests.get(fetch_url, headers=headers, timeout=5)
            if not r.ok:
                continue
            data = r.json()
            if "contents" in data:
                data = json.loads(data["contents"])
            children = data.get("data", {}).get("children", [])
            posts = []
            for item in children:
                pd    = item.get("data", {})
                body  = pd.get("selftext", "")
                title = pd.get("title", "")
                if not body or len(body) < MIN_LENGTH:       continue
                if pd.get("score", 0) < MIN_SCORE:           continue
                if pd.get("stickied") or pd.get("pinned"):   continue
                if body in ("[deleted]", "[removed]"):        continue
                if not _is_taboo(title, body):               continue
                posts.append({
                    "sub":      f"r/{sub}",
                    "avatar":   (pd.get("author") or "A")[0].upper(),
                    "user":     pd.get("author", "anonymous"),
                    "title":    title,
                    "text":     body[:900].strip(),
                    "upvotes":  _fmt_num(pd.get("score", 0)),
                    "comments": _fmt_num(pd.get("num_comments", 0)),
                    "time":     _time_ago(pd.get("created_utc", time.time())),
                    "url":      "https://reddit.com" + pd.get("permalink", ""),
                    "flair":    pd.get("link_flair_text") or sub.replace("_", " ").title(),
                })
            if posts:
                return posts
        except Exception:
            continue
    return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_posts():
    tasks     = [(sub, "hot") for sub in SUBREDDITS]
    all_posts = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tasks}
        # FIX: wrap outer loop to catch TimeoutError from as_completed itself
        try:
            for future in as_completed(futures, timeout=12):
                try:
                    all_posts.extend(future.result())
                except Exception:
                    pass
        except Exception:
            pass  # TimeoutError or similar — use whatever posts we managed to collect

    if all_posts:
        random.shuffle(all_posts)
        seen, unique = set(), []
        for p in all_posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique.append(p)
        return unique[: POST_COUNT * 2]

    # Guaranteed fallback — always works
    pool = FALLBACK_POSTS.copy()
    random.shuffle(pool)
    return pool[:POST_COUNT]


# ─── OPENAI: QUESTION GENERATOR ──────────────────────────────────────────────

def generate_question(post, client):
    user_prompt = f"""Reddit post:
SUBREDDIT: {post['sub']}
TITLE: {post['title']}
TEXT: {post['text']}

Write a short, provocative quiz question (1-2 sentences) asking the reader their honest gut reaction.

Then write 4 answer options as a genuine gradient:
- pts 0: closed off, uncomfortable, protective
- pts 2: cautious but curious  
- pts 3: genuinely intrigued, open-minded
- pts 5: fully ready or experienced, deeply relatable

Each option: 1-2 authentic sentences. No generic filler.

Return ONLY this JSON, nothing else:
{{"prompt":"your question here","opts":[{{"t":"option text","pts":0}},{{"t":"option text","pts":2}},{{"t":"option text","pts":3}},{{"t":"option text","pts":5}}]}}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=700,
        temperature=0.9,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write questions for an adults-only desire quiz. "
                    "You ALWAYS respond with valid JSON only — no markdown fences, "
                    "no preamble, no explanation. Just the raw JSON object."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Response was not a JSON object: {raw[:100]}")
    if not data.get("prompt"):
        raise ValueError(f"Missing 'prompt' key in response: {list(data.keys())}")
    if not data.get("opts") or len(data["opts"]) < 4:
        raise ValueError(f"Not enough opts: {len(data.get('opts', []))}")
    return data


# ─── OPENAI: FANTASY GENERATOR ───────────────────────────────────────────────

def generate_fantasies(result_type, openness_pct, hd_answers, questions, answers, client):
    hd_str           = _hd_signal_str(hd_answers)
    pos_str, neg_str = _quiz_context(questions, answers)

    prompt = f"""You generate a personalised adult fantasy category menu for Vice Vault — a verified 18+ adult platform.

USER PROFILE:
- Openness result: {result_type['name']} — "{result_type['meta']}"
- Openness index: {openness_pct}%
- Description: {result_type['desc']}

HIDDEN DESIRE SIGNALS (what resonated strongly):
{hd_str}

SCENARIOS THEY RESONATED WITH:
{pos_str}

SCENARIOS THEY REJECTED (do NOT appear in any form):
{neg_str}

Generate exactly 25 EXPLICIT adult sexual fantasy category labels for this person.
These are real adult content categories — specific, direct, and genuinely arousing. Not soft or euphemistic.

Rules:
- Name the actual fantasy, kink, or scenario directly (e.g. "power exchange", "being watched", "stranger in a hotel room", "slow seduction from behind", "dominance and submission", "tied up and teased", "voice-only arousal", "public risk", "possessive partner energy", "consensual loss of control")
- Short labels, 3-8 words each
- Order: closest match to this person's signals → interesting adjacent territory → 4-5 stretches at the end
- Gender-neutral, orientation-neutral phrasing
- No gendered anatomy in labels
- Rejected scenarios must NOT appear in any form

Return ONLY a JSON array of exactly 25 strings, no markdown, no preamble:
["label one", "label two", ...]"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1000,
        temperature=0.9,
        messages=[
            {"role": "system", "content": "You generate content for a verified 18+ adult app. Respond with valid JSON only — a raw JSON array of strings. No markdown, no preamble, no explanation."},
            {"role": "user", "content": prompt},
        ],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, list) or len(data) < 10:
        raise ValueError(f"Received {len(data) if isinstance(data, list) else 0} categories (need ≥10). Raw: {raw[:200]}")
    return data[:25]


# ─── OPENAI: RECOMMENDATIONS ─────────────────────────────────────────────────

def generate_recommendations(result_type, openness_pct, hd_answers, questions, answers, selected_fantasies, client):
    hd_str           = _hd_signal_str(hd_answers)
    pos_str, neg_str = _quiz_context(questions, answers)
    fantasy_str      = "\n".join(f"- {f}" for f in selected_fantasies) if selected_fantasies else "None selected."

    prompt = f"""You are a frank, sex-positive desire analyst for Vice Vault — a verified 18+ adult lifestyle app.

USER PROFILE:
- Openness result: {result_type['name']} — "{result_type['meta']}"
- Openness index: {openness_pct}%
- {result_type['desc']}

WHAT RESONATED IN THE QUIZ:
{pos_str}

WHAT THEY REJECTED (strictly off limits — do not reference):
{neg_str}

HIDDEN DESIRE SIGNALS:
{hd_str}

FANTASY CATEGORIES THEY SELECTED:
{fantasy_str}

Write exactly 5 personalised, specific recommendations synthesising ALL of the above.
- Selected fantasies must be woven in — not just listed back
- Strong hidden signals should be reflected directly
- Rejected items: strictly forbidden, nothing adjacent either
- Tone: frank, knowledgeable, non-judgmental. 1-2 sentences each.
- Gender-neutral, orientation-neutral.

Return ONLY a JSON array of 5 strings, no markdown:
["rec one.", "rec two.", ...]"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        temperature=0.9,
        messages=[
            {"role": "system", "content": "You are a desire analyst for a verified 18+ adult app. Respond with valid JSON only — a raw JSON array of exactly 5 strings. No markdown, no preamble, no explanation."},
            {"role": "user", "content": prompt},
        ],
    )
    raw  = resp.choices[0].message.content.strip()
    data = _safe_json(raw)
    if not isinstance(data, list):
        raise ValueError(f"Recommendations not a list. Raw: {raw[:200]}")
    return data[:5]


# ─── STATE ───────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "wwyd_phase":         "start",
    "wwyd_load_errors":   [],
    "wwyd_questions":     [],
    "wwyd_answers":       [],
    "wwyd_cur":           0,
    "wwyd_error":         "",
    "wwyd_source":        "live",
    "wwyd_hd_cur":        0,
    "wwyd_hd_answers":    {},
    "wwyd_fantasies":     [],
    "wwyd_selected":      [],
    "wwyd_fantasy_error": "",
    "wwyd_result_type":   {},
    "wwyd_openness_pct":  0,
    "wwyd_total_pts":     0,
    "wwyd_recs":          [],
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


# ─── HEADER ──────────────────────────────────────────────────────────────────

def _render_header():
    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Desire Quiz</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(44px,9vw,72px);
              color:var(--text); letter-spacing:3px; line-height:0.92; margin-bottom:6px;">
    WHAT WOULD<br><span style="color:var(--magenta);">YOU DO?</span>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:2px; text-transform:uppercase;">
    Reddit × AI × Hidden Desires · 18+
  </div>
</div>
""")


# ─── PHASE: START ─────────────────────────────────────────────────────────────

def render_start():
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    subs_html = "".join(
        f'<span style="display:inline-block; padding:3px 10px; margin:3px; border:1px solid var(--border); '
        f'border-radius:2px; font-family:\'Space Mono\',monospace; font-size:9px; color:var(--muted);">r/{s}</span>'
        for s in SUBREDDITS
    )

    # FIX: "Claude writes" → "AI writes" (code uses gpt-4o-mini, not Claude)
    st.html(f"""
<div class="enter-card">
  <p style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:24px; font-style:italic;">
    Real scenarios pulled from Reddit.<br>
    Then — what's actually going on beneath the surface.
  </p>

  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--magenta); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:6px;">Phase 1 · Reddit Quiz</div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8; margin:0;">
      10 real posts. AI writes a personal question for each. Your answers build your Openness Profile.
    </p>
    <div style="margin-top:10px; display:flex; flex-wrap:wrap; gap:4px;">{subs_html}</div>
  </div>

  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--amber); border-radius:4px;
              padding:16px 18px; margin-bottom:10px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--amber); margin-bottom:6px;">Phase 2 · Hidden Desires</div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8; margin:0;">
      15 indirect statements designed to surface what you don't usually name out loud.
    </p>
  </div>

  <div style="background:var(--card); border:1px solid var(--border);
              border-left:3px solid var(--cyan); border-radius:4px;
              padding:16px 18px; margin-bottom:24px;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--cyan); margin-bottom:6px;">Phase 3 · Your Fantasy Menu</div>
    <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8; margin:0;">
      25 categories generated specifically for you. Pick everything that fits.
      Your selections shape the final recommendations.
    </p>
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
        upd(5, "Fetching scenarios from Reddit…")
        posts = fetch_posts()
        upd(30, f"Found {len(posts)} relevant scenarios — generating questions with AI…")

        client   = _get_client()
        selected = posts[:POST_COUNT]

        upd(32, f"Generating {len(selected)} questions in parallel…")

        # Fire all generate_question calls simultaneously instead of sequentially.
        # Before: 10 calls × ~2s each = ~20s total. After: ~3-5s total.
        failed_questions = []
        results          = [None] * len(selected)

        def _gen_one(args):
            idx, post = args
            try:
                return idx, generate_question(post, client), None
            except Exception as e:
                return idx, None, str(e)

        with ThreadPoolExecutor(max_workers=len(selected)) as pool:
            futs = {pool.submit(_gen_one, (i, p)): i for i, p in enumerate(selected)}
            done = 0
            for fut in as_completed(futs, timeout=60):
                done += 1
                pct = 35 + int((done / len(selected)) * 58)
                upd(pct, f"Questions ready: {done}/{len(selected)}…")
                idx, q_data, err = fut.result()
                if q_data:
                    results[idx] = {**selected[idx], **q_data}
                else:
                    failed_questions.append(str(err))
                    results[idx] = {
                        **selected[idx],
                        "prompt": "Read the story above — what's your honest gut reaction?",
                        "opts":   FALLBACK_OPTS,
                    }

        questions = results

        if failed_questions:
            st.session_state.wwyd_load_errors = failed_questions

        upd(98, "Preparing Phase 1…")
        time.sleep(0.3)

        st.session_state.wwyd_questions = questions
        st.session_state.wwyd_answers   = [None] * len(questions)
        st.session_state.wwyd_cur       = 0
        st.session_state.wwyd_source    = "live" if any("reddit.com/r/" in p.get("url", "") for p in posts) else "curated"
        st.session_state.wwyd_phase     = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Failed to load quiz: {e}. Please try again."
        st.session_state.wwyd_phase = "start"
        st.rerun()


# ─── PHASE: QUIZ (Phase 1) ────────────────────────────────────────────────────

def render_quiz():
    questions = st.session_state.wwyd_questions
    cur       = st.session_state.wwyd_cur
    answers   = st.session_state.wwyd_answers

    if not questions or cur >= len(questions):
        st.session_state.wwyd_phase = "start"
        st.rerun()
        return

    q        = questions[cur]
    total    = len(questions)
    is_last  = (cur == total - 1)
    selected = answers[cur] if cur < len(answers) else None

    # Progress bar
    segs_html = "".join(
        f'<div style="flex:1; height:2px; border-radius:1px; background:'
        f'{"var(--magenta)" if i < cur else "rgba(255,45,120,0.5)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 1 of 3 &nbsp;·&nbsp; Reddit Scenarios &nbsp;·&nbsp; {cur + 1} / {total}
</div>
<div style="display:flex; gap:3px; margin-bottom:18px;">{segs_html}</div>

<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-radius:4px; overflow:hidden; margin-bottom:16px;">
  <div style="display:flex; align-items:center; gap:10px; padding:12px 16px;
              border-bottom:1px solid var(--border);">
    <div style="width:30px; height:30px; border-radius:50%; background:var(--magenta);
                color:#fff; display:flex; align-items:center; justify-content:center;
                font-family:'DM Sans',sans-serif; font-size:13px; font-weight:700; flex-shrink:0;">
      {q['avatar']}
    </div>
    <div style="flex:1; min-width:0;">
      <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">{q['sub']}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">u/{q['user']} · {q['time']}</div>
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                padding:3px 8px; border:1px solid var(--border); color:var(--muted);
                text-transform:uppercase; border-radius:2px; white-space:nowrap;">
      {q.get('flair', 'Post')}
    </div>
  </div>
  <div style="padding:16px;">
    <div style="font-family:'DM Sans',sans-serif; font-size:15px; font-weight:500;
                color:var(--text); line-height:1.5; margin-bottom:10px;">{q['title']}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
                line-height:1.8;">{q['text'][:600]}{"…" if len(q['text']) > 600 else ""}</div>
  </div>
  <div style="padding:10px 16px; border-top:1px solid var(--border);
              display:flex; align-items:center; gap:16px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">▲ {q['upvotes']}</span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">💬 {q['comments']}</span>
    <a href="{q['url']}" target="_blank"
       style="margin-left:auto; font-family:'Space Mono',monospace; font-size:9px;
              color:var(--cyan); text-decoration:none; text-transform:uppercase; letter-spacing:1px;">
      View ↗
    </a>
  </div>
</div>

<div style="font-family:'DM Sans',sans-serif; font-size:14px; font-style:italic;
            color:var(--amber); border-left:2px solid var(--amber); padding-left:12px;
            margin-bottom:16px; line-height:1.6;">{q['prompt']}</div>
""")

    for i, opt in enumerate(q["opts"]):
        is_sel = (selected == i)
        label  = opt["t"] if isinstance(opt, dict) else opt
        if st.button(
            ("◆  " if is_sel else "") + label,
            key=f"opt_{cur}_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            # FIX: safe copy-reassign instead of direct index mutation on session_state list
            answers_copy      = list(st.session_state.wwyd_answers)
            answers_copy[cur] = i
            st.session_state.wwyd_answers = answers_copy
            st.rerun()

    source_label = "Live post" if st.session_state.wwyd_source == "live" else "Curated scenario"
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
            text-align:center; letter-spacing:1px; text-transform:uppercase; margin-top:8px;">
  {source_label} · {q['sub']}
</div>
""")

    # FIX: load errors belong here (quiz phase), not in render_start where they never appear.
    # wwyd_load_errors is set during loading and never survives the hard_reset back to start.
    load_errors = st.session_state.get("wwyd_load_errors", [])
    if load_errors and cur == 0:
        with st.expander(f"⚠ {len(load_errors)} question(s) used a generic fallback"):
            for err in load_errors:
                st.code(err, language=None)

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="quiz_back", use_container_width=True):
                st.session_state.wwyd_cur -= 1
                st.rerun()
    with col_next:
        btn_label = "Next: Hidden Desires →" if is_last else "Next →"
        disabled  = (selected is None)
        if st.button(btn_label, key="quiz_next", disabled=disabled, use_container_width=True, type="primary"):
            if is_last:
                st.session_state.wwyd_hd_cur = 0
                st.session_state.wwyd_phase  = "hidden_desires"
            else:
                st.session_state.wwyd_cur += 1
            st.rerun()


# ─── PHASE: HIDDEN DESIRES (Phase 2) ─────────────────────────────────────────

def render_hidden_desires():
    total   = len(HIDDEN_DESIRE_QUESTIONS)
    answers = st.session_state.wwyd_hd_answers

    # FIX: clamp AND write back so session_state stays valid
    raw_cur = st.session_state.wwyd_hd_cur
    cur     = max(0, min(raw_cur, total - 1))
    if cur != raw_cur:
        st.session_state.wwyd_hd_cur = cur

    q       = HIDDEN_DESIRE_QUESTIONS[cur]
    sel_id  = answers.get(q["id"])
    sel_i   = next((i for i, (oid, _, _) in enumerate(HD_OPTS) if oid == sel_id), None)
    is_last = (cur == total - 1)

    segs_html = "".join(
        f'<div style="flex:1; height:2px; border-radius:1px; background:'
        f'{"var(--amber)" if i < cur else "rgba(255,179,0,0.5)" if i == cur else "var(--border)"}"></div>'
        for i in range(total)
    )

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 2 of 3 &nbsp;·&nbsp; Hidden Desires &nbsp;·&nbsp; {cur + 1} / {total}
</div>
<div style="display:flex; gap:3px; margin-bottom:18px;">{segs_html}</div>

<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--amber); border-radius:4px;
            padding:24px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:3px;
              text-transform:uppercase; color:var(--amber); margin-bottom:10px;">
    How much does this resonate?
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:16px; font-style:italic;
              color:var(--text); line-height:1.65;">{q['text']}</div>
</div>
""")

    for i, (oid, label, _) in enumerate(HD_OPTS):
        is_sel = (sel_i == i)
        if st.button(
            ("◆  " if is_sel else "") + label,
            key=f"hd_{cur}_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            # FIX: only auto-advance if this is a NEW selection, not a re-click
            was_already_selected = (sel_id == oid)
            # FIX: copy-reassign dict (same safety principle as wwyd_answers list)
            hd_copy            = dict(st.session_state.wwyd_hd_answers)
            hd_copy[q["id"]]   = oid
            st.session_state.wwyd_hd_answers = hd_copy
            if not is_last and not was_already_selected:
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
        answered = q["id"] in answers
        if is_last:
            # Last question: explicit "Next" to trigger phase transition
            if st.button(
                "Next: Build My Fantasy Menu →",
                key="hd_next_last",
                disabled=not answered,
                use_container_width=True,
                type="primary",
            ):
                st.session_state.wwyd_fantasy_error = ""
                st.session_state.wwyd_phase         = "generating_fantasies"
                st.rerun()
        else:
            # FIX: non-last questions also get an explicit "Next →" button.
            # This makes back-then-forward work without forcing a re-click of the answer.
            if st.button(
                "Next →",
                key="hd_next_mid",
                disabled=not answered,
                use_container_width=True,
                type="primary" if answered else "secondary",
            ):
                st.session_state.wwyd_hd_cur += 1
                st.rerun()


# ─── PHASE: GENERATING FANTASIES ─────────────────────────────────────────────

def render_generating_fantasies():
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:24px;">BUILDING YOUR FANTASY MENU</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, status):
        ph_bar.progress(pct)
        ph_status.caption(status)

    try:
        upd(15, "Computing your openness profile from Phase 1…")

        questions = st.session_state.wwyd_questions
        answers   = st.session_state.wwyd_answers
        hd_ans    = st.session_state.wwyd_hd_answers

        # Score Phase 1
        total_pts = 0
        for i, a in enumerate(answers):
            if a is None or i >= len(questions):
                continue
            opts = questions[i].get("opts", [])
            if a < len(opts):
                opt = opts[a]
                total_pts += opt.get("pts", 0) if isinstance(opt, dict) else 0

        # FIX: use max(..., default=0) so empty opts list never raises ValueError
        max_pts = sum(
            max(
                ((o.get("pts", 0) if isinstance(o, dict) else 0) for o in (q.get("opts") or [])),
                default=0,
            )
            for q in questions
        )
        pct         = round((total_pts / max_pts) * 100) if max_pts else 0
        result_type = next((r for r in RESULT_TYPES if r["min"] <= total_pts <= r["max"]), RESULT_TYPES[-1])

        upd(40, "Reading your hidden desire signals…")
        client = _get_client()

        upd(60, "Generating 25 personalised fantasy categories…")
        fantasies = generate_fantasies(result_type, pct, hd_ans, questions, answers, client)

        upd(100, "Ready for Phase 3")
        time.sleep(0.3)

        st.session_state.wwyd_result_type  = result_type
        st.session_state.wwyd_openness_pct = pct
        st.session_state.wwyd_total_pts    = total_pts
        st.session_state.wwyd_fantasies    = fantasies
        st.session_state.wwyd_phase        = "fantasy_selector"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_fantasy_error = str(e)
        st.session_state.wwyd_phase         = "fantasy_error"
        st.rerun()


# ─── PHASE: FANTASY ERROR ─────────────────────────────────────────────────────

def render_fantasy_error():
    err = st.session_state.get("wwyd_fantasy_error", "Unknown error")
    st.error(f"Couldn't build your fantasy menu: {err}")
    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px 18px; margin-top:12px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.7;">
    Your Phase 1 and Phase 2 answers are still saved — retry without losing any progress.
  </div>
</div>
""")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Retry", use_container_width=True, type="primary", key="fe_retry"):
            st.session_state.wwyd_fantasy_error = ""
            st.session_state.wwyd_phase         = "generating_fantasies"
            st.rerun()
    with col2:
        if st.button("← Back to Hidden Desires", use_container_width=True, key="fe_back"):
            st.session_state.wwyd_hd_cur = len(HIDDEN_DESIRE_QUESTIONS) - 1
            st.session_state.wwyd_phase  = "hidden_desires"
            st.rerun()


# ─── PHASE: FANTASY SELECTOR (Phase 3) ───────────────────────────────────────

def render_fantasy_selector():
    # FIX: render_generating_result redirects here on failure with wwyd_error set.
    # Without this check the user gets silently dropped back with no explanation.
    if st.session_state.get("wwyd_error"):
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    fantasies = st.session_state.wwyd_fantasies
    selected  = set(st.session_state.wwyd_selected)

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
  Phase 3 of 3 &nbsp;·&nbsp; Your Fantasy Menu
</div>
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--cyan); border-radius:4px;
            padding:20px 22px; margin-bottom:20px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--text);
              letter-spacing:2px; margin-bottom:8px;">25 CATEGORIES BUILT FOR YOU</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.7;">
    Generated from your quiz reactions and hidden desire signals.
    Ordered closest match → interesting stretch.<br>
    <strong style="color:var(--text);">Tap everything that resonates.</strong>
    Your picks shape the final recommendations.
  </div>
</div>
""")

    cols = st.columns(2)
    for idx, label in enumerate(fantasies):
        is_sel = label in selected
        with cols[idx % 2]:
            if st.button(
                ("✓ " if is_sel else "") + label,
                key=f"f_{idx}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                if is_sel:
                    selected.discard(label)
                else:
                    selected.add(label)
                st.session_state.wwyd_selected = list(selected)
                st.rerun()

    count       = len(selected)
    count_color = "var(--magenta)" if count > 0 else "var(--muted)"
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:11px; letter-spacing:2px;
            color:{count_color}; text-align:center; margin:16px 0 4px;">{count} selected</div>
""")

    if count == 0:
        st.html("""
<div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
            text-align:center; margin-bottom:12px;">Select at least one to continue</div>
""")

    st.html("<br>")
    if st.button(
        "Build My Full Profile →",
        use_container_width=True,
        type="primary",
        disabled=(count == 0),
        key="f_next",
    ):
        st.session_state.wwyd_phase = "generating_result"
        st.rerun()


# ─── PHASE: GENERATING RESULT ─────────────────────────────────────────────────

def render_generating_result():
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:24px;">BUILDING YOUR PROFILE</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, status):
        ph_bar.progress(pct)
        ph_status.caption(status)

    try:
        upd(20, "Pulling everything together…")

        questions   = st.session_state.wwyd_questions
        answers     = st.session_state.wwyd_answers
        hd_ans      = st.session_state.wwyd_hd_answers
        result_type = st.session_state.wwyd_result_type
        pct         = st.session_state.wwyd_openness_pct
        sel_f       = st.session_state.wwyd_selected

        upd(55, "Writing your personalised recommendations…")
        client = _get_client()
        recs   = generate_recommendations(result_type, pct, hd_ans, questions, answers, sel_f, client)

        upd(100, "Your full profile is ready")
        time.sleep(0.2)

        st.session_state.wwyd_recs  = recs
        st.session_state.wwyd_phase = "result"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Something went wrong generating recommendations: {e}"
        st.session_state.wwyd_phase = "fantasy_selector"
        st.rerun()


# ─── PHASE: RESULT ────────────────────────────────────────────────────────────

def render_result():
    result_type = st.session_state.get("wwyd_result_type") or RESULT_TYPES[0]
    pct         = st.session_state.get("wwyd_openness_pct", 0)
    sel_f       = st.session_state.get("wwyd_selected", [])
    recs        = st.session_state.get("wwyd_recs", [])
    hd_ans      = st.session_state.get("wwyd_hd_answers", {})

    # ── Openness profile ──────────────────────────────────────────────────────
    st.html(f"""
<div class="enter-card" style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--magenta); border-radius:4px;
            padding:32px 28px; text-align:center; margin-bottom:16px;">
  <div style="font-size:52px; margin-bottom:12px;">{result_type['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(30px,6vw,48px);
              letter-spacing:3px; color:var(--text); line-height:1.05; margin-bottom:4px;">
    {result_type['name'].upper()}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--magenta); text-transform:uppercase; margin-bottom:18px;">
    {result_type['meta']}
  </div>
  <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
             line-height:1.9; margin-bottom:24px;">{result_type['desc']}</p>
  <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
              padding:16px; text-align:left;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-bottom:8px;">Openness Index</div>
    <div style="height:4px; background:var(--border); border-radius:2px; margin-bottom:6px;">
      <div style="width:{pct}%; height:100%;
                  background:linear-gradient(90deg, var(--amber), var(--magenta));
                  border-radius:2px;"></div>
    </div>
    <div style="display:flex; justify-content:space-between;">
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">Closed off</span>
      <span style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--text);">{pct}<span style="font-size:14px; color:var(--muted);"> / 100</span></span>
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);">Wide open</span>
    </div>
  </div>
</div>
""")

    # ── Hidden desire signals ─────────────────────────────────────────────────
    strong_signals = [
        q for q in HIDDEN_DESIRE_QUESTIONS
        if hd_ans.get(q["id"]) in ("yes", "strongly")
    ]
    if strong_signals:
        signals_html = "".join(
            f'<div style="display:flex; align-items:flex-start; gap:10px; padding:8px 0; '
            f'border-bottom:1px solid var(--border);">'
            f'<span style="color:var(--amber); font-size:12px; flex-shrink:0; margin-top:2px;">'
            f'{"★" if hd_ans.get(q["id"]) == "strongly" else "◆"}</span>'
            f'<div style="font-family:\'DM Sans\',sans-serif; font-size:12.5px; color:var(--soft); '
            f'line-height:1.65; font-style:italic;">{q["text"]}</div>'
            f'</div>'
            for q in strong_signals
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:20px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--amber); margin-bottom:12px;">
    Hidden Desire Signals ({len(strong_signals)})
  </div>
  {signals_html}
</div>
""")

    # ── Selected fantasy categories ───────────────────────────────────────────
    if sel_f:
        tags_html = "".join(
            f'<span style="display:inline-block; padding:5px 12px; margin:3px; border-radius:2px; '
            f'font-family:\'Space Mono\',monospace; font-size:9px; letter-spacing:1px; '
            f'text-transform:uppercase; border:1px solid var(--border); '
            f'background:var(--surface); color:var(--soft);">{f}</span>'
            for f in sel_f
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:20px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--cyan); margin-bottom:12px;">
    Your Selected Fantasies ({len(sel_f)})
  </div>
  <div>{tags_html}</div>
</div>
""")

    # ── Recommendations ───────────────────────────────────────────────────────
    if recs:
        recs_html = "".join(
            f'<div style="background:var(--surface); border:1px solid var(--border); '
            f'border-left:2px solid var(--magenta); border-radius:0 4px 4px 0; '
            f'padding:14px 16px; margin-bottom:8px; font-family:\'DM Sans\',sans-serif; '
            f'font-size:13px; color:var(--soft); line-height:1.75;">{r}</div>'
            for r in recs
        )
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:20px; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--magenta); margin-bottom:12px;">
    Things Worth Exploring
  </div>
  {recs_html}
</div>
""")

    # ── Actions ───────────────────────────────────────────────────────────────
    share = (
        f"What Would You Do? — Vice Vault\n\n"
        f"Result: {result_type['name']}\n\"{result_type['meta']}\"\n"
        f"Openness Index: {pct}%\n\n"
        f"{result_type['desc']}\n\n"
    )
    if strong_signals:
        share += "Hidden signals: " + ", ".join(q["signal"] for q in strong_signals[:5]) + "\n\n"
    if sel_f:
        share += "My fantasies:\n" + "\n".join(f"· {f}" for f in sel_f[:10]) + "\n\n"
    if recs:
        share += "Recommendations:\n" + "\n".join(f"· {r}" for r in recs[:3])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Try Again", use_container_width=True, key="try_again"):
            hard_reset()
    with col2:
        st.download_button(
            "↓ Save Result",
            data=share,
            file_name="wwyd_result.txt",
            mime="text/plain",
            use_container_width=True,
            key="save_result",
        )


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()

    _render_header()

    phase = st.session_state.wwyd_phase
    if   phase == "start":                render_start()
    elif phase == "loading":              render_loading()
    elif phase == "quiz":                 render_quiz()
    elif phase == "hidden_desires":       render_hidden_desires()
    elif phase == "generating_fantasies": render_generating_fantasies()
    elif phase == "fantasy_error":        render_fantasy_error()
    elif phase == "fantasy_selector":     render_fantasy_selector()
    elif phase == "generating_result":    render_generating_result()
    elif phase == "result":               render_result()
    else:
        # FIX: removed unreachable duplicate _wipe/init_state/rerun after first rerun
        _wipe()
        init_state()
        st.rerun()
