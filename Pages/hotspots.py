"""
Pages/hotspots.py — Kingston hot spots. Where to go tonight.
Vibe filter: Chill / Turn Up / Late Night
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
from styles import inject_page_css


# ── Hardcoded fallback/seed spots ─────────────────────────────────────────────
SPOTS = [
    {
        "name": "Kingston Dub Club",
        "tag": "🌿🥃", "type": "cannabis",
        "vibe": ["chill"],
        "one_line": "Best view in Kingston. Bring a spliff and stay til the city lights up.",
        "details": "Sundays only · 5PM–midnight · $2000 JMD entry · Cash only",
        "tip": "Go before sunset to catch the view. Wear flat shoes — the steps are steep.",
        "rating": 4.6, "reviews": 475,
        "address": "7b Skyline Dr, Kingston",
        "maps": "https://maps.google.com/?q=Kingston+Dub+Club+Jamaica",
        "color": "#c6ff00", "lat": 18.0331659, "lng": -76.7452831,
        "source": "curated",
    },
    {
        "name": "Kaya Herb House",
        "tag": "🌿", "type": "cannabis",
        "vibe": ["chill"],
        "one_line": "Jamaica's only licensed dispensary worth the drive.",
        "details": "Daily 9AM–10PM (Sat til 11PM)",
        "tip": "Worth the drive from Kingston.",
        "rating": 4.2, "reviews": 157,
        "address": "1 Weed Street, Drax Hall, St. Ann",
        "maps": "https://maps.google.com/?q=Kaya+Herb+House+Drax+Hall+Jamaica",
        "color": "#c6ff00", "lat": 18.4239339, "lng": -77.1745351,
        "source": "curated",
    },
    {
        "name": "Ribbiz UltraLounge",
        "tag": "🥃", "type": "drinks",
        "vibe": ["turn_up", "late_night"],
        "one_line": "The spot everyone ends up at.",
        "details": "Mon–Sat late",
        "tip": "Book early.",
        "rating": 4.1, "reviews": 3145,
        "address": "7-9 Ardenne Rd, Kingston",
        "maps": "https://maps.google.com/?q=Ribbiz+UltraLounge+Kingston",
        "color": "#ffb300", "lat": 18.01547, "lng": -76.78409,
        "source": "curated",
    },
]

CURATED_NAMES = {s["name"].lower() for s in SPOTS}

FALLBACK_API_KEY = "YOUR_API_KEY"


def get_api_key():
    try:
        return st.secrets["GOOGLE_PLACES_KEY"]
    except Exception:
        return FALLBACK_API_KEY


# ── Helpers ───────────────────────────────────────────────────────────────────
def _assign_vibe(types, name):
    name = name.lower()
    t = " ".join(types)

    if "night_club" in t or "club" in name:
        return ["turn_up"]
    return ["chill"]


def _rating_color(r):
    return "#c6ff00" if r >= 4.5 else "#ffb300" if r >= 4 else "#00e5ff"


# ── Places API ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_places_spots(api_key):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.location,places.rating,places.userRatingCount,places.formattedAddress,places.googleMapsUri,places.types"
    }

    queries = [
        ("bars in Kingston Jamaica", "drinks"),
        ("nightlife Kingston Jamaica", "drinks"),

        # Cannabis (expanded)
        ("cannabis store Kingston Jamaica", "cannabis"),
        ("weed shop Kingston Jamaica", "cannabis"),
        ("herb house Kingston Jamaica", "cannabis"),
        ("dispensary Kingston Jamaica", "cannabis"),
    ]

    results = []
    seen = set(CURATED_NAMES)

    for q, base_type in queries:
        r = requests.post(url, headers=headers, json={"textQuery": q})
        data = r.json()

        for p in data.get("places", []):
            name = p["displayName"]["text"]
            if name.lower() in seen:
                continue
            seen.add(name.lower())

            results.append({
                "name": name,
                "tag": "🌿" if base_type == "cannabis" else "🥃",
                "type": base_type,
                "vibe": _assign_vibe(p.get("types", []), name),
                "one_line": p.get("formattedAddress", ""),
                "details": "Hours not listed",
                "tip": "Check it out.",
                "rating": round(p.get("rating", 0), 1),
                "reviews": p.get("userRatingCount", 0),
                "address": p.get("formattedAddress", ""),
                "maps": p.get("googleMapsUri", ""),
                "color": _rating_color(p.get("rating", 0)),
                "lat": p["location"]["latitude"],
                "lng": p["location"]["longitude"],
                "source": "places_api"
            })

    return results


def get_all_spots(api_key):
    return SPOTS + fetch_places_spots(api_key)


# ── UI ────────────────────────────────────────────────────────────────────────
def spot_card(s):
    if s["type"] == "cannabis":
        label = "CANNABIS"
        color = "#c6ff00"
    else:
        label = "DRINKS"
        color = "#ffb300"

    st.markdown(f"""
**{s['name']}**  
{label} · ⭐ {s['rating']} ({s['reviews']})  
{s['address']}  

_{s['one_line']}_  

[Open in Maps]({s['maps']})
---
""")


def hotspots_page():
    inject_page_css()

    st.title("Where to go tonight")
    st.caption("Drinks. Cannabis. Picked by someone who's been.")

    api_key = get_api_key()
    spots = get_all_spots(api_key)

    # Filters
    vibe = st.selectbox("Vibe", ["all", "chill", "turn_up", "late_night"])
    typ = st.selectbox("Type", ["all", "drinks", "cannabis"])

    visible = [
        s for s in spots
        if (vibe == "all" or vibe in s["vibe"])
        and (typ == "all" or s["type"] == typ)
    ]

    for s in visible:
        spot_card(s)
