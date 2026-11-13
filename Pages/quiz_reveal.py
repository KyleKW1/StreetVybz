"""
Pages/quiz_reveal.py — Showing Read Between The Lines results to other people.

Two places use it:
  • a match page: both people see each other's result, freak score (openness %),
    quiz match % and the hidden desires they BOTH said yes to — never the rest;
  • drop codes (Me › Quiz): share a code with anyone; they see the same, except
    hidden desires are only counted, never named.

A match only sees results saved once the quiz said so (older ones stay private), and each
side is pinned to the result it had when both first had one (see social_db.match_quiz_pair).

Plus the screenshot deterrents for pages that show this: a watermark with the
viewer's username, blur when the app loses focus, and no copying.
"""

from html import escape as _xml_escape
from urllib.parse import quote

import streamlit as st

import social_db
from matching import DESIRE_LABELS, quiz_match, shared_desires
from ui import esc, open_quiz


def result_icon(name: str) -> str:
    try:
        from Pages.what_would_you_do import RESULT_TYPES
        return next((r["icon"] for r in RESULT_TYPES if r["name"] == name), "🎯")
    except Exception:
        return "🎯"


def summary_from_row(result_name, openness, dim_scores) -> dict | None:
    """Same shape as social_db.load_quiz_summaries(), from a raw quiz_results row."""
    if not result_name and openness is None:
        return None
    dims = dim_scores if isinstance(dim_scores, dict) else {}
    raw = dims.get("hd_signals") or ""
    signals = [] if raw in ("", "none") else [s.split(":")[0].strip() for s in raw.split(",") if s.strip()]
    return {"result": result_name, "openness": openness, "signals": signals,
            "categories": dims.get("selected") or []}


def _tile(label: str, q: dict) -> str:
    return (f'<div class="hd-qz-tile"><div class="hd-kicker">{esc(label)}</div>'
            f'<div class="hd-qz-name">{result_icon(q.get("result"))} {esc(q.get("result") or "—")}</div>'
            f'<div class="hd-qz-freak">Freak score <b>{int(q.get("openness") or 0)}%</b></div></div>')


_CSS = """
<style>
.hd-qz { background:linear-gradient(160deg,#1c1c24 0%,#131318 100%); border:1px solid rgba(255,45,120,.35);
  border-radius:18px; padding:16px; margin:0 0 16px; }
.hd-qz-row { display:flex; gap:10px; }
.hd-qz-tile { flex:1; min-width:0; background:#111116; border:1px solid var(--border); border-radius:12px; padding:10px 12px; }
.hd-qz-name { font-family:'Bebas Neue',sans-serif; font-size:21px; letter-spacing:1px; color:var(--text);
  line-height:1.1; margin-top:4px; }
.hd-qz-freak { font-family:'Space Mono',monospace; font-size:10px; color:var(--amber); margin-top:4px; }
.hd-qz-freak b { font-size:13px; }
.hd-qz-match { display:flex; align-items:baseline; justify-content:center; gap:8px; margin:12px 0 6px; }
.hd-qz-match b { font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--lime); line-height:1; }
</style>
"""


def comparison_html(me_label: str, mq: dict, them_label: str, tq: dict, name_desires: bool) -> str:
    """Two result tiles, the quiz match %, and shared hidden desires (named or just counted)."""
    pct = quiz_match(mq, tq)
    shared = shared_desires(mq, tq)
    if name_desires:
        chips = "".join(f'<span class="hd-chip magenta">🔥 {esc(DESIRE_LABELS[s])}</span>' for s in shared)
        desires = (f'<div class="hd-kicker" style="margin-top:10px;">Hidden desires you share</div>'
                   f'<div class="hd-chips" style="margin:6px 0 0;">{chips}</div>' if shared else
                   '<div class="hd-sub" style="margin-top:8px;text-align:center;">No hidden desires in common yet.</div>')
    else:
        n = len(shared)
        desires = (f'<div class="hd-sub" style="margin-top:8px;text-align:center;">'
                   f'🔥 {n} hidden desire{"s" if n != 1 else ""} in common</div>')
    match = (f'<div class="hd-qz-match"><b>{pct}%</b><span class="hd-kicker">quiz match</span></div>'
             if pct is not None else "")
    return (_CSS + f'<div class="hd-qz"><div class="hd-kicker" style="margin-bottom:8px;">Read Between The Lines</div>'
            f'<div class="hd-qz-row">{_tile(me_label, mq)}{_tile(them_label, tq)}</div>{match}{desires}</div>')


# Someone who said yes to nearly every hidden desire only sees how many they share with
# a match, so answering yes to everything can't be used to read the other person's list.
MAX_NAMED_DESIRES = 7    # of the 10 statements


def match_quiz_card(uid: int, other_id: int, other_name: str, matched_at, key: str):
    """On a match page: reveal both results once BOTH have one saved as shown to matches."""
    mq, tq, mine_private = social_db.match_quiz_pair(uid, other_id, matched_at)
    if mq and tq:
        st.html(comparison_html("You", mq, other_name, tq,
                                name_desires=len(mq.get("signals") or []) <= MAX_NAMED_DESIRES))
        return
    them = esc(other_name)
    if mine_private:
        text = ("Your result is from before quiz results were shown to matches, so it stays private. "
                f"Retake the quiz to share it with {them}.")
    elif not mq:
        text = (f"{them} took the quiz. Take it and you'll both see each other's result, "
                "freak score and the hidden desires you share." if tq else
                "Take the quiz and once they do too, you'll both see each other's result, "
                "freak score and the hidden desires you share.")
    else:
        text = (f"{them} hasn't shared a quiz result yet. When they do, you'll both see each "
                "other's result, freak score and the hidden desires you share.")
    with st.container(key=f"qzn_{key}"):
        c1, c2 = st.columns([3, 1.3], vertical_alignment="center")
        with c1:
            st.html(f'<div class="hd-sub" style="line-height:1.4;"><b style="color:var(--text);">🎯 Quiz match'
                    f'</b><br>{text}</div>')
        with c2:
            if not mq and st.button("Retake quiz" if mine_private else "Take quiz", key=f"qz_take_{key}",
                                    use_container_width=True):
                open_quiz("matches")


# ─── DROP CODES ──────────────────────────────────────────────────────────────

def _drops(uid: int) -> dict:
    """This user's drop-code state; thrown away if another account logs in on the same tab."""
    s = st.session_state.get("hd_drop")
    if not s or s.get("uid") != uid:
        s = st.session_state.hd_drop = {"uid": uid, "mine": None, "view": None}
    return s


def _use_code(uid: int, code: str) -> str | None:
    """On Compare: attach my latest result to an open code that isn't mine. Returns an error, or None."""
    import database as db
    drop = db.get_compat_drop(code)
    if not drop or not drop.get("is_live"):
        return "That code doesn't exist or has expired."
    if uid in (drop.get("creator_id"), drop.get("partner_id")):
        return None
    if drop.get("status") != "open":
        return "That code has already been used by someone else."
    latest = db.load_latest_rbtl_result(uid)
    if not (latest and latest.get("id")):
        return "Take the quiz first, then enter the code to compare."
    if not db.link_compat_drop(code, uid, latest["id"]):
        return "Someone else just used that code."
    return None


def _drop_view(uid: int, code: str):
    """Both results for a code — only for the person who made it and the one who used it."""
    import database as db
    drop = db.get_compat_drop(code)
    if not drop or not drop.get("is_live"):
        st.error("That code has expired.")
        return
    if drop.get("creator_id") == uid:
        if not drop.get("partner_id"):
            st.info("Nobody has used your code yet.")
            return
        me_side, them_side = "creator", "partner"
    elif drop.get("partner_id") == uid:
        me_side, them_side = "partner", "creator"
    else:
        return
    mq = summary_from_row(drop.get(f"{me_side}_result_name"), drop.get(f"{me_side}_openness_pct"),
                          drop.get(f"{me_side}_dim_scores"))
    tq = summary_from_row(drop.get(f"{them_side}_result_name"), drop.get(f"{them_side}_openness_pct"),
                          drop.get(f"{them_side}_dim_scores"))
    if not (mq and tq):
        st.error("Couldn't load both results — try again.")
        return
    st.html(comparison_html("You", mq, "Them", tq, name_desires=False))


def drop_codes_section(uid: int):
    """Me › Quiz: get your own code, or enter someone else's."""
    import database as db
    s = _drops(uid)
    st.html('<div class="hd-kicker" style="margin:22px 0 4px;">Compare with anyone</div>'
            '<div class="hd-sub" style="margin-bottom:10px;">Share a code and whoever enters it sees both results, '
            'both freak scores and how many hidden desires you share. Never which ones. Entering someone '
            'else\'s code shows them yours too.</div>')

    mine = db.get_compat_drop(s["mine"]) if s["mine"] else None
    if s["mine"] and not (mine and mine.get("is_live")):
        s["mine"] = mine = None
    if mine:
        used = bool(mine.get("partner_id"))
        st.html(f'<div class="hd-card" style="text-align:center;padding:16px;"><div class="hd-kicker">Your code · '
                f'{"used" if used else "valid 7 days"}</div><div class="hd-brand" '
                f'style="font-size:40px;letter-spacing:8px;">{esc(s["mine"])}</div></div>')
        if st.button("See who used it", use_container_width=True, key="drop_mine"):
            s["view"] = s["mine"]
    if (not mine or mine.get("partner_id")) and st.button(
            "◈ Get a new code" if mine else "◈ Get my code", use_container_width=True, key="drop_new"):
        latest = db.load_latest_rbtl_result(uid)
        new = db.create_compat_drop(uid, latest["id"]) if latest and latest.get("id") else None
        if new:
            s["mine"], s["view"] = new, None
            st.rerun()
        st.error("Couldn't make a code — try again.")

    with st.form("drop_enter", border=False, clear_on_submit=True):
        c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
        with c1:
            entered = st.text_input("Someone's code", max_chars=8, placeholder="6-character code",
                                    label_visibility="collapsed")
        with c2:
            go = st.form_submit_button("Compare", use_container_width=True)
    if go and entered.strip():
        code = entered.strip().upper()
        err = _use_code(uid, code)
        s["view"] = None if err else code
        if err:
            st.error(err)
    if s["view"]:
        _drop_view(uid, s["view"])


# ─── SCREENSHOT DETERRENTS ───────────────────────────────────────────────────

def screenshot_shield(viewer: str):
    """A website can't block screenshots, so make them less useful on this page:
    a faint watermark with the viewer's username (a leak shows who took it), blur
    while the app isn't focused (app switcher, window switching), and no copying."""
    label = _xml_escape((viewer or "hidden")[:32]) + " · HIDDEN"
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='260' height='150'>"
           "<text x='10' y='90' transform='rotate(-24 130 75)' fill='white' fill-opacity='0.07' "
           "font-family='monospace' font-size='15' font-weight='700'>" + label + "</text></svg>")
    st.html(
        '<style>'
        '.hd-shield { position:fixed; inset:0; pointer-events:none; z-index:999990; '
        f'background-image:url("data:image/svg+xml,{quote(svg)}"); background-repeat:repeat; }}'
        'body.hd-away:has(.hd-shield) section.stMain { filter:blur(22px) !important; }'
        'section.stMain:has(.hd-shield) { -webkit-user-select:none; user-select:none; '
        '-webkit-touch-callout:none; }'
        'section.stMain:has(.hd-shield) :is(input, textarea) { -webkit-user-select:text; user-select:text; }'
        '</style><div class="hd-shield"></div>'
        '<script>(function(){'
        'if (window.__hdShield) return; window.__hdShield = true;'
        'var d = document, on = function(){ return !!d.querySelector(".hd-shield"); };'
        'var away = function(){ if (on()) d.body.classList.add("hd-away"); };'
        'var back = function(){ d.body.classList.remove("hd-away"); };'
        'window.addEventListener("blur", away); window.addEventListener("focus", back);'
        'd.addEventListener("visibilitychange", function(){ d.hidden ? away() : back(); });'
        '["copy","cut","contextmenu","dragstart"].forEach(function(t){'
        '  d.addEventListener(t, function(e){ if (on() && !/INPUT|TEXTAREA/.test((e.target||{}).tagName||"")) e.preventDefault(); }, true);'
        '});'
        '})();</script>',
        unsafe_allow_javascript=True,
    )
