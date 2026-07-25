"""
Pages/do_or_drink_core.py
Prompt building, OpenAI generation, fallback dares, and session-state helpers.

Performance improvement: _player_vice_summary results are cached in session_state
with a 5-minute TTL. The DoD setup screen no longer hits the DB on every render
for players whose data hasn't changed.
"""

import json
import random
import time
import streamlit as st

# ─── VICE LABELS ──────────────────────────────────────────────────────────────

_VICE_LABELS = {
    "weed":    "weed/smoking",
    "alcohol": "alcohol",
    "sex":     "unprotected sex",
    "other":   "other substances",
}

# ─── HIDDEN DESIRE SIGNAL MAPS ────────────────────────────────────────────────

HD_ID_TO_SIGNAL = {
    "hd_01": "power_dynamic_latent",
    "hd_02": "hidden_fantasy_present",
    "hd_03": "archetype_attraction",
    "hd_04": "shame_adjacent_arousal",
    "hd_05": "desired_intensity",
    "hd_06": "dom_latent",
    "hd_07": "sub_latent",
    "hd_08": "exhib_latent",
    "hd_09": "group_latent",
    "hd_10": "unnamed_fixation",
    "hd_11": "taboo_draw",
    "hd_12": "elaborated_fantasy",
    "hd_13": "authentic_exposure",
    "hd_14": "stranger_context",
    "hd_15": "verbal_latent",
}

HD_SCORE_MAP = {
    "strongly": 3,
    "yes":      2,
    "maybe":    1,
    "nope":     0,
}

# TTL for player summary cache (seconds)
_SUMMARY_CACHE_TTL = 300  # 5 minutes


# ─── DB WRAPPER ───────────────────────────────────────────────────────────────

def _db(fn, *args, default=None, **kwargs):
    try:
        import database as db
        f = getattr(db, fn, None)
        return f(*args, **kwargs) if f else default
    except Exception:
        return default


# ─── SESSION HELPERS ──────────────────────────────────────────────────────────

def _me():
    u = st.session_state.get("user", {})
    return u.get("username", "You"), u.get("id")


def _player_vice_summary(user_id: int) -> dict:
    """
    Load vice log + quiz profile for a player.
    Results are cached in session_state for _SUMMARY_CACHE_TTL seconds
    so the DoD setup screen doesn't hit the DB on every button click.
    """
    cache_key  = f"_dod_vs_{user_id}"
    cache_time = f"_dod_vs_ts_{user_id}"

    cached_at = st.session_state.get(cache_time, 0)
    if st.session_state.get(cache_key) and (time.time() - cached_at) < _SUMMARY_CACHE_TTL:
        return st.session_state[cache_key]

    # Cache miss — fetch from DB
    result = _fetch_player_summary(user_id)
    st.session_state[cache_key]  = result
    st.session_state[cache_time] = time.time()
    return result


def _fetch_player_summary(user_id: int) -> dict:
    """Actual DB fetch — called only on cache miss."""
    try:
        import database as db
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
                    """SELECT result_name, result_meta, dim_scores
                       FROM quiz_results
                       WHERE user_id = %s AND quiz_type LIKE 'rbtl_v4_%'
                       ORDER BY completed_at DESC LIMIT 1""",
                    (user_id,)
                )
                row = cur.fetchone()
                cur.close()

                if row:
                    raw_dim = row.get("dim_scores") or {}
                    if isinstance(raw_dim, str):
                        try:
                            raw_dim = json.loads(raw_dim)
                        except Exception:
                            raw_dim = {}

                    hd_full = raw_dim.get("hd_full", {})
                    signal_scores = {}
                    for hd_id, answer in hd_full.items():
                        signal = HD_ID_TO_SIGNAL.get(hd_id)
                        score  = HD_SCORE_MAP.get(answer, 0)
                        if signal and score > 0:
                            signal_scores[signal] = score

                    summary["quiz"] = {
                        "profile_name": row.get("result_name", ""),
                        "profile_meta": row.get("result_meta", ""),
                        "dim_scores":   signal_scores,
                        "hd_signals":   raw_dim.get("hd_signals", ""),
                    }
            finally:
                conn.close()

        return summary

    except Exception:
        return {}


def invalidate_player_summary_cache(user_id: int):
    """Call after a new vice log entry to force fresh data on next DoD setup render."""
    st.session_state.pop(f"_dod_vs_{user_id}", None)
    st.session_state.pop(f"_dod_vs_ts_{user_id}", None)


def _has_data(vice_summary: dict) -> bool:
    return bool(vice_summary.get("counts")) or bool(
        vice_summary.get("quiz", {}).get("profile_name")
    )


def _my_full_summary() -> dict:
    _, my_id = _me()
    return _player_vice_summary(my_id) if my_id else {}


# ─── GROUP PROFILE ────────────────────────────────────────────────────────────

def build_group_profile(players: list) -> dict:
    combined_counts, combined_details, quiz_profiles = {}, {}, []
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
        group["quiz"] = max(quiz_profiles, key=lambda q: len(q.get("dim_scores", {})))
    return group


# ─── OPENAI CLIENT ────────────────────────────────────────────────────────────

def get_openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "openai package missing. Add 'openai>=1.0.0' to requirements.txt and redeploy."
        )
    api_key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in Streamlit secrets. Add it under Settings → Secrets."
        )
    return OpenAI(api_key=api_key)


# ─── PROFILE TEXT ─────────────────────────────────────────────────────────────

def _profile_text(vice_summary: dict) -> str:
    counts  = vice_summary.get("counts", {})
    details = vice_summary.get("sample_details", {})
    quiz    = vice_summary.get("quiz", {})
    lines   = []

    for vk, cnt in counts.items():
        label = _VICE_LABELS.get(vk, vk)
        d     = details.get(vk, {})
        extra = ""
        if vk == "weed"    and d.get("method"):        extra = f", usually {d['method']}"
        elif vk == "alcohol" and d.get("drink_type"):  extra = f", drinks {d['drink_type']}"
        elif vk == "sex"    and d.get("partner_type"): extra = f", partner type: {d['partner_type']}"
        elif vk == "other"  and d.get("substance"):    extra = f" ({d['substance']})"
        lines.append(f"- {label} ({cnt} session{'s' if cnt != 1 else ''}{extra})")

    if quiz.get("profile_name"):
        signal_scores = quiz.get("dim_scores", {})
        top_signals = sorted(
            ((s, v) for s, v in signal_scores.items() if v >= 2),
            key=lambda x: -x[1],
        )[:3]

        if top_signals:
            sig_str = ", ".join(
                f"{s.replace('_latent', '').replace('_', ' ')}:"
                f"{'strong' if v == 3 else 'yes'}"
                for s, v in top_signals
            )
        else:
            sig_str = quiz.get("hd_signals", "") or "none surfaced"

        lines.append(
            f"- Desire profile: {quiz['profile_name']} — "
            f"{quiz.get('profile_meta', '')} "
            f"(signals: {sig_str})"
        )

    return "\n".join(lines) if lines else ""


# ─── MODE LINE ────────────────────────────────────────────────────────────────

def _mode_line(mode: str) -> str:
    if mode == "regular":
        return (
            "Regular mode — social, funny, mildly embarrassing. "
            "No explicit content. Caribbean lime vibes."
        )
    if mode == "kinky":
        return (
            "Kinky mode — ADULTS ONLY. Every single dare must be seductive, "
            "physically charged, or explicitly sexual. "
            "STRICTLY NO heat:1 cards — every card must be heat:2 or heat:3. "
            "Dares should involve: slow touching of another player, whispering something "
            "sexually explicit in someone's ear, a lap sit that lasts 30 seconds, "
            "tracing fingers down someone's neck or back, kissing someone's neck or shoulder, "
            "describing out loud what you'd do to someone if you had them alone, "
            "demonstrating how you kiss on a willing player, removing an item of clothing, "
            "giving a slow sensual shoulder or back massage, or doing something that starts "
            "innocent and escalates into foreplay. "
            "The tone is seductive, slow-burning, Caribbean heat. "
            "No euphemisms. No softening. No mild social dares hiding in this mode."
        )
    return (
        "Mixed mode — roughly half social/funny Caribbean energy, half explicitly seductive "
        "and sexual. The kinky half must involve real physical contact or explicit confessions "
        "— no heat:1 in those cards. Alternate the energy so the game builds from fun into "
        "something charged."
    )


# ─── DARE JSON SCHEMA ─────────────────────────────────────────────────────────

def _dare_json_schema(mode: str) -> str:
    if mode == "kinky":
        heat3_label = "explicit sexual act or forced confession"
        heat2_label = "seductive physical contact or charged dare"
        schema_note = (
            "IMPORTANT: For kinky mode, heat:1 is FORBIDDEN. "
            "Every card must be heat:2 or heat:3."
        )
    else:
        heat3_label = "maximum chaos or explicit"
        heat2_label = "spicy/awkward"
        schema_note = ""

    return (
        f"Return ONLY valid JSON — no markdown, no preamble.\n"
        f"[\n"
        f"  {{\n"
        f'    "type": "DO" or "TRUTH",\n'
        f'    "dare": "The dare or question.",\n'
        f'    "drink": "What they drink if they refuse — one short punishing sentence.",\n'
        f'    "heat": 2\n'
        f"  }}\n"
        f"]\n"
        f"heat: 1=mild/funny  2={heat2_label}  3={heat3_label}\n"
        f"{schema_note}"
    )


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

def _prompt_personalised(player_name: str, vice_summary: dict, mode: str, n: int = 12) -> str:
    return (
        f"You write dare cards for Hidden 'Do or Drink' — a Caribbean party game "
        f"(Jamaica/English Caribbean).\n"
        f"Tone: direct, seductive where needed, a little savage, real. "
        f"Natural Caribbean cadence where it fits — not forced patois.\n\n"
        f"Player: {player_name}\n"
        f"Their personal profile (use for subtle personalisation — a nod, not a direct callout):\n"
        f"{_profile_text(vice_summary)}\n\n"
        f"{_mode_line(mode)}\n"
        f"Write exactly {n} dare cards. Each is a DO (action) or TRUTH (question said out loud).\n"
        f"Include a DRINK alternative if they refuse — make it sting a little.\n"
        f"{_dare_json_schema(mode)}"
    )


def _prompt_group_shaped(player_name: str, group_profile: dict, mode: str, n: int = 12) -> str:
    return (
        f"You write dare cards for Hidden 'Do or Drink' — a Caribbean party game "
        f"(Jamaica/English Caribbean).\n"
        f"Tone: direct, seductive where needed, a little savage, real.\n\n"
        f"Player: {player_name}\n"
        f"No personal data. Use the group profile below to match the game's energy "
        f"so {player_name}'s cards belong.\n\n"
        f"Group profile:\n"
        f"{_profile_text(group_profile)}\n\n"
        f"{_mode_line(mode)}\n"
        f"Write exactly {n} dare cards for {player_name}.\n"
        f"Include a DRINK alternative if they refuse.\n"
        f"{_dare_json_schema(mode)}"
    )


def _prompt_generic(player_name: str, mode: str, n: int = 12) -> str:
    return (
        f"You write dare cards for Hidden 'Do or Drink' — a Caribbean party game "
        f"(Jamaica/English Caribbean).\n"
        f"Tone: direct, seductive where needed, a little savage, real.\n\n"
        f"Player: {player_name}\n"
        f"No profile data. Write sharp, charged, chaotic Caribbean party dares.\n\n"
        f"{_mode_line(mode)}\n"
        f"Write exactly {n} dare cards.\n"
        f"Include a DRINK alternative if they refuse.\n"
        f"{_dare_json_schema(mode)}"
    )


# ─── DARE GENERATION ──────────────────────────────────────────────────────────

def _parse_dares(raw: str) -> list:
    raw   = raw.strip().replace("```json", "").replace("```", "").strip()
    dares = json.loads(raw)
    valid = []
    for d in dares:
        if isinstance(d, dict) and d.get("dare") and d.get("drink"):
            d.setdefault("type", "DO")
            d.setdefault("heat", 2)
            valid.append(d)
    return valid


def _fallback_dares(player_name: str, mode: str) -> list:
    regular = [
        {
            "type": "DO",
            "dare": f"Text the last person in your contacts and tell them {player_name} says hi — send it now, no editing.",
            "drink": "Two fingers if you mek excuses.",
            "heat": 1,
        },
        {
            "type": "TRUTH",
            "dare": "What's the most embarrassing thing you've done while under the influence? 30 seconds.",
            "drink": "Drink and stay quiet — same thing really.",
            "heat": 1,
        },
        {
            "type": "DO",
            "dare": "Do your best impression of the person to your left. They rate it. Under 5/10 means you drink anyway.",
            "drink": "Drink for being afraid of embarrassment.",
            "heat": 2,
        },
        {
            "type": "TRUTH",
            "dare": "Who in this room would you call first if you were in real trouble? Say the name out loud.",
            "drink": "Drink and keep your secrets then.",
            "heat": 1,
        },
        {
            "type": "DO",
            "dare": "Set your phone screen brightness to max and show the last photo in your camera roll. No skipping.",
            "drink": "Drink and delete it, coward.",
            "heat": 2,
        },
        {
            "type": "TRUTH",
            "dare": "On a scale of 1-10, how messy were you last weekend? The real number, not the polite one.",
            "drink": "Drink for lying to yourself.",
            "heat": 1,
        },
    ]
    kinky = [
        {
            "type": "DO",
            "dare": "Sit in someone's lap — your choice who — and stay there for the next two turns.",
            "drink": "Drink twice and sit on the floor alone.",
            "heat": 2,
        },
        {
            "type": "DO",
            "dare": "Whisper something you'd actually do to someone in this room into their ear. They can't repeat it.",
            "drink": "Drink three fingers and live with the curiosity.",
            "heat": 3,
        },
        {
            "type": "DO",
            "dare": "Give the person to your right a slow neck massage for 30 seconds. Make it count.",
            "drink": "Drink and let them know you're scared of your own hands.",
            "heat": 2,
        },
        {
            "type": "TRUTH",
            "dare": "Describe out loud, in detail, what you'd do to the most attractive person in this room if you had them alone tonight.",
            "drink": "Drink four fingers and keep that fantasy to yourself then.",
            "heat": 3,
        },
        {
            "type": "DO",
            "dare": "Trace one finger slowly from the back of someone's neck down to their shoulder blade. They pick who does it to them.",
            "drink": "Drink and admit you're too scared to touch anyone.",
            "heat": 2,
        },
        {
            "type": "TRUTH",
            "dare": "What's the most explicit thing you've ever done with someone you just met? Say it out loud.",
            "drink": "Drink four fingers and keep lying to yourself that you're innocent.",
            "heat": 3,
        },
        {
            "type": "DO",
            "dare": "Show the group how you actually kiss — demonstrate on a willing player. No peck. Do it properly.",
            "drink": "Drink and let everyone wonder what you're hiding.",
            "heat": 3,
        },
        {
            "type": "DO",
            "dare": "Remove one item of clothing. Your choice what. It stays off for the next three turns.",
            "drink": "Drink three fingers and stay fully dressed like a coward.",
            "heat": 2,
        },
        {
            "type": "TRUTH",
            "dare": "Who in this room do you think about sexually? Say the name. No deflecting, no jokes.",
            "drink": "Drink five fingers and let us all guess.",
            "heat": 3,
        },
        {
            "type": "DO",
            "dare": "Give someone in the room a compliment — but make it explicitly about their body. Say it slowly.",
            "drink": "Drink and admit you can't handle a little heat.",
            "heat": 2,
        },
    ]

    if mode == "regular":
        return random.sample(regular, min(12, len(regular)))
    if mode == "kinky":
        return random.sample(kinky, min(12, len(kinky)))
    pool = regular[:6] + kinky[:6]
    random.shuffle(pool)
    return pool


def generate_dares_for_player(
    player_name: str,
    vice_summary: dict,
    group_profile: dict,
    any_group_has_data: bool,
    mode: str,
    client,
) -> list:
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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=2800,
        )
        dares = _parse_dares(resp.choices[0].message.content)
        if dares:
            return dares
        raise ValueError("Parsed 0 valid dares.")
    except Exception as e:
        existing = st.session_state.get("dod_error", "")
        st.session_state.dod_error = (
            f"{existing}\n[{player_name} · {strategy}] {e}".strip()
        )
        return _fallback_dares(player_name, mode)


# ─── STATE MANAGEMENT ─────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "dod_phase":       "setup",
        "dod_mode":        "regular",
        "dod_players":     [],
        "dod_dares":       {},
        "dod_deck":        [],
        "dod_cur_card":    None,
        "dod_scores":      {},
        "dod_history":     [],
        "dod_error":       "",
        "dod_timer_start": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_state():
    for k in list(st.session_state.keys()):
        if k.startswith("dod_"):
            del st.session_state[k]
    init_state()
    st.rerun()
