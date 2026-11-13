"""
matching.py — Pure matching logic for Hidden (no Streamlit, no DB).

Hidden is a link-up app, not a dating app: who can see whom (eligibility),
how far apart they are (proximity), and how much heat there is (similarity +
the reasons shown on the card). Read Between The Lines carries most of it.
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
    "tonight": "Tonight only",
    "regular": "Regular link-up",
    "open":    "Open to either",
}
INTENT_ICONS = {"tonight": "🔥", "regular": "🔁", "open": "✨"}
# Profiles saved while Hidden was a dating app
_LEGACY_INTENT = {"date": "regular", "linkup": "open", "both": "open"}

STATUSES = {"single": "Single", "couple": "Couple", "open": "Open relationship"}
HOSTING = {"host": "Can host", "travel": "Can travel", "either": "Host or travel", "out": "Meet out first"}

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


def norm_intent(intent) -> str | None:
    intent = _LEGACY_INTENT.get(intent, intent)
    return intent if intent in INTENTS else None


def _intent_set(intent) -> set:
    intent = norm_intent(intent)
    return {"tonight", "regular"} if intent == "open" else {intent} if intent else set()


def _wants(show_me, gender) -> bool:
    allowed = _SHOW_MAP.get(show_me)
    return allowed is None or gender in allowed


# ─── ELIGIBILITY + PROXIMITY ─────────────────────────────────────────────────

def into_each_other(me: dict, them: dict) -> bool:
    """Each person's gender is one the other is into."""
    return (_wants(me.get("show_me"), them.get("gender"))
            and _wants(them.get("show_me"), me.get("gender")))


def shared_intents(me: dict, them: dict) -> set:
    """Kinds of link-up both people are up for ("tonight" / "regular")."""
    if not into_each_other(me, them):
        return set()
    return _intent_set(me.get("intent")) & _intent_set(them.get("intent"))


def free_tonight(p: dict, tonight: str | None) -> bool:
    return bool(tonight) and str(p.get("available_on") or "")[:10] == tonight


def logistics(me: dict, them: dict) -> str | None:
    """Where it could happen, when that's worth saying on the card."""
    a, b = me.get("hosting"), them.get("hosting")
    if not a or not b:
        return None
    can_host, can_travel = {"host", "either"}, {"travel", "either"}
    if a in can_host and b in can_travel and (a == "host" or b == "travel"):
        return "You can host, they can travel"
    if b in can_host and a in can_travel and (b == "host" or a == "travel"):
        return "They can host, you can travel"
    if "out" in (a, b):
        return "Meet out first"
    return None


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
    gender      — not into each other's gender
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


# Opposite halves that fit together — read between the lines
_COMPLEMENTS = [("dom_active", "sub_active")]


def desires_fit(mq: dict, tq: dict) -> bool:
    """One wants to take control, the other wants to give it up."""
    a, b = set((mq or {}).get("signals") or []), set((tq or {}).get("signals") or [])
    return any((x in a and y in b) or (y in a and x in b) for x, y in _COMPLEMENTS)


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
        parts.append((0.4, 1 - abs(int(mq["openness"]) - int(tq["openness"])) / 100))
    sig = _jaccard(mq.get("signals"), tq.get("signals"))
    if sig is not None:
        parts.append((0.45, min(1.0, sig + (0.25 if desires_fit(mq, tq) else 0))))
    cats = _jaccard(mq.get("categories"), tq.get("categories"))
    if cats is not None:
        parts.append((0.15, cats))
    if not parts:
        return None
    return round(100 * sum(w * s for w, s in parts) / sum(w for w, _ in parts))


def similarity(me: dict, them: dict) -> tuple[int, list[str]]:
    """Returns (0–100 heat score, short human reasons): 65% quiz, 35% lifestyle.

    On Discover, hidden-desire signals only count toward the score: the card
    says how many you share, never which ones (a match page names shared ones).
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
    if desires_fit(mq, tq):
        quiz_reasons.append("Your desires fit together 🔥")
    if shared:
        quiz_reasons.append(f"{shared} hidden desire{'s' if shared != 1 else ''} in common")

    quiz = quiz_match(mq, tq)
    score = lifestyle if quiz is None else 0.35 * lifestyle + 0.65 * quiz / 100
    return max(0, min(100, round(score * 100))), (quiz_reasons + reasons)[:3]


def describe(me: dict, them: dict, today=None, tonight: str | None = None,
             require_fit: bool = True) -> dict | None:
    """One person annotated for a tile, post or request: age, where, heat score, reasons.

    With require_fit, returns None for anyone who doesn't fit (the grid and posts).
    Incoming requests pass require_fit=False: they already found you.
    """
    if require_fit and not is_candidate(me, them, today):
        return None
    km, where = distance(me, them) or (None, "")
    score, reasons = similarity(me, them)
    where_line = logistics(me, them)
    if where_line:
        reasons = reasons[:2] + [where_line]   # logistics always make the card
    return {**them, "age": age_on(them.get("birthdate"), today), "km": km,
            "where": where, "score": score, "reasons": reasons,
            "free_tonight": free_tonight(them, tonight),
            "shared_intents": sorted(shared_intents(me, them))}


def rank_candidates(me: dict, others: list[dict], today=None, tonight: str | None = None) -> list[dict]:
    """Everyone who fits, for the grid: free tonight first, then heat, then distance."""
    out = [d for d in (describe(me, them, today, tonight) for them in others) if d]
    out.sort(key=lambda c: (not c["free_tonight"], -c["score"],
                            c["km"] if c["km"] is not None else 1e9))
    return out
