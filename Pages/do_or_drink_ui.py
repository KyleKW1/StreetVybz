"""
Pages/do_or_drink_ui.py — All rendering phases for Do or Drink.

New in this version:
- Game over screen shows highlights from the session history
- Setup screen has "Join a game" option — enter a room code to join a host's game
- Host can share a room code so players don't need to know each other's usernames
"""

import random
import time
import streamlit as st

from Pages.do_or_drink_core import (
    _db, _me, _has_data, _player_vice_summary, _my_full_summary,
    build_group_profile, get_openai_client, generate_dares_for_player,
    reset_state, _VICE_LABELS,
)
from styles import inject_page_css

_HEAT_LABELS = {1: "mild", 2: "spicy", 3: "atomic"}
_HEAT_COLORS = {1: "var(--lime)", 2: "var(--amber)", 3: "var(--magenta)"}
_TYPE_ICONS  = {"DO": "⚡", "TRUTH": "💬"}


# ─── DARE TIMER ──────────────────────────────────────────────────────────────

def _inject_dare_timer(seconds: int = 30):
    st.html(f"""
<style>
@keyframes timer-flash {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}
#dod-dare-timer {{
  position:fixed; top:16px; right:16px; z-index:9990;
  background:var(--card); border:2px solid var(--lime);
  border-radius:50%; width:56px; height:56px;
  display:flex; align-items:center; justify-content:center;
  font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--lime);
  transition:border-color 0.4s, color 0.4s;
}}
#dod-dare-timer.amber {{ border-color:var(--amber); color:var(--amber); }}
#dod-dare-timer.hot   {{ border-color:var(--magenta); color:var(--magenta); animation:timer-flash 0.5s infinite; }}
</style>
<script>
(function() {{
  if (document.getElementById("dod-dare-timer")) return;
  var el = document.createElement("div");
  el.id  = "dod-dare-timer";
  el.textContent = "{seconds}";
  document.body.appendChild(el);
  var remaining = {seconds};
  var iv = setInterval(function() {{
    remaining--;
    if (remaining < 0) {{ clearInterval(iv); el.remove(); return; }}
    el.textContent = remaining;
    if (remaining <= 5)       {{ el.className = "hot"; }}
    else if (remaining <= 15) {{ el.className = "amber"; }}
    else                      {{ el.className = ""; }}
  }}, 1000);
}})();
</script>
""")


# ─── SETUP ───────────────────────────────────────────────────────────────────

def render_setup():
    inject_page_css()
    my_name, my_id = _me()

    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
    Hidden · Party Mode
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:56px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">
    DO OR<br><span style="color:var(--lime);">DRINK</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    AI reads your logs. Your habits become the dares. Yuh brave?
  </div>
</div>
""")

    if st.session_state.dod_error:
        st.error(st.session_state.dod_error)
        st.session_state.dod_error = ""

    # ── Join vs Host toggle ───────────────────────────────────────────────────
    st.session_state.setdefault("dod_setup_mode", "host")
    col_host, col_join = st.columns(2)
    with col_host:
        if st.button("🎯  Host a game", use_container_width=True,
                     type="primary" if st.session_state.dod_setup_mode == "host" else "secondary",
                     key="mode_host"):
            st.session_state.dod_setup_mode = "host"; st.rerun()
    with col_join:
        if st.button("🔗  Join with code", use_container_width=True,
                     type="primary" if st.session_state.dod_setup_mode == "join" else "secondary",
                     key="mode_join"):
            st.session_state.dod_setup_mode = "join"; st.rerun()

    st.html("<div style='height:20px'></div>")

    # ── JOIN FLOW ─────────────────────────────────────────────────────────────
    if st.session_state.dod_setup_mode == "join":
        st.html("""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:2px solid var(--lime); border-radius:4px;
            padding:20px 22px; margin-bottom:20px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft); line-height:1.8;">
    The host shares a 6-character room code. Enter it here to join their game.
    Your vice profile will be loaded automatically.
  </div>
</div>
""")
        code_input = st.text_input(
            "Room code",
            placeholder="ABC123",
            key="dod_join_code_input",
            max_chars=6,
        ).upper().strip()

        if st.button("Join Game →", type="primary", use_container_width=True, key="dod_join_btn"):
            if not code_input or len(code_input) < 6:
                st.error("Enter the full 6-character room code.")
            else:
                result = _db("join_dod_room", code_input, my_id, my_name)
                if result == "not_found":
                    st.error(f"Room '{code_input}' not found or already started.")
                elif result == "already_in":
                    st.success("You're already in this room. Waiting for the host to start…")
                elif result and isinstance(result, dict):
                    # Load the room's players into session state
                    players = result.get("players", [])
                    mode    = result.get("mode", "regular")
                    st.session_state.dod_mode    = mode
                    st.session_state.dod_room_code = code_input
                    st.success(f"Joined! Room '{code_input}' · {len(players)} player(s) so far. Wait for the host to start.")
                    st.rerun()
                else:
                    st.error("Couldn't join the room. Check the code and try again.")

        # Show waiting state if already joined
        if st.session_state.get("dod_room_code"):
            code  = st.session_state.dod_room_code
            room  = _db("get_dod_room", code)
            if room:
                players = room.get("players", [])
                st.html(f"""
<div style="background:var(--card); border:1px solid var(--lime); border-radius:4px;
            padding:16px 18px; margin-top:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:8px;">
    Room {code} · Waiting for host
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">
    {len(players)} player{'s' if len(players) != 1 else ''} in the room.
    The host will start when everyone's ready.
  </div>
</div>
""")
                if st.button("↺ Refresh", key="dod_join_refresh"):
                    st.rerun()
        return

    # ── HOST FLOW ─────────────────────────────────────────────────────────────

    # Mode selector
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Choose the vibe</div>
""")
    mode = st.session_state.dod_mode
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🍹  Regular", use_container_width=True,
                     type="primary" if mode == "regular" else "secondary", key="mode_reg"):
            st.session_state.dod_mode = "regular"; st.rerun()
    with c2:
        if st.button("🔥  Kinky", use_container_width=True,
                     type="primary" if mode == "kinky" else "secondary", key="mode_kink"):
            st.session_state.dod_mode = "kinky"; st.rerun()
    with c3:
        if st.button("⚡  Both", use_container_width=True,
                     type="primary" if mode == "both" else "secondary", key="mode_both"):
            st.session_state.dod_mode = "both"; st.rerun()

    mode_descs = {
        "regular": "Social dares. Mild embarrassment. Caribbean lime energy.",
        "kinky":   "Seductive, physical, explicitly adult. Every dare is heat:2 or heat:3.",
        "both":    "Half social, half seductive and explicit. The game builds from funny to charged.",
    }
    st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:20px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);">
    {mode_descs[st.session_state.dod_mode]}
  </div>
</div>
""")

    # Room code — generate one for sharing
    if not st.session_state.get("dod_room_code"):
        if st.button("◈  Generate room code for others to join", use_container_width=True,
                     key="dod_gen_code"):
            code = _db("create_dod_room", my_id, my_name, st.session_state.dod_mode)
            if code:
                st.session_state.dod_room_code = code
                st.rerun()
            else:
                st.warning("Couldn't create a room code right now — you can still add players by username.")
    else:
        code = st.session_state.dod_room_code
        # Refresh room players from DB
        room = _db("get_dod_room", code)
        if room:
            db_players = room.get("players", [])
            # Merge DB players into session state (new joins)
            existing_ids = {p["user_id"] for p in st.session_state.dod_players}
            for p in db_players:
                if p["user_id"] not in existing_ids:
                    p["vice_summary"] = _player_vice_summary(p["user_id"]) if p.get("user_id") else {}
                    st.session_state.dod_players.append(p)

        st.html(f"""
<div style="background:#0f1a10; border:1px solid var(--lime); border-radius:4px;
            padding:14px 18px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
              text-transform:uppercase; color:var(--lime); margin-bottom:6px;">
    Room Code — share with players
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--lime);
              letter-spacing:6px; line-height:1;">{code}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); margin-top:6px;">
    They go to Do or Drink → Join with code → enter {code}
  </div>
</div>
""")
        col_r, col_c = st.columns(2)
        with col_r:
            if st.button("↺ Refresh players", use_container_width=True, key="dod_refresh_room"):
                st.rerun()
        with col_c:
            if st.button("✕ Clear code", use_container_width=True, key="dod_clear_code"):
                st.session_state.pop("dod_room_code", None)
                st.rerun()

    # Players
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px; margin-top:4px;">
  Players
</div>
""")
    players    = st.session_state.dod_players
    me_already = any(p["username"] == my_name for p in players)
    if not me_already and my_id:
        players.append({
            "username":     my_name,
            "user_id":      my_id,
            "vice_summary": _my_full_summary(),
            "is_host":      True,
        })
        st.session_state.dod_players = players

    # Refresh summaries that are stale (cache handles this cheaply)
    for p in players:
        if p.get("user_id"):
            p["vice_summary"] = _player_vice_summary(p["user_id"])

    for i, p in enumerate(players):
        col_name, col_remove = st.columns([5, 1])
        with col_name:
            vs         = p.get("vice_summary", {})
            counts     = vs.get("counts", {})
            quiz       = vs.get("quiz", {})
            has_d      = _has_data(vs)
            vice_parts = [f"{_VICE_LABELS.get(vk, vk)}: *hidden*" for vk in counts.keys()]
            if quiz.get("profile_name"):
                vice_parts.append(f"profile: {quiz['profile_name']}")
            vice_str   = "  ·  ".join(vice_parts) if vice_parts else "No log data — generic dares"
            host_badge = " · HOST" if p.get("is_host") else ""
            d_color    = "var(--lime)" if has_d else "var(--muted)"
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {'var(--lime)' if p.get('is_host') else 'var(--border)'};
            border-radius:3px; padding:12px 14px; margin-bottom:6px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; letter-spacing:1px;
              color:{'var(--lime)' if p.get('is_host') else 'var(--text)'};">
    {p['username']}{host_badge}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:1px;
              text-transform:uppercase; color:{d_color}; margin-top:4px;">{vice_str}</div>
</div>
""")
        with col_remove:
            if not p.get("is_host"):
                st.html("<div style='height:6px'></div>")
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.dod_players.pop(i); st.rerun()

    st.html("<div style='height:6px'></div>")
    new_username = st.text_input(
        "Add player by username", placeholder="Their Hidden username", key="dod_add_input")
    if st.button("Add Player →", key="dod_add_btn"):
        uname = new_username.strip()
        if not uname:
            st.warning("Enter a username.")
        elif any(p["username"].lower() == uname.lower() for p in players):
            st.warning("Already in the game.")
        else:
            user = _db("get_user_by_username", uname)
            if not user:
                st.error(f"Can't find '{uname}' — they need a Hidden account.")
            else:
                uid = user["id"]
                st.session_state.dod_players.append({
                    "username":     user["username"],
                    "user_id":      uid,
                    "vice_summary": _player_vice_summary(uid),
                    "is_host":      False,
                })
                st.rerun()

    st.html("<div style='height:20px'></div>")
    n_players = len(players)

    if players:
        with_data    = [p for p in players if _has_data(p.get("vice_summary", {}))]
        all_have     = len(with_data) == n_players
        any_have     = len(with_data) > 0
        if all_have:
            smsg, scol = "✓ All players have log data — fully personalised dares.", "var(--lime)"
        elif any_have:
            names      = ", ".join(p["username"] for p in with_data)
            smsg, scol = f"◈ {names} {'has' if len(with_data)==1 else 'have'} data — shaping the whole game.", "var(--amber)"
        else:
            smsg, scol = "◇ No log data — sharp generic Caribbean dares for everyone.", "var(--muted)"

        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
              text-transform:uppercase; color:{scol};">{smsg}</div>
</div>
""")

    if n_players < 2:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:center; padding:12px 0;">
  Add at least one more player to start.</div>
""")
    else:
        if st.button(f"Generate Dares & Start →  ({n_players} players)",
                     type="primary", use_container_width=True, key="dod_start"):
            # Close the room so new joins are blocked
            if st.session_state.get("dod_room_code"):
                _db("close_dod_room", st.session_state.dod_room_code)
            st.session_state.dod_phase = "generating"
            st.rerun()

    st.html("""
<div style="margin-top:16px; padding:12px 14px; background:var(--surface);
            border:1px solid var(--border); border-radius:3px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); line-height:1.9;">
    12 dares per player · AI reads each player's logs and desire profile.<br>
    30-second dare timer · Skipped cards return to the deck.
  </div>
</div>
""")


# ─── GENERATING ──────────────────────────────────────────────────────────────

def render_generating():
    inject_page_css()
    players = st.session_state.dod_players
    mode    = st.session_state.dod_mode

    ph_title = st.empty()
    ph_bar   = st.empty()
    ph_msg   = st.empty()

    try:
        client = get_openai_client()
    except Exception:
        # No AI available — the game still runs on the built-in dare deck.
        client = None

    any_has_data  = any(_has_data(p.get("vice_summary", {})) for p in players)
    group_profile = build_group_profile(players) if any_has_data else {}
    all_dares     = {}

    for i, p in enumerate(players):
        pct      = int((i / len(players)) * 90)
        has_d    = _has_data(p.get("vice_summary", {}))
        strategy = "personalising" if has_d else ("using group vibe" if any_has_data else "generating")
        ph_title.markdown("**Building dare deck…**")
        ph_bar.progress(pct)
        ph_msg.caption(f"{p['username']} — {strategy}…")

        dares = generate_dares_for_player(
            player_name=p["username"],
            vice_summary=p.get("vice_summary", {}),
            group_profile=group_profile,
            any_group_has_data=any_has_data,
            mode=mode,
            client=client,
        )
        all_dares[p["username"]] = dares
        time.sleep(0.2)

    ph_bar.progress(100)
    ph_msg.caption("Shuffling the deck…")

    max_dares = max((len(all_dares[p["username"]]) for p in players), default=0)
    deck = []
    for round_idx in range(max_dares):
        round_cards = []
        for p in players:
            if round_idx < len(all_dares[p["username"]]):
                round_cards.append({"player": p["username"], "dare_idx": round_idx})
        random.shuffle(round_cards)
        deck.extend(round_cards)

    st.session_state.dod_dares       = all_dares
    st.session_state.dod_deck        = deck
    st.session_state.dod_scores      = {
        p["username"]: {"drinks": 0, "done": 0, "skipped": 0} for p in players
    }
    st.session_state.dod_history     = []
    st.session_state.dod_cur_card    = None
    st.session_state.dod_timer_start = None
    st.session_state.dod_phase       = "game"
    st.rerun()


# ─── GAME ────────────────────────────────────────────────────────────────────

def render_game():
    inject_page_css()
    scores  = st.session_state.dod_scores
    deck    = st.session_state.dod_deck
    dares   = st.session_state.dod_dares
    history = st.session_state.dod_history
    cur     = st.session_state.dod_cur_card
    mode    = st.session_state.dod_mode

    total_cards = sum(len(v) for v in dares.values())
    played      = len([h for h in history if h.get("result") != "skipped"])
    remaining   = len(deck)

    mode_colors = {"regular": "var(--lime)", "kinky": "var(--magenta)", "both": "var(--cyan)"}
    mode_label  = {"regular": "Regular", "kinky": "Kinky", "both": "Mixed"}

    st.html(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start;
            border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px;">
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
                letter-spacing:3px; line-height:1;">DO OR DRINK</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:{mode_colors.get(mode,'var(--lime)')};
                margin-top:2px;">{mode_label.get(mode,'Regular')} mode · {remaining} cards left</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--muted);">{played}/{total_cards}</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                text-transform:uppercase; letter-spacing:1px;">played</div>
  </div>
</div>
""")

    cols = st.columns(len(scores))
    for i, (uname, s) in enumerate(scores.items()):
        with cols[i]:
            is_active = cur and cur.get("player") == uname
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            {'border-top:2px solid var(--lime)' if is_active else 'border-top:2px solid var(--border)'};
            border-radius:3px; padding:12px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:15px; letter-spacing:1px;
              color:{'var(--lime)' if is_active else 'var(--text)'};">{uname}</div>
  <div style="display:flex; justify-content:center; gap:10px; margin-top:6px;">
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--lime);">{s['done']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;">did it</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--magenta);">{s['drinks']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;">drinks</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--muted);">{s.get('skipped', 0)}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;">skipped</div>
    </div>
  </div>
</div>
""")

    st.html("<div style='height:18px'></div>")

    if cur is None:
        if not deck:
            render_game_over()
            return
        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:48px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">PULL A CARD</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">Tap below to see who's up.</div>
</div>
""")
        if st.button("⚡  Draw Next Card", type="primary", use_container_width=True, key="draw_card"):
            if deck:
                card_ref = st.session_state.dod_deck.pop(0)
                player   = card_ref["player"]
                dare     = dares[player][card_ref["dare_idx"]]
                st.session_state.dod_cur_card    = {"player": player, "dare": dare}
                st.session_state.dod_timer_start = time.time()
            st.rerun()
    else:
        player     = cur["player"]
        dare       = cur["dare"]
        heat       = dare.get("heat", 2)
        dtype      = dare.get("type", "DO")
        heat_color = _HEAT_COLORS.get(heat, "var(--amber)")
        heat_label = _HEAT_LABELS.get(heat, "spicy")
        type_icon  = _TYPE_ICONS.get(dtype, "⚡")

        _inject_dare_timer(30)

        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {heat_color}; border-radius:4px; padding:28px 26px; margin-bottom:14px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; letter-spacing:3px;
                color:{heat_color}; line-height:1;">{player}</div>
    <div style="display:flex; gap:8px;">
      <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
                  text-transform:uppercase; color:{heat_color}; border:1px solid {heat_color};
                  padding:3px 10px; border-radius:2px;">{dtype} {type_icon}</div>
      <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
                  text-transform:uppercase; color:{heat_color}; border:1px solid {heat_color};
                  padding:3px 10px; border-radius:2px; opacity:0.7;">{heat_label}</div>
    </div>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:17px; color:var(--text);
              line-height:1.65; margin-bottom:20px;">{dare['dare']}</div>
  <div style="background:var(--surface); border-left:2px solid var(--magenta);
              padding:10px 14px; border-radius:0 3px 3px 0;">
    <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
                text-transform:uppercase; color:var(--magenta); margin-bottom:4px;">OR DRINK</div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">{dare['drink']}</div>
  </div>
</div>
""")

        col_done, col_drink, col_skip = st.columns([2, 2, 1])
        with col_done:
            if st.button("✓  Did it", type="primary", use_container_width=True, key="btn_done"):
                st.session_state.dod_scores[player]["done"] += 1
                st.session_state.dod_history.append({**cur, "result": "done"})
                st.session_state.dod_cur_card = None; st.session_state.dod_timer_start = None
                st.rerun()
        with col_drink:
            if st.button("🍹  Drinking", use_container_width=True, key="btn_drink"):
                st.session_state.dod_scores[player]["drinks"] += 1
                st.session_state.dod_history.append({**cur, "result": "drink"})
                st.session_state.dod_cur_card = None; st.session_state.dod_timer_start = None
                st.rerun()
        with col_skip:
            if st.button("Skip", use_container_width=True, key="btn_skip"):
                st.session_state.dod_scores[player]["skipped"] = st.session_state.dod_scores[player].get("skipped", 0) + 1
                st.session_state.dod_history.append({**cur, "result": "skipped"})
                rem = len(st.session_state.dod_deck)
                try:
                    dare_idx = dares[player].index(dare)
                except ValueError:
                    dare_idx = 0
                insert_at = random.randint(max(1, rem * 2 // 3), max(1, rem))
                st.session_state.dod_deck.insert(insert_at, {"player": player, "dare_idx": dare_idx})
                st.session_state.dod_cur_card = None; st.session_state.dod_timer_start = None
                st.rerun()

    if history:
        st.html("<div style='height:20px'></div>")
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Recent</div>
""")
        for h in reversed(history[-5:]):
            p      = h["player"]
            d      = h["dare"]["dare"][:80] + ("…" if len(h["dare"]["dare"]) > 80 else "")
            result = h.get("result", "done")
            r_icon, r_col = {"done": ("✓", "var(--lime)"), "drink": ("🍹", "var(--magenta)"), "skipped": ("↺", "var(--muted)")}.get(result, ("✓", "var(--lime)"))
            skipped_badge = '<span style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--muted); margin-left:6px; border:1px solid var(--border); padding:1px 5px; border-radius:2px;">SKIPPED</span>' if result == "skipped" else ''
            st.html(f"""
<div style="display:flex; gap:10px; align-items:flex-start; padding:8px 0; border-bottom:1px solid var(--border);">
  <div style="font-family:'Space Mono',monospace; font-size:14px; color:{r_col}; flex-shrink:0;">{r_icon}</div>
  <div>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft); letter-spacing:1px; text-transform:uppercase;">{p}</span>
    {skipped_badge}
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted); line-height:1.5;">{d}</div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    if st.button("End Game", use_container_width=True, key="end_game"):
        st.session_state.dod_phase = "gameover"
        st.rerun()


# ─── GAME OVER ───────────────────────────────────────────────────────────────

def render_game_over():
    inject_page_css()
    scores  = st.session_state.dod_scores
    history = st.session_state.dod_history

    winner  = max(scores, key=lambda u: scores[u]["done"])   if scores else "—"
    drinker = max(scores, key=lambda u: scores[u]["drinks"]) if scores else "—"

    drinker_drinks = scores.get(drinker, {}).get("drinks", 0)
    drinker_html = f'<div style="margin-top:12px;font-family:DM Sans,sans-serif;font-size:12px;color:var(--magenta);">🍹 {drinker} drank the most — {drinker_drinks} times</div>' if winner != drinker else ''
    winner_done = scores.get(winner, {}).get('done', 0)
    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--lime); border-radius:4px;
            padding:32px 28px; text-align:center; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Game Over</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--lime);
              letter-spacing:3px; line-height:0.9; margin-bottom:8px;">{winner.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--soft);">
    held it down the most — {winner_done} dares completed
  </div>
  {drinker_html}
</div>
""")

    # ── Session highlights ────────────────────────────────────────────────────
    done_history    = [h for h in history if h.get("result") == "done"]
    drink_history   = [h for h in history if h.get("result") == "drink"]
    wildest         = max(done_history, key=lambda h: h["dare"].get("heat", 0), default=None)
    most_refused    = max(scores, key=lambda u: scores[u]["drinks"], default=None) if scores else None
    brave_dare      = next((h for h in done_history if h["dare"].get("heat", 0) == 3), None)

    highlights = []
    if wildest:
        highlights.append(("🔥 Wildest dare completed", wildest["player"], wildest["dare"]["dare"][:90]))
    if brave_dare and brave_dare != wildest:
        highlights.append(("⚡ Went full atomic", brave_dare["player"], brave_dare["dare"]["dare"][:90]))
    if drink_history:
        most_drunk_player = max(scores, key=lambda u: scores[u]["drinks"]) if scores else None
        if most_drunk_player:
            highlights.append(("🍹 Biggest drinker", most_drunk_player,
                               f"{scores[most_drunk_player]['drinks']} drinks taken"))
    skipped_most = max(scores, key=lambda u: scores[u].get("skipped", 0), default=None) if scores else None
    if skipped_most and scores.get(skipped_most, {}).get("skipped", 0) > 0:
        highlights.append(("↺ Most skips", skipped_most,
                           f"{scores[skipped_most].get('skipped',0)} cards skipped"))

    if highlights:
        st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">
  Session Highlights
</div>
""")
        for label, player, detail in highlights:
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:14px 16px; margin-bottom:8px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted); margin-bottom:4px;">{label}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:var(--lime);
              letter-spacing:1px; margin-bottom:4px;">{player.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
              line-height:1.5; font-style:italic;">"{detail}"</div>
</div>
""")
        st.html("<div style='height:8px'></div>")

    # ── Final standings ───────────────────────────────────────────────────────
    st.html("""
<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Final Standings</div>
""")
    for rank, (uname, s) in enumerate(
        sorted(scores.items(), key=lambda x: x[1]["done"], reverse=True), 1
    ):
        rank_color = ["var(--lime)", "var(--amber)", "var(--cyan)"][min(rank - 1, 2)]
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {rank_color}; border-radius:3px;
            padding:14px 18px; margin-bottom:8px;
            display:flex; justify-content:space-between; align-items:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px;
              color:{rank_color}; letter-spacing:1px; line-height:1;">#{rank}  {uname}</div>
  <div style="display:flex; gap:16px; text-align:center;">
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:26px; color:var(--lime);">{s['done']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase;">did it</div>
    </div>
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:26px; color:var(--magenta);">{s['drinks']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase;">drinks</div>
    </div>
    <div>
      <div style="font-family:'Bebas Neue',sans-serif; font-size:26px; color:var(--muted);">{s.get('skipped',0)}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted); text-transform:uppercase;">skipped</div>
    </div>
  </div>
</div>
""")

    st.html("<div style='height:16px'></div>")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("↺  Play Again", use_container_width=True, type="primary"):
            for k in ["dod_dares", "dod_deck", "dod_cur_card", "dod_scores",
                      "dod_history", "dod_timer_start"]:
                st.session_state.pop(k, None)
            st.session_state.dod_phase = "generating"
            st.rerun()
    with col2:
        if st.button("New Game", use_container_width=True):
            st.session_state.pop("dod_room_code", None)
            reset_state()
