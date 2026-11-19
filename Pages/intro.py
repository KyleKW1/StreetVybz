"""
Pages/intro.py — "How Hidden works": a short walkthrough shown right after sign-up,
from the login page, and any time from Me.
"""

import streamlit as st

from ui import veil

# Small mock-ups of the real screens, so each slide shows what it's describing.
_PREVIEW_DISCOVER = f"""
<div class="hd-intro-mock" style="display:flex;gap:10px;">
  <div style="flex:1;min-width:0;">{veil("Jay", 2, hot=True, tag="Tonight", tag_kind="sodium")}
    <div class="hd-tile-name">Jay<span>26</span></div><div class="hd-tile-meta"><span>3 km</span><b>82%</b></div></div>
  <div style="flex:1;min-width:0;">{veil("Rae", 1)}
    <div class="hd-tile-name">Rae<span>24</span></div><div class="hd-tile-meta"><span>5 km</span><b>74%</b></div></div>
  <div style="flex:1;min-width:0;">{veil("Dre", 3)}
    <div class="hd-tile-name">Dre<span>29</span></div><div class="hd-tile-meta"><span>8 km</span><b>61%</b></div></div>
</div>
<div class="hd-post-quote" style="margin-top:14px;"><span class="hd-kicker">Tonight post</span>
  Can host after 11, New Kingston side. Drinks here.</div>
"""

_PREVIEW_QA = """
<div class="hd-intro-mock">
  <div class="hd-post-quote" style="margin-top:0;"><span class="hd-kicker">Request for you</span>
    Saw your post. I'm close. Say the word.</div>
  <div class="hd-intro-pills"><span>Ignore</span><span class="on">Accept</span></div>
</div>
"""

_PREVIEW_WELCOME = f"""
<div class="hd-intro-mock" style="display:flex;gap:10px;">
  <div style="flex:1;">{veil("Shanice", 0)}</div>
  <div style="flex:1;">{veil("Marlon", 4)}</div>
  <div style="flex:1;">{veil("Tash", 5, lifted=True, tag="Linked")}</div>
</div>
"""

_PREVIEW_VIBE = """
<div class="hd-intro-mock">
  <div class="hd-chips" style="margin:0;">
    <span class="hd-chip quiet">Weed: sometimes</span><span class="hd-chip quiet">Drinks: socially</span>
    <span class="hd-chip quiet">Parties: often</span><span class="hd-chip">Can host</span>
  </div>
  <div class="hd-note" style="margin-top:10px;">Match by live distance, or by city only.</div>
</div>
"""

_PREVIEW_QUIZ = """
<div class="hd-intro-mock">
  <div class="hd-kicker">What a heat score is made of</div>
  <div style="display:flex;height:10px;border-radius:99px;overflow:hidden;margin:10px 0 8px;gap:3px;">
    <div style="flex:35;background:var(--smoke);border-radius:99px;"></div>
    <div style="flex:65;background:var(--bulb);border-radius:99px;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;" class="hd-note">
    <span>35% lifestyle</span><span style="color:#ff8a98;">65% quiz</span>
  </div>
</div>
"""

_PREVIEW_SAFETY = """
<div class="hd-intro-mock">
  <div class="hd-why" style="margin:0;padding:0;border:0;">
    <div>Hide from Discover any time.</div>
    <div>Block or report anyone, any time.</div>
    <div>Quiz results: only your links, or people you give a code.</div>
    <div>Distances are rough, never your exact spot.</div>
  </div>
</div>
"""

SLIDES = [
    ("", "Welcome to Hidden",
     "Link up with people nearby who want what you want. Not a dating app. Everyone stays behind the tint "
     "until you both say yes.",
     _PREVIEW_WELCOME),
    ("", "Say what you're on",
     "Tonight only, regular or either. Who you're into, whether you can host, how you roll with weed, "
     "drinks and parties, and where you are. You only see people who fit, and they only see you if you fit them.",
     _PREVIEW_VIBE),
    ("", "Take the quiz",
     "Read Between The Lines is a 5-minute scenario quiz and 65% of your heat score. Once you link "
     "you'll see each other's result, freak score and the hidden desires you share.",
     _PREVIEW_QUIZ),
    ("", "See who's around",
     "A grid of everyone nearby who fits, free tonight first, then by heat. "
     "Or post what you're on tonight. It's gone at 6am.",
     _PREVIEW_DISCOVER),
    ("", "Send a link request",
     "Tap someone or reply to a post with a short note. If they accept, the chat opens. "
     "If they ignore it, you're never told. Nobody can message you without your yes.",
     _PREVIEW_QA),
    ("", "You're in control",
     "First time with someone? Meet in public, tell a friend, and keep consent out loud. "
     "Hide, block or report any time. And your first link unlocks something hidden.",
     _PREVIEW_SAFETY),
]

_CSS = """
<style>
.hd-intro-mock { margin-top:20px; }
.hd-intro-pills { display:flex; gap:8px; margin-top:14px; }
.hd-intro-pills span { flex:1; text-align:center; padding:10px 0; border-radius:99px; font-family:var(--font);
  font-size:15px; font-weight:600; border:1px solid var(--line); color:var(--ink); }
.hd-intro-pills span.on { background:var(--sodium); color:#000; border-color:var(--sodium); }
.hd-intro-dots { display:flex; gap:6px; margin:22px 0 6px; }
.hd-intro-dots i { width:7px; height:7px; border-radius:99px; background:var(--line); transition:width .3s, background .3s; }
.hd-intro-dots i.on { width:22px; background:var(--ink); }
div.st-key-intro_nav div[data-testid="stHorizontalBlock"],
div.st-key-intro_top div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:8px !important; }
div.st-key-intro_nav div[data-testid="stColumn"] { min-width:0 !important; flex:1 1 0 !important; width:auto !important; }
div.st-key-intro_top div[data-testid="stColumn"] { min-width:0 !important; }
div.st-key-intro_top div[data-testid="stColumn"]:last-child { flex:0 0 84px !important; }
</style>
"""


def open_intro(return_to: str, logged_in: bool = True):
    """Show the walkthrough; Skip or its last button goes back to `return_to`.

    Logged out (from the login page), the last button goes on to sign-up instead.
    """
    st.session_state._intro_return = return_to
    st.session_state.intro_step = 0
    if logged_in:
        st.session_state.tab = "intro"
    else:
        st.session_state.page = "intro"
    st.rerun()


def _finish(logged_in: bool, go: str | None = None):
    st.session_state.pop("intro_step", None)
    back = go or st.session_state.pop("_intro_return", None)
    st.session_state.pop("_intro_return", None)
    if logged_in:
        # "setup" just means back into the app; main() shows setup while the profile is incomplete
        st.session_state.tab = "discover" if back in (None, "setup") else back
    else:
        st.session_state.page = back or "login"
    st.rerun()


def intro_page(logged_in: bool = True):
    st.html(_CSS)
    i = max(0, min(int(st.session_state.get("intro_step", 0)), len(SLIDES) - 1))
    icon, title, body, preview = SLIDES[i]
    last = i == len(SLIDES) - 1

    with st.container(key="intro_top"):
        top_l, top_r = st.columns([3, 1], vertical_alignment="center")
        with top_l:
            from ui import wordmark
            st.html(wordmark())
        with top_r:
            if not last and st.button("Skip", key="intro_skip", type="tertiary"):
                _finish(logged_in)

    st.html(f"""
<div class="hd" style="margin-top:26px;">
  <div class="hd-note">{i + 1} of {len(SLIDES)}</div>
  <div class="hd-title" style="font-size:32px;margin-top:6px;">{title}</div>
  <div class="hd-sub" style="font-size:16px;">{body}</div>
  {preview or ""}
</div>
<div class="hd-intro-dots">{"".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(SLIDES)))}</div>
""")

    if last:
        done_label = "Sign me up" if not logged_in else "Let's go"
    else:
        done_label = "Next" if i else "Show me"

    with st.container(key="intro_nav"):
        c_back, c_next = st.columns(2)
        with c_back:
            if st.button("Back", key="intro_back", use_container_width=True, disabled=i == 0):
                st.session_state.intro_step = i - 1
                st.rerun()
        with c_next:
            if st.button(done_label, key="intro_next", type="primary", use_container_width=True):
                if last:
                    _finish(logged_in, None if logged_in else "register")
                st.session_state.intro_step = i + 1
                st.rerun()
