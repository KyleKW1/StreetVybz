import hashlib
import streamlit as st
from styles import inject_page_css

ROOMS = [
    {"key": "room_alcohol", "label": "Last Round",  "vice": "alcohol", "icon": "🥃", "color": "var(--amber)",   "desc": "Alcohol confessions. No filter."},
    {"key": "room_weed",    "label": "Hotbox",       "vice": "weed",    "icon": "🌿", "color": "var(--lime)",    "desc": "Weed talk. Stay paranoid."},
    {"key": "room_sex",     "label": "The Suite",    "vice": "sex",     "icon": "🔥", "color": "var(--magenta)", "desc": "18+. Anonymous. Honest."},
    {"key": "room_other",   "label": "The Drop",     "vice": "other",   "icon": "💊", "color": "#00e5ff",        "desc": "Everything else."},
    {"key": "room_vault",   "label": "The Hideout",    "vice": None,      "icon": "◈",  "color": "var(--lime)",    "desc": "General. For the bold."},
]


def _author_hash(user_id: int) -> str:
    raw = str(user_id) + "vv_salt_2025"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def heat_rooms_page(user_id: int):
    inject_page_css()

    if not user_id:
        st.html("""
<div style="padding:60px;text-align:center;font-family:'Bebas Neue',sans-serif;
            font-size:28px;letter-spacing:3px;color:var(--muted);">LOG IN TO ACCESS HEAT ROOMS</div>
""")
        return

    import database as db

    active_key = st.session_state.get("heat_room_active")

    if active_key is None:
        _render_room_list(user_id, db)
    else:
        room = next((r for r in ROOMS if r["key"] == active_key), None)
        if room is None:
            st.session_state.heat_room_active = None
            st.rerun()
        else:
            _render_room(user_id, room, db)


def _render_room_list(user_id: int, db):
    st.html("""
<div style="border-bottom:1px solid var(--border); padding-bottom:20px; margin-bottom:28px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:4px;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px;">
    Hidden · Anonymous Rooms
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:clamp(40px,8vw,62px);
              color:var(--text); letter-spacing:3px; line-height:0.92; margin-bottom:6px;">
    HEAT<br><span style="color:var(--magenta);">ROOMS</span>
  </div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--muted); margin-top:4px;">
    Anonymous 24-hour group chats by vice and vibe.
  </div>
</div>
""")

    counts = db.get_heat_room_counts()
    cols = st.columns(2)
    for i, room in enumerate(ROOMS):
        col = cols[i % 2]
        with col:
            msg_count = counts.get(room["key"], 0)
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-top:3px solid {room['color']}; border-radius:4px;
            padding:16px 16px 12px; margin-bottom:4px;">
  <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
    <div style="font-size:22px;">{room['icon']}</div>
    <div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
                letter-spacing:1px; text-transform:uppercase;">{msg_count} active</div>
  </div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:20px; color:var(--text);
              letter-spacing:2px; margin-bottom:4px;">{room['label']}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--muted);
              line-height:1.5; margin-bottom:12px;">{room['desc']}</div>
</div>
""")
            if st.button(f"Enter → {room['label']}", key=f"enter_{room['key']}", use_container_width=True):
                st.session_state.heat_room_active = room["key"]
                st.rerun()


def _render_room(user_id: int, room: dict, db):
    my_hash = _author_hash(user_id)

    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Rooms", key="hr_back"):
            st.session_state.heat_room_active = None
            st.rerun()
    with col_title:
        st.html(f"""
<div style="display:flex; align-items:center; gap:10px; padding-top:4px;">
  <span style="font-size:20px;">{room['icon']}</span>
  <div>
    <div style="font-family:'Bebas Neue',sans-serif; font-size:22px; color:var(--text);
                letter-spacing:2px; line-height:1;">{room['label']}</div>
    <div style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);
                letter-spacing:1px; text-transform:uppercase;">Messages auto-delete after 24h</div>
  </div>
</div>
""")

    st.html(f"""
<div style="font-family:'Space Mono',monospace; font-size:8px; color:var(--muted);
            letter-spacing:1px; text-transform:uppercase; margin:16px 0 8px;">
  You appear as Ghost#{my_hash[:4].upper()}
</div>
""")

    refresh_key = f"hr_refresh_{room['key']}"
    if st.button("↺ Refresh", key=refresh_key):
        db.load_heat_room_messages.clear()
        st.rerun()

    messages = db.load_heat_room_messages(room["key"])

    st.html("""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:16px; margin-bottom:12px; min-height:200px;">
""")

    if not messages:
        st.html("""
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; text-align:center; padding:32px 0;">
    Nothing yet. You could go first.
  </div>
""")
    else:
        for msg in messages:
            ts_raw = str(msg.get("created_at", ""))
            ts = ts_raw[11:16] if len(ts_raw) >= 16 else ""
            handle = f"Ghost#{msg['author_hash'][:4].upper()}"
            is_me = msg["author_hash"] == my_hash
            handle_color = "var(--lime)" if is_me else "var(--muted)"
            st.html(f"""
  <div style="margin-bottom:12px;">
    <div style="display:flex; gap:8px; align-items:baseline; margin-bottom:3px;">
      <span style="font-family:'Space Mono',monospace; font-size:8px; color:{handle_color};
                   letter-spacing:1px;">{handle}</span>
      <span style="font-family:'Space Mono',monospace; font-size:7px; color:var(--muted);">{ts}</span>
    </div>
    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--text);
                line-height:1.55; padding-left:4px;">{msg['content']}</div>
  </div>
""")

    st.html("</div>")

    input_key_n = st.session_state.get("hr_input_n", 0)
    msg_text = st.text_area(
        "Message",
        key=f"hr_msg_{input_key_n}",
        max_chars=280,
        height=80,
        label_visibility="collapsed",
        placeholder="Say something. It's anonymous."
    )

    if st.button("Send →", key=f"hr_send_{input_key_n}", type="primary", use_container_width=True):
        content = (msg_text or "").strip()
        if content:
            import database as _db
            _db.send_heat_room_message(room["key"], user_id, content)
            st.session_state["hr_input_n"] = input_key_n + 1
            st.rerun()
