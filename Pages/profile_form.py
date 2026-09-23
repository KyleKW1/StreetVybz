"""
Pages/profile_form.py — Profile editor (first-time setup and the Me tab),
18+ birthdate gate and live-location capture.
"""

from datetime import date

import streamlit as st

import social_db
from matching import (LIFESTYLE, INTENTS, GENDERS, SHOW_ME, MIN_AGE,
                      is_adult, age_on, round_coord)
from ui import header, open_quiz


def _uid():
    return (st.session_state.get("user") or {}).get("id")


# ─── LOCATION ────────────────────────────────────────────────────────────────

def location_capture(uid: int, profile: dict, key: str):
    """Ask the browser for a location; store it rounded to ~1 km."""
    has_fix = profile.get("lat") is not None
    st.caption("📍 Location set — others only ever see a rough distance."
               if has_fix else "📍 No location yet — tap below and allow access in your browser.")

    pending = f"_geo_pending_{key}"
    if st.button("📍 Update my location" if has_fix else "📍 Use my current location",
                 key=f"geo_btn_{key}", use_container_width=True):
        st.session_state[pending] = st.session_state.get(pending, 0) + 1

    if st.session_state.get(pending):
        try:
            from streamlit_js_eval import get_geolocation
        except ImportError:
            st.error("Live location isn't available right now — use City only.")
            st.session_state.pop(pending, None)
            return
        loc = get_geolocation(component_key=f"geo_{key}_{st.session_state[pending]}")
        if not loc:
            st.info("Waiting for your browser… allow location access if asked.")
        elif "coords" in loc:
            lat, lon = loc["coords"]["latitude"], loc["coords"]["longitude"]
            if social_db.save_profile(uid, {"lat": round_coord(lat), "lon": round_coord(lon)}):
                st.session_state.pop(pending, None)
                st.session_state.pop("disc_queue", None)
                st.toast("Location updated 📍")
                st.rerun()
            else:
                st.error("Couldn't save your location — try again.")
        else:
            st.session_state.pop(pending, None)
            st.warning("Location was blocked or unavailable. Allow it in your browser settings, "
                       "or switch to City only.")


# ─── FORM ────────────────────────────────────────────────────────────────────

def profile_form(uid: int, profile: dict | None, key: str, submit_label: str) -> bool:
    """Render the editor. Returns True once a valid profile has been saved."""
    p = profile or {}
    today = date.today()

    birthdate = p.get("birthdate")
    if not birthdate:
        birthdate = st.date_input(
            "Your birthday", value=None, key=f"{key}_bd",
            min_value=date(today.year - 100, 1, 1), max_value=today, format="DD/MM/YYYY",
            help=f"Hidden is {MIN_AGE}+ only. This can't be changed later.",
        )

    intent = st.segmented_control(
        "I'm here for", options=list(INTENTS), format_func=lambda k: {
            "date": "💘 Dating", "linkup": "🤝 Link-ups", "both": "✨ Both"}[k],
        default=p.get("intent") or "both", key=f"{key}_intent",
    )

    c1, c2 = st.columns(2)
    with c1:
        gender = st.selectbox("I am", GENDERS, key=f"{key}_gender",
                              index=GENDERS.index(p["gender"]) if p.get("gender") in GENDERS else 0)
    with c2:
        show_me = p.get("show_me") or "Everyone"
        if intent in ("date", "both"):
            show_me = st.selectbox("Date", SHOW_ME, key=f"{key}_showme",
                                   index=SHOW_ME.index(show_me) if show_me in SHOW_ME else 0)

    st.html('<div class="hd-kicker" style="margin:14px 0 4px;">Your lifestyle</div>')
    lifestyle = {}
    for field, (label, opts) in LIFESTYLE.items():
        current = p.get(field)
        choice = st.select_slider(label, options=opts, key=f"{key}_{field}",
                                  value=opts[int(current)] if current is not None else opts[1])
        lifestyle[field] = opts.index(choice)

    age_min, age_max = st.slider("Show me people aged", MIN_AGE, 80, key=f"{key}_ages",
                                 value=(int(p.get("age_min") or MIN_AGE), min(80, int(p.get("age_max") or 80))))

    st.html('<div class="hd-kicker" style="margin:14px 0 4px;">Where you are</div>')
    city = st.text_input("City / area", value=p.get("city") or "", key=f"{key}_city",
                         placeholder="e.g. Kingston", max_chars=100)
    mode = st.radio("Match by", ["live", "city"], horizontal=True, key=f"{key}_mode",
                    index=0 if p.get("location_mode") == "live" else 1,
                    format_func=lambda m: "📍 Live distance" if m == "live" else "🏙 City only")
    max_km = int(p.get("max_km") or 25)
    if mode == "live":
        max_km = st.slider("Max distance (km)", 1, 100, max_km, key=f"{key}_km")
        location_capture(uid, p, key)
        st.caption("People without live location still show up if they're in the same city.")

    bio = st.text_area("About you (optional)", value=p.get("bio") or "", key=f"{key}_bio",
                       max_chars=300, height=90, placeholder="What's your ideal night out?")

    if not st.button(submit_label, type="primary", use_container_width=True, key=f"{key}_save"):
        return False

    if not birthdate:
        st.error("Add your birthday.")
        return False
    if not is_adult(birthdate):
        st.error(f"Sorry — Hidden is for people {MIN_AGE} and over.")
        return False
    if not intent:
        st.error("Pick what you're here for.")
        return False
    if not city.strip():
        st.error("Add your city or area so we can find people near you.")
        return False

    fields = {
        "birthdate": birthdate if isinstance(birthdate, date) else str(birthdate)[:10],
        "intent": intent, "gender": gender, "show_me": show_me,
        "city": city.strip(), "location_mode": mode, "max_km": max_km,
        "age_min": age_min, "age_max": age_max, "bio": bio.strip() or None, **lifestyle,
    }
    if social_db.save_profile(uid, fields):
        st.session_state.pop("disc_queue", None)
        return True
    st.error("Couldn't save — check your connection and try again.")
    return False


# ─── FIRST-TIME SETUP ────────────────────────────────────────────────────────

def setup_page():
    uid = _uid()
    profile = social_db.get_profile(uid) or {}
    if profile.get("birthdate") and not is_adult(profile["birthdate"]):
        header("Hidden", "18+ only", f"You must be {MIN_AGE} or older to use Hidden.")
        return
    header("Step 1 of 2", "Set up your vibe",
           "Tell us how you live and where you are — we'll find people who match.")
    if st.button("How does Hidden work?", key="setup_intro", type="tertiary"):
        from Pages.intro import open_intro
        open_intro("setup")
    if profile_form(uid, profile, "setup", "Next →"):
        st.session_state.tab = "quiz_offer"
        st.rerun()


def quiz_offer_page():
    st.html('<div class="hd-brand" style="margin-bottom:10px;">HIDDEN</div>')
    header("Step 2 of 2", "Sharpen your matches",
           "Read Between The Lines is a quick scenario quiz. It powers your vibe score, "
           "and your matches see your result.")
    st.html("""
<div class="hd-card" style="padding:20px 22px;">
  <div class="hd-why" style="margin:0;padding:0;border:0;">
    <div>🎭 &nbsp;Real-life scenarios — pick what you'd actually do</div>
    <div>🔒 &nbsp;Hidden desires: a match only sees the ones you both share</div>
    <div>🎯 &nbsp;Worth 40% of every vibe score</div>
    <div>⏱ &nbsp;About 5 minutes</div>
  </div>
</div>""")
    st.html("<div style='height:12px'></div>")
    if st.button("Take the quiz →", type="primary", use_container_width=True, key="offer_take"):
        open_quiz("discover")
    if st.button("Skip for now", use_container_width=True, key="offer_skip"):
        st.session_state.tab = "discover"
        st.rerun()


def age_text(profile: dict) -> str:
    a = age_on(profile.get("birthdate"))
    return str(a) if a is not None else ""
