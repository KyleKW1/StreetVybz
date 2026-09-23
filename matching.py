"""
matching.py — Pure matching logic for Hidden (no Streamlit, no DB).

Who can see whom (eligibility), how far apart they are (proximity),
and how alike they are (similarity + the reasons shown on the card).
"""

import math
from datetime import date, datetime

MIN_AGE = 18

# Lifestyle questions: key → (label, answer options low→high)
LIFESTYLE = {
    "weed":  ("Weed",    ["Never", "Sometimes", "Often", "Daily"]),
    "drink": ("Drinks",  ["Never", "Socially", "Often", "Every weekend+"]),
    "party": ("Parties", ["Homebody", "Sometimes", "Often", "Every chance"]),
}

INTENTS = {
    "date":   "Dating",
    "linkup": "Link-ups",
    "both":   "Dating + link-ups",
}

GENDERS   = ["Woman", "Man", "Non-binary", "Other"]
SHOW_ME   = ["Everyone", "Women", "Men"]
_SHOW_MAP = {"Women": {"Woman"}, "Men": {"Man"}}


# ─── BASICS ───────────────────────────────────────────────────────────────────

def age_on(birthdate, today=None) -> int | None:
    if not birthdate:
        return None
    if isinstance(birthdate, str):
        try:
            birthdate = date.fromisoformat(birthdate[:10])
        except ValueError:
            return None
    if isinstance(birthdate, datetime):
        birthdate = birthdate.date()
    today = today or date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def is_adult(birthdate, today=None) -> bool:
    a = age_on(birthdate, today)
    return a is not None and a >= MIN_AGE


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def round_coord(x: float) -> float:
    """~1 km precision — enough to match on, too coarse to find someone's door."""
    return round(float(x), 2)


def norm_city(city) -> str:
    return " ".join(str(city or "").lower().split())


def _intent_set(intent) -> set:
    return {"date", "linkup"} if intent == "both" else {intent} if intent in INTENTS else set()


def _wants(show_me, gender) -> bool:
    allowed = _SHOW_MAP.get(show_me)
    return allowed is None or gender in allowed


# ─── ELIGIBILITY + PROXIMITY ─────────────────────────────────────────────────

def shared_intents(me: dict, them: dict) -> set:
    """Intents both people are open to, after dating gender preferences.

    Dating only counts when each person's gender is one the other wants to see.
    Link-ups ignore gender.
    """
    shared = _intent_set(me.get("intent")) & _intent_set(them.get("intent"))
    if "date" in shared and not (_wants(me.get("show_me"), them.get("gender"))
                                 and _wants(them.get("show_me"), me.get("gender"))):
        shared.discard("date")
    return shared


def distance(me: dict, them: dict):
    """Returns (km or None, label) if they're close enough, else None.

    Live location on both sides → real distance within *my* radius.
    Otherwise fall back to being in the same city.
    """
    if (me.get("location_mode") == "live" and them.get("location_mode") == "live"
            and None not in (me.get("lat"), me.get("lon"), them.get("lat"), them.get("lon"))):
        km = haversine_km(me["lat"], me["lon"], them["lat"], them["lon"])
        if km <= float(me.get("max_km") or 25):
            return km, ("< 1 km away" if km < 1 else f"{round(km)} km away")
        return None
    if norm_city(me.get("city")) and norm_city(me.get("city")) == norm_city(them.get("city")):
        return None, f"In {str(them.get('city')).strip().title()}"
    return None


def is_candidate(me: dict, them: dict, today=None) -> bool:
    if me.get("user_id") == them.get("user_id") or them.get("hidden"):
        return False
    if not (is_adult(me.get("birthdate"), today) and is_adult(them.get("birthdate"), today)):
        return False
    my_age, their_age = age_on(me["birthdate"], today), age_on(them["birthdate"], today)
    if not (int(me.get("age_min") or 18) <= their_age <= int(me.get("age_max") or 99)):
        return False
    if not (int(them.get("age_min") or 18) <= my_age <= int(them.get("age_max") or 99)):
        return False
    return bool(shared_intents(me, them)) and distance(me, them) is not None


def filter_reasons(me: dict, others: list[dict], today=None) -> dict:
    """Why nearby people aren't in Discover: counts by the first rule each one fails.

    my_ages     — outside my age range (I can change this)
    their_ages  — I'm outside theirs
    intent      — not looking for the same thing
    gender      — dating preferences don't line up
    """
    out = {"nearby": 0, "my_ages": 0, "their_ages": 0, "intent": 0, "gender": 0}
    if not is_adult(me.get("birthdate"), today):
        return out
    my_age = age_on(me["birthdate"], today)
    for them in others:
        if (me.get("user_id") == them.get("user_id") or them.get("hidden")
                or not is_adult(them.get("birthdate"), today) or distance(me, them) is None):
            continue
        out["nearby"] += 1
        if is_candidate(me, them, today):
            continue
        their_age = age_on(them["birthdate"], today)
        if not (int(me.get("age_min") or 18) <= their_age <= int(me.get("age_max") or 99)):
            out["my_ages"] += 1
        elif not (int(them.get("age_min") or 18) <= my_age <= int(them.get("age_max") or 99)):
            out["their_ages"] += 1
        elif not (_intent_set(me.get("intent")) & _intent_set(them.get("intent"))):
            out["intent"] += 1
        else:
            out["gender"] += 1
    return out


# ─── SIMILARITY ───────────────────────────────────────────────────────────────

def _jaccard(a, b):
    a, b = set(a or []), set(b or [])
    return len(a & b) / len(a | b) if (a or b) else None


# Short, readable names for the hidden-desire signals (Read Between The Lines, phase 2)
DESIRE_LABELS = {
    "verbal_arousal":       "Dirty talk",
    "desired_intensity":    "Being wanted badly",
    "authentic_exposure":   "Being truly seen",
    "power_dynamic":        "Power dynamics",
    "archetype_attraction": "A certain energy",
    "stranger_fantasy":     "Strangers",
    "dom_active":           "Taking control",
    "sub_active":           "Giving up control",
    "taboo_arousal":        "Taboo turn-ons",
    "exhib_active":         "Being watched",
    "secret_fantasy":       "An untold fantasy",
    "group_sex":            "More than two",
    "taboo_fixation":       "A guilty-pleasure category",
    "elaborated_fantasy":   "A mapped-out fantasy",
    "unnamed_fixation":     "Something not tried yet",
}


def shared_desires(mq: dict, tq: dict) -> list[str]:
    """Hidden-desire signals both people said yes to — the only ones a match ever sees."""
    mine = set((mq or {}).get("signals") or [])
    return [s for s in DESIRE_LABELS if s in mine and s in set((tq or {}).get("signals") or [])]


def quiz_match(mq: dict, tq: dict) -> int | None:
    """0–100 from two quiz results (openness gap, shared desires, categories); None unless both took it."""
    if not (mq and tq):
        return None   # one side skipped the quiz: don't let that drag the score down
    parts = []   # (weight, score)
    if mq.get("openness") is not None and tq.get("openness") is not None:
        parts.append((0.5, 1 - abs(int(mq["openness"]) - int(tq["openness"])) / 100))
    sig = _jaccard(mq.get("signals"), tq.get("signals"))
    if sig is not None:
        parts.append((0.3, sig))
    cats = _jaccard(mq.get("categories"), tq.get("categories"))
    if cats is not None:
        parts.append((0.2, cats))
    if not parts:
        return None
    return round(100 * sum(w * s for w, s in parts) / sum(w for w, _ in parts))


def similarity(me: dict, them: dict) -> tuple[int, list[str]]:
    """Returns (0–100 score, short human reasons) from lifestyle + quiz answers.

    Hidden-desire signals only ever count toward the score, never shown by
    name — the card says how many you share, not what they are.
    """
    reasons, quiz_reasons = [], []

    diffs = []
    for key, (label, opts) in LIFESTYLE.items():
        a, b = me.get(key), them.get(key)
        if a is None or b is None:
            continue
        diffs.append(abs(int(a) - int(b)) / (len(opts) - 1))
        if a == b and int(a) >= 1:
            reasons.append(f"{label}: both {opts[int(a)].lower()}")
    lifestyle = 1 - sum(diffs) / len(diffs) if diffs else 0.5

    mq, tq = me.get("quiz") or {}, them.get("quiz") or {}
    if mq.get("openness") is not None and tq.get("openness") is not None:
        if abs(int(mq["openness"]) - int(tq["openness"])) <= 10:
            quiz_reasons.append("Same level of openness")
    shared = len(shared_desires(mq, tq))
    if shared:
        quiz_reasons.append(f"{shared} hidden desire{'s' if shared != 1 else ''} in common")
    if mq.get("result") and mq.get("result") == tq.get("result"):
        quiz_reasons.append(f"Both got “{tq['result']}”")

    quiz = quiz_match(mq, tq)
    score = lifestyle if quiz is None else 0.6 * lifestyle + 0.4 * quiz / 100
    return max(0, min(100, round(score * 100))), (quiz_reasons + reasons)[:3]


def rank_candidates(me: dict, others: list[dict], today=None) -> list[dict]:
    """Eligible people, best match first, each annotated for the Discover card."""
    out = []
    for them in others:
        if not is_candidate(me, them, today):
            continue
        km, where = distance(me, them)
        score, reasons = similarity(me, them)
        out.append({**them, "age": age_on(them["birthdate"], today), "km": km,
                    "where": where, "score": score, "reasons": reasons,
                    "shared_intents": sorted(shared_intents(me, them))})
    out.sort(key=lambda c: (-c["score"], c["km"] if c["km"] is not None else 1e9))
    return out
