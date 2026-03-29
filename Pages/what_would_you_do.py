"""
Pages/what_would_you_do.py
Live Reddit-powered sexual taboo quiz.
"""

import streamlit as st
import json
import random
import time
import anthropic

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

MIN_SCORE  = 100
MIN_LENGTH = 250
POST_COUNT = 10

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


def time_ago(ts: float) -> str:
    diff = int(time.time() - ts)
    if diff < 3600:  return f"{diff // 60} min ago"
    if diff < 86400: return f"{diff // 3600} hours ago"
    return f"{diff // 86400} days ago"


def is_taboo(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw in text for kw in TABOO_KEYWORDS)


def fmt_num(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_posts() -> list:
    import requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    all_posts = []
    session = requests.Session()
    session.headers.update(headers)

    for sub in SUBREDDITS:
        for sort, params in [("hot", {}), ("top", {"t": "month"})]:
            url = f"https://www.reddit.com/r/{sub}/{sort}.json"
            try:
                r = session.get(url, params={"limit": 50, **params}, timeout=10)
                if not r.ok:
                    continue
                children = r.json().get("data", {}).get("children", [])
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
            except Exception as e:
                st.warning(f"r/{sub} ({sort}): {e}")

    random.shuffle(all_posts)
    seen, unique = set(), []
    for p in all_posts:
        if p["title"] not in seen:
            seen.add(p["title"])
            unique.append(p)
    return unique[:POST_COUNT * 2]


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

Each option: 1-2 sentences, specific and authentic.

Respond ONLY with JSON (no markdown):
{{"prompt":"...","opts":[{{"t":"...","pts":0}},{{"t":"...","pts":2}},{{"t":"...","pts":3}},{{"t":"...","pts":5}}]}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


def init_state():
    for k, v in {
        "wwyd_phase":     "start",
        "wwyd_questions": [],
        "wwyd_answers":   [],
        "wwyd_cur":       0,
        "wwyd_error":     "",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


def hard_reset():
    for k in list(st.session_state.keys()):
        if k.startswith("wwyd_"):
            del st.session_state[k]
    fetch_posts.clear()
    init_state()
    st.rerun()


def inject_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
section.main .block-container { padding-top: 1rem !important; }
:root {
  --bg:#0f0f13; --card:#16161d; --surface:#1c1c26;
  --a1:#ff4d6d; --a2:#c77dff; --a3:#48cae4;
  --gold:#ffd166; --text:#f0eeff; --muted:#555570;
  --soft:#9090b0; --border:#252535;
}
.quiz-hdr { text-align:center; margin-bottom:24px; }
.eyebrow { font-size:9px; letter-spacing:5px; color:var(--a2); text-transform:uppercase; margin-bottom:10px; display:block; }
.quiz-title { font-family:'Syne',sans-serif; font-size:clamp(36px,8vw,58px); font-weight:800; line-height:.95; letter-spacing:-1px; color:var(--text); margin:0; }
.quiz-title em { font-style:normal; background:linear-gradient(90deg,var(--a1),var(--a2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.quiz-sub { font-size:9px; letter-spacing:2px; color:var(--muted); margin-top:10px; text-transform:uppercase; }
.live-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(255,77,109,.12); border:1px solid rgba(255,77,109,.3); border-radius:20px; padding:4px 12px; font-size:9px; letter-spacing:2px; text-transform:uppercase; color:var(--a1); margin-top:10px; }
.live-dot { width:6px; height:6px; border-radius:50%; background:var(--a1); display:inline-block; animation:pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{ opacity:1; transform:scale(1); } 50%{ opacity:.4; transform:scale(.7); } }
.qcard { background:var(--card); border:1px solid var(--border); border-radius:6px; padding:24px 20px; position:relative; margin-bottom:10px; }
.qcard::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; border-radius:6px 6px 0 0; background:linear-gradient(90deg,var(--a1),var(--a2),var(--a3)); }
.prog { display:flex; gap:4px; margin-bottom:20px; }
.p { height:3px; flex:1; background:var(--border); border-radius:10px; transition:all .3s; }
.p.done { background:var(--a2); } .p.now { background:var(--a1); }
.reddit-post { background:var(--surface); border:1px solid var(--border); border-radius:5px; margin-bottom:16px; overflow:hidden; }
.post-header { display:flex; align-items:center; gap:10px; padding:12px 14px 0; }
.post-avatar { width:30px; height:30px; border-radius:50%; background:linear-gradient(135deg,var(--a2),var(--a1)); display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:#fff; flex-shrink:0; }
.post-sub { font-size:10px; font-weight:600; color:var(--a2); }
.post-info { font-size:10px; color:var(--muted); margin-top:2px; }
.post-flair { font-size:9px; letter-spacing:1px; padding:2px 8px; border:1px solid rgba(199,125,255,.3); color:var(--a2); border-radius:20px; text-transform:uppercase; white-space:nowrap; margin-left:auto; }
.post-body { padding:12px 14px 14px; }
.post-title { font-family:'Syne',sans-serif; font-size:13px; font-weight:700; color:var(--text); margin-bottom:10px; line-height:1.4; }
.post-text { font-size:12px; color:var(--soft); line-height:1.85; }
.post-footer { border-top:1px solid var(--border); padding:9px 14px; display:flex; gap:14px; align-items:center; }
.post-stat { font-size:10px; color:var(--muted); }
.post-link { font-size:9px; color:var(--a3); text-decoration:none; letter-spacing:1px; margin-left:auto; }
.q-prompt { font-size:11px; color:var(--gold); margin-bottom:14px; padding-left:10px; border-left:2px solid var(--gold); font-style:italic; line-height:1.6; }
.s-desc { font-size:13px; line-height:1.9; color:var(--soft); margin-bottom:20px; text-align:center; }
.info-box { background:var(--surface); border:1px solid var(--border); border-radius:5px; padding:14px 16px; margin-bottom:12px; }
.info-label { font-size:9px; letter-spacing:2px; color:var(--a3); text-transform:uppercase; margin-bottom:8px; }
.pill-row { display:flex; flex-wrap:wrap; gap:6px; }
.pill { font-size:10px; padding:4px 12px; border:1px solid var(--a2); border-radius:20px; color:var(--a2); background:rgba(199,125,255,.07); display:inline-block; }
.res-icon { font-size:54px; display:block; text-align:center; margin-bottom:12px; }
.res-name { font-family:'Syne',sans-serif; font-size:clamp(26px,6vw,40px); font-weight:800; margin-bottom:4px; text-align:center; color:var(--text); }
.res-meta { font-size:10px; letter-spacing:2px; color:var(--gold); text-transform:uppercase; margin-bottom:16px; text-align:center; }
.res-desc { font-size:13px; line-height:1.9; color:var(--soft); margin-bottom:20px; text-align:center; }
.meter-wrap { background:var(--surface); border:1px solid var(--border); border-radius:5px; padding:18px; margin-bottom:20px; }
.meter-label { font-size:9px; letter-spacing:2px; color:var(--muted); text-transform:uppercase; margin-bottom:10px; }
.meter-track { height:10px; background:var(--border); border-radius:10px; overflow:hidden; margin-bottom:8px; }
.meter-fill { height:100%; border-radius:10px; background:linear-gradient(90deg,var(--a3),var(--a2),var(--a1)); }
.meter-ends { display:flex; justify-content:space-between; font-size:9px; color:var(--muted); }
.meter-score { font-family:'Syne',sans-serif; font-size:34px; font-weight:800; color:var(--text); margin-top:10px; }
.meter-score small { font-size:14px; color:var(--muted); font-family:'DM Sans',sans-serif; font-weight:400; }
.source-note { font-size:9px; color:var(--muted); text-align:center; margin-top:10px; letter-spacing:1px; }
.source-note a { color:var(--a3); text-decoration:none; }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
<div class="quiz-hdr">
  <span class="eyebrow">Real posts · Real people · Real reactions</span>
  <h1 class="quiz-title">What Would<br><em>You Do?</em></h1>
  <p class="quiz-sub">Live from Reddit — fresh every time</p>
  <div class="live-badge"><span class="live-dot"></span>&nbsp;Live Edition</div>
</div>
""", unsafe_allow_html=True)


def render_start():
    if st.session_state.wwyd_error:
        st.error(st.session_state.wwyd_error)
        st.session_state.wwyd_error = ""

    subs_html = "".join(f'<span class="pill">r/{s}</span>' for s in SUBREDDITS)
    st.markdown(f"""
<div class="qcard">
  <p class="s-desc">
    Real posts pulled live from Reddit right now.<br>
    Every post gets a question generated just for you.<br>
    Different scenarios every single time.
  </p>
  <div class="info-box">
    <div class="info-label">Pulling from</div>
    <div class="pill-row">{subs_html}</div>
  </div>
  <div class="info-box">
    <div class="info-label">How it works</div>
    <p style="color:var(--soft);font-size:12px;line-height:1.7;margin:0">
      Posts about threesomes, open relationships, confessions, and sexual curiosity
      are fetched and filtered live. AI writes a personal question for each one.
      Your answers build your Openness Profile.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("🔥  Pull Live Posts", use_container_width=True, type="primary"):
        st.session_state.wwyd_phase = "loading"
        st.rerun()


def render_loading():
    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(title, pct, status):
        ph_title.markdown(f"### {title}")
        ph_bar.progress(pct)
        ph_status.caption(status)

    try:
        upd("Connecting to Reddit…", 5, "Fetching posts from multiple subreddits")
        posts = fetch_posts()

        if not posts:
            st.session_state.wwyd_error = (
                "No taboo posts found — Reddit may be rate-limiting. "
                "Try again in 30 seconds."
            )
            st.session_state.wwyd_phase = "start"
            st.rerun()
            return

        upd("Filtering posts…", 20, f"Found {len(posts)} relevant posts")
        time.sleep(0.2)

        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        except Exception:
            client = anthropic.Anthropic()

        selected  = posts[:POST_COUNT]
        questions = []

        for i, post in enumerate(selected):
            pct = 25 + int((i / len(selected)) * 70)
            upd("Generating questions with AI…", pct, f"Question {i+1} of {len(selected)}")
            try:
                q_data = generate_question(post, client)
                questions.append({**post, **q_data})
            except Exception:
                questions.append({**post, "prompt": "Your honest gut reaction to this is:", "opts": FALLBACK_OPTS})

        upd("Almost ready…", 98, "Preparing your quiz")
        time.sleep(0.3)

        st.session_state.wwyd_questions = questions
        st.session_state.wwyd_answers   = [None] * len(questions)
        st.session_state.wwyd_cur       = 0
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

    dots = "".join(
        f'<div class="p {"done" if i < cur else "now" if i == cur else ""}"></div>'
        for i in range(total)
    )

    st.markdown(f"""
<div class="qcard">
  <div class="prog">{dots}</div>
  <div class="reddit-post">
    <div class="post-header">
      <div class="post-avatar">{q['avatar']}</div>
      <div style="flex:1">
        <div class="post-sub">{q['sub']}</div>
        <div class="post-info">u/{q['user']} · {q['time']}</div>
      </div>
      <span class="post-flair">{q.get('flair','Post')}</span>
    </div>
    <div class="post-body">
      <div class="post-title">{q['title']}</div>
      <div class="post-text">{q['text'][:700]}{"…" if len(q['text']) > 700 else ""}</div>
    </div>
    <div class="post-footer">
      <span class="post-stat">▲ {q['upvotes']}</span>
      <span class="post-stat">💬 {q['comments']}</span>
      <a class="post-link" href="{q['url']}" target="_blank">View on Reddit ↗</a>
    </div>
  </div>
  <div class="q-prompt">{q['prompt']}</div>
</div>
""", unsafe_allow_html=True)

    for i, opt in enumerate(q["opts"]):
        prefix = "◆  " if selected == i else ""
        if st.button(prefix + opt["t"], key=f"opt_{cur}_{i}",
                     use_container_width=True,
                     type="primary" if selected == i else "secondary"):
            st.session_state.wwyd_answers[cur] = i
            st.rerun()

    st.markdown(
        f'<div class="source-note">Real post · '
        f'<a href="{q["url"]}" target="_blank">{q["sub"]}</a> · '
        f'Scenario {cur+1}/{total}</div>',
        unsafe_allow_html=True
    )

    col_back, _, col_next = st.columns([1, 0.2, 1])
    with col_back:
        if cur > 0:
            if st.button("← Back", key="back_btn", use_container_width=True):
                st.session_state.wwyd_cur -= 1
                st.rerun()
    with col_next:
        if st.button(
            "Get My Profile →" if is_last else "Next →",
            key="next_btn", disabled=(selected is None),
            use_container_width=True, type="primary"
        ):
            st.session_state.wwyd_phase = "result" if is_last else "quiz"
            if not is_last:
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
<div class="qcard">
  <span class="res-icon">{result['icon']}</span>
  <div class="res-name">{result['name']}</div>
  <div class="res-meta">{result['meta']}</div>
  <p class="res-desc">{result['desc']}</p>
  <div class="meter-wrap">
    <div class="meter-label">Openness Index</div>
    <div class="meter-track"><div class="meter-fill" style="width:{pct}%"></div></div>
    <div class="meter-ends"><span>Closed off</span><span>Wide open</span></div>
    <div class="meter-score">{pct}<small>% open</small></div>
  </div>
</div>
""", unsafe_allow_html=True)

    share = (
        f'Just took "What Would You Do?" — Live Reddit Edition\n\n'
        f'My result: {result["name"]}\n"{result["meta"]}"\n'
        f'Openness Index: {pct}%\n\n'
        f'Every quiz is different — real posts, fresh questions 👀'
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  New Posts", use_container_width=True):
            hard_reset()
    with col2:
        st.download_button("📋  Copy Result", data=share,
                           file_name="my_result.txt", mime="text/plain",
                           use_container_width=True)


def what_would_you_do_page():
    inject_css()
    init_state()
    _, col, _ = st.columns([1, 3, 1])
    with col:
        render_header()
        phase = st.session_state.wwyd_phase
        if   phase == "start":   render_start()
        elif phase == "loading": render_loading()
        elif phase == "quiz":    render_quiz()
        elif phase == "result":  render_result()
    st.markdown(QUIZ_CSS, unsafe_allow_html=True)
    st.markdown('<div class="quiz-outer">', unsafe_allow_html=True)

    init_state()
    render_header()

    phase = st.session_state.wwyd_phase

    if phase == "start":
        if st.session_state.wwyd_error:
            st.error(st.session_state.wwyd_error)
            st.session_state.wwyd_error = ""
        render_start()
    elif phase == "loading":
        render_loading()
    elif phase == "quiz":
        render_quiz()
    elif phase == "result":
        render_result()

    st.markdown('</div>', unsafe_allow_html=True)
