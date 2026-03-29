"""
Pages/hotspots.py — Kingston, Jamaica hot spots for drinks & weed
"""

import streamlit as st


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
section.main .block-container {
  padding-top:2rem !important; padding-bottom:3rem !important;
  max-width:900px !important;
}
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
  color:var(--lime) !important; box-shadow:none !important; transform:none !important;
}
.stButton > button {
  background:transparent !important; color:var(--soft) !important;
  border:1px solid var(--border) !important; border-radius:3px !important;
  font-family:'Space Mono',monospace !important; font-size:10px !important;
  letter-spacing:1.5px !important; text-transform:uppercase !important;
  transition:all 0.15s !important; box-shadow:none !important;
}
.stButton > button:hover {
  border-color:var(--lime) !important; color:var(--lime) !important;
  box-shadow:none !important; transform:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--lime) !important; color:#0a0a0b !important;
  border-color:var(--lime) !important; font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#d4ff1a !important; box-shadow:0 0 20px rgba(198,255,0,0.2) !important;
}
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""")


# ─── SPOT DATA ────────────────────────────────────────────────────────────────

SPOTS = [
    # ── DRINKS ────────────────────────────────────────────────────────────────
    {
        "name":    "Kingston Dub Club",
        "tag":     "🌿🥃",
        "type":    "weed",
        "vibe":    "Legendary hillside reggae venue. Open-air, epic city view, zero pretension.",
        "details": "Sundays only · 5PM–midnight · $2000 JMD entry · Cash only",
        "tip":     "Go before sunset to catch the view. Wear flat shoes — the steps are steep.",
        "rating":  4.6,
        "reviews": 475,
        "address": "7b Skyline Dr, Kingston",
        "maps":    "https://maps.google.com/?q=Kingston+Dub+Club+Jamaica",
        "color":   "#c6ff00",
        "place_id": "ChIJeZsZHMY-244RlxKUWiLmmhI",
        "lat": 18.0331659, "lng": -76.7452831,
    },
    {
        "name":    "Ribbiz UltraLounge",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "The spot everyone ends up at. High energy, bottle service, massive crowd on weekends.",
        "details": "Mon–Thu til 3AM · Fri–Sat til 5AM · Ardenne Emirates Plaza",
        "tip":     "Friday and Saturday are wild. Go early or book a table — it fills fast.",
        "rating":  4.1,
        "reviews": 3145,
        "address": "7-9 Ardenne Rd, New Kingston",
        "maps":    "https://maps.google.com/?q=Ribbiz+UltraLounge+Kingston+Jamaica",
        "color":   "#ffb300",
        "place_id": "ChIJoTipKPg-244RMpaNGHizPVo",
        "lat": 18.0154705, "lng": -76.7840958,
    },
    {
        "name":    "Club Cubana",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Cuban cocktails, live music, outdoor terrace on Hope Road. Mojitos are elite.",
        "details": "Tue–Thu til midnight · Fri til 2:30AM · Sat 7PM til 2:30AM",
        "tip":     "Classic mojito. Order it. That's the move.",
        "rating":  4.2,
        "reviews": 208,
        "address": "75 Hope Rd, Kingston",
        "maps":    "https://maps.google.com/?q=Club+Cubana+Kingston+Jamaica",
        "color":   "#ff2d78",
        "place_id": "ChIJ3VtaJgo_244Rt4i3oRVMj-s",
        "lat": 18.019587899999998, "lng": -76.7775369,
    },
    {
        "name":    "Dulcé Bar & Lounge",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Highest-rated lounge in Kingston. Chill outdoor setting, live music, great for dates.",
        "details": "Mon–Sat noon til 2AM · Sun 1PM–10PM · 22 Barbican Rd",
        "tip":     "Best for a Tuesday or Thursday — vibes without the weekend madness.",
        "rating":  4.8,
        "reviews": 15,
        "address": "22 Barbican Rd, Kingston",
        "maps":    "https://maps.google.com/?q=Dulce+Bar+Lounge+Kingston+Jamaica",
        "color":   "#00e5ff",
        "place_id": "ChIJ0_IutDA_244R53uOPo6cpgc",
        "lat": 18.021321, "lng": -76.7656563,
    },
    {
        "name":    "Mezza Luna Kingston",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Rooftop restaurant with a proper view. Cocktails, good food, date-night energy.",
        "details": "Daily noon–10:30PM · Rooftop at 110 Constant Spring Rd",
        "tip":     "Book ahead on weekends. The bartender Taylor is the one to talk to.",
        "rating":  4.6,
        "reviews": 302,
        "address": "110 Constant Spring Rd (Rooftop), Kingston",
        "maps":    "https://maps.google.com/?q=Mezza+Luna+Kingston+Jamaica",
        "color":   "#ffb300",
        "place_id": "ChIJU4ulfgA_244Rsw-Fc8amsDM",
        "lat": 18.032263, "lng": -76.7951551,
    },
    {
        "name":    "Di Bar at Blue Mahoe Estate",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Local favourite. Soca Thursdays, good bartenders, laid-back atmosphere.",
        "details": "Mon–Thu 3PM–midnight · Fri 3PM–2AM · Sat 3PM–midnight · Sun noon–6PM",
        "tip":     "Thursday night Soca session is the one. Bartender Theo knows his craft.",
        "rating":  4.1,
        "reviews": 122,
        "address": "5 Haining Rd, Kingston",
        "maps":    "https://maps.google.com/?q=Di+Bar+Blue+Mahoe+Estate+Kingston",
        "color":   "#c6ff00",
        "place_id": "ChIJRwg7LFM_244RrBQHNsavWQI",
        "lat": 18.0041531, "lng": -76.78401079999999,
    },
    {
        "name":    "Usain Bolt's Tracks & Records",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Sports bar vibes, Jamaican food, open til midnight daily. Tourist-friendly but genuinely fun.",
        "details": "Daily 11:30AM–midnight · 67 Constant Spring Rd",
        "tip":     "Go for drinks and wings. Skip the ribs. The Scotch bonnet hot sauce is legendary — buy a bottle.",
        "rating":  4.1,
        "reviews": 3470,
        "address": "67 Constant Spring Rd, Kingston",
        "maps":    "https://maps.google.com/?q=Usain+Bolt+Tracks+Records+Kingston",
        "color":   "#ffb300",
        "place_id": "ChIJI1Fzg0s-244R_tp6kNAgyGA",
        "lat": 18.0219849, "lng": -76.79773,
    },
    {
        "name":    "Offshore Rooftop Lounge",
        "tag":     "🥃",
        "type":    "drinks",
        "vibe":    "Rooftop with views, Jamaican food, karaoke nights. Casual Kingston energy.",
        "details": "Wed–Sun 3PM–midnight · Consumer Plaza, 103 Constant Spring Rd",
        "tip":     "Thursday pasta + $500 margarita deal is unbeatable. Karaoke on Sundays.",
        "rating":  3.8,
        "reviews": 319,
        "address": "103 Constant Spring Rd (Rooftop), Kingston",
        "maps":    "https://maps.google.com/?q=Offshore+Rooftop+Lounge+Kingston+Jamaica",
        "color":   "#00e5ff",
        "place_id": "ChIJFSPI_-I_244RJ-PW_DzjhUE",
        "lat": 18.0280394, "lng": -76.7965894,
    },
    # ── WEED ──────────────────────────────────────────────────────────────────
    {
        "name":    "Kaya Herb House",
        "tag":     "🌿",
        "type":    "weed",
        "vibe":    "Jamaica's premier licensed cannabis dispensary. Farm tour, high quality flower, knowledgeable staff.",
        "details": "Daily 9AM–10PM (Sat til 11PM) · 1 Weed Street, Drax Hall (St. Ann — day trip)",
        "tip":     "Worth the drive from Kingston. Staff product knowledge is exceptional. Rolling papers in-store.",
        "rating":  4.2,
        "reviews": 157,
        "address": "1 Weed Street, Drax Hall, St. Ann",
        "maps":    "https://maps.google.com/?q=Kaya+Herb+House+Drax+Hall+Jamaica",
        "color":   "#c6ff00",
        "place_id": "ChIJ_wBrdHP_2o4R9tF5cyCVf9E",
        "lat": 18.423933899999998, "lng": -77.1745351,
    },
    {
        "name":    "Bamboo Bar & Lounge",
        "tag":     "🌿🥃",
        "type":    "weed",
        "vibe":    "Chill outdoor spot. Good atmosphere, laid-back crowd, weed-friendly energy.",
        "details": "Daily 11AM–11:30PM · 8 Barbican Rd, Kingston",
        "tip":     "Good for an afternoon session. Bring your own — it's that kind of spot.",
        "rating":  4.0,
        "reviews": 72,
        "address": "8 Barbican Rd, Kingston",
        "maps":    "https://maps.google.com/?q=Bamboo+Bar+Lounge+Barbican+Kingston+Jamaica",
        "color":   "#c6ff00",
        "place_id": "ChIJlc9waCg_244RUBQKems0zLU",
        "lat": 18.0312862, "lng": -76.77619829999999,
    },
]


def stars(rating):
    filled = int(rating)
    half   = 1 if (rating - filled) >= 0.5 else 0
    empty  = 5 - filled - half
    return "★" * filled + ("½" if half else "") + "☆" * empty


def spot_card(s):
    type_label = "DRINKS" if s["type"] == "drinks" else "WEED" if s["type"] == "weed" else "DRINKS · WEED"
    type_color = "#ffb300" if s["type"] == "drinks" else "#c6ff00" if s["type"] == "weed" else "#00e5ff"

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
    inject_css()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Kingston, Jamaica</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:48px; color:var(--text);
              letter-spacing:3px; line-height:0.95;">
    HOT SPOTS
  </div>
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
                     type="primary" if st.session_state[filter_key] == "all" else "secondary"):
            st.session_state[filter_key] = "all"
            st.rerun()
    with col_drinks:
        if st.button("🥃  Drinks", use_container_width=True,
                     type="primary" if st.session_state[filter_key] == "drinks" else "secondary"):
            st.session_state[filter_key] = "drinks"
            st.rerun()
    with col_weed:
        if st.button("🌿  Weed", use_container_width=True,
                     type="primary" if st.session_state[filter_key] == "weed" else "secondary"):
            st.session_state[filter_key] = "weed"
            st.rerun()

    st.html("<div style='height:1.5rem'></div>")

    filt = st.session_state[filter_key]
    visible = [s for s in SPOTS if filt == "all" or s["type"] == filt or
               (filt == "weed" and "weed" in s["type"])]

    # Count badge
    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:16px;">
  {len(visible)} spot{"s" if len(visible) != 1 else ""} · Kingston & surrounds
</div>
""")

    for s in visible:
        spot_card(s)

    # Disclaimer
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
