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
        "name":    "Kingston Dub Club",
        "tag":     "🌿🥃", "type": "weed",
        "vibe":    ["chill"],
        "one_line": "Best view in Kingston. Bring a spliff and stay til the city lights up.",
        "details": "Sundays only · 5PM–midnight · $2000 JMD entry · Cash only",
        "tip":     "Go before sunset to catch the view. Wear flat shoes — the steps are steep.",
        "rating": 4.6, "reviews": 475,
        "address": "7b Skyline Dr, Kingston",
        "maps":   "https://maps.google.com/?q=Kingston+Dub+Club+Jamaica",
        "color":  "#c6ff00", "lat": 18.0331659, "lng": -76.7452831,
        "source": "curated",
    },
    {
        "name":    "Ribbiz UltraLounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["turn_up", "late_night"],
        "one_line": "The spot everyone ends up at. High energy, bottle service, no pretending you're going home early.",
        "details": "Mon–Thu til 3AM · Fri–Sat til 5AM · Ardenne Emirates Plaza",
        "tip":     "Friday and Saturday are wild. Go early or book a table — it fills fast.",
        "rating": 4.1, "reviews": 3145,
        "address": "7-9 Ardenne Rd, New Kingston",
        "maps":   "https://maps.google.com/?q=Ribbiz+UltraLounge+Kingston+Jamaica",
        "color":  "#ffb300", "lat": 18.0154705, "lng": -76.7840958,
        "source": "curated",
    },
    {
        "name":    "Club Cubana",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["chill", "turn_up"],
        "one_line": "Cuban cocktails, live music, terrace on Hope Road. The mojito alone is worth it.",
        "details": "Tue–Thu til midnight · Fri til 2:30AM · Sat 7PM til 2:30AM",
        "tip":     "Classic mojito. Order it. That's the move.",
        "rating": 4.2, "reviews": 208,
        "address": "75 Hope Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Club+Cubana+Kingston+Jamaica",
        "color":  "#ff2d78", "lat": 18.019587899999998, "lng": -76.7775369,
        "source": "curated",
    },
    {
        "name":    "Dulcé Bar & Lounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["chill"],
        "one_line": "Highest-rated lounge in Kingston. Outdoor, live music, genuinely nice energy.",
        "details": "Mon–Sat noon til 2AM · Sun 1PM–10PM · 22 Barbican Rd",
        "tip":     "Best on a Tuesday or Thursday — vibes without the weekend madness.",
        "rating": 4.8, "reviews": 15,
        "address": "22 Barbican Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Dulce+Bar+Lounge+Kingston+Jamaica",
        "color":  "#00e5ff", "lat": 18.021321, "lng": -76.7656563,
        "source": "curated",
    },
    {
        "name":    "Mezza Luna Kingston",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["chill"],
        "one_line": "Rooftop with a view. Cocktails, good food, and the kind of atmosphere that makes a date work.",
        "details": "Daily noon–10:30PM · Rooftop at 110 Constant Spring Rd",
        "tip":     "Book ahead on weekends. Ask for Taylor at the bar.",
        "rating": 4.6, "reviews": 302,
        "address": "110 Constant Spring Rd (Rooftop), Kingston",
        "maps":   "https://maps.google.com/?q=Mezza+Luna+Kingston+Jamaica",
        "color":  "#ffb300", "lat": 18.032263, "lng": -76.7951551,
        "source": "curated",
    },
    {
        "name":    "Di Bar at Blue Mahoe Estate",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["chill", "turn_up"],
        "one_line": "Soca Thursdays, solid bartenders, no pretension. A proper local spot.",
        "details": "Mon–Thu 3PM–midnight · Fri 3PM–2AM · Sat 3PM–midnight · Sun noon–6PM",
        "tip":     "Thursday night Soca session is the one. Bartender Theo knows his craft.",
        "rating": 4.1, "reviews": 122,
        "address": "5 Haining Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Di+Bar+Blue+Mahoe+Estate+Kingston",
        "color":  "#c6ff00", "lat": 18.0041531, "lng": -76.78401079999999,
        "source": "curated",
    },
    {
        "name":    "Usain Bolt's Tracks & Records",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["chill", "turn_up"],
        "one_line": "Sports bar energy, Jamaican food, open til midnight. More fun than you expect.",
        "details": "Daily 11:30AM–midnight · 67 Constant Spring Rd",
        "tip":     "Go for drinks and wings. Skip the ribs. The Scotch bonnet hot sauce is legendary.",
        "rating": 4.1, "reviews": 3470,
        "address": "67 Constant Spring Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Usain+Bolt+Tracks+Records+Kingston",
        "color":  "#ffb300", "lat": 18.0219849, "lng": -76.79773,
        "source": "curated",
    },
    {
        "name":    "Offshore Rooftop Lounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    ["late_night"],
        "one_line": "Rooftop, karaoke Sundays, and a Thursday pasta + $500 margarita deal that makes no sense but works.",
        "details": "Wed–Sun 3PM–midnight · Consumer Plaza, 103 Constant Spring Rd",
        "tip":     "Thursday pasta + $500 margarita deal is unbeatable. Karaoke on Sundays.",
        "rating": 3.8, "reviews": 319,
        "address": "103 Constant Spring Rd (Rooftop), Kingston",
        "maps":   "https://maps.google.com/?q=Offshore+Rooftop+Lounge+Kingston+Jamaica",
        "color":  "#00e5ff", "lat": 18.0280394, "lng": -76.7965894,
        "source": "curated",
    },
    {
        "name":    "Kaya Herb House",
        "tag":     "🌿", "type": "weed",
        "vibe":    ["chill"],
        "one_line": "Jamaica's only licensed dispensary worth the drive. Farm tour, quality flower, staff who actually know what they're talking about.",
        "details": "Daily 9AM–10PM (Sat til 11PM) · 1 Weed Street, Drax Hall, St. Ann",
        "tip":     "Worth the drive from Kingston. Staff product knowledge is exceptional.",
        "rating": 4.2, "reviews": 157,
        "address": "1 Weed Street, Drax Hall, St. Ann",
        "maps":   "https://maps.google.com/?q=Kaya+Herb+House+Drax+Hall+Jamaica",
        "color":  "#c6ff00", "lat": 18.423933899999998, "lng": -77.1745351,
        "source": "curated",
    },
    {
        "name":    "Bamboo Bar & Lounge",
        "tag":     "🌿🥃", "type": "weed",
        "vibe":    ["chill"],
        "one_line": "Outdoor, laid-back, bring your own. Good for an afternoon that drifts into evening.",
        "details": "Daily 11AM–11:30PM · 8 Barbican Rd, Kingston",
        "tip":     "Good for an afternoon session. Bring your own — it's that kind of spot.",
        "rating": 4.0, "reviews": 72,
        "address": "8 Barbican Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Bamboo+Bar+Lounge+Barbican+Kingston+Jamaica",
        "color":  "#c6ff00", "lat": 18.0312862, "lng": -76.77619829999999,
        "source": "curated",
    },
]

# Curated spot names — used to avoid duplicates when merging Places results
CURATED_NAMES = {s["name"].lower() for s in SPOTS}


# ── Google Places fetcher ─────────────────────────────────────────────────────

def _assign_vibe(types: list[str], name: str) -> list[str]:
    """Guess vibe tags from Places API type labels and name keywords."""
    name_lower = name.lower()
    t = " ".join(types)

    vibes = []
    if any(k in t for k in ("bar", "lounge", "night_club")) or \
       any(k in name_lower for k in ("lounge", "bar", "club", "republic")):
        vibes.append("chill")
    if "night_club" in t or any(k in name_lower for k in ("club", "nightclub", "ultra")):
        vibes.append("turn_up")
    if not vibes:
        vibes = ["chill"]
    return list(dict.fromkeys(vibes))  # dedupe, preserve order


def _rating_color(rating: float) -> str:
    if rating >= 4.5:
        return "#c6ff00"
    if rating >= 4.0:
        return "#ffb300"
    return "#00e5ff"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_places_spots(api_key: str) -> list[dict]:
    """
    Pull bars / nightlife / lounges in Kingston from the Places API (New).
    Returns a list of spot dicts compatible with the SPOTS schema.
    Cached for 1 hour so we don't hammer the API on every rerun.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,"
            "places.location,places.rating,places.userRatingCount,"
            "places.googleMapsUri,places.types,places.regularOpeningHours"
        ),
    }

    queries = [
        "bars and lounges in Kingston Jamaica",
        "nightclubs in Kingston Jamaica",
        "rooftop bars Kingston Jamaica",
    ]

    seen_names: set[str] = set(CURATED_NAMES)
    results: list[dict] = []

    for q in queries:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "textQuery": q,
                    "locationBias": {
                        "circle": {
                            "center": {"latitude": 18.018, "longitude": -76.793},
                            "radius": 8000.0,
                        }
                    },
                    "maxResultCount": 15,
                },
                timeout=8,
            )
            data = resp.json()
        except Exception:
            continue

        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "Unknown")
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            lat = place.get("location", {}).get("latitude", 18.018)
            lng = place.get("location", {}).get("longitude", -76.793)
            rating = place.get("rating", 0.0)
            reviews = place.get("userRatingCount", 0)
            address = place.get("formattedAddress", "Kingston, Jamaica")
            maps_url = place.get("googleMapsUri", f"https://maps.google.com/?q={name.replace(' ', '+')}")
            types = place.get("types", [])

            # Build a minimal hours string
            hours_info = place.get("regularOpeningHours", {})
            weekday_text = hours_info.get("weekdayDescriptions", [])
            details = weekday_text[0] if weekday_text else "Hours not listed"

            color = _rating_color(rating)
            vibe = _assign_vibe(types, name)

            results.append({
                "name":     name,
                "tag":      "🥃",
                "type":     "drinks",
                "vibe":     vibe,
                "one_line": f"Discovered via Google Places · {address}",
                "details":  details,
                "tip":      "No insider tip yet — be the first to visit and tell us.",
                "rating":   round(rating, 1),
                "reviews":  reviews,
                "address":  address,
                "maps":     maps_url,
                "color":    color,
                "lat":      lat,
                "lng":      lng,
                "source":   "places_api",
            })

    return results


def get_all_spots(api_key: str | None) -> list[dict]:
    """Merge curated spots with Places API results, curated first."""
    if not api_key:
        return SPOTS
    live = fetch_places_spots(api_key)
    return SPOTS + live


# ── Map ───────────────────────────────────────────────────────────────────────

def _build_leaflet_map(visible_spots):
    if not visible_spots:
        return

    markers_js = ""
    for s in visible_spots:
        name    = s["name"].replace("'", "\\'")
        address = s["address"].replace("'", "\\'")
        tip     = s["tip"].replace("'", "\\'")
        color   = s["color"]
        maps    = s["maps"]
        source_badge = (
            '<span style="font-size:9px; color:#c6ff00; letter-spacing:1px;">✦ CURATED</span>'
            if s.get("source") == "curated"
            else '<span style="font-size:9px; color:#9090aa; letter-spacing:1px;">◈ PLACES</span>'
        )
        markers_js += f"""
        L.circleMarker([{s['lat']}, {s['lng']}], {{
            radius: 9,
            fillColor: '{color}',
            color: '#2a2a35',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9
        }}).addTo(map).bindPopup(
            '<div style="font-family:monospace; background:#1e1e26; color:#f0f0f5; ' +
            'border:1px solid #3a3a4a; border-radius:4px; padding:10px 12px; min-width:180px;">' +
            '<div style="margin-bottom:4px;">{source_badge}</div>' +
            '<div style="font-size:13px; font-weight:700; color:{color}; margin-bottom:4px;">{name}</div>' +
            '<div style="font-size:11px; color:#9090aa; margin-bottom:6px;">{address}</div>' +
            '<div style="font-size:11px; color:#9090aa; margin-bottom:8px; font-style:italic;">{tip}</div>' +
            '<a href="{maps}" target="_blank" style="font-size:10px; color:#00e5ff; ' +
            'text-decoration:none; text-transform:uppercase; letter-spacing:1px;">↗ Maps</a>' +
            '</div>',
            {{maxWidth: 240}}
        );"""

    avg_lat = sum(s["lat"] for s in visible_spots) / len(visible_spots)
    avg_lng = sum(s["lng"] for s in visible_spots) / len(visible_spots)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body {{ margin:0; padding:0; background:transparent; }}
    #map {{ height:380px; width:100%; border-radius:4px; }}
    .leaflet-popup-content-wrapper,
    .leaflet-popup-tip {{
      background: #1e1e26 !important;
      border: 1px solid #3a3a4a !important;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4) !important;
      color: #f0f0f5 !important;
    }}
    .leaflet-popup-content {{ margin: 0 !important; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {{zoomControl:true}}).setView([{avg_lat:.4f}, {avg_lng:.4f}], 13);
    L.tileLayer(
      'https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png',
      {{
        attribution: '&copy; <a href="https://carto.com">CARTO</a> &copy; <a href="https://openstreetmap.org">OSM</a>',
        subdomains: 'abcd',
        maxZoom: 19
      }}
    ).addTo(map);
    {markers_js}
  </script>
</body>
</html>"""

    components.html(html, height=400, scrolling=False)


# ── Spot card ─────────────────────────────────────────────────────────────────

def spot_card(s):
    type_label = "DRINKS · WEED" if s["type"] == "weed" and "🥃" in s["tag"] else \
                 "WEED" if s["type"] == "weed" else "DRINKS"
    type_color = "#c6ff00" if s["type"] == "weed" else "#ffb300"

    source_label = (
        '<span style="font-family:\'Space Mono\',monospace; font-size:7px; letter-spacing:1px; '
        'padding:2px 7px; border:1px solid #c6ff00; color:#c6ff00; border-radius:2px;">✦ CURATED</span>'
        if s.get("source") == "curated"
        else
        '<span style="font-family:\'Space Mono\',monospace; font-size:7px; letter-spacing:1px; '
        'padding:2px 7px; border:1px solid #555566; color:#555566; border-radius:2px;">◈ PLACES</span>'
    )

    vibe_map = {
        "chill":      ("CHILL",      "var(--cyan)"),
        "turn_up":    ("TURN UP",    "var(--amber)"),
        "late_night": ("LATE NIGHT", "var(--magenta)"),
    }
    vibe_chips = "".join(
        f'<span style="font-family:\'Space Mono\',monospace; font-size:7px; letter-spacing:1px; '
        f'padding:2px 7px; border:1px solid {col}; color:{col}; border-radius:2px; margin-right:4px;">{lbl}</span>'
        for v in s.get("vibe", [])
        for lbl, col in [vibe_map.get(v, ("", "var(--muted)"))]
    )

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {s['color']}; border-radius:4px;
            padding:20px 22px; margin-bottom:12px;">
  <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:10px;">
    <div style="flex:1; min-width:0;">
      <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:6px;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--text);
                     letter-spacing:1px;">{s['name']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                     padding:3px 8px; border:1px solid {type_color}; color:{type_color};
                     border-radius:2px; text-transform:uppercase;">{type_label}</span>
        <span style="font-size:16px;">{s['tag']}</span>
        {source_label}
      </div>
      <div style="margin-bottom:6px;">{vibe_chips}</div>
      <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);">
        {s['address']}
      </div>
    </div>
    <div style="text-align:right; flex-shrink:0; margin-left:16px;">
      <div style="font-family:'Space Mono',monospace; font-size:11px; color:{s['color']};">
        {s['rating']} ⭐
      </div>
      <div style="font-family:'DM Sans',sans-serif; font-size:10px; color:var(--muted);">
        {s['reviews']:,} reviews
      </div>
    </div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              line-height:1.6; margin-bottom:10px; font-style:italic;">"{s['one_line']}"</div>
  <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
                 background:var(--surface); border:1px solid var(--border);
                 border-radius:2px; padding:3px 8px;">🕐 {s['details']}</span>
  </div>
  <div style="background:var(--surface); border-left:2px solid {s['color']};
              padding:8px 12px; border-radius:0 3px 3px 0; margin-bottom:12px;">
    <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                 color:var(--muted); text-transform:uppercase;">Tip · </span>
    <span style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
                 font-style:italic;">{s['tip']}</span>
  </div>
  <a href="{s['maps']}" target="_blank"
     style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
            color:var(--cyan); text-decoration:none; text-transform:uppercase;">
    ↗ Open in Maps
  </a>
</div>
""")


# ── Page ──────────────────────────────────────────────────────────────────────

def hotspots_page():
    inject_page_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Kingston, Jamaica</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">WHERE TO GO TONIGHT</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Drinks. Weed. Picked by someone who's been.
  </div>
</div>
""")

    # ── Google Places API key (from secrets or manual entry) ──────────────────
    api_key = None
    try:
        api_key = st.secrets["GOOGLE_PLACES_KEY"]
    except Exception:
        pass  # No secret configured yet

    if not api_key:
        with st.expander("🔑 Add Google Places API key to discover more spots", expanded=False):
            st.markdown(
                "Add `GOOGLE_PLACES_KEY = 'your_key'` to `.streamlit/secrets.toml` "
                "to pull live bars and nightlife from Google. Currently showing curated spots only."
            )
            manual_key = st.text_input("Or paste your key here (session only):", type="password", key="gplaces_key_input")
            if manual_key:
                api_key = manual_key

    # ── Load spots ────────────────────────────────────────────────────────────
    if api_key:
        with st.spinner("Pulling live spots from Google Places…"):
            all_spots = get_all_spots(api_key)
    else:
        all_spots = SPOTS

    # ── Vibe filter ───────────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">What's the vibe tonight?</div>
""")

    vibe_key = "hotspots_vibe"
    type_key = "hotspots_type"
    if vibe_key not in st.session_state:
        st.session_state[vibe_key] = "all"
    if type_key not in st.session_state:
        st.session_state[type_key] = "all"

    cv1, cv2, cv3, cv4 = st.columns(4)
    with cv1:
        if st.button("◈  All Vibes", use_container_width=True,
                     type="primary" if st.session_state[vibe_key] == "all" else "secondary",
                     key="vibe_all"):
            st.session_state[vibe_key] = "all"; st.rerun()
    with cv2:
        if st.button("🌊  Chill", use_container_width=True,
                     type="primary" if st.session_state[vibe_key] == "chill" else "secondary",
                     key="vibe_chill"):
            st.session_state[vibe_key] = "chill"; st.rerun()
    with cv3:
        if st.button("🔥  Turn Up", use_container_width=True,
                     type="primary" if st.session_state[vibe_key] == "turn_up" else "secondary",
                     key="vibe_turn_up"):
            st.session_state[vibe_key] = "turn_up"; st.rerun()
    with cv4:
        if st.button("🌙  Late Night", use_container_width=True,
                     type="primary" if st.session_state[vibe_key] == "late_night" else "secondary",
                     key="vibe_late"):
            st.session_state[vibe_key] = "late_night"; st.rerun()

    vibe_desc = {
        "all":        "",
        "chill":      "Low-key, outdoor, easy conversation. No pressure.",
        "turn_up":    "Loud music, big crowd, bottle service. You know what you came for.",
        "late_night": "Still going when everyone else stopped. These places know.",
    }
    desc = vibe_desc.get(st.session_state[vibe_key], "")
    if desc:
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:8px 14px; margin-bottom:16px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">{desc}</div>
</div>
""")
    else:
        st.html("<div style='height:8px'></div>")

    ct1, ct2, ct3 = st.columns(3)
    with ct1:
        if st.button("◈  Everything", use_container_width=True,
                     type="primary" if st.session_state[type_key] == "all" else "secondary",
                     key="type_all"):
            st.session_state[type_key] = "all"; st.rerun()
    with ct2:
        if st.button("🥃  Drinks", use_container_width=True,
                     type="primary" if st.session_state[type_key] == "drinks" else "secondary",
                     key="type_drinks"):
            st.session_state[type_key] = "drinks"; st.rerun()
    with ct3:
        if st.button("🌿  Weed", use_container_width=True,
                     type="primary" if st.session_state[type_key] == "weed" else "secondary",
                     key="type_weed"):
            st.session_state[type_key] = "weed"; st.rerun()

    st.html("<div style='height:1rem'></div>")

    # ── Filter ────────────────────────────────────────────────────────────────
    vibe_f = st.session_state[vibe_key]
    type_f = st.session_state[type_key]

    visible = [
        s for s in all_spots
        if (vibe_f == "all" or vibe_f in s.get("vibe", []))
        and (type_f == "all" or s["type"] == type_f or (type_f == "weed" and "weed" in s["type"]))
    ]

    # ── Map ───────────────────────────────────────────────────────────────────
    if visible:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Map</div>
""")
        _build_leaflet_map(visible)
        st.html("<div style='height:1.5rem'></div>")

    # ── Count / empty state ───────────────────────────────────────────────────
    if not visible:
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:60px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted);">NOTHING MATCHES</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    Try a different vibe or type filter.
  </div>
</div>
""")
        return

    curated_count = sum(1 for s in visible if s.get("source") == "curated")
    live_count    = len(visible) - curated_count
    source_note   = f" ({curated_count} curated · {live_count} from Google)" if live_count else ""

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:16px;">
  {len(visible)} spot{"s" if len(visible) != 1 else ""}{source_note}
</div>
""")

    for s in visible:
        spot_card(s)

    st.html("""
<div style="margin-top:24px; padding:16px; background:var(--surface); border:1px solid var(--border);
            border-radius:4px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              color:var(--muted); text-transform:uppercase; line-height:1.8;">
    Cannabis is decriminalised in Jamaica for personal use (up to 2oz).<br>
    Kaya Herb House is the only licensed retail dispensary listed.<br>
    Always verify hours before visiting — spots change.
  </div>
</div>
""")
