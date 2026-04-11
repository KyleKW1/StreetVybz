"""
Pages/do_or_drink.py — Do or Drink: ViceVault Edition
AI generates personalised dares from each player's vice log + desire profile.
Host picks the vibe: Regular, Kinky, or Both.
Caribbean English throughout — no generic Western party game energy.

GENERATION LOGIC:
- All players have data       → each player gets fully personalised dares
- Some players have data      → players WITH data personalise the whole game;
                                players without data get dares shaped by the
                                group's combined profile (not generic fallback)
- No players have any data    → fully random generic dares for everyone
- OpenAI fails                → error is surfaced clearly on setup screen
"""

import streamlit as st
import json
import random
import time


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
section.main .block-container { padding-top:2rem !important; max-width:860px !important; }
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
  background:var(--lime) !important; color:#0a0a0b !important;
  border-color:var(--lime) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#d4ff1a !important; box-shadow:0 0 20px rgba(198,255,0,0.2) !important;
}
.stTextInput > div > div > input {
  background:var(--card) !important; border:1px solid var(--border) !important;
  border-radius:4px !important; color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important; font-size:14px !important;
}
.stTextInput label {
  font-family:'Space Mono',monospace !important; font-size:9px !important;
  letter-spacing:2px !important; text-transform:uppercase !important; color:var(--muted) !important;
}
@keyframes card-slam {
  0%   { opacity:0; transform: translateY(-30px) scale(0.9) rotate(-2deg); }
  60%  { transform: translateY(4px) scale(1.02) rotate(0.5deg); }
  100% { opacity:1; transform: translateY(0) scale(1) rotate(0deg); }
}
.dare-card { animation: card-slam 0.4s cubic-bezier(0.19,1,0.22,1) both; }
@keyframes spin-settle {
  0%   { opacity:0.3; letter-spacing:8px; }
  70%  { opacity:1; letter-spacing:4px; }
  100% { opacity:1; letter-spacing:3px; }
}
.player-reveal { animation: spin-settle 0.6s ease-out both; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")


# ─── DB WRAPPER ───────────────────────────────────────────────────────────────

def _db(fn, *args, default=None, **kwargs):
    try:
        import database as db
        f = getattr(db, fn, None)
        if f:
            return f(*args, **kwargs)
        return default
    except Exception:
        return default


# ─── SESSION HELPERS ──────────────────────────────────────────────────────────

def _me():
    u = st.session_state.get("user", {})
    return u.get("username", "You"), u.get("id")


def _player_vice_summary(user_id: int) -> dict:
    """Fetch vice log + desire profile from DB for any player."""
    try:
        import database as db
        import json as _json

        entries = db.load_vice_log(user_id)
        counts, details = {}, {}
        for e in entries:
            v = e["vice"]
            counts[v] = counts.get(v, 0) + 1
            if v not in details:
                details[v] = e.get("data", {})

        summary = {"counts": counts, "sample_details": details}

        conn = db.create_connection()
        if conn:
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    """SELECT profile_name, profile_meta, dim_scores
                       FROM quiz_results
                       WHERE user_id = %s AND quiz_type = 'read_between_lines'
                       ORDER BY completed_at DESC LIMIT 1""",
                    (user_id,)
                )
                row = cur.fetchone()
                cur.close()
                if row:
                    dim_scores = row.get("dim_scores")
                    if isinstance(dim_scores, str):
                        try:
                            dim_scores = _json.loads(dim_scores)
                        except Exception:
                            dim_scores = {}
                    summary["quiz"] = {
                        "profile_name": row.get("profile_name", ""),
                        "profile_meta": row.get("profile_meta", ""),
                        "dim_scores":   dim_scores or {},
                    }
            finally:
                conn.close()

        return summary
    except Exception:
        return {}


def _has_data(vice_summary: dict) -> bool:
    """True if a player has any logged vices or quiz results."""
    return bool(vice_summary.get("counts")) or bool(
        vice_summary.get("quiz", {}).get("profile_name")
    )


def _my_full_summary() -> dict:
    _, my_id = _me()
    return _player_vice_summary(my_id) if my_id else {}


# ─── GROUP PROFILE ────────────────────────────────────────────────────────────

def _build_group_profile(players: list) -> dict:
    """
    Merge all players who HAVE data into one combined group profile.
    Used so players without their own data still get dares shaped
    by the group's collective vibe — not a generic fallback.
    """
    combined_counts  = {}
    combined_details = {}
    quiz_profiles    = []

    for p in players:
        vs = p.get("vice_summary", {})
        if not _has_data(vs):
            continue
        for vk, cnt in vs.get("counts", {}).items():
            combined_counts[vk] = combined_counts.get(vk, 0) + cnt
            if vk not in combined_details:
                combined_details[vk] = vs.get("sample_details", {}).get(vk, {})
        quiz = vs.get("quiz", {})
        if quiz.get("profile_name"):
            quiz_profiles.append(quiz)

    group = {"counts": combined_counts, "sample_details": combined_details}
    if quiz_profiles:
        best = max(quiz_profiles, key=lambda q: len(q.get("dim_scores", {})))
        group["quiz"] = best
    return group


# ─── OPENAI CLIENT ────────────────────────────────────────────────────────────

def _get_openai_client():
    """Returns an OpenAI client or raises RuntimeError with a clear message."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package missing or too old. "
            "Add 'openai>=1.0.0' to requirements.txt and redeploy."
        )
    api_key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in Streamlit secrets. "
            "Add it under Settings → Secrets in Streamlit Cloud."
        )
    return OpenAI(api_key=api_key)


# ─── VICE LABELS ──────────────────────────────────────────────────────────────

_VICE_LABELS = {
    "weed":    "weed/smoking",
    "alcohol": "alcohol",
    "sex":     "unprotected sex",
    "other":   "other substances",
}


# ─── PROMPT HELPERS ───────────────────────────────────────────────────────────

def _profile_text(vice_summary: dict) -> str:
    """Convert a vice_summary into bullet-point profile text for the prompt."""
    counts  = vice_summary.get("counts", {})
    details = vice_summary.get("sample_details", {})
    quiz    = vice_summary.get("quiz", {})
    lines   = []

    for vk, cnt in counts.items():
        label = _VICE_LABELS.get(vk, vk)
        d     = details.get(vk, {})
        extra = ""
        if vk == "weed"    and d.get("method"):      extra = f", usually {d['method']}"
        elif vk == "alcohol" and d.get("drink_type"): extra = f", drinks {d['drink_type']}"
        elif vk == "sex"    and d.get("partner_type"):extra = f", partner type: {d['partner_type']}"
        elif vk == "other"  and d.get("substance"):   extra = f" ({d['substance']})"
        lines.append(f"- {label} ({cnt} sessions{extra})")

    if quiz.get("profile_name"):
        dim_scores = quiz.get("dim_scores", {})
        top_dims   = sorted(dim_scores.items(), key=lambda x: -float(x[1]))[:2]
        dim_str    = ", ".join(f"{d}: {v}%" for d, v in top_dims)
        lines.append(
            f"- Desire profile: {quiz['profile_name']} — "
            f"{quiz.get('profile_meta', '')} (top dims: {dim_str})"
        )

    return "\n".join(lines) if lines else ""


def _mode_line(mode: str) -> str:
    if mode == "regular":
        return "Regular mode — social, funny, mildly embarrassing. No explicit content. Caribbean lime vibes."
    if mode == "kinky":
        return "Kinky mode — adults only, explicit, bold. No sanitising, no euphemisms. Let dem sweat."
    return "Mixed mode — half social/funny, half adult/explicit. Caribbean energy."


def _dare_json_schema(mode: str) -> str:
    heat3 = "explicit/adult" if mode != "regular" else "maximum chaos"
    return f"""Return ONLY valid JSON — no markdown, no preamble.
[
  {{
    "type": "DO" or "TRUTH",
    "dare": "The dare or question.",
    "drink": "What they drink if they refuse — one short sentence.",
    "heat": 1
  }}
]
heat: 1=mild/funny  2=spicy/awkward  3={heat3}"""


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

def _prompt_personalised(player_name: str, vice_summary: dict, mode: str, n: int = 6) -> str:
    """Player HAS their own data — fully personalised."""
    profile = _profile_text(vice_summary)
    return f"""You write dare cards for ViceVault "Do or Drink" — a Caribbean party game (Jamaica/English Caribbean).
Tone: direct, funny, a little savage, real. Natural Caribbean cadence where it fits — not forced patois.

Player: {player_name}
Their personal profile (use for subtle personalisation — a nod, not a direct callout):
{profile}

{_mode_line(mode)}

Write exactly {n} dare cards. Each is a DO (action) or TRUTH (question said out loud).
Include a DRINK alternative if they refuse.

{_dare_json_schema(mode)}"""


def _prompt_group_shaped(player_name: str, group_profile: dict, mode: str, n: int = 6) -> str:
    """
    Player has NO personal data but the group does.
    Dares are written for this player but shaped by the group's collective vibe
    so the whole game feels coherent — not a random generic batch.
    """
    profile = _profile_text(group_profile)
    return f"""You write dare cards for ViceVault "Do or Drink" — a Caribbean party game (Jamaica/English Caribbean).
Tone: direct, funny, a little savage, real. Natural Caribbean cadence where it fits — not forced patois.

Player: {player_name}
This player has no personal data on file. The rest of their group has this combined profile.
Use it to match the energy and vibe of the game so {player_name}'s cards feel like they belong
to the same session — even though the dares aren't directly about their own history.

Group profile:
{profile}

{_mode_line(mode)}

Write exactly {n} dare cards for {player_name}. Each is a DO (action) or TRUTH (question said out loud).
Include a DRINK alternative if they refuse.

{_dare_json_schema(mode)}"""


def _prompt_generic(player_name: str, mode: str, n: int = 6) -> str:
    """Nobody in the game has any data — pure Caribbean party energy."""
    return f"""You write dare cards for ViceVault "Do or Drink" — a Caribbean party game (Jamaica/English Caribbean).
Tone: direct, funny, a little savage, real. Natural Caribbean cadence where it fits — not forced patois.

Player: {player_name}
No profile data for anyone in this game. Write sharp, funny, chaotic Caribbean party dares.

{_mode_line(mode)}

Write exactly {n} dare cards. Each is a DO (action) or TRUTH (question said out loud).
Include a DRINK alternative if they refuse.

{_dare_json_schema(mode)}"""


# ─── DARE GENERATION ──────────────────────────────────────────────────────────

def _parse_dares(raw: str) -> list:
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    dares = json.loads(raw)
    valid = []
    for d in dares:
        if isinstance(d, dict) and d.get("dare") and d.get("drink"):
            d.setdefault("type", "DO")
            d.setdefault("heat", 1)
            valid.append(d)
    return valid


def _generate_dares_for_player(
    player_name: str,
    vice_summary: dict,
    group_profile: dict,
    any_group_has_data: bool,
    mode: str,
    client,
) -> list:
    """
    Pick the right prompt strategy and call OpenAI.
    Errors are stored in session_state.dod_error so they surface on the
    setup screen after rerun instead of disappearing silently.
    """
    has_own = _has_data(vice_summary)

    if has_own:
        prompt   = _prompt_personalised(player_name, vice_summary, mode)
        strategy = "personalised"
    elif any_group_has_data:
        prompt   = _prompt_group_shaped(player_name, group_profile, mode)
        strategy = "group-shaped"
    else:
        prompt   = _prompt_generic(player_name, mode)
        strategy = "generic"

    try:
        resp  = client.chat.completions.create(
            model    = "gpt-4o-mini",
            messages = [{"role": "user", "content": prompt}],
            temperature = 0.9,
            max_tokens  = 1400,
        )
        dares = _parse_dares(resp.choices[0].message.content)
        if dares:
            return dares
        raise ValueError("Parsed 0 valid dares from response")
    except Exception as e:
        existing = st.session_state.get("dod_error", "")
        st.session_state.dod_error = (
            f"{existing}\n[{player_name} · {strategy}] {e}".strip()
        )
        return _fallback_dares(player_name, mode)


def _fallback_dares(player_name: str, mode: str) -> list:
    """Curated fallback dares — only used when the API call fails."""
    regular = [
        {"type": "DO",    "dare": f"Text the last person in your contacts and tell them {player_name} says hi — send it now, no editing.", "drink": "Two fingers if you mek excuses.", "heat": 1},
        {"type": "TRUTH", "dare": f"What's the most embarrassing thing {player_name} has done while under the influence? 30 seconds.", "drink": "Drink and stay quiet — same thing really.", "heat": 1},
        {"type": "DO",    "dare": "Do your best impression of the person to your left. They rate it. Under 5/10 means you drink anyway.", "drink": "Drink for being afraid of embarrassment.", "heat": 2},
        {"type": "TRUTH", "dare": "Who in this room would you call first if you were in real trouble? Say the name out loud.", "drink": "Drink and keep your secrets then.", "heat": 1},
        {"type": "DO",    "dare": "Set your phone screen brightness to max and show the last photo in your camera roll. No skipping.", "drink": "Drink and delete it, coward.", "heat": 2},
        {"type": "TRUTH", "dare": "On a scale of 1-10, how messy were you last weekend? The real number, not the polite one.", "drink": "Drink for lying to yourself.", "heat": 1},
    ]
    kinky = [
        {"type": "TRUTH", "dare": "Tell the group the last time you did something you said you wouldn't — and exactly why.", "drink": "Drink and pretend you're innocent.", "heat": 3},
        {"type": "DO",    "dare": "Send a voice note to your most recent contact saying 'I've been thinking about you.' Don't explain it.", "drink": "Drink if your heart rate just went up.", "heat": 3},
        {"type": "TRUTH", "dare": "What's one thing about your sex life you've never told anyone in this room? Say it.", "drink": "Take two drinks and keep living that double life.", "heat": 3},
        {"type": "DO",    "dare": "Let the person on your right set your Instagram status for 10 minutes. No veto.", "drink": "Drink if you're too scared of your own timeline.", "heat": 2},
    ]
    if mode == "regular":
        return random.sample(regular, min(6, len(regular)))
    elif mode == "kinky":
        pool = kinky + regular[:2]
        return random.sample(pool, min(6, len(pool)))
    pool = regular[:3] + kinky[:3]
    random.shuffle(pool)
    return pool


# ─── STATE MANAGEMENT ─────────────────────────────────────────────────────────

def _init():
    defaults = {
        "dod_phase":    "setup",
        "dod_mode":     "regular",
        "dod_players":  [],
        "dod_dares":    {},
        "dod_deck":     [],
        "dod_cur_card": None,
        "dod_scores":   {},
        "dod_history":  [],
        "dod_error":    "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset():
    for k in list(st.session_state.keys()):
        if k.startswith("dod_"):
            del st.session_state[k]
    _init()
    st.rerun()


# ─── SETUP PHASE ──────────────────────────────────────────────────────────────

def _render_setup():
    inject_css()
    my_name, my_id = _me()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Party Mode</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:56px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">DO OR<br><span style="color:var(--lime);">DRINK</span></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    AI reads your vault. Your habits become the dares. Yuh brave?
  </div>
</div>
""")

    # Surface any errors from the previous generation attempt
    if st.session_state.dod_error:
        st.error(st.session_state.dod_error)
        st.session_state.dod_error = ""

    # ── Mode selector ────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Choose the vibe</div>
""")
    mode = st.session_state.dod_mode
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍹  Regular", use_container_width=True,
                     type="primary" if mode == "regular" else "secondary", key="mode_reg"):
            st.session_state.dod_mode = "regular"; st.rerun()
    with c2:
        if st.button("🔥  Kinky", use_container_width=True,
                     type="primary" if mode == "kinky" else "secondary", key="mode_kink"):
            st.session_state.dod_mode = "kinky"; st.rerun()
    with c3:
        if st.button("⚡  Both", use_container_width=True,
                     type="primary" if mode == "both" else "secondary", key="mode_both"):
            st.session_state.dod_mode = "both"; st.rerun()

    mode_descs = {
        "regular": "Social dares. Mild embarrassment. Caribbean lime energy. Safe(ish) for family gatherings.",
        "kinky":   "Adult dares built from your actual vice data and desire profile. Explicit. Not for the faint-hearted.",
        "both":    "Half social, half adult. The AI decides which way it goes based on your profile.",
    }
    st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:20px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
    {mode_descs[st.session_state.dod_mode]}
  </div>
</div>
""")

    # ── Players ──────────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px; margin-top:4px;">Players</div>
""")

    players = st.session_state.dod_players
    me_already = any(p["username"] == my_name for p in players)

    if not me_already and my_id:
        players.append({
            "username":     my_name,
            "user_id":      my_id,
            "vice_summary": _my_full_summary(),
            "is_host":      True,
        })
        st.session_state.dod_players = players

    # Refresh summaries on every render
    for p in players:
        p["vice_summary"] = _player_vice_summary(p["user_id"]) if p.get("user_id") else {}

    for i, p in enumerate(players):
        col_name, col_remove = st.columns([5, 1])
        with col_name:
            host_badge = " · HOST" if p.get("is_host") else ""
            vs         = p.get("vice_summary", {})
            counts     = vs.get("counts", {})
            vice_parts = [f"{_VICE_LABELS.get(vk, vk)}: {cnt}" for vk, cnt in counts.items()]
            quiz       = vs.get("quiz", {})
            if quiz.get("profile_name"):
                vice_parts.append(f"profile: {quiz['profile_name']}")
            has_d      = _has_data(vs)
            vice_str   = "  ·  ".join(vice_parts) if vice_parts else "No data — will use group profile"
            data_color = "var(--lime)" if has_d else "var(--muted)"
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {'var(--lime)' if p.get('is_host') else 'var(--border)'};
            border-radius:3px; padding:12px 14px; margin-bottom:6px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px;
              color:{'var(--lime)' if p.get('is_host') else 'var(--text)'}; letter-spacing:1px;">
    {p['username']}{host_badge}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px;
              color:{data_color}; letter-spacing:1px; text-transform:uppercase;">{vice_str}</div>
</div>
""")
        with col_remove:
            if not p.get("is_host"):
                st.html("<div style='height:6px'></div>")
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.dod_players.pop(i)
                    st.rerun()

    st.html("<div style='height:6px'></div>")
    new_username = st.text_input(
        "Add player by username",
        placeholder="Their ViceVault username",
        key="dod_add_input",
    )
    if st.button("Add Player →", key="dod_add_btn"):
        uname = new_username.strip()
        if not uname:
            st.warning("Enter a username.")
        elif any(p["username"].lower() == uname.lower() for p in players):
            st.warning("Already in the game.")
        else:
            user = _db("get_user_by_username", uname)
            if not user:
                st.error(f"Can't find '{uname}' — they need a ViceVault account.")
            else:
                uid = user["id"]
                st.session_state.dod_players.append({
                    "username":     user["username"],
                    "user_id":      uid,
                    "vice_summary": _player_vice_summary(uid),
                    "is_host":      False,
                })
                st.rerun()

    st.html("<div style='height:20px'></div>")
    n_players = len(players)

    # ── Group data status banner ──────────────────────────────────────────────
    if players:
        any_has  = any(_has_data(p.get("vice_summary", {})) for p in players)
        all_have = all(_has_data(p.get("vice_summary", {})) for p in players)
        if all_have:
            status_msg   = "✓ All players have data — fully personalised dares for everyone."
            status_color = "var(--lime)"
        elif any_has:
            names = [p["username"] for p in players if _has_data(p.get("vice_summary", {}))]
            status_msg   = f"◈ {', '.join(names)} have data — personalising the whole game for everyone."
            status_color = "var(--amber)"
        else:
            status_msg   = "◇ No player data found — generating sharp generic Caribbean dares."
            status_color = "var(--muted)"
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
              text-transform:uppercase; color:{status_color};">{status_msg}</div>
</div>
""")

    if n_players < 2:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:center; padding:12px 0;">
  Add at least one more player to start.
</div>
""")
    else:
        if st.button(f"Generate Dares & Start →  ({n_players} players)", type="primary",
                     use_container_width=True, key="dod_start"):
            st.session_state.dod_phase = "generating"
            st.rerun()

    st.html("""
<div style="margin-top:16px; padding:12px 14px; background:var(--surface);
            border:1px solid var(--border); border-radius:3px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); line-height:1.9;">
    AI reads each player's logged sessions and desire profile.<br>
    Players without data are shaped by the group's combined vibe — the whole game stays personalised.
  </div>
</div>
""")


# ─── GENERATING PHASE ─────────────────────────────────────────────────────────

def _render_generating():
    inject_css()
    players = st.session_state.dod_players
    mode    = st.session_state.dod_mode

    ph_title = st.empty()
    ph_bar   = st.empty()
    ph_msg   = st.empty()

    # Fail loudly before touching anything if the API key is missing
    try:
        client = _get_openai_client()
    except RuntimeError as e:
        st.session_state.dod_error = str(e)
        st.session_state.dod_phase = "setup"
        st.rerun()
        return

    # Build group profile from players who have data
    any_has_data  = any(_has_data(p.get("vice_summary", {})) for p in players)
    group_profile = _build_group_profile(players) if any_has_data else {}

    all_dares = {}
    for i, p in enumerate(players):
        pct      = int((i / len(players)) * 90)
        has_d    = _has_data(p.get("vice_summary", {}))
        strategy = (
            "personalising"   if has_d else
            "using group profile" if any_has_data else
            "generating generic"
        )
        ph_title.markdown("**Building dare deck…**")
        ph_bar.progress(pct)
        ph_msg.caption(f"{p['username']} — {strategy}…")

        dares = _generate_dares_for_player(
            player_name        = p["username"],
            vice_summary       = p.get("vice_summary", {}),
            group_profile      = group_profile,
            any_group_has_data = any_has_data,
            mode               = mode,
            client             = client,
        )
        all_dares[p["username"]] = dares
        time.sleep(0.2)

    ph_bar.progress(100)
    ph_msg.caption("Shuffling the deck…")

    # Round-robin deck — one card per player per round before cycling
    max_dares = max((len(all_dares[p["username"]]) for p in players), default=0)
    deck = []
    for round_idx in range(max_dares):
        round_cards = []
        for p in players:
            if round_idx < len(all_dares[p["username"]]):
                round_cards.append({"player": p["username"], "dare_idx": round_idx})
        random.shuffle(round_cards)
        deck.extend(round_cards)

    st.session_state.dod_dares    = all_dares
    st.session_state.dod_deck     = deck
    st.session_state.dod_scores   = {p["username"]: {"drinks": 0, "done": 0} for p in players}
    st.session_state.dod_history  = []
    st.session_state.dod_cur_card = None
    st.session_state.dod_phase    = "game"
    st.rerun()


# ─── GAME PHASE ───────────────────────────────────────────────────────────────

_HEAT_LABELS = {1: "mild", 2: "spicy", 3: "atomic"}
_HEAT_COLORS = {1: "var(--lime)", 2: "var(--amber)", 3: "var(--magenta)"}
_TYPE_ICONS  = {"DO": "⚡", "TRUTH": "💬"}


def _render_game():
    inject_css()

    scores  = st.session_state.dod_scores
    deck    = st.session_state.dod_deck
    dares   = st.session_state.dod_dares
    history = st.session_state.dod_history
    cur     = st.session_state.dod_cur_card
    mode    = st.session_state.dod_mode

    total_cards = sum(len(v) for v in dares.values())
    played      = len(history)
    remaining   = len(deck)

    mode_colors = {"regular": "var(--lime)", "kinky": "var(--magenta)", "both": "var(--cyan)"}
    mode_label  = {"regular": "Regular", "kinky": "Kinky", "both": "Mixed"}

    st.html(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start;
            border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px;">
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
                letter-spacing:3px; line-height:1;">DO OR DRINK</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:{mode_colors.get(mode,'var(--lime)')};
                ">{mode_label.get(mode,'Regular')} mode · {remaining} cards left</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--muted);">
      {played}/{total_cards}
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                text-transform:uppercase; letter-spacing:1px;">played</div>
  </div>
</div>
""")

    # Scoreboard
    cols = st.columns(len(scores))
    for i, (uname, s) in enumerate(scores.items()):
        with cols[i]:
            is_active = cur and cur.get("player") == uname
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            {'border-top:2px solid var(--lime)' if is_active else 'border-top:2px solid var(--border)'};
            border-radius:3px; padding:12px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:15px; letter-spacing:1px;
              color:{'var(--lime)' if is_active else 'var(--text)'};">{uname}</div>
  <div style="display:flex; justify-content:center; gap:14px; margin-top:6px;">
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime);">{s['done']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">did it</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--magenta);">{s['drinks']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">drinks</div>
    </div>
  </div>
</div>
""")

    st.html("<div style='height:18px'></div>")

    # ── Current card or draw prompt ───────────────────────────────────────────
    if cur is None:
        if not deck:
            _render_game_over()
            return

        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:48px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">PULL A CARD</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Tap below to see who's up.
  </div>
</div>
""")
        if st.button("⚡  Draw Next Card", type="primary", use_container_width=True, key="draw_card"):
            if deck:
                card_ref = st.session_state.dod_deck.pop(0)
                player   = card_ref["player"]
                dare     = dares[player][card_ref["dare_idx"]]
                st.session_state.dod_cur_card = {"player": player, "dare": dare}
            st.rerun()

    else:
        player     = cur["player"]
        dare       = cur["dare"]
        heat       = dare.get("heat", 1)
        dtype      = dare.get("type", "DO")
        heat_color = _HEAT_COLORS.get(heat, "var(--lime)")
        heat_label = _HEAT_LABELS.get(heat, "mild")
        type_icon  = _TYPE_ICONS.get(dtype, "⚡")

        st.html(f"""
<div class="dare-card" style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {heat_color}; border-radius:4px; padding:28px 26px; margin-bottom:14px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div class="player-reveal" style="font-family:'Bebas Neue',sans-serif; font-size:32px;
                letter-spacing:3px; color:{heat_color}; line-height:1;">{player}</div>
    <div style="display:flex; gap:8px; align-items:center;">
      <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                  text-transform:uppercase; color:{heat_color}; border:1px solid {heat_color};
                  padding:3px 10px; border-radius:2px;">{dtype} {type_icon}</div>
      <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
                  text-transform:uppercase; color:{heat_color}; border:1px solid {heat_color};
                  padding:3px 10px; border-radius:2px; opacity:0.7;">{heat_label}</div>
    </div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:17px; color:var(--text);
              line-height:1.65; margin-bottom:20px;">{dare['dare']}</div>
  <div style="background:var(--surface); border-left:2px solid var(--magenta);
              padding:10px 14px; border-radius:0 3px 3px 0;">
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:4px;">OR DRINK</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">{dare['drink']}</div>
  </div>
</div>
""")

        col_done, col_drink, col_skip = st.columns([2, 2, 1])
        with col_done:
            if st.button("✓  Did it", type="primary", use_container_width=True, key="btn_done"):
                st.session_state.dod_scores[player]["done"] += 1
                st.session_state.dod_history.append({**cur, "result": "done"})
                st.session_state.dod_cur_card = None
                st.rerun()
        with col_drink:
            if st.button("🍹  Drinking", use_container_width=True, key="btn_drink"):
                st.session_state.dod_scores[player]["drinks"] += 1
                st.session_state.dod_history.append({**cur, "result": "drink"})
                st.session_state.dod_cur_card = None
                st.rerun()
        with col_skip:
            if st.button("Skip", use_container_width=True, key="btn_skip"):
                rem = len(st.session_state.dod_deck)
                insert_at = random.randint(max(1, rem // 2), max(1, rem))
                try:
                    dare_idx = dares[player].index(dare)
                except ValueError:
                    dare_idx = 0
                st.session_state.dod_deck.insert(insert_at, {"player": player, "dare_idx": dare_idx})
                if st.session_state.dod_deck:
                    nxt      = st.session_state.dod_deck.pop(0)
                    np_name  = nxt["player"]
                    np_dare  = dares[np_name][nxt["dare_idx"]]
                    st.session_state.dod_cur_card = {"player": np_name, "dare": np_dare}
                else:
                    st.session_state.dod_cur_card = None
                st.rerun()

    # Recent history
    if history:
        st.html("<div style='height:20px'></div>")
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Recent</div>
""")
        for h in reversed(history[-4:]):
            p      = h["player"]
            d      = h["dare"]["dare"][:80] + ("…" if len(h["dare"]["dare"]) > 80 else "")
            result = h.get("result", "done")
            r_icon = "✓" if result == "done" else "🍹"
            r_col  = "var(--lime)" if result == "done" else "var(--magenta)"
            st.html(f"""
<div style="display:flex; gap:10px; align-items:flex-start; padding:8px 0;
            border-bottom:1px solid var(--border);">
  <div style="font-family:'Space Mono',monospace; font-size:14px; color:{r_col}; flex-shrink:0;">{r_icon}</div>
  <div>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft);
                 letter-spacing:1px; text-transform:uppercase;">{p}</span>
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
                line-height:1.5;">{d}</div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    if st.button("End Game", use_container_width=True, key="end_game"):
        st.session_state.dod_phase = "gameover"
        st.rerun()


# ─── GAME OVER ────────────────────────────────────────────────────────────────

def _render_game_over():
    inject_css()
    scores  = st.session_state.dod_scores
    history = st.session_state.dod_history

    winner  = max(scores, key=lambda u: scores[u]["done"]) if scores else "—"
    drinker = max(scores, key=lambda u: scores[u]["drinks"]) if scores else "—"

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--lime); border-radius:4px;
            padding:32px 28px; text-align:center; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Game Over</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--lime);
              letter-spacing:3px; line-height:0.9; margin-bottom:8px;">{winner.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--soft);">
    held it down the most — {scores.get(winner, {}).get('done', 0)} dares completed
  </div>
  {'<div style="margin-top:12px;font-family:\'DM Sans\',sans-serif;font-size:12px;color:var(--magenta);">🍹 ' + drinker + ' drank the most — ' + str(scores.get(drinker,{}).get("drinks",0)) + ' times</div>' if winner != drinker else ''}
</div>
""")

    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Final Standings</div>
""")
    for rank, (uname, s) in enumerate(
        sorted(scores.items(), key=lambda x: x[1]["done"], reverse=True), 1
    ):
        rank_color = ["var(--lime)", "var(--amber)", "var(--cyan)"][min(rank - 1, 2)]
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {rank_color}; border-radius:3px;
            padding:14px 18px; margin-bottom:8px;
            display:flex; justify-content:space-between; align-items:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px;
              color:{rank_color}; letter-spacing:1px; line-height:1;">#{rank}  {uname}</div>
  <div style="display:flex; gap:20px; text-align:center;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--lime);">{s['done']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase;">did it</div>
    </div>
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--magenta);">{s['drinks']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase;">drinks</div>
    </div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Play Again", use_container_width=True, type="primary"):
            for k in ["dod_dares", "dod_deck", "dod_cur_card", "dod_scores", "dod_history"]:
                st.session_state.pop(k, None)
            st.session_state.dod_phase = "generating"
            st.rerun()
    with col2:
        if st.button("New Game", use_container_width=True):
            _reset()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def do_or_drink_page():
    _init()
    phase = st.session_state.dod_phase

    if phase == "setup":
        _render_setup()
    elif phase == "generating":
        inject_css()
        st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">BUILDING DECK</div>
</div>
""")
        _render_generating()
    elif phase == "game":
        _render_game()
    elif phase == "gameover":
        inject_css()
        st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">DO OR <span style="color:var(--lime);">DRINK</span></div>
</div>
""")
        _render_game_over()
