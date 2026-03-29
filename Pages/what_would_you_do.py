"""
Pages/what_would_you_do.py
Live Reddit-powered taboo quiz — parallel fetch, rebrand, consolidated file.
"""

import streamlit as st
import json
import random
import time
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONFIG ───────────────────────────────────────────────────────────────────

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
    {"min":  0, "max": 10,  "icon": "🔒", "name": "Closed Garden",
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
     "desc": "There's no internal conflict left in you on this. You read these scenarios and recognised yourself — not as an observer but as someone who's either been in a version of these situations or is clearly ready. You know what you want. You manage the emotional complexity well. You're not waiting for permission."},
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

# ─── PARALLEL REDDIT FETCH ────────────────────────────────────────────────────

def _fetch_one(args) -> list:
    """Fetch one subreddit — tries direct then allorigins proxy."""
    import requests
    sub, sort = args
    reddit_url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit=25"
    if sort == "top":
        reddit_url += "&t=month"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ViceVault/1.0)",
        "Accept": "application/json",
    }
    attempts = [
        reddit_url,
        "https://api.allorigins.win/raw?url=" + reddit_url,
        "https://corsproxy.io/?" + reddit_url,
    ]

    for url in attempts:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if not r.ok:
                continue
            data = r.json()
            if "contents" in data:
                data = json.loads(data["contents"])
            children = data.get("data", {}).get("children", [])
            if not children:
                continue

            posts = []
            for item in children:
                pd = item.get("data", {})
                body  = pd.get("selftext", "")
                title = pd.get("title", "")
                if not body or len(body) < MIN_LENGTH:     continue
                if pd.get("score", 0) < MIN_SCORE:         continue
                if pd.get("stickied") or pd.get("pinned"): continue
                if body in ("[deleted]", "[removed]"):      continue
                if not is_taboo(title, body):              continue
                posts.append({
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
                    "_live":    True,
                })
            return posts
        except Exception:
            continue
    return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_posts() -> tuple:
    """
    Fire all subreddit requests in parallel.
    Returns (posts_list, is_live: bool).
    Falls back to curated posts if nothing comes through.
    """
    tasks = [(sub, "hot") for sub in SUBREDDITS]
    all_posts = []

    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tasks}
        for future in as_completed(futures):
            try:
                all_posts.extend(future.result())
            except Exception:
                pass

    if all_posts:
        random.shuffle(all_posts)
        seen, unique = set(), []
        for p in all_posts:
            if p["title"] not in seen:
                seen.add(p["title"])
                unique.append(p)
        return unique[:POST_COUNT * 2], True

    posts = FALLBACK_POSTS.copy()
    random.shuffle(posts)
    return posts[:POST_COUNT], False


# ─── CLAUDE QUESTION GENERATOR ────────────────────────────────────────────────

def generate_question(post: dict, client) -> dict:
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

Respond ONLY with JSON (no markdown):
{{"prompt":"...","opts":[{{"t":"...","pts":0}},{{"t":"...","pts":2}},{{"t":"...","pts":3}},{{"t":"...","pts":5}}]}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ─── SESSION STATE ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "wwyd_phase":     "start",
        "wwyd_questions": [],
        "wwyd_answers":   [],
        "wwyd_cur":       0,
        "wwyd_error":     "",
        "wwyd_live":      False,
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
    st.html("""
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d;
  --border:#2a2a35; --lime:#c6ff00; --magenta:#ff2d78;
  --cyan:#00e5ff; --amber:#ffb300; --text:#f0f0f5;
  --muted:#5a5a72; --soft:#9090aa;
}
.stApp { background:var(--bg) !important; }
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container {
  padding-top:0.5rem !important; padding-bottom:2rem !important;
  max-width:720px !important;
}
section[data-testid="stSidebar"] {
  background:#0d0d10 !important; border-right:1px solid var(--border) !important;
}
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
  font-family:'Space Mono',monospace !important;
  font-size:10px !important; letter-spacing:1.5px !important;
  text-transform:uppercase !important; padding:10px 16px !important;
  transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover {
  background:#222230 !important; border-color:var(--lime) !important;
  color:var(--lime) !important; box-shadow:none !important; transform:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--lime) !important; color:#0a0a0b !important;
  border-color:var(--lime) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#d4ff1a !important; box-shadow:0 0 20px rgba(198,255,0,0.2) !important;
}
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"][disabled] {
  background:var(--border) !important; color:var(--muted) !important;
  border-color:var(--border) !important; box-shadow:none !important;
}
.stProgress > div > div > div { background:var(--lime) !important; }
.stDownloadButton > button {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important; font-family:'Space Mono',monospace !important;
  font-size:10px !important; letter-spacing:1px !important; text-transform:uppercase !important;
}
#MainMenu { visibility:hidden; }
footer    { visibility:hidden; }
</style>
""")

# ─── RENDER PHASES ────────────────────────────────────────────────────────────

def render_header(is_live: bool):
    badge_color = "#c6ff00" if is_live else "#ffb300"
    badge_label = "LIVE · Reddit" if is_live else "CURATED · Fallback"
    st.html(f"""
<div style="text-align:center; padding:32px 0 24px; border-bottom:1px solid var(--border); margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
    Real posts · Real people · Real reactions
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(52px,12vw,80px);
              color:var(--text); letter-spacing:3px; line-height:0.9; margin-bottom:8px;">
    WHAT WOULD<br><span style="color:var(--magenta);">YOU DO?</span>
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:2px; text-transform:uppercase;">Scored by AI</div>
  <div style="display:inline-flex; align-items:center; gap:6px; margin-top:14px;
              background:rgba(198,255,0,0.07); border:1px solid rgba(198,255,0,0.2);
              border-radius:2px; padding:5px 14px;">
    <span style="width:5px; height:5px; border-radius:50%; background:{badge_color};
                 display:inline-block; animation:blink 1.4s ease-in-out infinite;"></span>
    <span style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                 text-transform:uppercase; color:{badge_color};">{badge_label}</span>
  </div>
</div>
<style>@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}</style>
""")


def render_start():
    if st.session_state.wwyd_error:
        st.warning(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    subs_html = "".join(
        f'<span style="font-family:\'Space Mono\',monospace; font-size:9px; padding:4px 10px; '
        f'border:1px solid var(--border); border-radius:2px; color:var(--soft); '
        f'background:var(--card);">r/{s}</span>'
        for s in SUBREDDITS
    )
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:28px; margin-bottom:16px;">
  <p style="font-family:'DM Sans',sans-serif; font-size:15px; color:var(--soft);
             line-height:1.8; text-align:center; margin-bottom:24px; font-style:italic;">
    Real scenarios pulled from Reddit.<br>
    Every post gets a fresh AI-generated question.<br>
    Different every time. Honest answers only.
  </p>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Pulling from</div>
  <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:20px;">{subs_html}</div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); margin-bottom:8px;">How it works</div>
  <p style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
             line-height:1.75; margin:0;">
    Posts about open relationships, confessions, and intimate curiosity are fetched in parallel
    and filtered for relevance. Claude writes a personal question for each one.
    Your answers build your Openness Profile.
  </p>
</div>
""")

    if st.button("Begin →", use_container_width=True, type="primary"):
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
        upd("Fetching live scenarios…", 5, "Firing parallel requests to Reddit")
        posts, is_live = fetch_posts()
        upd("Posts loaded.", 30, f"{'Live data — ' if is_live else 'Curated fallback — '}{len(posts)} scenarios found")

        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        except Exception:
            client = anthropic.Anthropic()

        selected  = posts[:POST_COUNT]
        questions = []

        for i, post in enumerate(selected):
            pct = 35 + int((i / len(selected)) * 60)
            upd("Generating questions with Claude…", pct, f"Question {i+1} of {len(selected)}")
            try:
                q_data = generate_question(post, client)
                questions.append({**post, **q_data})
            except Exception:
                questions.append({**post, "prompt": "Your honest gut reaction to this scenario:", "opts": FALLBACK_OPTS})

        upd("Almost ready…", 98, "Preparing your quiz")
        time.sleep(0.2)

        st.session_state.wwyd_questions = questions
        st.session_state.wwyd_answers   = [None] * len(questions)
        st.session_state.wwyd_cur       = 0
        st.session_state.wwyd_live      = is_live
        st.session_state.wwyd_phase     = "quiz"
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
    is_live   = st.session_state.wwyd_live

    # Progress bar
    segs = "".join(
        f'<div style="flex:1; height:2px; background:{"var(--lime)" if i < cur else "var(--magenta)" if i == cur else "var(--border)"}; border-radius:1px;"></div>'
        for i in range(total)
    )
    source = "Live post" if is_live else "Curated scenario"

    st.html(f"""
<div style="display:flex; gap:3px; margin-bottom:20px;">{segs}</div>

<div style="background:var(--card); border:1px solid var(--border); margin-bottom:16px; overflow:hidden; border-radius:4px;">
  <div style="display:flex; align-items:center; gap:10px; padding:14px 16px 12px; border-bottom:1px solid var(--border);">
    <div style="width:30px; height:30px; border-radius:50%; background:var(--magenta);
                display:flex; align-items:center; justify-content:center;
                font-family:'Bebas Neue',sans-serif; font-size:14px; color:#fff; flex-shrink:0;">
      {q['avatar']}
    </div>
    <div style="flex:1; min-width:0;">
      <div style="font-family:'Space Mono',monospace; font-size:10px; color:var(--magenta);">{q['sub']}</div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted); margin-top:1px;">
        u/{q['user']} · {q['time']}
      </div>
    </div>
    <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                 padding:3px 8px; border:1px solid var(--border); color:var(--soft);
                 text-transform:uppercase; border-radius:2px; white-space:nowrap;">
      {q.get('flair','Post')}
    </span>
  </div>
  <div style="padding:16px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:17px; letter-spacing:1px;
                color:var(--text); margin-bottom:10px; line-height:1.3;">{q['title']}</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft); line-height:1.85;">
      {q['text'][:680]}{'…' if len(q['text']) > 680 else ''}
    </div>
  </div>
  <div style="border-top:1px solid var(--border); padding:10px 16px;
              display:flex; gap:14px; align-items:center; background:var(--surface);">
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--muted);">▲ {q['upvotes']}</span>
    <span style="font-family:'Space Mono',monospace; font-size:10px; color:var(--muted);">💬 {q['comments']}</span>
    <a href="{q['url']}" target="_blank"
       style="margin-left:auto; font-family:'Space Mono',monospace; font-size:9px;
              letter-spacing:1px; color:var(--cyan); text-decoration:none; text-transform:uppercase;">
      Reddit ↗
    </a>
  </div>
</div>

<div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--amber);
            border-left:2px solid var(--amber); padding-left:12px;
            margin-bottom:16px; line-height:1.65; font-style:italic;">
  {q['prompt']}
</div>
""")

    for i, opt in enumerate(q["opts"]):
        is_sel = selected == i
        if st.button(
            ("◆  " if is_sel else "") + opt["t"],
            key=f"opt_{cur}_{i}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            st.session_state.wwyd_answers[cur] = i
            st.rerun()

    st.html(
        f'<div style="font-family:\'Space Mono\',monospace; font-size:9px; color:var(--muted); '
        f'text-align:center; margin-top:10px; letter-spacing:1px; text-transform:uppercase;">'
        f'{source} · <a href="{q["url"]}" target="_blank" style="color:var(--cyan); text-decoration:none;">'
        f'{q["sub"]}</a> · {cur+1}/{total}</div>'
    )

    st.html("<br>")
    col_back, col_next = st.columns(2)
    with col_back:
        if cur > 0:
            if st.button("← Back", key="back_btn", use_container_width=True):
                st.session_state.wwyd_cur -= 1
                st.rerun()
    with col_next:
        label = "See My Profile →" if is_last else "Next →"
        if st.button(label, key="next_btn", disabled=(selected is None),
                     use_container_width=True, type="primary"):
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

    fill_color = "#c6ff00" if pct >= 60 else "#ffb300" if pct >= 30 else "#ff2d78"

    st.markdown(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px; padding:32px 28px;">
  <div style="font-size:52px; text-align:center; display:block; margin-bottom:12px;">{result['icon']}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(32px,7vw,52px);
              letter-spacing:3px; color:var(--text); text-align:center; margin-bottom:4px; line-height:1.05;">
    {result['name']}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:10px; letter-spacing:2px;
              color:var(--amber); text-transform:uppercase; text-align:center; margin-bottom:18px;">
    {result['meta']}
  </div>
  <p style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
             line-height:1.9; text-align:center; margin-bottom:28px;">
    {result['desc']}
  </p>
  <div style="background:var(--surface); border:1px solid var(--border); border-radius:3px; padding:20px; margin-bottom:0;">
    <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Openness Index</div>
    <div style="height:6px; background:var(--border); border-radius:3px; margin-bottom:8px; overflow:hidden;">
      <div style="width:{pct}%; height:100%; background:{fill_color}; border-radius:3px;"></div>
    </div>
    <div style="display:flex; justify-content:space-between;
                font-family:'Space Mono',monospace; font-size:9px; color:var(--muted); margin-bottom:10px;">
      <span>Closed off</span><span>Wide open</span>
    </div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:{fill_color}; line-height:1;">
      {pct}<span style="font-family:'DM Sans',sans-serif; font-size:16px; color:var(--muted); font-weight:300;"> / 100</span>
    </div>
  </div>
</div>
""")

    share = (
        f'Just took "What Would You Do?" on ViceVault\n\n'
        f'Result: {result["name"]}\n"{result["meta"]}"\n'
        f'Openness Index: {pct}/100\n\nEvery quiz uses different scenarios 👀'
    )
    st.html("<br>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺ Try Again", use_container_width=True):
            hard_reset()
    with col2:
        st.download_button("↓ Save Result", data=share, file_name="my_result.txt",
                           mime="text/plain", use_container_width=True)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def what_would_you_do_page():
    inject_css()
    init_state()
    _, col, _ = st.columns([1, 5, 1])
    with col:
        render_header(st.session_state.wwyd_live)
        phase = st.session_state.wwyd_phase
        if   phase == "start":   render_start()
        elif phase == "loading": render_loading()
        elif phase == "quiz":    render_quiz()
        elif phase == "result":  render_result()
