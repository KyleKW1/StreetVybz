"""
Pages/do_or_drink.py — Entry point for Do or Drink.

Split into:
  do_or_drink_core.py — prompts, generation, state helpers
  do_or_drink_ui.py   — all rendering phases
  do_or_drink.py      — this file, thin router
"""

import streamlit as st
from Pages.do_or_drink_core import init_state
from Pages.do_or_drink_ui import (
    render_setup,
    render_generating,
    render_game,
    render_game_over,
)
from styles import inject_page_css


def do_or_drink_page():
    init_state()
    phase = st.session_state.dod_phase

    if phase == "setup":
        render_setup()

    elif phase == "generating":
        inject_page_css()
        st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">BUILDING DECK</div>
</div>
""")
        render_generating()

    elif phase == "game":
        render_game()

    elif phase == "gameover":
        inject_page_css()
        st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:24px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:40px; color:var(--text);
              letter-spacing:3px;">DO OR <span style="color:var(--lime);">DRINK</span></div>
</div>
""")
        render_game_over()
