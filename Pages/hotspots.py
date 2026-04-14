"""
Pages/hotspots.py — Kingston, Jamaica hot spots for drinks & weed.
Now includes an interactive Leaflet map with CartoDB dark tiles.
"""

import streamlit as st
import streamlit.components.v1 as components
from styles import inject_page_css


SPOTS = [
    {
        "name":    "Kingston Dub Club",
        "tag":     "🌿🥃", "type": "weed",
        "vibe":    "Legendary hillside reggae venue. Open-air, epic city view, zero pretension.",
        "details": "Sundays only · 5PM–midnight · $2000 JMD entry · Cash only",
        "tip":     "Go before sunset to catch the view. Wear flat shoes — the steps are steep.",
        "rating": 4.6, "reviews": 475,
        "address": "7b Skyline Dr, Kingston",
        "maps":   "https://maps.google.com/?q=Kingston+Dub+Club+Jamaica",
        "color":  "#c6ff00", "lat": 18.0331659, "lng": -76.7452831,
    },
    {
        "name":    "Ribbiz UltraLounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "The spot everyone ends up at. High energy, bottle service, massive crowd on weekends.",
        "details": "Mon–Thu til 3AM · Fri–Sat til 5AM · Ardenne Emirates Plaza",
        "tip":     "Friday and Saturday are wild. Go early or book a table — it fills fast.",
        "rating": 4.1, "reviews": 3145,
        "address": "7-9 Ardenne Rd, New Kingston",
        "maps":   "https://maps.google.com/?q=Ribbiz+UltraLounge+Kingston+Jamaica",
        "color":  "#ffb300", "lat": 18.0154705, "lng": -76.7840958,
    },
    {
        "name":    "Club Cubana",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Cuban cocktails, live music, outdoor terrace on Hope Road. Mojitos are elite.",
        "details": "Tue–Thu til midnight · Fri til 2:30AM · Sat 7PM til 2:30AM",
        "tip":     "Classic mojito. Order it. That's the move.",
        "rating": 4.2, "reviews": 208,
        "address": "75 Hope Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Club+Cubana+Kingston+Jamaica",
        "color":  "#ff2d78", "lat": 18.019587899999998, "lng": -76.7775369,
    },
    {
        "name":    "Dulcé Bar & Lounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Highest-rated lounge in Kingston. Chill outdoor setting, live music, great for dates.",
        "details": "Mon–Sat noon til 2AM · Sun 1PM–10PM · 22 Barbican Rd",
        "tip":     "Best for a Tuesday or Thursday — vibes without the weekend madness.",
        "rating": 4.8, "reviews": 15,
        "address": "22 Barbican Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Dulce+Bar+Lounge+Kingston+Jamaica",
        "color":  "#00e5ff", "lat": 18.021321, "lng": -76.7656563,
    },
    {
        "name":    "Mezza Luna Kingston",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Rooftop restaurant with a proper view. Cocktails, good food, date-night energy.",
        "details": "Daily noon–10:30PM · Rooftop at 110 Constant Spring Rd",
        "tip":     "Book ahead on weekends. The bartender Taylor is the one to talk to.",
        "rating": 4.6, "reviews": 302,
        "address": "110 Constant Spring Rd (Rooftop), Kingston",
        "maps":   "https://maps.google.com/?q=Mezza+Luna+Kingston+Jamaica",
        "color":  "#ffb300", "lat": 18.032263, "lng": -76.7951551,
    },
    {
        "name":    "Di Bar at Blue Mahoe Estate",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Local favourite. Soca Thursdays, good bartenders, laid-back atmosphere.",
        "details": "Mon–Thu 3PM–midnight · Fri 3PM–2AM · Sat 3PM–midnight · Sun noon–6PM",
        "tip":     "Thursday night Soca session is the one. Bartender Theo knows his craft.",
        "rating": 4.1, "reviews": 122,
        "address": "5 Haining Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Di+Bar+Blue+Mahoe+Estate+Kingston",
        "color":  "#c6ff00", "lat": 18.0041531, "lng": -76.78401079999999,
    },
    {
        "name":    "Usain Bolt's Tracks & Records",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Sports bar vibes, Jamaican food, open til midnight daily. Tourist-friendly but genuinely fun.",
        "details": "Daily 11:30AM–midnight · 67 Constant Spring Rd",
        "tip":     "Go for drinks and wings. Skip the ribs. The Scotch bonnet hot sauce is legendary.",
        "rating": 4.1, "reviews": 3470,
        "address": "67 Constant Spring Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Usain+Bolt+Tracks+Records+Kingston",
        "color":  "#ffb300", "lat": 18.0219849, "lng": -76.79773,
    },
    {
        "name":    "Offshore Rooftop Lounge",
        "tag":     "🥃", "type": "drinks",
        "vibe":    "Rooftop with views, Jamaican food, karaoke nights. Casual Kingston energy.",
        "details": "Wed–Sun 3PM–midnight · Consumer Plaza, 103 Constant Spring Rd",
        "tip":     "Thursday pasta + $500 margarita deal is unbeatable. Karaoke on Sundays.",
        "rating": 3.8, "reviews": 319,
        "address": "103 Constant Spring Rd (Rooftop), Kingston",
        "maps":   "https://maps.google.com/?q=Offshore+Rooftop+Lounge+Kingston+Jamaica",
        "color":  "#00e5ff", "lat": 18.0280394, "lng": -76.7965894,
    },
    {
        "name":    "Kaya Herb House",
        "tag":     "🌿", "type": "weed",
        "vibe":    "Jamaica's premier licensed cannabis dispensary. Farm tour, high-quality flower, knowledgeable staff.",
        "details": "Daily 9AM–10PM (Sat til 11PM) · 1 Weed Street, Drax Hall (St. Ann — day trip)",
        "tip":     "Worth the drive from Kingston. Staff product knowledge is exceptional.",
        "rating": 4.2, "reviews": 157,
        "address": "1 Weed Street, Drax Hall, St. Ann",
        "maps":   "https://maps.google.com/?q=Kaya+Herb+House+Drax+Hall+Jamaica",
        "color":  "#c6ff00", "lat": 18.423933899999998, "lng": -77.1745351,
    },
    {
        "name":    "Bamboo Bar & Lounge",
        "tag":     "🌿🥃", "type": "weed",
        "vibe":    "Chill outdoor spot. Good atmosphere, laid-back crowd, weed-friendly energy.",
        "details": "Daily 11AM–11:30PM · 8 Barbican Rd, Kingston",
        "tip":     "Good for an afternoon session. Bring your own — it's that kind of spot.",
        "rating": 4.0, "reviews": 72,
        "address": "8 Barbican Rd, Kingston",
        "maps":   "https://maps.google.com/?q=Bamboo+Bar+Lounge+Barbican+Kingston+Jamaica",
        "color":  "#c6ff00", "lat": 18.0312862, "lng": -76.77619829999999,
    },
]


def _build_leaflet_map(visible_spots):
    """Render a Leaflet map with CartoDB dark tiles."""
    if not visible_spots:
        return

    # Build JS marker array
    markers_js = ""
    for s in visible_spots:
        # Escape single quotes in strings
        name    = s["name"].replace("'", "\\'")
        address = s["address"].replace("'", "\\'")
        tip     = s["tip"].replace("'", "\\'")
        color   = s["color"]
        maps    = s["maps"]
        markers_js += f"""
        L.circleMarker([{s['lat']}, {s['lng']}], {{
            radius: 9,
            fillColor: '{color}',
            color: '#0a0a0b',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        }}).addTo(map).bindPopup(
            '<div style="font-family:monospace; background:#18181d; color:#f0f0f5; ' +
            'border:1px solid #2a2a35; border-radius:4px; padding:10px 12px; min-width:180px;">' +
            '<div style="font-size:13px; font-weight:700; color:{color}; margin-bottom:4px;">{name}</div>' +
            '<div style="font-size:11px; color:#9090aa; margin-bottom:6px;">{address}</div>' +
            '<div style="font-size:11px; color:#9090aa; margin-bottom:8px; font-style:italic;">{tip}</div>' +
            '<a href="{maps}" target="_blank" style="font-size:10px; color:#00e5ff; ' +
            'text-decoration:none; text-transform:uppercase; letter-spacing:1px;">↗ Maps</a>' +
            '</div>',
            {{maxWidth: 220}}
        );"""

    # Centre map on visible spots
    avg_lat = sum(s["lat"] for s in visible_spots) / len(visible_spots)
    avg_lng = sum(s["lng"] for s in visible_spots) / len(visible_spots)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body {{ margin:0; padding:0; background:#0a0a0b; }}
    #map {{ height:380px; width:100%; }}
    .leaflet-popup-content-wrapper,
    .leaflet-popup-tip {{
      background: #18181d !important;
      border: 1px solid #2a2a35 !important;
      box-shadow: none !important;
      color: #f0f0f5 !important;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {{zoomControl:true}}).setView([{avg_lat:.4f}, {avg_lng:.4f}], 13);
    L.tileLayer(
      'https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
      {{
        attribution: '&copy; <a href="https://carto.com">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
      }}
    ).addTo(map);
    {markers_js}
  </script>
</body>
</html>"""

    components.html(html, height=400, scrolling=False)


def spot_card(s):
    type_label = "DRINKS · WEED" if s["type"] == "weed" and "🥃" in s["tag"] else \
                 "WEED" if s["type"] == "weed" else "DRINKS"
    type_color = "#c6ff00" if s["type"] == "weed" else "#ffb300"

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {s['color']}; border-radius:4px;
            padding:20px 22px; margin-bottom:12px;">
  <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:10px;">
    <div style="flex:1; min-width:0;">
      <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:4px;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--text);
                     letter-spacing:1px;">{s['name']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                     padding:3px 8px; border:1px solid {type_color}; color:{type_color};
                     border-radius:2px; text-transform:uppercase;">{type_label}</span>
        <span style="font-size:16px;">{s['tag']}</span>
      </div>
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
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
              line-height:1.7; margin-bottom:10px;">{s['vibe']}</div>
  <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
                 background:var(--surface); border:1px solid var(--border);
                 border-radius:2px; padding:3px 8px;">🕐 {s['details']}</span>
  </div>
  <div style="background:var(--surface); border-left:2px solid {s['color']};
              padding:8px 12px; border-radius:0 3px 3px 0; margin-bottom:12px;">
    <span style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
                 color:var(--muted); text-transform:uppercase;">Pro tip · </span>
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


def hotspots_page():
    inject_page_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
    Vice Vault · Kingston, Jamaica
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">HOT SPOTS</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:6px;">
    Drinks. Weed. Kingston's finest.
  </div>
</div>
""")

    # Filter tabs
    filter_key = "hotspots_filter"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = "all"

    col_all, col_drinks, col_weed = st.columns(3)
    with col_all:
        if st.button("◈  All Spots", use_container_width=True,
                     type="primary" if st.session_state[filter_key] == "all" else "secondary",
                     key="hs_all"):
            st.session_state[filter_key] = "all"; st.rerun()
    with col_drinks:
        if st.button("🥃  Drinks", use_container_width=True,
                     type="primary" if st.session_state[filter_key] == "drinks" else "secondary",
                     key="hs_drinks"):
            st.session_state[filter_key] = "drinks"; st.rerun()
    with col_weed:
        if st.button("🌿  Weed", use_container_width=True,
                     type="primary" if st.session_state[filter_key] == "weed" else "secondary",
                     key="hs_weed"):
            st.session_state[filter_key] = "weed"; st.rerun()

    st.html("<div style='height:1rem'></div>")

    filt    = st.session_state[filter_key]
    visible = [
        s for s in SPOTS
        if filt == "all"
        or s["type"] == filt
        or (filt == "weed" and "weed" in s["type"])
    ]

    # ── Interactive map ───────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Map</div>
""")
    _build_leaflet_map(visible)

    st.html("<div style='height:1.5rem'></div>")

    # ── Count badge ───────────────────────────────────────────────────────────
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:16px;">
  {len(visible)} spot{"s" if len(visible) != 1 else ""} · Kingston & surrounds
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
