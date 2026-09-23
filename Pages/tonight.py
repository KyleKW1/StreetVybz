"""
Pages/tonight.py — Secret feature, unlocked by your first match.
Pick where you're heading tonight and see which of your matches are going too.
"""

import streamlit as st

import social_db
from Pages.hotspots import get_all_spots, get_api_key, spot_card
from ui import esc, header


def _uid():
    return (st.session_state.get("user") or {}).get("id")


def is_unlocked(uid: int) -> bool:
    if st.session_state.get("_tonight_unlocked"):
        return True
    unlocked = social_db.has_match(uid)
    if unlocked:
        st.session_state["_tonight_unlocked"] = True
    return unlocked


def _locked():
    st.html("""
<div class="hd-card" style="text-align:center;padding:56px 24px;">
  <div class="hd-lock">🔒</div>
  <div class="hd-brand" style="font-size:clamp(26px,8vw,40px);letter-spacing:3px;margin:10px 0 6px;">SOMETHING'S HIDDEN HERE</div>
  <div class="hd-sub">Get your first match to unlock it.<br>
  <span style="color:var(--muted);">Hint: it's about where the night takes you.</span></div>
</div>
""")
    if st.button("Go find a match →", type="primary", use_container_width=True, key="tonight_go"):
        st.session_state.tab = "discover"
        st.rerun()


def tonight_page():
    uid = _uid()
    if not is_unlocked(uid):
        _locked()
        return

    if not st.session_state.get("_tonight_seen"):
        st.session_state["_tonight_seen"] = True
        st.balloons()
        st.toast("🌙 Tonight unlocked!")

    header("Unlocked", "Tonight 🌙",
           "Say where you're heading. Your matches see it — everyone else only sees a headcount.")

    mine = social_db.my_check_in(uid)
    going = social_db.tonight_by_spot(uid)

    if mine:
        c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
        with c1:
            st.html(f'<div class="hd-card hot" style="padding:14px 18px;border-radius:14px;">'
                    f'<div class="hd-kicker">You\'re heading to</div>'
                    f'<div class="hd-title" style="font-size:26px;margin:0;">{esc(mine)}</div></div>')
        with c2:
            if st.button("Change", use_container_width=True, key="tonight_clear"):
                social_db.clear_check_in(uid)
                st.rerun()

    me = social_db.get_profile(uid) or {}
    city = (me.get("city") or "").strip()
    live = me.get("location_mode") == "live"
    with st.spinner("Finding spots near you…"):
        all_spots = get_all_spots(get_api_key(), city or None,
                                  me.get("lat") if live else None, me.get("lon") if live else None)

    kind = st.segmented_control("Show", ["all", "drinks", "cannabis"], default="all", key="tonight_type",
                                format_func=lambda k: {"all": "All", "drinks": "🥃 Drinks",
                                                       "cannabis": "🌿 Cannabis"}[k])
    spots = [s for s in all_spots if kind in (None, "all") or s["type"] == kind]
    # Busiest spots (most matches, then most people) first
    spots.sort(key=lambda s: (-len(going.get(s["name"], {}).get("matches", [])),
                              -going.get(s["name"], {}).get("count", 0)))

    if not all_spots:
        st.html(f'<div class="hd-card" style="text-align:center;padding:28px 20px;">'
                f'<div class="hd-title" style="font-size:26px;">No spots listed in {esc(city.title() or "your area")} yet</div>'
                f'<div class="hd-sub">Say where you\'re heading below and your matches will see it.</div></div>')
        st.html("<div style='height:12px'></div>")

    for s in spots:
        info = going.get(s["name"], {"count": 0, "matches": []})
        spot_card(s)
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            bits = []
            if info["matches"]:
                bits.append(f'<span class="hd-chip magenta">💘 {esc(", ".join(info["matches"]))} going</span>')
            if info["count"]:
                bits.append(f'<span class="hd-chip">👥 {info["count"]} heading here</span>')
            if bits:
                st.html(f'<div class="hd-chips" style="margin:0;">{"".join(bits)}</div>')
        with c2:
            if mine == s["name"]:
                st.button("✓ You're going", disabled=True, use_container_width=True, key=f"go_{s['name']}")
            elif st.button("I'm going here", type="primary", use_container_width=True, key=f"go_{s['name']}"):
                social_db.check_in(uid, s["name"])
                st.toast(f"See you at {s['name']} 🌙")
                st.rerun()
        st.html("<div style='height:14px'></div>")

    _elsewhere(uid, mine, going, {s["name"] for s in all_spots})


def _elsewhere(uid: int, mine, going: dict, listed: set):
    """Spots that aren't in the list: where your matches are going, and your own pick."""
    others = {name: info for name, info in going.items() if name not in listed and info["matches"]}
    if others:
        st.html('<div class="hd-kicker" style="margin:8px 0;">Your matches are also heading to</div>')
        for name, info in others.items():
            c1, c2 = st.columns([3, 2], vertical_alignment="center")
            with c1:
                st.html(f'<div class="hd-title" style="font-size:22px;margin:0;">{esc(name)}</div>'
                        f'<div class="hd-chips" style="margin:4px 0 0;"><span class="hd-chip magenta">'
                        f'💘 {esc(", ".join(info["matches"]))} going</span></div>')
            with c2:
                if mine == name:
                    st.button("✓ You're going", disabled=True, use_container_width=True, key=f"go_x_{name}")
                elif st.button("Me too", type="primary", use_container_width=True, key=f"go_x_{name}"):
                    social_db.check_in(uid, name)
                    st.toast(f"See you at {name} 🌙")
                    st.rerun()
        st.html("<div style='height:14px'></div>")

    st.html('<div class="hd-kicker" style="margin:8px 0;">Going somewhere not listed?</div>')
    with st.form("tonight_custom", clear_on_submit=True, border=False):
        c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
        with c1:
            spot = st.text_input("Spot name", max_chars=80, placeholder="e.g. Cafe Blue, Hope Road",
                                 label_visibility="collapsed")
        with c2:
            go = st.form_submit_button("I'm going", use_container_width=True)
    if go and spot.strip():
        social_db.check_in(uid, " ".join(spot.split()))
        st.toast(f"See you at {spot.strip()} 🌙")
        st.rerun()
