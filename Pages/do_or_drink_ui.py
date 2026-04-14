"""
Pages/do_or_drink_ui.py
All rendering phases for Do or Drink.
Imported by do_or_drink.py entry point.

Improvements vs original:
- Dare timer: 30-second JS countdown per card, colour-shifts at 10s.
- Skip mechanic: surfaced clearly in history as "SKIPPED" with visual indicator.
- Player card refreshes vice_summary on every setup render (catches new logs).
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

# ─── HEAT / TYPE MAPS ────────────────────────────────────────────────────────

_HEAT_LABELS = {1: "mild", 2: "spicy", 3: "atomic"}
_HEAT_COLORS = {1: "var(--lime)", 2: "var(--amber)", 3: "var(--magenta)"}
_TYPE_ICONS  = {"DO": "⚡", "TRUTH": "💬"}


# ─── DARE TIMER ──────────────────────────────────────────────────────────────

def _inject_dare_timer(seconds: int = 30):
    """
    Injects a floating 30s countdown that turns amber at 15s, magenta at 5s.
    Purely cosmetic — does NOT auto-resolve the card.
    """
    st.html(f"""
<style>
@keyframes timer-flash {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}
#dod-dare-timer {{
  position: fixed; top: 16px; right: 16px; z-index: 9990;
  background: var(--card); border: 2px solid var(--lime);
  border-radius: 50%; width: 56px; height: 56px;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Bebas Neue', sans-serif; font-size: 22px;
  color: var(--lime); letter-spacing: 1px;
  transition: border-color 0.4s, color 0.4s;
}}
#dod-dare-timer.amber {{ border-color: var(--amber); color: var(--amber); }}
#dod-dare-timer.hot   {{ border-color: var(--magenta); color: var(--magenta); animation: timer-flash 0.5s infinite; }}
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
    if (remaining <= 5)  {{ el.className = "hot"; }}
    else if (remaining <= 15) {{ el.className = "amber"; }}
    else {{ el.className = ""; }}
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
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">Vice Vault · Party Mode</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:56px; color:var(--text);
              letter-spacing:3px; line-height:0.9;">DO OR<br><span style="color:var(--lime);">DRINK</span></div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:8px;">
    AI reads your vault. Your habits become the dares. Yuh brave?
  </div>
</div>
""")

    if st.session_state.dod_error:
        st.error(st.session_state.dod_error)
        st.session_state.dod_error = ""

    # Mode selector
    st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Choose the vibe</div>""")
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
        "regular": "Social dares. Mild embarrassment. Caribbean lime energy. Safe(ish) for family gatherings.",
        "kinky":   "Seductive, physical, explicitly adult. Every dare is heat:2 or heat:3. No mild cards.",
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

    # Players
    st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px; margin-top:4px;">Players</div>""")

    players = st.session_state.dod_players
    me_already = any(p["username"] == my_name for p in players)

    if not me_already and my_id:
        players.append({
            "username":     my_name,
            "user_id":      my_id,
            "vice_summary": _my_full_summary(),
            "is_host":      True,
        })
        st.session_state.dod_players = players

    # Refresh summaries in case new logs were added
    for p in players:
        p["vice_summary"] = _player_vice_summary(p["user_id"]) if p.get("user_id") else {}

    for i, p in enumerate(players):
        col_name, col_remove = st.columns([5, 1])
        with col_name:
            host_badge = " · HOST" if p.get("is_host") else ""
            vs         = p.get("vice_summary", {})
            counts     = vs.get("counts", {})
            vice_parts = [f"{_VICE_LABELS.get(vk, vk)}: {cnt}" for vk, cnt in counts.items()]
            quiz       = vs.get("quiz", {})
            if quiz.get("profile_name"):
                vice_parts.append(f"profile: {quiz['profile_name']}")
            has_d    = _has_data(vs)
            vice_str = "  ·  ".join(vice_parts) if vice_parts else "No data — will use group profile"
            d_color  = "var(--lime)" if has_d else "var(--muted)"
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {'var(--lime)' if p.get('is_host') else 'var(--border)'};
            border-radius:3px; padding:12px 14px; margin-bottom:6px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px;
              color:{'var(--lime)' if p.get('is_host') else 'var(--text)'}; letter-spacing:1px;">
    {p['username']}{host_badge}
  </div>
  <div style="font-family:'Space Mono',monospace; font-size:8px;
              color:{d_color}; letter-spacing:1px; text-transform:uppercase;">{vice_str}</div>
</div>
""")
        with col_remove:
            if not p.get("is_host"):
                st.html("<div style='height:6px'></div>")
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.dod_players.pop(i); st.rerun()

    st.html("<div style='height:6px'></div>")
    new_username = st.text_input(
        "Add player by username", placeholder="Their ViceVault username", key="dod_add_input")
    if st.button("Add Player →", key="dod_add_btn"):
        uname = new_username.strip()
        if not uname:
            st.warning("Enter a username.")
        elif any(p["username"].lower() == uname.lower() for p in players):
            st.warning("Already in the game.")
        else:
            user = _db("get_user_by_username", uname)
            if not user:
                st.error(f"Can't find '{uname}' — they need a ViceVault account.")
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
        any_has  = any(_has_data(p.get("vice_summary", {})) for p in players)
        all_have = all(_has_data(p.get("vice_summary", {})) for p in players)
        if all_have:
            smsg, scol = "✓ All players have data — fully personalised dares.", "var(--lime)"
        elif any_has:
            names       = [p["username"] for p in players if _has_data(p.get("vice_summary", {}))]
            smsg, scol  = f"◈ {', '.join(names)} have data — shaping the whole game.", "var(--amber)"
        else:
            smsg, scol  = "◇ No player data found — generating sharp generic Caribbean dares.", "var(--muted)"
        st.html(f"""
<div style="background:var(--surface); border:1px solid var(--border); border-radius:3px;
            padding:10px 14px; margin-bottom:16px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
              text-transform:uppercase; color:{scol};">{smsg}</div>
</div>
""")

    if n_players < 2:
        st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:2px;
            text-transform:uppercase; color:var(--muted); text-align:center; padding:12px 0;">
  Add at least one more player to start.</div>""")
    else:
        if st.button(
            f"Generate Dares & Start →  ({n_players} players)",
            type="primary", use_container_width=True, key="dod_start",
        ):
            st.session_state.dod_phase = "generating"; st.rerun()

    st.html("""
<div style="margin-top:16px; padding:12px 14px; background:var(--surface);
            border:1px solid var(--border); border-radius:3px; text-align:center;">
  <div style="font-family:'Space Mono',monospace; font-size:8px; letter-spacing:2px;
              text-transform:uppercase; color:var(--muted); line-height:1.9;">
    12 dares per player · AI reads each player's logged sessions and desire profile.<br>
    Each card has a 30-second dare timer. Skipped cards return to the deck.
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
    except RuntimeError as e:
        st.session_state.dod_error = str(e)
        st.session_state.dod_phase = "setup"
        st.rerun()
        return

    any_has_data  = any(_has_data(p.get("vice_summary", {})) for p in players)
    group_profile = build_group_profile(players) if any_has_data else {}
    all_dares     = {}

    for i, p in enumerate(players):
        pct      = int((i / len(players)) * 90)
        has_d    = _has_data(p.get("vice_summary", {}))
        strategy = "personalising" if has_d else ("using group profile" if any_has_data else "generating generic")
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

    st.session_state.dod_dares    = all_dares
    st.session_state.dod_deck     = deck
    st.session_state.dod_scores   = {p["username"]: {"drinks": 0, "done": 0, "skipped": 0} for p in players}
    st.session_state.dod_history  = []
    st.session_state.dod_cur_card = None
    st.session_state.dod_timer_start = None
    st.session_state.dod_phase    = "game"
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
                ">{mode_label.get(mode,'Regular')} mode · {remaining} cards left</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:var(--muted);">
      {played}/{total_cards}
    </div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                text-transform:uppercase; letter-spacing:1px;">played</div>
  </div>
</div>
""")

    # Scoreboard
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
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">did it</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--magenta);">{s['drinks']}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">drinks</div>
    </div>
    <div style="text-align:center;">
      <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--muted);">{s.get('skipped', 0)}</div>
      <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                  text-transform:uppercase; letter-spacing:1px;">skipped</div>
    </div>
  </div>
</div>
""")

    st.html("<div style='height:18px'></div>")

    # Current card or draw prompt
    if cur is None:
        if not deck:
            render_game_over()
            return

        st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:48px; text-align:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:28px; letter-spacing:3px;
              color:var(--muted); margin-bottom:8px;">PULL A CARD</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted);">
    Tap below to see who's up.
  </div>
</div>
""")
        if st.button("⚡  Draw Next Card", type="primary", use_container_width=True, key="draw_card"):
            if deck:
                card_ref = st.session_state.dod_deck.pop(0)
                player   = card_ref["player"]
                dare     = dares[player][card_ref["dare_idx"]]
                st.session_state.dod_cur_card   = {"player": player, "dare": dare}
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

        # Dare timer
        _inject_dare_timer(30)

        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {heat_color}; border-radius:4px; padding:28px 26px; margin-bottom:14px;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div style="font-family:'Bebas Neue',sans-serif; font-size:32px;
                letter-spacing:3px; color:{heat_color}; line-height:1;">{player}</div>
    <div style="display:flex; gap:8px; align-items:center;">
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
                st.session_state.dod_cur_card   = None
                st.session_state.dod_timer_start = None
                st.rerun()
        with col_drink:
            if st.button("🍹  Drinking", use_container_width=True, key="btn_drink"):
                st.session_state.dod_scores[player]["drinks"] += 1
                st.session_state.dod_history.append({**cur, "result": "drink"})
                st.session_state.dod_cur_card   = None
                st.session_state.dod_timer_start = None
                st.rerun()
        with col_skip:
            if st.button("Skip", use_container_width=True, key="btn_skip"):
                # Increment skip counter
                st.session_state.dod_scores[player]["skipped"] = \
                    st.session_state.dod_scores[player].get("skipped", 0) + 1

                # Record in history so players know it was skipped
                st.session_state.dod_history.append({**cur, "result": "skipped"})

                # Reinsert card in the back third of the remaining deck
                rem        = len(st.session_state.dod_deck)
                try:
                    dare_idx = dares[player].index(dare)
                except ValueError:
                    dare_idx = 0
                insert_at = random.randint(max(1, rem * 2 // 3), max(1, rem))
                st.session_state.dod_deck.insert(
                    insert_at, {"player": player, "dare_idx": dare_idx}
                )
                st.session_state.dod_cur_card   = None
                st.session_state.dod_timer_start = None
                st.rerun()

    # Recent history
    if history:
        st.html("<div style='height:20px'></div>")
        st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:10px;">Recent</div>""")
        for h in reversed(history[-5:]):
            p      = h["player"]
            d      = h["dare"]["dare"][:80] + ("…" if len(h["dare"]["dare"]) > 80 else "")
            result = h.get("result", "done")
            r_icon, r_col = {
                "done":    ("✓",  "var(--lime)"),
                "drink":   ("🍹", "var(--magenta)"),
                "skipped": ("↺",  "var(--muted)"),
            }.get(result, ("✓", "var(--lime)"))

            st.html(f"""
<div style="display:flex; gap:10px; align-items:flex-start; padding:8px 0;
            border-bottom:1px solid var(--border);">
  <div style="font-family:'Space Mono',monospace; font-size:14px; color:{r_col}; flex-shrink:0;">{r_icon}</div>
  <div>
    <span style="font-family:'Space Mono',monospace; font-size:9px; color:var(--soft);
                 letter-spacing:1px; text-transform:uppercase;">{p}</span>
    {'<span style="font-family:\'Space Mono\',monospace; font-size:8px; color:var(--muted); margin-left:6px; border:1px solid var(--border); padding:1px 5px; border-radius:2px;">SKIPPED</span>' if result == "skipped" else ''}
    <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
                line-height:1.5;">{d}</div>
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

    real_history = [h for h in history if h.get("result") != "skipped"]
    winner  = max(scores, key=lambda u: scores[u]["done"])   if scores else "—"
    drinker = max(scores, key=lambda u: scores[u]["drinks"]) if scores else "—"

    st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid var(--lime); border-radius:4px;
            padding:32px 28px; text-align:center; margin-bottom:20px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Game Over</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:52px; color:var(--lime);
              letter-spacing:3px; line-height:0.9; margin-bottom:8px;">{winner.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--soft);">
    held it down the most — {scores.get(winner, {}).get('done', 0)} dares completed
  </div>
  {'<div style="margin-top:12px;font-family:\'DM Sans\',sans-serif;font-size:12px;color:var(--magenta);">🍹 ' + drinker + ' drank the most — ' + str(scores.get(drinker,{}).get("drinks",0)) + ' times</div>' if winner != drinker else ''}
</div>
""")

    st.html("""<div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:3px;
            text-transform:uppercase; color:var(--muted); margin-bottom:12px;">Final Standings</div>""")

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
            reset_state()
