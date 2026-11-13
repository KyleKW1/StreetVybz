"""
matching.py — Pure matching logic for Hidden (no Streamlit, no DB).

Hidden is a link-up app: who can see whom (eligibility), how far apart they
are (proximity), and how much chemistry they have (similarity + the reasons
shown on the card). Read Between The Lines answers drive most of the score.
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
# Profiles saved before the switch from dating
_LEGACY_INTENT = {"date": "regular", "linkup": "open", "both": "open"}

STATUSES = {
    "single": "Single",
    "couple": "Couple",
    "open":   "Open relationship",
}

HOSTING = {
    "host":   "Can host",
    "travel": "Can travel",
    "either": "Host or travel",
    "out":    "Meet out first",
}

GENDERS   = ["Woman", "Man", "Non-binary", "Other"]
SHOW_ME   = ["Everyone", "Women", "Men"]
_SHOW_MAP = {"Women": {"Woman"}, "Men": {"Man"}}

# Read Between The Lines signals → names shown ONLY after a mutual match,
# ONLY where both people share them, and ONLY if both opted in.
DESIRE_LABELS = {
    "verbal_arousal":       "Dirty talk",
    "desired_intensity":    "Being wanted badly",
    "authentic_exposure":   "Being seen with no filter",
    "power_dynamic":        "Power dynamics",
    "archetype_attraction": "A very specific type",
    "stranger_fantasy":     "Strangers & new places",
    "dom_active":           "Taking control",
    "sub_active":           "Handing over control",
    "taboo_arousal":        "Something never said out loud",
    "exhib_active":         "Being watched",
    "secret_fantasy":       "A fantasy never told",
    "group_sex":            "More than two",
    "taboo_fixation":       "A private fixation",
    "elaborated_fantasy":   "A fully mapped-out fantasy",
    "unnamed_fixation":     "Something not tried yet",
}
# Opposite halves that fit together — read between the lines
_COMPLEMENTS = [("dom_active", "sub_active")]


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
    """A short line on where it could happen, or None if it doesn't add anything."""
    a, b = me.get("hosting"), them.get("hosting")
    if not a or not b:
        return None
    can_host, can_travel = {"host", "either"}, {"travel", "either"}
    if a in can_host and b in can_travel and not (a == b == "either"):
        if a == "host" or b == "travel":
            return "You can host, they can travel"
    if b in can_host and a in can_travel and not (a == b == "either"):
        if b == "host" or a == "travel":
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


# ─── SIMILARITY ───────────────────────────────────────────────────────────────

def _jaccard(a, b):
    a, b = set(a or []), set(b or [])
    return len(a & b) / len(a | b) if (a or b) else None


def _complements(a, b) -> list[tuple[str, str]]:
    a, b = set(a or []), set(b or [])
    return [(x, y) for x, y in _COMPLEMENTS
            if (x in a and y in b and x not in b) or (y in a and x in b and y not in b)]


def shared_desires(my_quiz: dict | None, their_quiz: dict | None) -> list[str]:
    """Names for the hidden desires two people overlap on (for the post-match reveal)."""
    mine = set((my_quiz or {}).get("signals") or [])
    theirs = set((their_quiz or {}).get("signals") or [])
    out = [DESIRE_LABELS[s] for s in DESIRE_LABELS if s in mine and s in theirs]
    for x, y in _complements(mine, theirs):
        out.insert(0, "You lead, they follow" if x in mine else "They lead, you follow")
    return out


def similarity(me: dict, them: dict) -> tuple[int, list[str]]:
    """Returns (0–100 chemistry score, short human reasons).

    Read Between The Lines answers carry most of the weight; lifestyle is the
    rest. Hidden-desire signals are never named on the card — it says how many
    you share, not what they are.
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

    quiz_parts = []   # (weight, score)
    mq, tq = me.get("quiz") or {}, them.get("quiz") or {}
    if mq.get("openness") is not None and tq.get("openness") is not None:
        gap = abs(int(mq["openness"]) - int(tq["openness"]))
        quiz_parts.append((0.4, 1 - gap / 100))
        if gap <= 10:
            quiz_reasons.append("Same level of openness")
    sig = _jaccard(mq.get("signals"), tq.get("signals"))
    fits = _complements(mq.get("signals"), tq.get("signals"))
    if sig is not None:
        quiz_parts.append((0.45, min(1.0, sig + 0.25 * len(fits))))
        shared = len(set(mq.get("signals") or []) & set(tq.get("signals") or []))
        if fits:
            quiz_reasons.append("Your desires fit together 🔥")
        if shared:
            quiz_reasons.append(f"{shared} hidden desire{'s' if shared != 1 else ''} in common")
    cats = _jaccard(mq.get("categories"), tq.get("categories"))
    if cats is not None:
        quiz_parts.append((0.15, cats))
    if mq.get("result") and mq.get("result") == tq.get("result"):
        quiz_reasons.append(f"Both got “{tq['result']}”")

    if quiz_parts:
        total_w = sum(w for w, _ in quiz_parts)
        quiz = sum(w * s for w, s in quiz_parts) / total_w
        score = 0.35 * lifestyle + 0.65 * quiz
    else:
        score = lifestyle
    return max(0, min(100, round(score * 100))), (quiz_reasons + reasons)[:3]


def rank_candidates(me: dict, others: list[dict], today=None, tonight: str | None = None) -> list[dict]:
    """Eligible people, annotated for the Discover card.

    Order: people free tonight first, then chemistry, then distance.
    """
    out = []
    for them in others:
        if not is_candidate(me, them, today):
            continue
        km, where = distance(me, them)
        score, reasons = similarity(me, them)
        where_line = logistics(me, them)
        if where_line:
            reasons = reasons[:2] + [where_line]   # logistics always make the card
        out.append({**them, "age": age_on(them["birthdate"], today), "km": km,
                    "where": where, "score": score, "reasons": reasons,
                    "free_tonight": free_tonight(them, tonight),
                    "shared_intents": sorted(shared_intents(me, them))})
    out.sort(key=lambda c: (not c["free_tonight"], -c["score"],
                            c["km"] if c["km"] is not None else 1e9))
    return out
