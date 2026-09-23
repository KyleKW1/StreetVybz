"""
Pages/hotspots.py — Hot spots near you. Where to go tonight.
Curated Kingston picks plus Google Places results for the user's own city.
Vibe filter: Chill / Turn Up / Late Night
"""

import html as _html
import streamlit as st
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
CURATED_CITY = "kingston"   # the hand-picked SPOTS above are all Kingston nights out

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
def _norm_city(city) -> str:
    return " ".join(str(city or "").lower().split())


def is_curated_city(city) -> bool:
    return CURATED_CITY in _norm_city(city)


def _search_area(city) -> str:
    """What to put after "bars in …". Plain "Kingston" would also match Kingston, Ontario."""
    return "Kingston Jamaica" if not _norm_city(city) or is_curated_city(city) else str(city).strip()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_places_spots(api_key, city=None, lat=None, lng=None):
    """Bars and cannabis spots in `city`, biased towards (lat, lng) when we have it."""
    if not api_key or api_key == FALLBACK_API_KEY:
        return []
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.location,places.rating,places.userRatingCount,places.formattedAddress,places.googleMapsUri,places.types"
    }

    area = _search_area(city)
    queries = [
        (f"bars in {area}", "drinks"),
        (f"nightlife in {area}", "drinks"),
        (f"cannabis dispensary in {area}", "cannabis"),
        (f"weed shop in {area}", "cannabis"),
    ]
    bias = ({"locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 20000.0}}}
            if lat is not None and lng is not None else {})

    results = []
    seen = set(CURATED_NAMES)

    for q, base_type in queries:
        try:
            r = requests.post(url, headers=headers, json={"textQuery": q, **bias}, timeout=8)
            data = r.json()
        except Exception:
            continue

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


def get_all_spots(api_key, city=None, lat=None, lng=None):
    """Spots for `city` (default Kingston). Curated picks only show for Kingston."""
    # ~10 km cache buckets, so nearby users share one lookup
    lat = round(lat, 1) if lat is not None else None
    lng = round(lng, 1) if lng is not None else None
    curated = SPOTS if (city is None or is_curated_city(city)) else []
    return curated + fetch_places_spots(api_key, _norm_city(city) or None, lat, lng)


# ── Card component ────────────────────────────────────────────────────────────
def spot_card(s):
    # Places results are external data — escape every text field before rendering.
    s = {k: _html.escape(v) if isinstance(v, str) else v for k, v in s.items()}
    type_color = "#c6ff00" if s["type"] == "cannabis" else "#ffb300"
    type_label = "CANNABIS" if s["type"] == "cannabis" else "DRINKS"
    rating_color = _rating_color(s["rating"])
    tip_html = ""
    if s.get("tip"):
        tip_html = f"""
        <div style="background:#111114;border:1px solid #2a2a35;border-radius:4px;
            padding:8px 12px;margin-bottom:12px;">
            <span style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
                color:#5a5a72;text-transform:uppercase;">TIP</span>
            <p style="color:#9090aa;font-size:12px;margin:4px 0 0;line-height:1.5;">{s["tip"]}</p>
        </div>"""

    st.html(f"""
    <div style="background:#18181d;border:1px solid #2a2a35;border-left:3px solid {type_color};
        border-radius:6px;padding:20px 24px;margin-bottom:12px;font-family:'DM Sans',sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div>
                <span style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:#f0f0f5;
                    letter-spacing:1px;line-height:1.1;">{s['name']}</span>
                <div style="margin-top:6px;">
                    <span style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
                        text-transform:uppercase;color:{type_color};background:{type_color}18;
                        border:1px solid {type_color}40;padding:2px 8px;border-radius:2px;
                        margin-right:8px;">{type_label}</span>
                    <span style="font-family:'Space Mono',monospace;font-size:9px;
                        letter-spacing:1px;color:{rating_color};">
                        ⭐ {s['rating']} <span style="color:#5a5a72;">({s['reviews']:,})</span>
                    </span>
                </div>
            </div>
            <span style="font-size:24px;line-height:1;">{s['tag']}</span>
        </div>
        <p style="color:#9090aa;font-size:13px;margin:10px 0 6px;font-style:italic;line-height:1.5;">
            {s['one_line']}</p>
        <p style="color:#5a5a72;font-size:12px;font-family:'Space Mono',monospace;margin:0 0 4px;">
            {s['address']}</p>
        <p style="color:#5a5a72;font-size:11px;margin:0 0 12px;">{s['details']}</p>
        {tip_html}
        <a href="{s['maps']}" target="_blank" style="font-family:'Space Mono',monospace;
            font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#00e5ff;
            text-decoration:none;border-bottom:1px solid #00e5ff40;padding-bottom:1px;">
            Open in Maps →</a>
    </div>
    """)


# ── Page ──────────────────────────────────────────────────────────────────────
def hotspots_page():
    inject_page_css()

    st.html("""
    <div style="margin-bottom:4px;">
        <span style="font-family:'Bebas Neue',sans-serif;font-size:40px;color:#f0f0f5;letter-spacing:2px;">
            Where to go tonight
        </span>
    </div>
    <p style="font-family:'Space Mono',monospace;font-size:11px;letter-spacing:2px;
        color:#5a5a72;text-transform:uppercase;margin-bottom:28px;">
        Drinks · Cannabis · Picked by someone who's been
    </p>
    """)

    api_key = get_api_key()
    spots = get_all_spots(api_key)

    # ── Session state for filters ─────────────────────────────────────────────
    if "vibe_filter" not in st.session_state:
        st.session_state.vibe_filter = "all"
    if "type_filter" not in st.session_state:
        st.session_state.type_filter = "all"

    # ── Vibe filter pills ─────────────────────────────────────────────────────
    st.html("""<p style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
        color:#5a5a72;text-transform:uppercase;margin-bottom:4px;">VIBE</p>""")

    vibe_options = {"All": "all", "Chill 🌿": "chill", "Turn Up 🔥": "turn_up", "Late Night 🌙": "late_night"}
    vcols = st.columns(len(vibe_options))
    for i, (label, val) in enumerate(vibe_options.items()):
        with vcols[i]:
            is_active = st.session_state.vibe_filter == val
            if st.button(label, key=f"vibe_{val}",
                         type="primary" if is_active else "secondary",
                         use_container_width=True):
                st.session_state.vibe_filter = val
                st.rerun()

    # ── Type filter pills ─────────────────────────────────────────────────────
    st.html("""<p style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
        color:#5a5a72;text-transform:uppercase;margin:16px 0 4px;">TYPE</p>""")

    type_options = {"All": "all", "Drinks 🥃": "drinks", "Cannabis 🌿": "cannabis"}
    tcols = st.columns(len(type_options))
    for i, (label, val) in enumerate(type_options.items()):
        with tcols[i]:
            is_active = st.session_state.type_filter == val
            if st.button(label, key=f"type_{val}",
                         type="primary" if is_active else "secondary",
                         use_container_width=True):
                st.session_state.type_filter = val
                st.rerun()

    st.html("<div style='margin-top:24px;'></div>")

    # ── Results ───────────────────────────────────────────────────────────────
    vibe = st.session_state.vibe_filter
    typ = st.session_state.type_filter

    visible = [
        s for s in spots
        if (vibe == "all" or vibe in s["vibe"])
        and (typ == "all" or s["type"] == typ)
    ]

    if not visible:
        st.html("""
        <div style="text-align:center;padding:60px 0;color:#5a5a72;
            font-family:'Space Mono',monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;">
            No spots match that filter
        </div>
        """)
    else:
        for s in visible:
            spot_card(s)
