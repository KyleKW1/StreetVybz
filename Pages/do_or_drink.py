"""
Pages/do_or_drink.py — Do or Drink: ViceVault Edition
AI generates personalized dares from each player's vice log + confession profile.
Host picks the vibe: Regular, Kinky, or Both.
Caribbean English throughout — no generic Western party game energy.
"""

import streamlit as st
import json
import random
import time
from datetime import datetime


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

/* ── Card flip animation ── */
@keyframes card-slam {
  0%   { opacity:0; transform: translateY(-30px) scale(0.9) rotate(-2deg); }
  60%  { transform: translateY(4px) scale(1.02) rotate(0.5deg); }
  100% { opacity:1; transform: translateY(0) scale(1) rotate(0deg); }
}
.dare-card { animation: card-slam 0.4s cubic-bezier(0.19,1,0.22,1) both; }

/* ── Spin animation for player picker ── */
@keyframes spin-settle {
  0%   { opacity:0.3; letter-spacing:8px; }
  70%  { opacity:1; letter-spacing:4px; }
  100% { opacity:1; letter-spacing:3px; }
}
.player-reveal { animation: spin-settle 0.6s ease-out both; }

/* ── Pulse ring on active player ── */
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(198,255,0,0.5); }
  70%  { box-shadow: 0 0 0 14px rgba(198,255,0,0); }
  100% { box-shadow: 0 0 0 0 rgba(198,255,0,0); }
}
.active-player { animation: pulse-ring 1.5s ease-out 2; }

/* ── Drink flash ── */
@keyframes drink-flash {
  0%   { background: rgba(255,45,120,0.3); }
  100% { background: var(--card); }
}
.drink-flash { animation: drink-flash 0.6s ease-out; }

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


def _my_vice_summary() -> dict:
    """Summarise the current user's vice log into a compact profile dict."""
    log = st.session_state.get("vice_log", [])
    if not log:
        return {}
    counts = {}
    details = {}
    for e in log:
        v = e["vice"]
        counts[v] = counts.get(v, 0) + 1
        data = e.get("data", {})
        if v not in details:
            details[v] = data
    return {"counts": counts, "sample_details": details}


def _player_vice_summary(user_id: int) -> dict:
    """Fetch vice summary from DB for any player."""
    try:
        import database as db
        entries = db.load_vice_log(user_id)
        if not entries:
            return {}
        counts = {}
        details = {}
        for e in entries:
            v = e["vice"]
            counts[v] = counts.get(v, 0) + 1
            if v not in details:
                details[v] = e.get("data", {})
        return {"counts": counts, "sample_details": details}
    except Exception:
        return {}


# ─── AI DARE GENERATOR ────────────────────────────────────────────────────────

_VICE_LABELS = {
    "weed":    "weed/smoking",
    "alcohol": "alcohol",
    "sex":     "unprotected sex",
    "other":   "other substances",
}

def _build_dare_prompt(player_name: str, vice_summary: dict, mode: str, n: int = 6) -> str:
    counts = vice_summary.get("counts", {})
    details = vice_summary.get("sample_details", {})

    vice_lines = []
    for vk, cnt in counts.items():
        label = _VICE_LABELS.get(vk, vk)
        extra = ""
        d = details.get(vk, {})
        if vk == "weed" and d.get("method"):
            extra = f" (usually {d['method']}, intensity {d.get('intensity','?')}/10)"
        elif vk == "alcohol" and d.get("drink_type"):
            extra = f" (prefers {d['drink_type']}, ~{d.get('drinks','?')} drinks/session)"
        elif vk == "sex" and d.get("partner_type"):
            extra = f" (partner: {d['partner_type']}, regret level {d.get('regret','?')}/10)"
        elif vk == "other" and d.get("substance"):
            extra = f" ({d['substance']})"
        vice_lines.append(f"  - {label}: {cnt} logged sessions{extra}")

    vice_str = "\n".join(vice_lines) if vice_lines else "  - No logged sessions yet (new to the vault)"

    if mode == "regular":
        mode_instruction = """MODE: Regular — keep it social, funny, mildly embarrassing. 
No explicit sexual content. Think Caribbean lime vibes — roast them gently, make them do something awkward, 
reveal something mild about their habits. Energy: chaotic good."""
    elif mode == "kinky":
        mode_instruction = """MODE: Kinky — adults-only dares and truth questions. Explicit, bold, 
sexual themes are fair game. Use their vice data to construct intimate dares (e.g. if they log unprotected sex a lot, 
go there). Caribbean directness — no sanitising, no euphemisms. Energy: let dem sweat."""
    else:  # both
        mode_instruction = """MODE: Mixed — alternate between social/funny dares and bold adult ones. 
Roughly half regular, half kinky. Let the vice data guide which direction each dare goes. 
Caribbean energy — some make them laugh, some make them blush."""

    return f"""You write dare cards for ViceVault's "Do or Drink" game. 
This is a Caribbean party app (Jamaica/English Caribbean). The tone is direct, funny, a little savage, and real.

Player profile for {player_name}:
{vice_str}

{mode_instruction}

Write exactly {n} dare cards for {player_name}. Each dare must:
- Be SPECIFIC to their actual logged behaviour — reference their real habits, counts, or details
- Sound Caribbean / Jamaican English where natural (not forced patois, just that cadence and directness)
- Be a "DO" (physical/social action) OR a "TRUTH" (honest question they must answer out loud)
- Have a "DRINK" alternative — what they drink if they refuse
- Be 1-2 sentences max — punchy, not wordy

{f"For kinky dares: be explicit, reference their sex/vice data directly. Adults-only, no softening." if mode != "regular" else ""}

Return ONLY valid JSON. No markdown. No preamble.

[
  {{
    "type": "DO" or "TRUTH",
    "dare": "The dare or truth question text.",
    "drink": "What they drink if they refuse — 1 short sentence.",
    "heat": 1-3
  }}
]

heat: 1 = mild/funny, 2 = spicy/awkward, 3 = {'"explicit/adult"' if mode != "regular" else '"maximum chaos"'}
"""


def _generate_dares_for_player(player_name: str, vice_summary: dict, mode: str) -> list:
    """Call Anthropic API to generate dares. Falls back to curated defaults."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        prompt = _build_dare_prompt(player_name, vice_summary, mode, n=6)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        dares = json.loads(raw)
        # validate structure
        valid = []
        for d in dares:
            if isinstance(d, dict) and d.get("dare") and d.get("drink"):
                d.setdefault("type", "DO")
                d.setdefault("heat", 1)
                valid.append(d)
        return valid if valid else _fallback_dares(player_name, mode)
    except Exception:
        return _fallback_dares(player_name, mode)


def _fallback_dares(player_name: str, mode: str) -> list:
    """Curated fallback dares when API call fails."""
    regular = [
        {"type": "DO",    "dare": f"Text the last person in your contacts and tell them {player_name} says hi — send it now, no editing.", "drink": "Two fingers if you mek excuses.", "heat": 1},
        {"type": "TRUTH", "dare": f"What's the most embarrassing thing {player_name} has done while under the influence? You have 30 seconds.", "drink": "Drink and stay quiet — same thing really.", "heat": 1},
        {"type": "DO",    "dare": f"Do your best impression of the person to your left. They rate it. Under 5/10 means you drink anyway.", "drink": "Drink for being afraid of embarrassment.", "heat": 2},
        {"type": "TRUTH", "dare": "Who in this room would you call first if you were in real trouble? Say the name out loud.", "drink": "Drink and keep your secrets then.", "heat": 1},
        {"type": "DO",    "dare": "Set your phone screen brightness to max and show the last photo in your camera roll. No skipping.", "drink": "Drink and delete it, coward.", "heat": 2},
        {"type": "TRUTH", "dare": "On a scale of 1-10, how messy were you last weekend? Give the real number, not the polite one.", "drink": "Drink for lying to yourself.", "heat": 1},
    ]
    kinky = [
        {"type": "TRUTH", "dare": f"Tell the group the last time you did something you said you wouldn't — and exactly why you did it.", "drink": "Drink and pretend you're innocent.", "heat": 3},
        {"type": "DO",    "dare": "Send a voice note to your most recent contact saying 'I've been thinking about you.' Don't explain it.", "drink": "Drink if your heart rate just went up.", "heat": 3},
        {"type": "TRUTH", "dare": "What's one thing about your sex life you've never told anyone in this room? You have to say it.", "drink": "Take two drinks and keep living that double life.", "heat": 3},
        {"type": "DO",    "dare": "Let the person on your right set your Instagram status for the next 10 minutes. No veto.", "drink": "Drink if you're too scared of your own timeline.", "heat": 2},
    ]
    if mode == "regular":
        return random.sample(regular, min(6, len(regular)))
    elif mode == "kinky":
        return random.sample(kinky + regular[:2], min(6, len(kinky) + 2))
    else:
        pool = regular[:3] + kinky[:3]
        random.shuffle(pool)
        return pool


# ─── STATE MANAGEMENT ─────────────────────────────────────────────────────────

def _init():
    defaults = {
        "dod_phase":        "setup",
        "dod_mode":         "regular",
        "dod_players":      [],   # list of {username, user_id, vice_summary}
        "dod_player_input": "",
        "dod_dares":        {},   # {username: [dare, ...]}
        "dod_deck":         [],   # shuffled list of {player, dare_idx}
        "dod_cur_card":     None, # {player, dare}
        "dod_scores":       {},   # {username: {drinks, done}}
        "dod_history":      [],   # list of resolved cards
        "dod_loading_msg":  "",
        "dod_error":        "",
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

    if st.session_state.dod_error:
        st.error(st.session_state.dod_error)
        st.session_state.dod_error = ""

    # ── Game mode ──────────────────────────────────────────────────────────────
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
        "kinky":   "Adult dares built from your actual vice data. Explicit. Not for the faint-hearted.",
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

    # ── Players ───────────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px; margin-top:4px;">Players</div>
""")

    players = st.session_state.dod_players
    me_already = any(p["username"] == my_name for p in players)

    # Auto-add host
    if not me_already and my_id:
        players.append({
            "username":     my_name,
            "user_id":      my_id,
            "vice_summary": _my_vice_summary(),
            "is_host":      True,
        })
        st.session_state.dod_players = players

    # ── Refresh vice summaries every render so stale/empty data gets updated ──
    for p in players:
        if p.get("is_host"):
            p["vice_summary"] = _my_vice_summary()
        else:
            uid = p.get("user_id")
            if uid:
                p["vice_summary"] = _player_vice_summary(uid)


    # ── DEBUG (remove once confirmed working) ──────────────────────────────────
    with st.expander("🔧 Debug info"):
        vice_log = st.session_state.get("vice_log", [])
        st.write(f"**vice_log in session:** {len(vice_log)} entries")
        if vice_log:
            st.write("**Sample entry:**", vice_log[0])
        for p in players:
            st.write(f"**{p['username']}** (user_id={p.get('user_id')}) → summary:", p.get("vice_summary"))
            if not p.get("is_host") and p.get("user_id"):
                try:
                    import database as db
                    raw = db.load_vice_log(p["user_id"])
                    st.write(f"  DB returned {len(raw)} entries")
                    if raw:
                        st.write("  First DB entry:", raw[0])
                except Exception as e:
                    st.write(f"  DB error: {e}")

    # Render current players
    for i, p in enumerate(players):
        col_name, col_remove = st.columns([5, 1])
        with col_name:
            host_badge = " · HOST" if p.get("is_host") else ""
            vs = p.get("vice_summary", {})
            counts = vs.get("counts", {})
            vice_str = "  ·  ".join(
                f"{_VICE_LABELS.get(vk, vk)}: {cnt}"
                for vk, cnt in counts.items()
            ) or "No data yet"
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {'var(--lime)' if p.get('is_host') else 'var(--border)'};
            border-radius:3px; padding:12px 14px; margin-bottom:6px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px;
              color:{'var(--lime)' if p.get('is_host') else 'var(--text)'}; letter-spacing:1px;">
    {p['username']}{host_badge}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px;
              color:var(--muted); letter-spacing:1px; text-transform:uppercase;">{vice_str}</div>
</div>
""")
        with col_remove:
            if not p.get("is_host"):
                st.html("<div style='height:6px'></div>")
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.dod_players.pop(i)
                    st.rerun()

    # Add player
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
                vs = _player_vice_summary(uid)
                st.session_state.dod_players.append({
                    "username":     user["username"],
                    "user_id":      uid,
                    "vice_summary": vs,
                    "is_host":      False,
                })
                st.rerun()

    st.html("<div style='height:20px'></div>")
    n_players = len(st.session_state.dod_players)
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
    AI reads each player's logged sessions from ViceVault.<br>
    The dares are built from your real habits. That's the whole point.
  </div>
</div>
""")


# ─── GENERATING PHASE ─────────────────────────────────────────────────────────

def _render_generating():
    inject_css()
    players = st.session_state.dod_players
    mode    = st.session_state.dod_mode

    ph_title  = st.empty()
    ph_bar    = st.empty()
    ph_msg    = st.empty()

    all_dares = {}
    for i, p in enumerate(players):
        pct = int((i / len(players)) * 90)
        ph_title.markdown(f"**Building dare deck…**")
        ph_bar.progress(pct)
        ph_msg.caption(f"Analysing {p['username']}'s vault history…")

        dares = _generate_dares_for_player(p["username"], p["vice_summary"], mode)
        all_dares[p["username"]] = dares
        time.sleep(0.3)

    ph_bar.progress(100)
    ph_msg.caption("Shuffling the deck…")

    # Build flat shuffled deck — each player gets each dare once
    deck = []
    for p in players:
        username = p["username"]
        for idx, _ in enumerate(all_dares[username]):
            deck.append({"player": username, "dare_idx": idx})
    random.shuffle(deck)

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

    # ── Header ────────────────────────────────────────────────────────────────
    mode_colors = {"regular": "var(--lime)", "kinky": "var(--magenta)", "both": "var(--cyan)"}
    mode_label  = {"regular": "Regular", "kinky": "Kinky", "both": "Mixed"}
    st.html(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start;
            border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px;">
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
                letter-spacing:3px; line-height:1;">DO OR DRINK</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:{mode_colors[mode]};">{mode_label[mode]} mode · {remaining} cards left</div>
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

    # ── Scoreboard ────────────────────────────────────────────────────────────
    cols = st.columns(len(scores))
    for i, (uname, s) in enumerate(scores.items()):
        with cols[i]:
            is_active = cur and cur.get("player") == uname
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            {'border-top:2px solid var(--lime)' if is_active else 'border-top:2px solid var(--border)'};
            border-radius:3px; padding:12px; text-align:center; {'animation: pulse-ring 1.5s ease-out 2;' if is_active else ''}">
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
        if not deck and not cur:
            # Game over
            _render_game_over()
            return

        # Draw button
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
                dare_idx = card_ref["dare_idx"]
                dare     = dares[player][dare_idx]
                st.session_state.dod_cur_card = {"player": player, "dare": dare}
            st.rerun()

    else:
        # Show the active dare card
        player = cur["player"]
        dare   = cur["dare"]
        heat   = dare.get("heat", 1)
        dtype  = dare.get("type", "DO")
        heat_color  = _HEAT_COLORS[heat]
        heat_label  = _HEAT_LABELS[heat]
        type_icon   = _TYPE_ICONS.get(dtype, "⚡")

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
                # Put back in deck at random position
                pos = random.randint(0, len(st.session_state.dod_deck))
                skip_ref = {"player": player, "dare_idx": dares[player].index(dare) if dare in dares[player] else 0}
                st.session_state.dod_deck.insert(pos, skip_ref)
                st.session_state.dod_cur_card = None
                st.rerun()

    # ── Recent history ─────────────────────────────────────────────────────────
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

    # ── End game button ────────────────────────────────────────────────────────
    st.html("<div style='height:16px'></div>")
    if st.button("End Game", use_container_width=True, key="end_game"):
        st.session_state.dod_phase = "gameover"
        st.rerun()


# ─── GAME OVER ────────────────────────────────────────────────────────────────

def _render_game_over():
    inject_css()
    scores  = st.session_state.dod_scores
    history = st.session_state.dod_history

    # Find winner (most dares done) and biggest drinker
    if scores:
        winner   = max(scores, key=lambda u: scores[u]["done"])
        drinker  = max(scores, key=lambda u: scores[u]["drinks"])

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--lime); border-radius:4px;
            padding:32px 28px; text-align:center; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Game Over</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--lime);
              letter-spacing:3px; line-height:0.9; margin-bottom:8px;">
    {winner.upper()}
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--soft);">
    held it down the most — {scores[winner]['done']} dares completed
  </div>
  {'<div style="margin-top:12px; font-family:\'DM Sans\',sans-serif; font-size:12px; color:var(--magenta);">🍹 ' + drinker + ' drank the most — ' + str(scores[drinker]["drinks"]) + ' times</div>' if winner != drinker else ''}
</div>
""")

    # Full leaderboard
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Final Standings</div>
""")
    sorted_players = sorted(scores.items(), key=lambda x: x[1]["done"], reverse=True)
    for rank, (uname, s) in enumerate(sorted_players, 1):
        rank_color = ["var(--lime)", "var(--amber)", "var(--cyan)"][min(rank-1, 2)]
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {rank_color}; border-radius:3px;
            padding:14px 18px; margin-bottom:8px;
            display:flex; justify-content:space-between; align-items:center;">
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:22px;
                color:{rank_color}; letter-spacing:1px; line-height:1;">#{rank}  {uname}</div>
  </div>
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
            # Keep players, regenerate dares
            for k in ["dod_dares", "dod_deck", "dod_cur_card", "dod_scores", "dod_history"]:
                if k in st.session_state:
                    del st.session_state[k]
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
