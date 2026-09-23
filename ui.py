"""
ui.py — Shared look & components for the Hidden app shell.

Everything user-provided goes through esc() before it reaches st.html.
"""

from html import escape

import streamlit as st

from matching import LIFESTYLE, INTENTS

_APP_CSS = """
<style>
/* No sidebar — navigation lives in the top bar */
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"] { display:none !important; }
section.main .block-container, div[data-testid="stMainBlockContainer"] {
  max-width: 640px !important; padding-top: 1.2rem !important;
}
/* The transparent Streamlit header overlaps the top of the page (thanks to the
   short padding above), so let clicks fall through it to our own buttons.
   Its own toolbar controls stay clickable. */
header[data-testid="stHeader"], header[data-testid="stHeader"] div { pointer-events: none; }
header[data-testid="stHeader"] :is(button, a, [role="button"], [data-testid="stMainMenu"],
  [data-testid="stToolbarActions"] *, [data-testid="stAppDeployButton"] *) { pointer-events: auto; }

@keyframes hd-rise  { from{opacity:0;transform:translateY(22px) scale(.97)} to{opacity:1;transform:none} }
@keyframes hd-pop   { 0%{transform:scale(.6);opacity:0} 60%{transform:scale(1.08);opacity:1} 100%{transform:scale(1)} }
@keyframes hd-glow  { 0%,100%{box-shadow:0 0 0 0 rgba(255,45,120,.0)} 50%{box-shadow:0 0 38px 4px rgba(255,45,120,.25)} }
@keyframes hd-shine { from{background-position:0% 50%} to{background-position:200% 50%} }
@keyframes hd-dot   { 0%,80%,100%{opacity:.2;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }
@keyframes hd-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }

.hd-brand {
  font-family:'Bebas Neue',sans-serif; font-size:34px; letter-spacing:5px; line-height:1;
  background:linear-gradient(90deg,var(--lime),var(--cyan),var(--magenta),var(--lime));
  background-size:200% auto; -webkit-background-clip:text; background-clip:text; color:transparent;
  animation:hd-shine 6s linear infinite;
}
.hd-kicker { font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
  text-transform:uppercase; color:var(--muted); }
.hd-title  { font-family:'Bebas Neue',sans-serif; font-size:40px; letter-spacing:2px;
  color:var(--text); line-height:1; margin:2px 0 6px; }
.hd-sub    { font-family:'DM Sans',sans-serif; font-size:14px; color:var(--soft); line-height:1.6; }

.hd-card {
  background:linear-gradient(160deg,#1c1c24 0%,#131318 100%);
  border:1px solid var(--border); border-radius:22px; padding:24px 22px;
  animation:hd-rise .45s cubic-bezier(.19,1,.22,1) both;
}
.hd-card.hot { border-color:rgba(255,45,120,.45); animation:hd-rise .45s cubic-bezier(.19,1,.22,1) both, hd-glow 3s ease-in-out infinite .5s; }

.hd-avatar {
  width:64px; height:64px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-family:'Bebas Neue',sans-serif; font-size:26px; color:#0a0a0b; letter-spacing:1px;
}
.hd-avatar.sm { width:44px; height:44px; font-size:18px; }

.hd-ring {
  --p:0; width:74px; height:74px; border-radius:50%; flex-shrink:0;
  background:conic-gradient(var(--c,var(--lime)) calc(var(--p)*1%), #262631 0);
  display:flex; align-items:center; justify-content:center;
  animation:hd-pop .6s cubic-bezier(.19,1,.22,1) both .15s;
}
.hd-ring > div {
  width:60px; height:60px; border-radius:50%; background:#15151b;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
}
.hd-ring b { font-family:'Bebas Neue',sans-serif; font-size:24px; color:var(--text); line-height:1; }
.hd-ring small { font-family:'Space Mono',monospace; font-size:7px; letter-spacing:1px; color:var(--muted); }

.hd-chips { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 4px; }
.hd-chip {
  font-family:'Space Mono',monospace; font-size:10px; letter-spacing:.5px;
  padding:5px 10px; border-radius:99px; border:1px solid var(--border);
  color:var(--soft); background:#17171d; white-space:nowrap;
}
.hd-chip.lime    { color:var(--lime);    border-color:rgba(198,255,0,.35);  background:rgba(198,255,0,.06); }
.hd-chip.magenta { color:var(--magenta); border-color:rgba(255,45,120,.4);  background:rgba(255,45,120,.07); }
.hd-chip.cyan    { color:var(--cyan);    border-color:rgba(0,229,255,.35);  background:rgba(0,229,255,.06); }
.hd-chip.amber   { color:var(--amber);   border-color:rgba(255,179,0,.35);  background:rgba(255,179,0,.06); }

.hd-why { margin-top:14px; padding-top:14px; border-top:1px dashed var(--border); }
.hd-why div { font-family:'DM Sans',sans-serif; font-size:13px; color:var(--text); padding:3px 0; }

.hd-dots span { display:inline-block; width:7px; height:7px; margin:0 2px; border-radius:50%;
  background:var(--magenta); animation:hd-dot 1.4s infinite ease-in-out; }
.hd-dots span:nth-child(2){animation-delay:.2s} .hd-dots span:nth-child(3){animation-delay:.4s}

.hd-bubble { max-width:80%; padding:10px 14px; border-radius:18px; margin:4px 0;
  font-family:'DM Sans',sans-serif; font-size:14px; line-height:1.45; word-wrap:break-word;
  animation:hd-rise .25s ease-out both; }
.hd-bubble.me   { margin-left:auto; background:var(--lime); color:#0a0a0b; border-bottom-right-radius:6px; }
.hd-bubble.them { margin-right:auto; background:#23232c; color:var(--text); border-bottom-left-radius:6px; }
.hd-bubble small { display:block; font-size:10px; opacity:.55; margin-top:3px; }

.hd-lock { font-size:64px; text-align:center; animation:hd-float 3s ease-in-out infinite; }

/* Side-by-side button rows that stay side by side on phones */
div.st-key-swipe div[data-testid="stHorizontalBlock"],
div[class*="st-key-mrow_"] div[data-testid="stHorizontalBlock"],
div[class*="st-key-qrow_"] div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:8px !important; }
div[class*="st-key-qrow_"] div[data-testid="stColumn"] { min-width:0 !important; }
div[class*="st-key-qrow_"] div[data-testid="stColumn"]:last-child { flex:0 0 52px !important; }
div.st-key-swipe div[data-testid="stColumn"] { min-width:0 !important; flex:1 1 0 !important; width:auto !important; }
div[class*="st-key-mrow_"] div[data-testid="stColumn"] { min-width:0 !important; }
div.st-key-swipe .stButton > button, div.st-key-swipe .stButton > button[kind="primary"] {
  height:58px !important; font-size:15px !important; border-radius:99px !important; }

/* Discover: Pass/Like stay pinned to the bottom of the screen while the card scrolls */
div[data-testid="stLayoutWrapper"]:has(> div.st-key-swipe), div.st-key-swipe {
  position:sticky !important; bottom:0; z-index:20; }
div.st-key-swipe { padding:12px 0 14px !important;
  background:linear-gradient(to bottom, rgba(10,10,11,0), var(--bg) 35%) !important; }

/* Slim quiz nudge row on Discover */
div.st-key-qnudge { background:var(--card); border:1px solid var(--border); border-radius:14px;
  padding:10px 12px !important; margin-bottom:10px; }
div.st-key-qnudge div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:10px !important; }
div.st-key-qnudge div[data-testid="stColumn"] { min-width:0 !important; }
div.st-key-qnudge div[data-testid="stColumn"]:last-child { flex:0 0 118px !important; }

/* Top nav: segmented control as one pill bar */
div.st-key-nav, div.st-key-nav div[data-testid="stButtonGroup"] { width:100% !important; }
div.st-key-nav div[data-testid="stButtonGroup"] > div {
  display:flex !important; flex-wrap:nowrap !important; width:100% !important; gap:4px; }
div.st-key-nav button {
  flex:1 1 0 !important; min-width:0 !important; padding:6px 4px !important;
  font-family:'Space Mono',monospace !important; font-size:11px !important; letter-spacing:.5px !important;
  border-radius:99px !important; white-space:nowrap !important;
  background:var(--card) !important; color:var(--soft) !important; border:1px solid var(--border) !important;
}
div.st-key-nav button[kind="segmented_controlActive"],
div.st-key-nav button[aria-checked="true"] {
  background:var(--lime) !important; color:#0a0a0b !important; border-color:var(--lime) !important;
}
div.st-key-nav button p { overflow:hidden; text-overflow:ellipsis; color:inherit !important; }
div.st-key-nav button[aria-checked="true"] * { color:#0a0a0b !important; }
/* Dark text on every lime (primary) button */
.stButton > button[kind="primary"] *, .stButton > button[kind="primary"] { color:#0a0a0b !important; }
@media (max-width:480px) {
  div.st-key-nav button { font-size:10px !important; letter-spacing:0 !important; padding:6px 2px !important; }
}

/* Tertiary buttons read as quiet text links */
.stButton > button[kind="tertiary"] {
  background:transparent !important; border:0 !important; box-shadow:none !important;
  color:var(--lime) !important; text-transform:none !important; letter-spacing:0 !important;
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
  min-height:0 !important; padding:4px 0 !important; }
.stButton > button[kind="tertiary"] * { color:var(--lime) !important; }
.stButton > button[kind="tertiary"]:hover { text-decoration:underline; transform:none !important; }

.hd-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
</style>
"""

_AVATAR_COLORS = ["#c6ff00", "#ff2d78", "#00e5ff", "#ffb300", "#b388ff", "#69f0ae"]
_CHIP_COLORS = ["", "cyan", "amber", "magenta"]


def esc(v) -> str:
    return escape("" if v is None else str(v))


def inject_app_css():
    """Call once per run, from app.main()."""
    st.html(_APP_CSS)


def avatar(name: str, uid: int = 0, small: bool = False) -> str:
    color = _AVATAR_COLORS[int(uid or 0) % len(_AVATAR_COLORS)]
    return (f'<div class="hd-avatar{" sm" if small else ""}" style="background:{color};">'
            f'{esc((name or "?")[:2].upper())}</div>')


def header(kicker: str, title: str, sub: str = ""):
    st.html(f'<div style="margin:6px 0 18px;"><div class="hd-kicker">{esc(kicker)}</div>'
            f'<div class="hd-title">{esc(title)}</div>'
            + (f'<div class="hd-sub">{esc(sub)}</div>' if sub else "") + "</div>")


def empty_state(icon: str, title: str, sub: str = ""):
    st.html(f'<div class="hd-card" style="text-align:center;padding:48px 24px;">'
            f'<div style="font-size:44px;margin-bottom:8px;">{icon}</div>'
            f'<div class="hd-title" style="font-size:28px;">{esc(title)}</div>'
            f'<div class="hd-sub">{esc(sub)}</div></div>')


def waiting(text: str):
    st.html(f'<div class="hd-card" style="text-align:center;padding:36px 20px;">'
            f'<div class="hd-dots" style="margin-bottom:12px;"><span></span><span></span><span></span></div>'
            f'<div class="hd-sub">{esc(text)}</div></div>')


def intent_chips(intents) -> str:
    return "".join(f'<span class="hd-chip magenta">{"💘" if i == "date" else "🤝"} {esc(INTENTS[i])}</span>'
                   for i in intents if i in INTENTS)


def lifestyle_chips(profile: dict) -> str:
    icons = {"weed": "🌿", "drink": "🥃", "party": "🪩"}
    out = []
    for key, (label, opts) in LIFESTYLE.items():
        v = profile.get(key)
        if v is None:
            continue
        out.append(f'<span class="hd-chip {_CHIP_COLORS[int(v)]}">{icons[key]} {esc(opts[int(v)])}</span>')
    return "".join(out)


def score_ring(score: int) -> str:
    color = "var(--lime)" if score >= 75 else "var(--cyan)" if score >= 50 else "var(--amber)"
    return (f'<div class="hd-ring" style="--p:{int(score)};--c:{color};">'
            f'<div><b>{int(score)}%</b><small>VIBE</small></div></div>')


def open_quiz(return_to: str):
    """Jump to the full-screen quiz; its exit button brings you back here."""
    st.session_state._quiz_return = return_to
    st.session_state.tab = "quiz"
    st.rerun()


def invite_link() -> str:
    try:
        base = st.secrets.get("APP_URL", "https://vivevaultapps.streamlit.app")
    except Exception:
        base = "https://vivevaultapps.streamlit.app"
    return base.rstrip("/")
