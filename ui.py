"""
ui.py — Shared look & components for the Hidden app shell.

Everything user-provided goes through esc() before it reaches st.html.

The one visual idea: a person stays behind a tint (a blurred band across a big
initial) until you're linked. The wordmark uses the same band. Colour means
state: sodium = tonight / your move, red bulb = desire and the quiz.
"""

from html import escape

import streamlit as st

from matching import LIFESTYLE, INTENTS, STATUSES, HOSTING

_APP_CSS = """
<style>
/* No sidebar — navigation lives in the top bar */
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"] { display:none !important; }
section.main .block-container, div[data-testid="stMainBlockContainer"] {
  max-width: 600px !important; padding-top: 1.1rem !important;
}
/* The transparent Streamlit header overlaps the top of the page (thanks to the
   short padding above), so let clicks fall through it to our own buttons.
   Its own toolbar controls stay clickable. */
header[data-testid="stHeader"], header[data-testid="stHeader"] div { pointer-events: none; }
header[data-testid="stHeader"] :is(button, a, [role="button"], [data-testid="stMainMenu"],
  [data-testid="stToolbarActions"] *, [data-testid="stAppDeployButton"] *) { pointer-events: auto; }

.hd { font-family:var(--font); color:var(--ink); }
.hd-num { font-variant-numeric: tabular-nums; }

/* ── Wordmark: "hidden" with the tint band across it ─────────── */
.hd-brand { position:relative; display:inline-block; font-family:var(--font); font-weight:800;
  font-stretch:125%; font-size:30px; letter-spacing:-0.02em; line-height:1; color:var(--ink); padding:2px 0; }
/* A strip of sodium-tinted glass: over black it vanishes, over the letters it turns them amber and soft */
.hd-brand::after { content:""; position:absolute; left:0; right:0; top:42%; height:26%;
  -webkit-backdrop-filter:blur(3px); backdrop-filter:blur(3px); background:var(--sodium); mix-blend-mode:multiply; }
.hd-brand.xl { font-size:64px; }

/* ── Type ─────────────────────────────────────────────────────── */
.hd-title { font-family:var(--font); font-weight:800; font-stretch:118%; font-size:30px;
  letter-spacing:-0.02em; line-height:1.05; color:var(--ink); margin:0 0 6px; }
.hd-sub   { font-family:var(--font); font-size:15px; color:var(--smoke); line-height:1.5; }
.hd-h3    { font-family:var(--font); font-weight:700; font-size:15px; color:var(--ink); margin:22px 0 10px; }
.hd-h3 b  { color:var(--sodium); font-weight:700; margin-left:6px; }
.hd-note  { font-family:var(--font); font-size:13px; color:var(--dim); line-height:1.45; }
/* old class name, now a plain small label */
.hd-kicker { font-family:var(--font); font-size:13px; font-weight:500; color:var(--dim); }

/* ── The veil: a person's tile ───────────────────────────────── */
.hd-veil { position:relative; overflow:hidden; border-radius:var(--radius); background:var(--t-bg);
  aspect-ratio:4/5; container-type:inline-size; }
.hd-veil.wide { aspect-ratio:2/1; }
.hd-veil-l { position:absolute; font-family:var(--font); font-weight:900; font-stretch:125%; font-size:150cqw;
  line-height:.8; color:var(--t-fg); text-transform:uppercase; user-select:none; left:-.08em; bottom:-.06em; }
/* each person gets one of three crops, so the grid reads like a set of posters */
.hd-veil.a1 .hd-veil-l { font-size:170cqw; left:-.1em; bottom:auto; top:.06em; }
.hd-veil.a2 .hd-veil-l { font-size:130cqw; left:auto; right:-.12em; bottom:-.02em; }
.hd-veil.wide .hd-veil-l { font-size:62cqw; left:-.06em; right:auto; top:auto; bottom:-.06em; }
.hd-veil-band { position:absolute; left:0; right:0; top:38%; height:26%;
  -webkit-backdrop-filter:blur(9px); backdrop-filter:blur(9px); background:rgba(0,0,0,.2);
  border-top:1px solid rgba(255,255,255,.10); border-bottom:1px solid rgba(255,255,255,.10); }
.lifted .hd-veil-band { display:none; }
.lifting .hd-veil-band { animation:hd-lift .9s cubic-bezier(.65,0,.35,1) .35s both; }
@keyframes hd-lift { to { transform:translateX(105%); } }
.hd-tag { position:absolute; left:8px; top:8px; font-family:var(--font); font-size:11px; font-weight:700;
  padding:3px 8px; border-radius:99px; background:rgba(0,0,0,.55); color:var(--ink); line-height:1.3; }
.hd-tag.sodium { background:var(--sodium); color:#000; }
.hd-tag.line { background:rgba(0,0,0,.55); box-shadow: inset 0 0 0 1px var(--sodium); color:var(--sodium); }

/* small square version, for lists and headers */
.hd-avatar { position:relative; overflow:hidden; flex-shrink:0; width:56px; height:56px; border-radius:12px;
  background:var(--t-bg); container-type:inline-size; }
.hd-avatar.sm { width:44px; height:44px; border-radius:10px; }
.hd-avatar .hd-veil-band { top:38%; height:26%; -webkit-backdrop-filter:blur(4px); backdrop-filter:blur(4px); }

/* ── Grid tiles ───────────────────────────────────────────────── */
.hd-tile { margin-bottom:4px; }
.hd-tile-name { font-family:var(--font); font-weight:700; font-size:15px; color:var(--ink); margin-top:8px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hd-tile-name span { color:var(--smoke); font-weight:500; margin-left:4px; }
.hd-tile-meta { font-family:var(--font); font-size:13px; color:var(--dim); margin-top:1px; display:flex; gap:10px;
  font-variant-numeric:tabular-nums; white-space:nowrap; overflow:hidden; }
.hd-tile-meta b { color:var(--ink); font-weight:600; }

/* The whole tile is the button: the real st.button sits on top of it, invisible */
div[class*="st-key-grow_"] div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:10px !important; }
div[class*="st-key-grow_"] div[data-testid="stColumn"] { min-width:0 !important; flex:1 1 0 !important;
  width:auto !important; position:relative; }
div[class*="st-key-grow_"] div[data-testid="stColumn"] div[data-testid="stElementContainer"]:has(.stButton) {
  position:absolute !important; inset:0; margin:0 !important; z-index:2; }
div[class*="st-key-grow_"] .stButton, div[class*="st-key-grow_"] .stButton button {
  width:100% !important; height:100% !important; }
div[class*="st-key-grow_"] .stButton button { background:transparent !important; border:0 !important;
  color:transparent !important; border-radius:var(--radius) !important; }
div[class*="st-key-grow_"] .stButton button * { color:transparent !important; }
div[class*="st-key-grow_"] .stButton button:focus-visible { outline:2px solid var(--sodium) !important; }
div[class*="st-key-grow_"] { margin-bottom:12px; }

/* ── Chips: words, not emoji ──────────────────────────────────── */
.hd-chips { display:flex; flex-wrap:wrap; gap:6px; margin:14px 0 4px; }
.hd-chip { font-family:var(--font); font-size:13px; font-weight:500; padding:5px 11px; border-radius:99px;
  border:1px solid var(--line); color:var(--ink); white-space:nowrap; line-height:1.3; }
.hd-chip.sodium { background:var(--sodium); border-color:var(--sodium); color:#000; font-weight:600; }
.hd-chip.bulb { border-color:rgba(232,67,90,.55); color:#ff8a98; }
.hd-chip.quiet { color:var(--smoke); }

/* ── Person header (profile view, requests) ───────────────────── */
.hd-who { display:flex; align-items:baseline; gap:8px; margin-top:14px; min-width:0; }
.hd-who .hd-title { margin:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
.hd-who .age { font-family:var(--font); font-size:22px; font-weight:500; color:var(--smoke); flex-shrink:0; }
.hd-meta { display:flex; flex-wrap:wrap; gap:4px 14px; font-family:var(--font); font-size:14px; color:var(--smoke);
  margin-top:4px; font-variant-numeric:tabular-nums; }
.hd-meta b, .hd-num b { color:var(--ink); font-weight:600; }
.hd-bio { font-family:var(--font); font-style:italic; font-size:17px; line-height:1.45; color:var(--ink); margin:16px 0 0; }
.hd-why { margin-top:18px; padding-top:14px; border-top:1px solid var(--line); }
.hd-why h4 { font-family:var(--font); font-size:13px; font-weight:600; color:var(--dim); margin:0 0 6px; }
.hd-why div { font-family:var(--font); font-size:15px; color:var(--ink); padding:3px 0; line-height:1.4; }

/* A note someone wrote you (requests, posts) */
.hd-post-quote { margin:12px 0 4px; padding:2px 0 2px 14px; border-left:2px solid var(--sodium);
  font-family:var(--font); font-size:16px; color:var(--ink); line-height:1.45; }
.hd-post-quote .hd-kicker { display:block; margin-bottom:2px; }

/* Rows separated by hairlines instead of boxed cards */
.hd-row { display:flex; align-items:center; gap:14px; padding:6px 0; min-width:0; }
.hd-row .hd-title { font-size:20px; font-stretch:112%; margin:0; }
.hd-rule { height:1px; background:var(--line); margin:4px 0; }
.hd-panel { background:var(--card); border-radius:var(--radius); padding:18px; }
.hd-panel.hot { box-shadow: inset 0 0 0 1px var(--sodium); }

/* Chat */
.hd-bubble { max-width:80%; padding:9px 13px; border-radius:18px; margin:3px 0;
  font-family:var(--font); font-size:15px; line-height:1.4; word-wrap:break-word; }
.hd-bubble.me   { margin-left:auto; background:var(--sodium); color:#000; border-bottom-right-radius:5px; }
.hd-bubble.them { margin-right:auto; background:var(--raised); color:var(--ink); border-bottom-left-radius:5px; }
.hd-bubble small { display:block; font-size:11px; opacity:.6; margin-top:2px; font-variant-numeric:tabular-nums; }

.hd-dots span { display:inline-block; width:6px; height:6px; margin:0 2px; border-radius:50%;
  background:var(--smoke); animation:hd-dot 1.4s infinite ease-in-out; }
.hd-dots span:nth-child(2){animation-delay:.2s} .hd-dots span:nth-child(3){animation-delay:.4s}
@keyframes hd-dot { 0%,80%,100%{opacity:.2} 40%{opacity:1} }

/* Side-by-side button rows that stay side by side on phones */
div.st-key-swipe div[data-testid="stHorizontalBlock"],
div[class*="st-key-mrow_"] div[data-testid="stHorizontalBlock"],
div[class*="st-key-qrow_"] div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:8px !important; }
div[class*="st-key-qrow_"] div[data-testid="stColumn"] { min-width:0 !important; }
div[class*="st-key-qrow_"] div[data-testid="stColumn"]:last-child { flex:0 0 52px !important; }
div[class*="st-key-mrow_"] div[data-testid="stColumn"] { min-width:0 !important; }

/* Slim quiz nudge row on Discover */
div.st-key-qnudge { border-top:1px solid var(--line); border-bottom:1px solid var(--line);
  padding:10px 0 !important; margin:4px 0 14px; }
div.st-key-qnudge div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:10px !important; }
div.st-key-qnudge div[data-testid="stColumn"] { min-width:0 !important; }
div.st-key-qnudge div[data-testid="stColumn"]:last-child { flex:0 0 112px !important; }

/* Top nav: segmented control as one quiet track */
div.st-key-nav, div.st-key-nav div[data-testid="stButtonGroup"] { width:100% !important; }
div.st-key-nav div[data-testid="stButtonGroup"] > div {
  display:flex !important; flex-wrap:nowrap !important; width:100% !important; gap:2px;
  background:var(--card); border-radius:99px; padding:3px; }
div.st-key-nav div[data-testid="stButtonGroup"] button {
  flex:1 1 0 !important; min-width:0 !important; min-height:38px !important; padding:6px 4px !important;
  font-size:14px !important; font-weight:600 !important; border-radius:99px !important; white-space:nowrap !important;
  background:transparent !important; color:var(--smoke) !important; border:0 !important; box-shadow:none !important; }
div.st-key-nav div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
div.st-key-nav div[data-testid="stButtonGroup"] button[aria-checked="true"] {
  background:var(--ink) !important; color:#000 !important; border:0 !important; }
div.st-key-nav button p { overflow:hidden; text-overflow:ellipsis; color:inherit !important; font-weight:600 !important; }
div.st-key-nav div[data-testid="stButtonGroup"] button[aria-checked="true"] * { color:#000 !important; }

/* Other segmented controls (Discover views, form choices): selected = lit, not amber */
div[data-testid="stButtonGroup"] button { font-weight:600 !important; background:transparent !important;
  color:var(--smoke) !important; border-color:var(--line) !important; }
div[data-testid="stButtonGroup"] button * { color:inherit !important; }
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
div[data-testid="stButtonGroup"] button[aria-checked="true"] {
  background:var(--raised) !important; color:var(--ink) !important; border-color:var(--smoke) !important; }

/* Tertiary buttons read as quiet text links */
.stButton button[kind="tertiary"] {
  background:transparent !important; border:0 !important; box-shadow:none !important; min-height:0 !important;
  color:var(--sodium) !important; font-size:15px !important; font-weight:600 !important; padding:4px 0 !important; }
.stButton button[kind="tertiary"] * { color:var(--sodium) !important; }
.stButton button[kind="tertiary"]:hover { text-decoration:underline; }

/* Discover: the quiet report link sits under the card */
div.st-key-disc_report .stButton button[kind="tertiary"],
div.st-key-disc_report .stButton button[kind="tertiary"] * { color:var(--dim) !important; font-size:14px !important;
  font-weight:500 !important; }

.hd-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }

/* Tabs (Me): the lit tab is ink, like the nav, not amber */
div[data-baseweb="tab-highlight"] { background:var(--ink) !important; }
button[role="tab"] p { font-weight:600 !important; color:var(--smoke) !important; }
button[role="tab"][aria-selected="true"] p { color:var(--ink) !important; }
</style>
"""

# Deep night colours for the veils: (field, letter)
_TINTS = [
    ("#3e121b", "#b8475a"),   # oxblood
    ("#12301f", "#4e9c6d"),   # bottle green
    ("#1c1d4a", "#6a6fd0"),   # indigo
    ("#3a220c", "#c07a35"),   # rum
    ("#33143a", "#a65bb5"),   # plum
    ("#0b3133", "#3e9ea2"),   # deep teal
]


def esc(v) -> str:
    return escape("" if v is None else str(v))


def inject_app_css():
    """Call once per run, from app.main()."""
    st.html(_APP_CSS)


def _tint(uid) -> str:
    bg, fg = _TINTS[int(uid or 0) % len(_TINTS)]
    return f"--t-bg:{bg};--t-fg:{fg};"


def _initial(name: str) -> str:
    return esc((name or "?").strip()[:1].lower() or "?")


def veil(name: str, uid: int = 0, *, lifted: bool = False, lifting: bool = False, hot: bool = False,
         tag: str = "", tag_kind: str = "", wide: bool = False) -> str:
    """A person's tile: their initial, huge, behind a tint band. The band lifts once you're linked."""
    cls = f"hd-veil a{int(uid or 0) % 3}" + (" wide" if wide else "") + (" lifted" if lifted else "") \
        + (" lifting" if lifting else "")
    tag_html = f'<span class="hd-tag {tag_kind}">{esc(tag)}</span>' if tag else ""
    return (f'<div class="{cls}" style="{_tint(uid)}" aria-hidden="true">'
            f'<span class="hd-veil-l">{_initial(name)}</span><i class="hd-veil-band"></i>{tag_html}</div>')


def avatar(name: str, uid: int = 0, small: bool = False, lifted: bool = False, lifting: bool = False) -> str:
    cls = "hd-avatar" + (" sm" if small else "") + (" lifted" if lifted else "") + (" lifting" if lifting else "")
    return (f'<div class="{cls}" style="{_tint(uid)}" aria-hidden="true">'
            f'<span class="hd-veil-l">{_initial(name)}</span><i class="hd-veil-band"></i></div>')


def wordmark(xl: bool = False) -> str:
    return f'<div class="hd-brand{" xl" if xl else ""}" role="img" aria-label="Hidden">hidden</div>'


def header(kicker: str, title: str, sub: str = ""):
    """Page title. `kicker` is kept for old callers but no longer shown."""
    st.html(f'<div style="margin:2px 0 14px;"><div class="hd-title">{esc(title)}</div>'
            + (f'<div class="hd-sub">{esc(sub)}</div>' if sub else "") + "</div>")


def section(title: str, count: int | None = None):
    st.html(f'<div class="hd-h3">{esc(title)}{f"<b>{int(count)}</b>" if count else ""}</div>')


def empty_state(icon: str, title: str, sub: str = ""):
    """`icon` is kept for old callers but no longer shown."""
    st.html(f'<div style="padding:28px 0 18px;">'
            f'<div class="hd-title" style="font-size:24px;">{esc(title)}</div>'
            f'<div class="hd-sub">{esc(sub)}</div></div>')


def waiting(text: str):
    st.html(f'<div style="padding:28px 0;">'
            f'<div class="hd-dots" style="margin-bottom:10px;"><span></span><span></span><span></span></div>'
            f'<div class="hd-sub">{esc(text)}</div></div>')


def intent_chips(intents) -> str:
    return "".join(f'<span class="hd-chip">{esc(INTENTS[i])}</span>' for i in intents if i in INTENTS)


def setup_chips(profile: dict, free_tonight: bool = False) -> str:
    """Free tonight / single-couple-open / host-travel chips."""
    out = []
    if free_tonight:
        out.append('<span class="hd-chip sodium">Free tonight</span>')
    if profile.get("status") in STATUSES:
        out.append(f'<span class="hd-chip">{esc(STATUSES[profile["status"]])}</span>')
    if profile.get("hosting") in HOSTING:
        out.append(f'<span class="hd-chip">{esc(HOSTING[profile["hosting"]])}</span>')
    return "".join(out)


def lifestyle_chips(profile: dict) -> str:
    out = []
    for key, (label, opts) in LIFESTYLE.items():
        v = profile.get(key)
        if v is None:
            continue
        out.append(f'<span class="hd-chip quiet">{esc(label)}: {esc(opts[int(v)].lower())}</span>')
    return "".join(out)


def score_ring(score: int) -> str:
    """Heat as plain words. (Was a ring; the name stays for old callers.)"""
    return f'<span class="hd-num"><b>{int(score)}%</b> heat</span>'


def open_quiz(return_to: str):
    """Jump to the full-screen quiz; its exit button brings you back here."""
    st.session_state._quiz_return = return_to
    st.session_state.tab = "quiz"
    st.rerun()


def invite_link() -> str:
    from config import APP_URL
    return APP_URL
