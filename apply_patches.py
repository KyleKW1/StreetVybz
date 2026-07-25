"""
apply_patches.py
Run this from your project root (where Pages/, database.py, auth.py live).
It applies all the security + RBTL fixes via simple text replacement.
Safe to re-run; each replacement is a no-op if already applied.

Usage:
    python apply_patches.py
"""
import re

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def save(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def replace_once(content, old, new, label, path):
    if old not in content:
        if new in content:
            print(f"  [skip] {label} (already applied)")
            return content
        print(f"  [WARN] {label}: pattern not found in {path} — check manually")
        return content
    print(f"  [ok]   {label}")
    return content.replace(old, new, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 1. database.py — add password_resets table
# ─────────────────────────────────────────────────────────────────────────────
def patch_database():
    path = "database.py"
    c = load(path)

    old = '''        """
        CREATE TABLE IF NOT EXISTS dod_rooms ('''
    new = '''        """
        CREATE TABLE IF NOT EXISTS password_resets (
            email      VARCHAR(255) NOT NULL PRIMARY KEY,
            token      VARCHAR(64)  NOT NULL UNIQUE,
            expires_at DATETIME     NOT NULL,
            INDEX idx_pr_token (token)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS dod_rooms ('''

    c = replace_once(c, old, new, "add password_resets table", path)
    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pages/confession.py — escape user-generated HTML
# ─────────────────────────────────────────────────────────────────────────────
def patch_confession():
    path = "Pages/confession.py"
    c = load(path)

    # add html import
    c = replace_once(
        c,
        "import streamlit as st\nimport secrets\nimport string\nimport re\nimport time\n",
        "import streamlit as st\nimport secrets\nimport string\nimport re\nimport time\nimport html as _html\n",
        "add html import", path,
    )

    # _exchange_card: escape q and a
    c = replace_once(
        c,
        '''    for i, (q, a) in enumerate(zip(questions, answers)):
        delay = delay_base + i * 0.12
        st.html(f"""
<div class="reveal-card" style="animation-delay:{delay}s; background:var(--card);
            border:1px solid var(--border); border-left:2px solid {color};
            border-radius:4px; padding:16px 18px; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Q{i + 1}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              line-height:1.6; margin-bottom:10px;">{q}</div>
  <div style="height:1px; background:var(--border); margin-bottom:10px;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Answer</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:{color};
              line-height:1.7; font-style:italic;">"{a}"</div>
</div>
""")''',
        '''    for i, (q, a) in enumerate(zip(questions, answers)):
        delay = delay_base + i * 0.12
        q_safe = _html.escape(str(q))
        a_safe = _html.escape(str(a))
        st.html(f"""
<div class="reveal-card" style="animation-delay:{delay}s; background:var(--card);
            border:1px solid var(--border); border-left:2px solid {color};
            border-radius:4px; padding:16px 18px; margin-bottom:10px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Q{i + 1}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
              line-height:1.6; margin-bottom:10px;">{q_safe}</div>
  <div style="height:1px; background:var(--border); margin-bottom:10px;"></div>
  <div style="font-family:'Space Mono',monospace; font-size:9px; color:var(--muted);
              letter-spacing:1px; text-transform:uppercase; margin-bottom:6px;">Answer</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:{color};
              line-height:1.7; font-style:italic;">"{a_safe}"</div>
</div>
""")''',
        "_exchange_card escape Q&A", path,
    )

    # _render_board_card: escape content
    c = replace_once(
        c,
        '''def _render_board_card(item: dict):
    cid     = item["id"]
    content = item.get("content", "")
    vice    = item.get("vice")''',
        '''def _render_board_card(item: dict):
    cid     = item["id"]
    content = _html.escape(item.get("content", ""))
    vice    = item.get("vice")''',
        "_render_board_card escape content", path,
    )

    # _render_board_card: escape reply content
    c = replace_once(
        c,
        '''            for reply in thread:
                reply_ago = _time_ago(reply.get("created_at"))
                st.html(f"""
<div style="background:var(--surface); border-left:2px solid var(--border);
            border-radius:0 3px 3px 0; padding:10px 14px; margin-bottom:8px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
              line-height:1.6; font-style:italic;">"{reply['content']}"</div>''',
        '''            for reply in thread:
                reply_ago = _time_ago(reply.get("created_at"))
                reply_text = _html.escape(reply.get("content", ""))
                st.html(f"""
<div style="background:var(--surface); border-left:2px solid var(--border);
            border-radius:0 3px 3px 0; padding:10px 14px; margin-bottom:8px;">
  <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);
              line-height:1.6; font-style:italic;">"{reply_text}"</div>''',
        "_render_board_card escape reply", path,
    )

    # _render_inbox_item: escape sender_questions
    c = replace_once(
        c,
        '''            recipient_answers = []
            for i, q in enumerate(sender_questions):
                st.html(
                    f'<div style="font-family:\\'DM Sans\\',sans-serif; font-size:14px;'
                    f' color:var(--text); padding:10px 14px; background:var(--surface);'
                    f' border-left:2px solid var(--magenta); border-radius:0 3px 3px 0;'
                    f' margin-bottom:6px; line-height:1.6;">{q}</div>'
                )''',
        '''            recipient_answers = []
            for i, q in enumerate(sender_questions):
                q_safe = _html.escape(str(q))
                st.html(
                    f'<div style="font-family:\\'DM Sans\\',sans-serif; font-size:14px;'
                    f' color:var(--text); padding:10px 14px; background:var(--surface);'
                    f' border-left:2px solid var(--magenta); border-radius:0 3px 3px 0;'
                    f' margin-bottom:6px; line-height:1.6;">{q_safe}</div>'
                )''',
        "_render_inbox_item escape sender_questions", path,
    )

    # _render_outbox_item: escape recipient_questions
    c = replace_once(
        c,
        '''            sender_answers = []
            for i, q in enumerate(recipient_questions):
                st.html(
                    f'<div style="font-family:\\'DM Sans\\',sans-serif; font-size:14px;'
                    f' color:var(--text); padding:10px 14px; background:var(--surface);'
                    f' border-left:2px solid var(--lime); border-radius:0 3px 3px 0;'
                    f' margin-bottom:6px; line-height:1.6;">{q}</div>'
                )''',
        '''            sender_answers = []
            for i, q in enumerate(recipient_questions):
                q_safe = _html.escape(str(q))
                st.html(
                    f'<div style="font-family:\\'DM Sans\\',sans-serif; font-size:14px;'
                    f' color:var(--text); padding:10px 14px; background:var(--surface);'
                    f' border-left:2px solid var(--lime); border-radius:0 3px 3px 0;'
                    f' margin-bottom:6px; line-height:1.6;">{q_safe}</div>'
                )''',
        "_render_outbox_item escape recipient_questions", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pages/do_or_drink_ui.py — escape AI/user-generated HTML
# ─────────────────────────────────────────────────────────────────────────────
def patch_dod():
    path = "Pages/do_or_drink_ui.py"
    c = load(path)

    c = replace_once(
        c,
        "import random\nimport time\nimport streamlit as st\n",
        "import random\nimport time\nimport html as _html\nimport streamlit as st\n",
        "add html import", path,
    )

    # dare card: escape player/dare/drink text
    c = replace_once(
        c,
        '''        heat_color = _HEAT_COLORS.get(heat, "var(--amber)")
        heat_label = _HEAT_LABELS.get(heat, "spicy")
        type_icon  = _TYPE_ICONS.get(dtype, "⚡")

        _inject_dare_timer(30)''',
        '''        heat_color = _HEAT_COLORS.get(heat, "var(--amber)")
        heat_label = _HEAT_LABELS.get(heat, "spicy")
        type_icon  = _TYPE_ICONS.get(dtype, "⚡")
        dare_text   = _html.escape(dare.get('dare', ''))
        drink_text  = _html.escape(dare.get('drink', ''))
        player_safe = _html.escape(player)

        _inject_dare_timer(30)''',
        "dare card prep escaped vars", path,
    )

    c = replace_once(
        c,
        '''    <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; letter-spacing:3px;
                color:{heat_color}; line-height:1;">{player}</div>''',
        '''    <div style="font-family:'Bebas Neue',sans-serif; font-size:32px; letter-spacing:3px;
                color:{heat_color}; line-height:1;">{player_safe}</div>''',
        "dare card player", path,
    )

    c = replace_once(
        c,
        '''  <div style="font-family:'DM Sans',sans-serif; font-size:17px; color:var(--text);
              line-height:1.65; margin-bottom:20px;">{dare['dare']}</div>''',
        '''  <div style="font-family:'DM Sans',sans-serif; font-size:17px; color:var(--text);
              line-height:1.65; margin-bottom:20px;">{dare_text}</div>''',
        "dare card dare text", path,
    )

    c = replace_once(
        c,
        '''    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">{dare['drink']}</div>''',
        '''    <div style="font-family:'DM Sans',sans-serif; font-size:13px; color:var(--soft);">{drink_text}</div>''',
        "dare card drink text", path,
    )

    # recent history list
    c = replace_once(
        c,
        '''        for h in reversed(history[-5:]):
            p      = h["player"]
            d      = h["dare"]["dare"][:80] + ("…" if len(h["dare"]["dare"]) > 80 else "")
            result = h.get("result", "done")''',
        '''        for h in reversed(history[-5:]):
            p_raw  = h["player"]
            d_raw  = h["dare"]["dare"]
            p      = _html.escape(p_raw)
            d      = _html.escape(d_raw[:80] + ("…" if len(d_raw) > 80 else ""))
            result = h.get("result", "done")''',
        "recent history escape", path,
    )

    # players list in setup
    c = replace_once(
        c,
        '''            vice_parts = [f"{_VICE_LABELS.get(vk, vk)}: *hidden*" for vk in counts.keys()]
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
  </div>''',
        '''            vice_parts = [f"{_VICE_LABELS.get(vk, vk)}: *hidden*" for vk in counts.keys()]
            if quiz.get("profile_name"):
                vice_parts.append(f"profile: {_html.escape(str(quiz['profile_name']))}")
            vice_str   = "  ·  ".join(vice_parts) if vice_parts else "No log data — generic dares"
            host_badge = " · HOST" if p.get("is_host") else ""
            d_color    = "var(--lime)" if has_d else "var(--muted)"
            uname_safe = _html.escape(p['username'])
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:2px solid {'var(--lime)' if p.get('is_host') else 'var(--border)'};
            border-radius:3px; padding:12px 14px; margin-bottom:6px;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; letter-spacing:1px;
              color:{'var(--lime)' if p.get('is_host') else 'var(--text)'};">
    {uname_safe}{host_badge}
  </div>''',
        "setup players list escape", path,
    )

    # game over highlights
    c = replace_once(
        c,
        '''        for label, player, detail in highlights:
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
""")''',
        '''        for label, player, detail in highlights:
            player_safe = _html.escape(str(player))
            detail_safe = _html.escape(str(detail))
            st.html(f"""
<div style="background:var(--card); border:1px solid var(--border); border-radius:4px;
            padding:14px 16px; margin-bottom:8px;">
  <div style="font-family:'Space Mono',monospace; font-size:9px; letter-spacing:1px;
              text-transform:uppercase; color:var(--muted); margin-bottom:4px;">{label}</div>
  <div style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:var(--lime);
              letter-spacing:1px; margin-bottom:4px;">{player_safe.upper()}</div>
  <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:var(--soft);
              line-height:1.5; font-style:italic;">"{detail_safe}"</div>
</div>
""")''',
        "game over highlights escape", path,
    )

    # final standings
    c = replace_once(
        c,
        '''    for rank, (uname, s) in enumerate(
        sorted(scores.items(), key=lambda x: x[1]["done"], reverse=True), 1
    ):
        rank_color = ["var(--lime)", "var(--amber)", "var(--cyan)"][min(rank - 1, 2)]
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {rank_color}; border-radius:3px;
            padding:14px 18px; margin-bottom:8px;
            display:flex; justify-content:space-between; align-items:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px;
              color:{rank_color}; letter-spacing:1px; line-height:1;">#{rank}  {uname}</div>''',
        '''    for rank, (uname, s) in enumerate(
        sorted(scores.items(), key=lambda x: x[1]["done"], reverse=True), 1
    ):
        rank_color = ["var(--lime)", "var(--amber)", "var(--cyan)"][min(rank - 1, 2)]
        uname_safe = _html.escape(uname)
        st.html(f"""
<div style="background:var(--card); border:1px solid var(--border);
            border-left:3px solid {rank_color}; border-radius:3px;
            padding:14px 18px; margin-bottom:8px;
            display:flex; justify-content:space-between; align-items:center;">
  <div style="font-family:'Bebas Neue',sans-serif; font-size:22px;
              color:{rank_color}; letter-spacing:1px; line-height:1;">#{rank}  {uname_safe}</div>''',
        "final standings escape", path,
    )

    save(path, c)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pages/what_would_you_do.py — RBTL fixes
# ─────────────────────────────────────────────────────────────────────────────
def patch_rbtl():
    path = "Pages/what_would_you_do.py"
    c = load(path)

    # simplify _uid()
    c = replace_once(
        c,
        '''def _uid():
    u = st.session_state.get("user")
    if isinstance(u, dict):
        uid = u.get("id") or u.get("user_id")
        if uid:
            try:
                return int(uid)
            except (TypeError, ValueError):
                pass
    try:
        uid = st.session_state.get("user_id")
        if uid:
            return int(uid)
    except (TypeError, ValueError):
        pass
    return None''',
        '''def _uid():
    u = st.session_state.get("user")
    if isinstance(u, dict) and u.get("id"):
        try:
            return int(u["id"])
        except (TypeError, ValueError):
            return None
    return None''',
        "simplify _uid", path,
    )

    # render_loading: progressive load — generate Q1 synchronously, rest lazily
    c = replace_once(
        c,
        '''def render_loading():
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:24px;">BUILDING YOUR QUIZ</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, msg):
        ph_bar.progress(pct)
        ph_status.caption(msg)

    try:
        upd(5, "Fetching live Reddit posts…")
        posts = fetch_posts()
        reddit_count = len([p for p in posts if "reddit.com" in p.get("url", "")])
        scratch_count = max(0, POST_COUNT - reddit_count)

        status_msg = f"{reddit_count} Reddit post{'s' if reddit_count != 1 else ''}"
        if scratch_count:
            status_msg += f" + {scratch_count} AI scenario{'s' if scratch_count != 1 else ''} generating…"
        else:
            status_msg += " — generating questions…"
        upd(20, status_msg)

        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            st.session_state.wwyd_error = "OPENAI_API_KEY not found in secrets."
            st.session_state.wwyd_phase = "start"
            st.rerun()
            return

        upd(35, "All generating in parallel…")
        questions = _build_question_list(posts, api_key)

        upd(100, "Ready.")
        st.session_state.wwyd_questions   = questions
        st.session_state.wwyd_answers     = [None] * len(questions)
        st.session_state.wwyd_cur         = 0
        st.session_state.wwyd_pulse_shown = {}
        st.session_state.wwyd_source      = "live" if reddit_count else "ai"
        st.session_state.wwyd_phase       = "quiz"
        st.rerun()

    except Exception as e:
        st.session_state.wwyd_error = f"Failed to load: {e}. Please try again."
        st.session_state.wwyd_phase = "start"
        st.rerun()''',
        '''@st.cache_data(ttl=3600, show_spinner=False)
def _generate_one_more(post_or_slot, api_key, slot_index):
    """Generate a single question for slot `slot_index`. post_or_slot is
    either a post dict (reddit) or None (use from-scratch generation)."""
    if post_or_slot is not None and "reddit.com" in post_or_slot.get("url", ""):
        try:
            q_data = _generate_question_cached(
                post_url=post_or_slot["url"], post_title=post_or_slot["title"],
                post_text=post_or_slot["text"], post_sub=post_or_slot["sub"],
                api_key=api_key,
            )
            return {**post_or_slot, **q_data}
        except Exception:
            return {**post_or_slot, **_make_fallback_question(post_or_slot)}
    try:
        return _generate_scenario_from_scratch(slot_index, api_key)
    except Exception:
        base = post_or_slot or FALLBACK_POSTS[slot_index % len(FALLBACK_POSTS)]
        return {**base, **_make_fallback_question(base)}


def _ensure_question_ready(idx: int):
    """Lazily fill st.session_state.wwyd_questions[idx] if it's still None."""
    questions = st.session_state.wwyd_questions
    if idx >= len(questions) or questions[idx] is not None:
        return
    remaining = st.session_state.get("wwyd_remaining_posts", [])
    slot_pos  = idx - 1  # slot 0 was generated synchronously in render_loading
    post      = remaining[slot_pos] if slot_pos < len(remaining) else None
    api_key   = st.secrets.get("OPENAI_API_KEY", "")
    questions[idx] = _generate_one_more(post, api_key, idx)
    st.session_state.wwyd_questions = questions


def render_loading():
    st.html("""
<div style="font-family:'Bebas Neue',sans-serif; font-size:36px; color:var(--text);
            letter-spacing:3px; margin-bottom:24px;">BUILDING YOUR QUIZ</div>
""")
    ph_bar    = st.empty()
    ph_status = st.empty()

    def upd(pct, msg):
        ph_bar.progress(pct)
        ph_status.caption(msg)

    try:
        upd(5, "Fetching live Reddit posts…")
        posts = fetch_posts()
        reddit_count = len([p for p in posts if "reddit.com" in p.get("url", "")])

        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            st.session_state.wwyd_error = "OPENAI_API_KEY not found in secrets."
            st.session_state.wwyd_phase = "start"
            st.rerun()
            return

        # Generate just the FIRST question synchronously so the user can
        # start immediately, then build the rest lazily as they progress.
        upd(20, "Preparing your first question…")
        reddit_posts  = [p for p in posts if "reddit.com" in p.get("url", "")]
        scratch_posts = posts[len(reddit_posts):]

        if reddit_posts:
            first_post = reddit_posts[0]
            try:
                q_data = _generate_question_cached(
                    post_url=first_post["url"], post_title=first_post["title"],
                    post_text=first_post["text"], post_sub=first_post["sub"],
                    api_key=api_key,
                )
                first_q = {**first_post, **q_data}
            except Exception:
                first_q = {**first_post, **_make_fallback_question(first_post)}
            remaining_posts = reddit_posts[1:] + scratch_posts
        else:
            try:
                first_q = _generate_scenario_from_scratch(0, api_key)
            except Exception:
                first_q = {**FALLBACK_POSTS[0], **_make_fallback_question(FALLBACK_POSTS[0])}
            remaining_posts = posts

        upd(100, "Ready — the rest will load as you go…")

        questions = [first_q] + [None] * (POST_COUNT - 1)
        st.session_state.wwyd_remaining_posts = remaining_posts
        st.session_state.wwyd_questions   = questions
        st.session_state.wwyd_answers     = [None] * len(questions)
        st.session_state.wwyd_cur         = 0
        st.session_state.wwyd_pulse_shown = {}
        st.session_state.wwyd_source      = "live" if reddit_count else "ai"
        st.session_state.wwyd_phase       = "quiz"
        st.rerun()

    except Exception as e:
        # Recoverable error — stay on start with a message instead of
        # silently wiping progress.
        st.session_state.wwyd_error = f"Couldn't load questions: {e}. Please try again."
        st.session_state.wwyd_phase = "start"
        st.rerun()''',
        "render_loading progressive load", path,
    )

    # render_quiz: handle None question slots
    c = replace_once(
        c,
        '''    if not questions or cur >= len(questions):
        st.session_state.wwyd_phase = "start"
        st.rerun()
        return

    if len(answers) < len(questions):''',
        '''    if not questions or cur >= len(questions):
        st.session_state.wwyd_phase = "start"
        st.rerun()
        return

    if questions[cur] is None:
        with st.spinner("Preparing this question…"):
            _ensure_question_ready(cur)
        st.rerun()
        return

    if len(answers) < len(questions):''',
        "render_quiz handle None slot", path,
    )

    save(path, c)


if __name__ == "__main__":
    print("Patching database.py ...")
    patch_database()
    print("Patching Pages/confession.py ...")
    patch_confession()
    print("Patching Pages/do_or_drink_ui.py ...")
    patch_dod()
    print("Patching Pages/what_would_you_do.py ...")
    patch_rbtl()
    print("Done.")
