"""
Pages/what_would_you_do.py
Live Reddit-powered sexual taboo quiz.
Falls back to curated posts if Reddit is blocked.
"""

import streamlit as st
import json
import random
import time
import anthropic

# ─── CONFIG ───────────────────────────────────────────────────────────────────

SUBREDDITS = [
    "sex", "nonmonogamy", "polyamory", "swingers",
    "confessions", "trueoffmychest", "relationship_advice",
    "openrelationships",
]

TABOO_KEYWORDS = [
    "threesome", "3some", "third", "open relationship", "swinger", "polyamory",
    "fantasy", "attracted to", "cheated", "affair", "tempted", "curious about",
    "another person", "someone else", "bring someone", "invite", "experiment",
    "exploring", "never told anyone", "taboo", "forbidden", "secret",
    "want to try", "thinking about", "nonmonogamy", "ethical non",
    "open marriage", "hotwife", "group", "voyeur", "exhibitionist",
    "fmf", "mmf", "confession", "told my partner", "my partner told me",
    "we tried", "we talked about",
]

MIN_SCORE  = 50
MIN_LENGTH = 200
POST_COUNT = 10

FALLBACK_POSTS = [
    {"sub":"r/relationship_advice","avatar":"T","user":"throwaway_82947","title":"My partner and I accidentally started a conversation we can't take back","text":"We've been together three years. Last Saturday we had some friends over and after everyone left, one of them made a joke about how 'it's a shame you two are taken.' Nobody laughed it off. There was this long pause where we all just looked at each other. My partner and I talked about it after they left and it turned into a two-hour conversation about things we'd never said out loud before. I don't know what we're doing but I don't feel scared about it.","upvotes":"14.2k","comments":"832","time":"6 hours ago","url":"https://reddit.com/r/relationship_advice","flair":"Long Post"},
    {"sub":"r/confessions","avatar":"A","user":"anon_user_2291","title":"I told my best friend exactly what happens in our bedroom because she asked — my partner walked in halfway through","text":"She's been single for a while and we were deep in a wine conversation when she said she was jealous — not of my relationship, specifically of the intimacy. She asked if I'd describe what it's actually like. I did. In detail. My partner walked in halfway through and just sat down and listened. Nobody was uncomfortable. Nobody said 'that's too much information.' When she left, my partner said, 'I didn't mind that.' We haven't talked about what that means yet.","upvotes":"9.7k","comments":"1.2k","time":"2 days ago","url":"https://reddit.com/r/confessions","flair":"True Story"},
    {"sub":"r/trueoffmychest","avatar":"S","user":"strangebutreal","title":"My partner and I spent four hours talking about a hypothetical last night and I've never felt closer to them","text":"It started with a dumb hypothetical — I said 'if you could add anyone to our relationship for one night, no consequences, who would you say?' I expected them to laugh it off. They didn't. They answered. Thoughtfully. With a name. So I answered too. Then we started talking about how it would actually work, what the rules would be, whether we'd feel jealous. We never agreed to do anything. I feel like I know them more than I did yesterday.","upvotes":"18.3k","comments":"976","time":"5 hours ago","url":"https://reddit.com/r/trueoffmychest","flair":"Personal"},
    {"sub":"r/nonmonogamy","avatar":"M","user":"maybe_mistakes","title":"AITA for telling my girlfriend that her being bothered by my fantasy means she doesn't trust me?","text":"I told her about a recurring fantasy — nothing I expected to act on, just something in my head. She got quiet for a while and then said it made her feel like she wasn't enough. I told her that's not what fantasies mean, and that being bothered by something I've never done makes me feel like she assumes the worst of me. She said I was being defensive. I said she was conflating imagination with intention. We're still in this argument three days later. The fantasy involved someone we both know.","upvotes":"22.1k","comments":"3.4k","time":"1 day ago","url":"https://reddit.com/r/nonmonogamy","flair":"Advice"},
    {"sub":"r/polyamory","avatar":"L","user":"late_night_post_88","title":"My close friend accidentally sent my partner a text I wrote about wanting to explore an open relationship","text":"My close friend had been asking for advice on her relationship. I sent her this long message about how I think openness between partners is underrated, and I gave a specific example — that I'd thought about what it would be like if we ever brought someone else into things, and that my partner's reaction if I ever brought it up was the thing stopping me. She screenshotted it and sent it to my partner by accident. He texted me three seconds later. I thought I was about to have the worst conversation of my life. He said: 'Why haven't you just told me this?'","upvotes":"31.5k","comments":"2.1k","time":"3 days ago","url":"https://reddit.com/r/polyamory","flair":"Story"},
    {"sub":"r/swingers","avatar":"W","user":"wontusemyname","title":"UPDATE: We did it. Here's the honest version of what happened.","text":"Original post was six months ago. Short version: my partner and I had been curious, we met someone we both trusted, and after a lot of conversations we stopped overthinking and made a decision. Here's what nobody tells you: the hardest part was the three days before, not the night itself. The night was calm. Everyone knew the agreement. Nobody felt left out. The morning after, we made breakfast together and laughed a lot. It wasn't perfect — there were small moments of awkwardness that we talked through over the next week. But if someone asked me today whether I'd do it again, the answer would be yes.","upvotes":"19.4k","comments":"1.1k","time":"2 days ago","url":"https://reddit.com/r/swingers","flair":"Update"},
    {"sub":"r/sex","avatar":"N","user":"nightowl_anon","title":"The reason most couples never talk about threesomes isn't morality — it's fear of the answer","text":"Think about it. The hesitation isn't really about whether it's a good idea. It's about the moment after you ask, when you see their face — and you find out who they actually are. If they're excited, now you know something. If they're horrified, now you know something else. Either answer changes things. So instead of asking, most people just carry the question around for years and call that loyalty. I'm not saying it should always be asked. I'm saying the reason it isn't has nothing to do with morality.","upvotes":"8.9k","comments":"2.3k","time":"12 hours ago","url":"https://reddit.com/r/sex","flair":"Discussion"},
    {"sub":"r/openrelationships","avatar":"C","user":"confessed_at_midnight","title":"I've been in a situation most people would call complicated. I consider it the best year of my life.","text":"About two years ago, my partner and I became very close with another person — someone we both trusted, liked, and were both, separately, attracted to. We never planned what happened. It evolved slowly over months. There were awkward conversations, check-ins, one moment where someone cried and we almost stopped everything. But we didn't stop. We spent a year navigating something that nobody gave us a map for and on the other side of it, my relationship with my partner is the strongest it's ever been.","upvotes":"27.8k","comments":"4.5k","time":"4 days ago","url":"https://reddit.com/r/openrelationships","flair":"Experience"},
    {"sub":"r/relationship_advice","avatar":"F","user":"finally_saying_it","title":"My partner told me they've always been curious about this and I said nothing. That was six months ago.","text":"They brought it up casually, like it was just a thought, not a request. I panicked internally and changed the subject and they never brought it up again. But I think about it almost every week. Not because I'm angry or hurt — because I keep asking myself what I actually think about it, and I don't have a clean answer. Part of me is curious. Part of me is scared. Part of me wonders what would have happened if I'd just said 'tell me more' instead of going quiet. I don't know if I'm ready to reopen the conversation.","upvotes":"12.6k","comments":"889","time":"8 hours ago","url":"https://reddit.com/r/relationship_advice","flair":"Serious"},
    {"sub":"r/confessions","avatar":"B","user":"burner_acct_now","title":"People who've actually had a threesome — what happened to your relationship after?","text":"Top comment: 'We talked about it for months before anything happened. The conversation itself changed our relationship — more honesty, more trust. We stopped performing for each other.' Second: 'We tried it. It was amazing and also complicated and also something I'd do again.' Third: 'The fact that we could have the conversation without falling apart told me more about our relationship than anything else ever had.' Fourth: 'We found out we wanted very different things. That was hard but also necessary to know.' Fifth: 'Still together four years later. No regrets.'","upvotes":"41.2k","comments":"7.8k","time":"1 week ago","url":"https://reddit.com/r/confessions","flair":"Discussion"},
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

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def time_ago(ts: float) -> str:
    diff = int(time.time() - ts)
    if diff < 3600:  return f"{diff // 60}m ago"
    if diff < 86400: return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"

def is_taboo(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw in text for kw in TABOO_KEYWORDS)

def fmt_num(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

# ─── REDDIT FETCH ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def fetch_posts() -> list:
    import requests
    PROXIES = [
        "https://api.allorigins.win/raw?url=",
        "https://corsproxy.io/?",
        "",
    ]
    all_posts = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; QuizApp/1.0)",
        "Accept": "application/json",
    })
    for sub in SUBREDDITS[:5]:
        for sort in ["hot", "top"]:
            reddit_url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit=40"
            if sort == "top":
                reddit_url += "&t=month"
            fetched = False
            for proxy in PROXIES:
                try:
                    url = proxy + reddit_url if proxy else reddit_url
                    r = session.get(url, timeout=8)
                    if not r.ok:
                        continue
                    data = r.json()
                    if "contents" in data:
                        data = json.loads(data["contents"])
                    children = data.get("data", {}).get("children", [])
                    if not children:
                        continue
                    for item in children:
                        pd = item.get("data", {})
                        body  = pd.get("selftext", "")
                        title = pd.get("title", "")
                        if not body or len(body) < MIN_LENGTH:         continue
                        if pd.get("score", 0) < MIN_SCORE:             continue
                        if pd.get("stickied") or pd.get("pinned"):     continue
                        if body in ("[deleted]", "[removed]"):          continue
                        if not is_taboo(title, body):                  continue
                        all_posts.append({
                            "sub":      f"r/{sub}",
                            "avatar":   (pd.get("author") or "A")[0].upper(),
                            "user":     pd.get("author", "anonymous"),
                            "title":    title,
                            "text":     body[:900].strip(),
                            "upvotes":  fmt_num(pd.get("score", 0)),
                            "comments": fmt_num(pd.get("num_comments", 0)),
                            "time":     time_ago(pd.get("created_utc", time.time())),
                            "url":      "https://reddit.com" + pd.get("permalink", ""),
                            "flair":    pd.get("link_flair_text") or sub.replace("_", " ").title(),
                        })
                    fetched = True
                    break
                except Exception:
                    continue
            if fetched:
                time.sleep(0.3)
    if all_posts:
        random.shuffle(all_posts)
        seen, unique = set(), []
        for p in all_posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique.append(p)
        return unique[:POST_COUNT * 2]
    posts = FALLBACK_POSTS.copy()
    random.shuffle(posts)
    return posts[:POST_COUNT]


# ─── CLAUDE QUESTION GENERATOR ────────────────────────────────────────────────

def generate_question(post: dict, client: anthropic.Anthropic) -> dict:
    prompt = f"""You write questions for a daring relationship/sexuality quiz called "What Would You Do?" exploring sexual taboos, open relationships, threesomes, and intimate boundaries.

Reddit post:
SUBREDDIT: {post['sub']}
TITLE: {post['title']}
TEXT: {post['text']}

Write a short provocative quiz question (1-2 sentences) asking the reader their honest gut reaction.

Write 4 answer options from most conservative (pts:0) to most open/adventurous (pts:5):
- Option 1 (pts:0): closed off, protective, uncomfortable
- Option 2 (pts:2): cautious, curious but hesitant
- Option 3 (pts:3): open-minded, genuinely intrigued
- Option 4 (pts:5): experienced or fully ready, deeply relatable

Each option: 1-2 sentences, specific and authentic. No generic filler.

Respond ONLY with JSON (no markdown, no explanation):
{{"prompt":"...","opts":[{{"t":"...","pts":0}},{{"t":"...","pts":2}},{{"t":"...","pts":3}},{{"t":"...","pts":5}}]}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ─── SESSION STATE ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "wwyd_phase":     "start",
        "wwyd_questions": [],
        "wwyd_answers":   [],
        "wwyd_cur":       0,
        "wwyd_error":     "",
        "wwyd_source":    "live",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def hard_reset():
    for k in list(st.session_state.keys()):
        if k.startswith("wwyd_"):
            del st.session_state[k]
    fetch_posts.clear()
    init_state()
    st.rerun()

# ─── CSS ──────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Mono:wght@400;500&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
<style>

/* ── Reset & Base ── */
section.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 720px !important;
}

:root {
    --ink: #0d0d0f;
    --paper: #f5f2eb;
    --cream: #ede9df;
    --warm-white: #faf8f3;
    --rouge: #c0392b;
    --rouge-dim: rgba(192,57,43,0.12);
    --rouge-border: rgba(192,57,43,0.3);
    --gold: #b8922a;
    --gold-dim: rgba(184,146,42,0.15);
    --charcoal: #2a2826;
    --ash: #6b6560;
    --mist: #9e9891;
    --rule: #d4cfc5;
    --selected-bg: #1a1714;
    --selected-text: #f5f2eb;
}

/* ── Page background ── */
.stApp {
    background: var(--paper) !important;
}
section[data-testid="stMain"] {
    background: var(--paper) !important;
}

/* ── Sidebar overrides ── */
section[data-testid="stSidebar"] {
    background: #121110 !important;
    border-right: 1px solid #2a2826 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid #2a2826 !important;
    color: #c8c2b8 !important;
    border-radius: 4px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    transition: all 0.2s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #1e1c1a !important;
    border-color: var(--rouge) !important;
    color: var(--paper) !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ── Global button reset ── */
.stButton > button {
    background: var(--charcoal) !important;
    color: var(--paper) !important;
    border: 1px solid var(--charcoal) !important;
    border-radius: 3px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    background: var(--ink) !important;
    border-color: var(--ink) !important;
    transform: none !important;
    box-shadow: 2px 2px 0 var(--rouge) !important;
}

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--ash) !important;
    border: 1px solid var(--rule) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--cream) !important;
    color: var(--charcoal) !important;
    border-color: var(--charcoal) !important;
    box-shadow: none !important;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background: var(--charcoal) !important;
    color: var(--paper) !important;
    border: 1px solid var(--charcoal) !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--ink) !important;
    box-shadow: 3px 3px 0 var(--rouge) !important;
}
.stButton > button[kind="primary"]:disabled {
    background: var(--rule) !important;
    color: var(--mist) !important;
    border-color: var(--rule) !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
}

/* ── Header ── */
.wwyd-masthead {
    text-align: center;
    padding: 40px 0 32px;
    border-bottom: 2px solid var(--charcoal);
    margin-bottom: 32px;
    position: relative;
}
.wwyd-kicker {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: var(--rouge);
    margin-bottom: 14px;
    display: block;
}
.wwyd-headline {
    font-family: 'Playfair Display', serif;
    font-size: clamp(42px, 9vw, 72px);
    font-weight: 900;
    line-height: 0.92;
    color: var(--ink);
    margin: 0;
    letter-spacing: -1px;
}
.wwyd-headline em {
    font-style: italic;
    color: var(--rouge);
}
.wwyd-deck {
    font-family: 'Lato', sans-serif;
    font-size: 12px;
    color: var(--ash);
    margin-top: 14px;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.live-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--rouge-dim);
    border: 1px solid var(--rouge-border);
    border-radius: 2px;
    padding: 5px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--rouge);
    margin-top: 16px;
}
.live-pip {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--rouge);
    animation: blink 1.4s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

/* ── Cards ── */
.card {
    background: var(--warm-white);
    border: 1px solid var(--rule);
    border-top: 3px solid var(--charcoal);
    padding: 28px 24px;
    margin-bottom: 16px;
}

/* ── Reddit post card ── */
.post-wrap {
    background: white;
    border: 1px solid var(--rule);
    margin-bottom: 20px;
    overflow: hidden;
}
.post-top {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px 16px 0;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 12px;
}
.post-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: var(--charcoal);
    color: var(--paper);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
}
.post-meta-sub {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--rouge);
    font-weight: 500;
}
.post-meta-info {
    font-family: 'Lato', sans-serif;
    font-size: 10px;
    color: var(--mist);
    margin-top: 1px;
}
.post-flair-tag {
    margin-left: auto;
    font-family: 'DM Mono', monospace;
    font-size: 8px;
    letter-spacing: 1px;
    padding: 3px 10px;
    border: 1px solid var(--rule);
    color: var(--ash);
    text-transform: uppercase;
    white-space: nowrap;
    border-radius: 2px;
}
.post-body-inner {
    padding: 16px;
}
.post-headline {
    font-family: 'Playfair Display', serif;
    font-size: 15px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.45;
    margin-bottom: 10px;
}
.post-excerpt {
    font-family: 'Lato', sans-serif;
    font-size: 12.5px;
    color: var(--ash);
    line-height: 1.9;
}
.post-footer-bar {
    border-top: 1px solid var(--rule);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--cream);
}
.post-stat {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--mist);
}
.post-reddit-link {
    margin-left: auto;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 1px;
    color: var(--rouge);
    text-decoration: none;
    text-transform: uppercase;
}

/* ── Progress bar ── */
.progress-row {
    display: flex;
    gap: 3px;
    margin-bottom: 22px;
}
.prog-seg {
    height: 2px;
    flex: 1;
    background: var(--rule);
}
.prog-seg.done { background: var(--charcoal); }
.prog-seg.now  { background: var(--rouge); }

/* ── Question prompt ── */
.q-prompt-text {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 14px;
    color: var(--gold);
    border-left: 2px solid var(--gold);
    padding-left: 12px;
    margin-bottom: 18px;
    line-height: 1.65;
}

/* ── Source note ── */
.source-footnote {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: var(--mist);
    text-align: center;
    letter-spacing: 1px;
    margin-top: 8px;
    text-transform: uppercase;
}
.source-footnote a { color: var(--rouge); text-decoration: none; }

/* ── Start page pills ── */
.sub-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}
.sub-pill {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    padding: 4px 10px;
    border: 1px solid var(--rule);
    border-radius: 2px;
    color: var(--ash);
    background: white;
}
.info-section {
    background: white;
    border: 1px solid var(--rule);
    padding: 16px;
    margin-bottom: 10px;
}
.info-label {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--rouge);
    margin-bottom: 8px;
}
.info-body {
    font-family: 'Lato', sans-serif;
    font-size: 12.5px;
    color: var(--ash);
    line-height: 1.8;
    margin: 0;
}
.start-lede {
    font-family: 'Playfair Display', serif;
    font-size: 17px;
    color: var(--charcoal);
    line-height: 1.7;
    text-align: center;
    margin-bottom: 24px;
    font-style: italic;
}

/* ── Result ── */
.result-icon { font-size: 52px; text-align: center; display: block; margin-bottom: 12px; }
.result-name {
    font-family: 'Playfair Display', serif;
    font-size: clamp(28px, 6vw, 44px);
    font-weight: 900;
    color: var(--ink);
    text-align: center;
    margin-bottom: 4px;
    line-height: 1.1;
}
.result-meta {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--gold);
    text-transform: uppercase;
    text-align: center;
    margin-bottom: 18px;
}
.result-desc {
    font-family: 'Lato', sans-serif;
    font-size: 13.5px;
    color: var(--ash);
    line-height: 1.9;
    text-align: center;
    margin-bottom: 24px;
}
.meter-box {
    background: white;
    border: 1px solid var(--rule);
    padding: 20px;
    margin-bottom: 20px;
}
.meter-label-text {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--mist);
    margin-bottom: 12px;
}
.meter-track {
    height: 6px;
    background: var(--rule);
    margin-bottom: 8px;
}
.meter-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--gold), var(--rouge));
}
.meter-ends {
    display: flex;
    justify-content: space-between;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: var(--mist);
    text-transform: uppercase;
    letter-spacing: 1px;
}
.meter-big-score {
    font-family: 'Playfair Display', serif;
    font-size: 48px;
    font-weight: 900;
    color: var(--ink);
    line-height: 1;
    margin-top: 10px;
}
.meter-big-score small {
    font-family: 'Lato', sans-serif;
    font-size: 14px;
    color: var(--mist);
    font-weight: 300;
}
.divider-rule {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 24px 0;
}
.curated-note {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: var(--gold);
    text-align: center;
    letter-spacing: 1px;
    padding: 8px;
    text-transform: uppercase;
    opacity: 0.8;
}

/* ── Loading ── */
.stProgress > div > div > div {
    background: var(--rouge) !important;
}
</style>
""", unsafe_allow_html=True)

# ─── RENDER PHASES ────────────────────────────────────────────────────────────

def render_header():
    st.markdown("""
<div class="wwyd-masthead">
  <span class="wwyd-kicker">Real posts · Real people · Real reactions</span>
  <h1 class="wwyd-headline">What Would<br><em>You Do?</em></h1>
  <p class="wwyd-deck">Powered by Reddit · Scored by AI</p>
  <div class="live-chip"><span class="live-pip"></span>&nbsp;Live Edition</div>
</div>
""", unsafe_allow_html=True)


def render_start():
    if st.session_state.wwyd_error:
        st.info(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    subs_html = "".join(f'<span class="sub-pill">r/{s}</span>' for s in SUBREDDITS)

    st.markdown(f"""
<p class="start-lede">
  Real scenarios pulled from Reddit.<br>
  A fresh question generated just for you.<br>
  Different every time. Honest answers only.
</p>
<div class="info-section">
  <div class="info-label">Pulling from</div>
  <div class="sub-pills">{subs_html}</div>
</div>
<div class="info-section">
  <div class="info-label">How it works</div>
  <p class="info-body">
    Taboo posts about open relationships, confessions, and intimate curiosity are fetched and filtered.
    AI writes a personal question for each one. Your answers build your Openness Profile.
  </p>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Begin the Quiz →", use_container_width=True, type="primary"):
        st.session_state.wwyd_phase = "loading"
        st.rerun()


def render_loading():
    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(title, pct, status):
        ph_title.markdown(f"**{title}**")
        ph_bar.progress(pct)
        ph_status.caption(status)

    try:
        upd("Fetching scenarios…", 5, "Connecting to Reddit")
        posts = fetch_posts()

        upd("Filtering posts…", 20, f"Found {len(posts)} relevant scenarios")
        time.sleep(0.2)

        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        except Exception:
            client = anthropic.Anthropic()

        selected  = posts[:POST_COUNT]
        questions = []

        for i, post in enumerate(selected):
            pct = 25 + int((i / len(selected)) * 70)
            upd("Generating questions…", pct, f"Question {i+1} of {len(selected)}")
            try:
                q_data = generate_question(post, client)
                questions.append({**post, **q_data})
            except Exception:
                questions.append({
                    **post,
                    "prompt": "Your honest gut reaction to this scenario is:",
                    "opts": FALLBACK_OPTS,
                })

        upd("Almost ready…", 98, "Preparing your quiz")
        time.sleep(0.3)

        st.session_state.wwyd_questions = questions
        st.session_state.wwyd_answers   = [None] * len(questions)
        st.session_state.wwyd_cur       = 0
        st.session_state.wwyd_phase     = "quiz"
        is_curated = all(
            p.get("comments","").endswith("k") and not p.get("time","").startswith("0")
            for p in posts[:3]
        )
        st.session_state.wwyd_source = "curated" if is_curated else "live"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Something went wrong: {e}"
        st.session_state.wwyd_phase = "start"
        st.rerun()


def render_quiz():
    questions = st.session_state.wwyd_questions
    cur       = st.session_state.wwyd_cur
    answers   = st.session_state.wwyd_answers
    q         = questions[cur]
    total     = len(questions)
    is_last   = cur == total - 1
    selected  = answers[cur]

    # Progress bar
    segs = "".join(
        f'<div class="prog-seg {"done" if i < cur else "now" if i == cur else ""}"></div>'
        for i in range(total)
    )
    source_label = "Live post" if st.session_state.wwyd_source == "live" else "Curated scenario"

    st.markdown(f"""
<div class="progress-row">{segs}</div>
<div class="post-wrap">
  <div class="post-top">
    <div class="post-avatar">{q['avatar']}</div>
    <div style="flex:1; min-width:0;">
      <div class="post-meta-sub">{q['sub']}</div>
      <div class="post-meta-info">u/{q['user']} · {q['time']}</div>
    </div>
    <span class="post-flair-tag">{q.get('flair','Post')}</span>
  </div>
  <div class="post-body-inner">
    <div class="post-headline">{q['title']}</div>
    <div class="post-excerpt">{q['text'][:680]}{"…" if len(q['text']) > 680 else ""}</div>
  </div>
  <div class="post-footer-bar">
    <span class="post-stat">▲ {q['upvotes']}</span>
    <span class="post-stat">💬 {q['comments']}</span>
    <a class="post-reddit-link" href="{q['url']}" target="_blank">View on Reddit ↗</a>
  </div>
</div>
<div class="q-prompt-text">{q['prompt']}</div>
""", unsafe_allow_html=True)

    # Answer options
    for i, opt in enumerate(q["opts"]):
        is_sel = selected == i
        prefix = "◆  " if is_sel else ""
        btn_type = "primary" if is_sel else "secondary"
        if st.button(
            prefix + opt["t"],
            key=f"opt_{cur}_{i}",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state.wwyd_answers[cur] = i
            st.rerun()

    st.markdown(
        f'<div class="source-footnote">{source_label} · '
        f'<a href="{q["url"]}" target="_blank">{q["sub"]}</a> · '
        f'Scenario {cur+1} of {total}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if cur > 0:
            if st.button("← Back", key="back_btn", use_container_width=True, type="secondary"):
                st.session_state.wwyd_cur -= 1
                st.rerun()
    with col_next:
        label = "See My Profile →" if is_last else "Next →"
        if st.button(label, key="next_btn", disabled=(selected is None), use_container_width=True, type="primary"):
            if is_last:
                st.session_state.wwyd_phase = "result"
            else:
                st.session_state.wwyd_cur += 1
            st.rerun()


def render_result():
    questions = st.session_state.wwyd_questions
    answers   = st.session_state.wwyd_answers

    total_pts = sum(
        questions[i]["opts"][a]["pts"]
        for i, a in enumerate(answers) if a is not None
    )
    max_pts = sum(max(o["pts"] for o in q["opts"]) for q in questions)
    pct     = round((total_pts / max_pts) * 100) if max_pts else 0
    result  = next(
        (r for r in RESULT_TYPES if r["min"] <= total_pts <= r["max"]),
        RESULT_TYPES[-1],
    )

    st.markdown(f"""
<div class="card">
  <span class="result-icon">{result['icon']}</span>
  <div class="result-name">{result['name']}</div>
  <div class="result-meta">{result['meta']}</div>
  <p class="result-desc">{result['desc']}</p>
  <hr class="divider-rule">
  <div class="meter-box">
    <div class="meter-label-text">Openness Index</div>
    <div class="meter-track"><div class="meter-fill" style="width:{pct}%"></div></div>
    <div class="meter-ends"><span>Closed off</span><span>Wide open</span></div>
    <div class="meter-big-score">{pct}<small> / 100</small></div>
  </div>
</div>
""", unsafe_allow_html=True)

    share = (
        f'Just took "What Would You Do?" — Reddit Edition\n\n'
        f'My result: {result["name"]}\n"{result["meta"]}"\n'
        f'Openness Index: {pct}%\n\n'
        f'Every quiz uses different scenarios 👀'
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Try Again", use_container_width=True, type="secondary"):
            hard_reset()
    with col2:
        st.download_button(
            "Save Result ↓",
            data=share,
            file_name="my_result.txt",
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
        phase = st.session_state.wwyd_phase
        if   phase == "start":   render_start()
        elif phase == "loading": render_loading()
        elif phase == "quiz":    render_quiz()
        elif phase == "result":  render_result()
