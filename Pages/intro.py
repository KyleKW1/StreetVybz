"""
Pages/intro.py — "How Hidden works": a short walkthrough shown right after sign-up,
from the login page, and any time from Me.
"""

import streamlit as st

from ui import avatar, score_ring

# Small mock-ups of the real screens, so each slide shows what it's describing.
_PREVIEW_DISCOVER = f"""
<div class="hd-intro-mock" style="display:flex;align-items:center;gap:12px;">
  {avatar("Jay", 2, small=True)}
  <div style="flex:1;min-width:0;">
    <div class="hd-title" style="font-size:24px;margin:0;">Jay, 26</div>
    <div class="hd-kicker">📍 3 km away</div>
  </div>
  {score_ring(82)}
</div>
<div class="hd-intro-pills"><span>✕ Pass</span><span class="on">♥ Like</span></div>
"""

_PREVIEW_QA = """
<div class="hd-intro-mock">
  <div class="hd-intro-steps">
    <span class="on">1 · Ask</span><span>2 · Answer</span><span>3 · Reveal</span><span>4 · Chat</span>
  </div>
  <div class="hd-bubble them" style="max-width:100%;">What's your perfect Friday?</div>
  <div class="hd-bubble me" style="max-width:100%;filter:blur(4px);">Hidden until you both answer</div>
</div>
"""

_PREVIEW_WELCOME = """
<div class="hd-intro-mock">
  <div class="hd-chips" style="margin:0;justify-content:center;">
    <span class="hd-chip lime">🎚️ Vibe</span><span class="hd-chip">🎯 Quiz</span>
    <span class="hd-chip cyan">🔥 Discover</span><span class="hd-chip magenta">💘 Q&amp;A</span>
    <span class="hd-chip amber">💬 Chat</span>
  </div>
</div>
"""

_PREVIEW_VIBE = """
<div class="hd-intro-mock">
  <div class="hd-chips" style="margin:0;justify-content:center;">
    <span class="hd-chip cyan">🌿 Sometimes</span><span class="hd-chip amber">🥃 Socially</span>
    <span class="hd-chip magenta">🪩 Often</span>
  </div>
  <div class="hd-sub" style="text-align:center;margin-top:10px;">📍 Live distance or 🏙 city only</div>
</div>
"""

_PREVIEW_QUIZ = """
<div class="hd-intro-mock" style="text-align:center;">
  <div class="hd-kicker">Vibe score</div>
  <div style="display:flex;height:12px;border-radius:99px;overflow:hidden;margin:10px 0 8px;">
    <div style="flex:6;background:var(--cyan);"></div><div style="flex:4;background:var(--magenta);"></div>
  </div>
  <div style="display:flex;justify-content:space-between;" class="hd-kicker">
    <span style="color:var(--cyan);">60% lifestyle</span><span style="color:var(--magenta);">40% quiz</span>
  </div>
</div>
"""

_PREVIEW_SAFETY = """
<div class="hd-intro-mock">
  <div class="hd-why" style="margin:0;padding:0;border:0;">
    <div>👻 &nbsp;Hide from Discover any time</div>
    <div>⚑ &nbsp;Block or report from any match</div>
    <div>🔒 &nbsp;Only matches see your quiz result</div>
    <div>📍 &nbsp;Distances are rough, never your exact spot</div>
  </div>
</div>
"""

SLIDES = [
    ("⚡", "Welcome to Hidden",
     "Meet people nearby who live like you do. Here's how it works, in five quick steps.",
     _PREVIEW_WELCOME),
    ("🎚️", "1 · Set your vibe",
     "Tell us how you roll with weed, drinks and parties, who you want to meet, and where you are. "
     "You only see people who fit, and they only see you if you fit them.",
     _PREVIEW_VIBE),
    ("🎯", "2 · Take the quiz",
     "Read Between The Lines is a 5-minute scenario quiz. It sharpens your vibe score, and once you "
     "match you'll see each other's result, freak score and the hidden desires you share.",
     _PREVIEW_QUIZ),
    ("🔥", "3 · Discover",
     "One person at a time, best vibe first. The ring shows how alike you are. "
     "Tap Like or Pass. If you both like each other, it's a match.",
     _PREVIEW_DISCOVER),
    ("💘", "4 · Blind Q&A, then chat",
     "Before anyone can message, you each ask 3 questions and answer theirs. "
     "Answers reveal at the same time, then the chat opens.",
     _PREVIEW_QA),
    ("🛡️", "5 · You're in control",
     "Meet in public and tell a friend where you're going. You can hide, block or report any time. "
     "And your first match unlocks something hidden… 🔒",
     _PREVIEW_SAFETY),
]

_CSS = """
<style>
.hd-intro-emoji { font-size:52px; text-align:center; line-height:1; animation:hd-pop .6s both; }
.hd-intro-mock { margin-top:18px; padding:16px; border-radius:16px; background:#111116;
  border:1px solid var(--border); }
.hd-intro-pills { display:flex; gap:8px; margin-top:12px; }
.hd-intro-pills span { flex:1; text-align:center; padding:9px 0; border-radius:99px;
  font-family:'Space Mono',monospace; font-size:11px; border:1px solid var(--border); color:var(--soft); }
.hd-intro-pills span.on { background:var(--lime); color:#0a0a0b; border-color:var(--lime); }
.hd-intro-steps { display:flex; gap:4px; margin-bottom:10px; }
.hd-intro-steps span { flex:1; text-align:center; font-family:'Space Mono',monospace; font-size:9px;
  padding:5px 0; border-radius:99px; background:#1d1d25; color:var(--muted); white-space:nowrap; }
.hd-intro-steps span.on { background:rgba(255,45,120,.15); color:var(--magenta); }
.hd-intro-dots { display:flex; justify-content:center; gap:6px; margin:16px 0 4px; }
.hd-intro-dots i { width:7px; height:7px; border-radius:99px; background:#2a2a35; transition:all .3s; }
.hd-intro-dots i.on { width:22px; background:var(--lime); }
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
            st.html('<div class="hd-brand">HIDDEN</div>')
        with top_r:
            if not last and st.button("Skip", key="intro_skip", use_container_width=True):
                _finish(logged_in)

    st.html(f"""
<div class="hd-card" style="margin-top:14px;padding:30px 22px 24px;">
  <div class="hd-intro-emoji">{icon}</div>
  <div class="hd-title" style="text-align:center;font-size:36px;margin-top:12px;">{title}</div>
  <div class="hd-sub" style="text-align:center;">{body}</div>
  {preview or ""}
</div>
<div class="hd-intro-dots">{"".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(len(SLIDES)))}</div>
""")

    if last:
        done_label = "Sign me up →" if not logged_in else "Let's go →"
    else:
        done_label = "Next →" if i else "Show me →"

    with st.container(key="intro_nav"):
        c_back, c_next = st.columns(2)
        with c_back:
            if st.button("← Back", key="intro_back", use_container_width=True, disabled=i == 0):
                st.session_state.intro_step = i - 1
                st.rerun()
        with c_next:
            if st.button(done_label, key="intro_next", type="primary", use_container_width=True):
                if last:
                    _finish(logged_in, None if logged_in else "register")
                st.session_state.intro_step = i + 1
                st.rerun()
