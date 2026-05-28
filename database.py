# database.py
import json
import streamlit as st

try:
    import mysql.connector
    from mysql.connector import pooling
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    from config import DB_CONFIG
except ImportError:
    DB_CONFIG = {}

# ─── CONNECTION POOL ─────────────────────────────────────────────────────────

_pool: "pooling.MySQLConnectionPool | None" = None


def _get_pool() -> "pooling.MySQLConnectionPool | None":
    global _pool
    if _pool is not None:
        return _pool
    if not MYSQL_AVAILABLE or not DB_CONFIG.get("host"):
        return None
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="vicevault",
            pool_size=10,
            pool_reset_session=True,
            host=DB_CONFIG.get("host", ""),
            port=int(DB_CONFIG.get("port", 3306)),
            user=DB_CONFIG.get("user", ""),
            password=DB_CONFIG.get("password", ""),
            database=DB_CONFIG.get("database", ""),
            connection_timeout=30,
            autocommit=False,
            ssl_disabled=True,
        )
        return _pool
    except Exception as e:
        st.error(f"DB pool init error: {e}")
        return None


def create_connection():
    pool = _get_pool()
    if pool:
        try:
            return pool.get_connection()
        except Exception:
            pass

    if not MYSQL_AVAILABLE or not DB_CONFIG.get("host"):
        return None
    try:
        return mysql.connector.connect(
            host=DB_CONFIG.get("host", ""),
            port=int(DB_CONFIG.get("port", 3306)),
            user=DB_CONFIG.get("user", ""),
            password=DB_CONFIG.get("password", ""),
            database=DB_CONFIG.get("database", ""),
            connection_timeout=30,
            autocommit=False,
            ssl_disabled=True,
        )
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


def ensure_tables():
    conn = create_connection()
    if not conn:
        return

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS vice_log (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            vice        VARCHAR(32)  NOT NULL,
            logged_at   DATETIME     NOT NULL,
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            details     JSON,
            INDEX idx_vice_log_user (user_id),
            INDEX idx_vice_log_time (user_id, logged_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS quiz_results (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id         INT NOT NULL,
            quiz_type       VARCHAR(64)  NOT NULL,
            completed_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            profile_name    VARCHAR(128),
            profile_meta    VARCHAR(255),
            dim_scores      JSON,
            recommendations JSON,
            total_pct       TINYINT UNSIGNED,
            result_name     VARCHAR(128),
            result_meta     VARCHAR(255),
            openness_pct    TINYINT UNSIGNED,
            total_pts       SMALLINT UNSIGNED,
            questions       LONGTEXT,
            answers         JSON,
            INDEX idx_quiz_user (user_id),
            INDEX idx_quiz_type (user_id, quiz_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS confessions (
            id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            code                VARCHAR(16) NOT NULL UNIQUE,
            sender_id           INT NOT NULL,
            recipient_id        INT          DEFAULT NULL,
            recipient_email     VARCHAR(255) DEFAULT NULL,
            sender_questions    JSON NOT NULL,
            recipient_answers   JSON,
            recipient_questions JSON,
            sender_answers      JSON,
            status              VARCHAR(16) NOT NULL DEFAULT 'sent',
            reveal_window_secs  INT NOT NULL DEFAULT 60,
            revealed_at         DATETIME    DEFAULT NULL,
            created_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_conf_sender    (sender_id),
            INDEX idx_conf_recipient (recipient_id),
            INDEX idx_conf_code      (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS screenshot_alerts (
            id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            confession_code         VARCHAR(16),
            screenshotter_id        INT NOT NULL,
            screenshotter_username  VARCHAR(128) NOT NULL,
            other_username          VARCHAR(128) NOT NULL,
            dismissed               TINYINT(1) NOT NULL DEFAULT 0,
            created_at              DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sa_other     (other_username),
            INDEX idx_sa_dismissed (other_username, dismissed)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS confession_reactions (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            confession_code VARCHAR(16) NOT NULL,
            user_id         INT NOT NULL,
            emoji           VARCHAR(8) NOT NULL,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_reaction (confession_code, user_id, emoji),
            INDEX idx_react_code (confession_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS vice_goals (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            vice        VARCHAR(32) NOT NULL,
            weekly_limit INT NOT NULL DEFAULT 0,
            updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_vice_goal (user_id, vice)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS session_tokens (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            token       VARCHAR(64) NOT NULL UNIQUE,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at  DATETIME NOT NULL,
            invalidated TINYINT(1) NOT NULL DEFAULT 0,
            INDEX idx_st_user  (user_id),
            INDEX idx_st_token (token)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS public_confessions (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            author_id   INT NOT NULL,
            content     TEXT NOT NULL,
            vice        VARCHAR(32) DEFAULT NULL,
            reply_count INT NOT NULL DEFAULT 0,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_pcb_time (created_at),
            INDEX idx_pcb_vice (vice)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS public_confession_replies (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            confession_id   BIGINT UNSIGNED NOT NULL,
            author_id       INT NOT NULL,
            content         TEXT NOT NULL,
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_pcr_confession (confession_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS community_quiz_answers (
            question_hash   VARCHAR(64) NOT NULL,
            opt_index       TINYINT    NOT NULL,
            tally           INT        NOT NULL DEFAULT 0,
            PRIMARY KEY (question_hash, opt_index)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS dod_rooms (
            room_code       VARCHAR(6) NOT NULL PRIMARY KEY,
            host_id         INT NOT NULL,
            host_username   VARCHAR(128) NOT NULL,
            players         JSON NOT NULL DEFAULT ('[]'),
            mode            VARCHAR(16) NOT NULL DEFAULT 'regular',
            status          VARCHAR(16) NOT NULL DEFAULT 'waiting',
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_dod_host   (host_id),
            INDEX idx_dod_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id          INT NOT NULL,
            interaction_type VARCHAR(32)  NOT NULL,
            created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            payload          JSON,
            INDEX idx_int_user (user_id),
            INDEX idx_int_type (user_id, interaction_type),
            INDEX idx_int_time (user_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS shadow_scores (
            user_id          INT NOT NULL PRIMARY KEY,
            hypocrisy_idx    TINYINT UNSIGNED DEFAULT 0,
            conflict_idx     TINYINT UNSIGNED DEFAULT 0,
            freak_score      TINYINT UNSIGNED DEFAULT 0,
            updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS deleted_user_archive (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            original_user_id INT NOT NULL,
            username        VARCHAR(128),
            email           VARCHAR(255),
            deleted_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            vice_log        LONGTEXT,
            quiz_results    LONGTEXT,
            goals           LONGTEXT,
            interactions    LONGTEXT,
            shadow_scores   LONGTEXT,
            INDEX idx_dua_user    (original_user_id),
            INDEX idx_dua_deleted (deleted_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        # ── Friends / Social ──────────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS friend_requests (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            sender_id       INT NOT NULL,
            recipient_id    INT NOT NULL,
            status          VARCHAR(16) NOT NULL DEFAULT 'pending',
            created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_friend_pair (sender_id, recipient_id),
            INDEX idx_fr_recipient (recipient_id, status),
            INDEX idx_fr_sender    (sender_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    try:
        cur = conn.cursor()
        for ddl in ddl_statements:
            cur.execute(ddl)
        conn.commit()

        for migration in [
            "ALTER TABLE quiz_results MODIFY COLUMN quiz_type VARCHAR(64) NOT NULL",
            "ALTER TABLE confessions ADD COLUMN revealed_at DATETIME DEFAULT NULL",
            "ALTER TABLE confessions ADD COLUMN reveal_window_secs INT NOT NULL DEFAULT 60",
            "ALTER TABLE confessions MODIFY COLUMN recipient_id INT DEFAULT NULL",
            "ALTER TABLE confessions ADD COLUMN recipient_email VARCHAR(255) DEFAULT NULL",
        ]:
            try:
                cur.execute(migration)
                conn.commit()
            except Exception:
                pass

        cur.close()
    except Exception as e:
        st.error(f"Schema bootstrap error: {e}")
    finally:
        conn.close()


# ─── USERS ────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        return user
    except Exception as e:
        return None
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()


def create_user(username: str, email: str, password_hash: str):
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
        cur.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        return False, "Username or email already exists."
    except Exception as e:
        return False, f"Registration error: {e}"
    finally:
        conn.close()


def update_last_login(user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_user_password(user_id: int, new_password_hash: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ─── SESSION TOKENS ───────────────────────────────────────────────────────────

def create_session_token(user_id: int, token: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO session_tokens (user_id, token, expires_at)
               VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 30 DAY))""",
            (user_id, token)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def verify_session_token(user_id: int, token: str) -> bool:
    conn = create_connection()
    if not conn:
        return True
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id FROM session_tokens
               WHERE user_id = %s AND token = %s
                 AND invalidated = 0 AND expires_at > NOW()""",
            (user_id, token)
        )
        row = cur.fetchone()
        cur.close()
        return row is not None
    except Exception:
        return True
    finally:
        conn.close()


def invalidate_session_token(token: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE session_tokens SET invalidated = 1 WHERE token = %s",
            (token,)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def invalidate_user_sessions(user_id: int) -> None:
    conn = create_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE session_tokens SET invalidated = 1 WHERE user_id = %s AND invalidated = 0",
            (user_id,)
        )
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        conn.close()


# ─── VICE LOG ─────────────────────────────────────────────────────────────────

def save_vice_entry(user_id: int, vice: str, logged_at, details: dict):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vice_log (user_id, vice, logged_at, details) VALUES (%s, %s, %s, %s)",
            (user_id, vice, logged_at, json.dumps(details, default=str))
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.close()
        # ── Cache invalidation ──
        try:
            load_vice_log.clear()
            load_social_feed.clear()
        except Exception:
            pass
        return new_id
    except Exception as e:
        st.error(f"Error saving vice entry: {e}")
        return None
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def load_vice_log(user_id: int) -> list:
    """Cached 60s. Cleared on save/delete."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, vice, logged_at, details FROM vice_log WHERE user_id = %s ORDER BY logged_at DESC",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        entries = []
        for row in rows:
            details = row["details"]
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            entries.append({
                "id":        row["id"],
                "vice":      row["vice"],
                "timestamp": row["logged_at"].isoformat() if hasattr(row["logged_at"], "isoformat") else str(row["logged_at"]),
                "data":      details or {},
            })
        return entries
    except Exception as e:
        st.error(f"Error loading vice log: {e}")
        return []
    finally:
        conn.close()


def delete_vice_log(user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM vice_log WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        try:
            load_vice_log.clear()
            load_social_feed.clear()
        except Exception:
            pass
        return True
    except Exception as e:
        st.error(f"Error deleting vice log: {e}")
        return False
    finally:
        conn.close()


# ─── SOCIAL FEED ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def load_social_feed(limit: int = 20) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT vice, logged_at FROM vice_log ORDER BY logged_at DESC LIMIT %s",
            (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        return [{"vice": r["vice"], "logged_at": r["logged_at"]} for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


# ─── VICE GOALS ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def get_vice_goals(user_id: int) -> dict:
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT vice, weekly_limit FROM vice_goals WHERE user_id = %s", (user_id,))
        rows = cur.fetchall()
        cur.close()
        return {r["vice"]: r["weekly_limit"] for r in rows}
    except Exception:
        return {}
    finally:
        conn.close()


def save_vice_goal(user_id: int, vice: str, weekly_limit: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO vice_goals (user_id, vice, weekly_limit)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE weekly_limit = VALUES(weekly_limit)""",
            (user_id, vice, weekly_limit)
        )
        conn.commit()
        cur.close()
        get_vice_goals.clear()
        return True
    except Exception as e:
        st.error(f"Error saving vice goal: {e}")
        return False
    finally:
        conn.close()


# ─── QUIZ RESULTS ─────────────────────────────────────────────────────────────

def save_read_between_lines_v4(
    user_id: int, phase: str, result_name: str, result_meta: str,
    openness_pct: int, total_pts: int, questions: list, answers: dict,
    dim_scores: dict, recommendations: list,
) -> bool:
    conn = create_connection()
    if not conn:
        return False
    quiz_type = f"rbtl_v4_{phase}"[:64]
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, result_name, result_meta,
                openness_pct, total_pts, questions, answers, dim_scores, recommendations)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id, quiz_type,
                result_name[:128] if result_name else "",
                result_meta[:255] if result_meta else "",
                max(0, min(255, openness_pct)),
                max(0, min(65535, total_pts)),
                json.dumps(questions, default=str),
                json.dumps(answers,   default=str),
                json.dumps(dim_scores, default=str),
                json.dumps(recommendations, default=str),
            )
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"DB save error (rbtl_v4/{phase}): {e}")
        return False
    finally:
        conn.close()


def update_rbtl_selected_categories(user_id: int, selected_cats: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id, dim_scores FROM quiz_results
               WHERE user_id = %s AND quiz_type LIKE 'rbtl_v4_%'
               ORDER BY completed_at DESC LIMIT 1""",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return False
        dim_scores = row.get("dim_scores") or {}
        if isinstance(dim_scores, str):
            try:
                dim_scores = json.loads(dim_scores)
            except Exception:
                dim_scores = {}
        dim_scores["selected"]            = selected_cats
        dim_scores["selection_confirmed"] = True
        cur.execute(
            "UPDATE quiz_results SET dim_scores = %s WHERE id = %s",
            (json.dumps(dim_scores, default=str), row["id"])
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"DB update error (selected_categories): {e}")
        return False
    finally:
        conn.close()


def load_latest_rbtl_result(user_id: int) -> dict | None:
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT * FROM quiz_results
               WHERE user_id = %s AND quiz_type LIKE 'rbtl_v4_%'
               ORDER BY completed_at DESC LIMIT 1""",
            (user_id,)
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        for col in ("dim_scores", "recommendations", "answers"):
            val = row.get(col)
            if isinstance(val, str):
                try:
                    row[col] = json.loads(val)
                except Exception:
                    row[col] = {} if col == "dim_scores" else []
        q = row.get("questions")
        if isinstance(q, str):
            try:
                row["questions"] = json.loads(q)
            except Exception:
                row["questions"] = []
        return row
    except Exception:
        return None
    finally:
        conn.close()


# ─── CONFESSIONS ──────────────────────────────────────────────────────────────

def _clear_confession_cache():
    """Clear inbox/outbox caches after any status mutation."""
    try:
        load_confessions_inbox.clear()
        load_confessions_outbox.clear()
    except Exception:
        pass


def save_confession(sender_id: int, recipient_id: int, code: str,
                    questions: list, window_seconds: int = 60) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO confessions
               (code, sender_id, recipient_id, sender_questions, reveal_window_secs, status)
               VALUES (%s, %s, %s, %s, %s, 'sent')""",
            (code, sender_id, recipient_id, json.dumps(questions), window_seconds)
        )
        conn.commit()
        cur.close()
        _clear_confession_cache()
        return True
    except Exception as e:
        st.error(f"Error saving confession: {e}")
        return False
    finally:
        conn.close()


def save_confession_invite(sender_id: int, recipient_email: str, code: str,
                            questions: list, window_seconds: int = 60) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO confessions
               (code, sender_id, recipient_id, recipient_email,
                sender_questions, reveal_window_secs, status)
               VALUES (%s, %s, NULL, %s, %s, %s, 'sent')""",
            (code, sender_id, recipient_email, json.dumps(questions), window_seconds)
        )
        conn.commit()
        cur.close()
        _clear_confession_cache()
        return True
    except Exception as e:
        st.error(f"Error saving confession invite: {e}")
        return False
    finally:
        conn.close()


def get_confession_by_code(code: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
               WHERE c.code = %s""",
            (code,)
        )
        row = cur.fetchone()
        cur.close()
        return _parse_confession_row(row)
    except Exception:
        return None
    finally:
        conn.close()


@st.cache_data(ttl=20, show_spinner=False)
def load_confessions_inbox(user_id: int) -> list:
    """Cached 20s. Cleared on any confession mutation."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
               WHERE c.recipient_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [r for r in (_parse_confession_row(row) for row in rows) if r]
    except Exception as e:
        st.error(f"Error loading inbox: {e}")
        return []
    finally:
        conn.close()


@st.cache_data(ttl=20, show_spinner=False)
def load_confessions_outbox(user_id: int) -> list:
    """Cached 20s. Cleared on any confession mutation."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
               WHERE c.sender_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [r for r in (_parse_confession_row(row) for row in rows) if r]
    except Exception as e:
        st.error(f"Error loading outbox: {e}")
        return []
    finally:
        conn.close()


def confession_recipient_submit_questions(code: str, recipient_questions: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions SET recipient_questions = %s, status = 'questioning'
               WHERE code = %s AND status = 'sent'""",
            (json.dumps(recipient_questions), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        if changed:
            _clear_confession_cache()
        return changed
    except Exception as e:
        st.error(f"Error submitting questions: {e}")
        return False
    finally:
        conn.close()


def confession_recipient_answer(code: str, recipient_answers: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions SET recipient_answers = %s, status = 'responded'
               WHERE code = %s AND status = 'questioning'""",
            (json.dumps(recipient_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        if changed:
            _clear_confession_cache()
        return changed
    except Exception as e:
        st.error(f"Error saving answers: {e}")
        return False
    finally:
        conn.close()


def confession_sender_answer(code: str, sender_answers: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions
               SET sender_answers = %s,
                   status         = 'revealed',
                   revealed_at    = NOW()
               WHERE code = %s AND status = 'responded'""",
            (json.dumps(sender_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        if changed:
            _clear_confession_cache()
        return changed
    except Exception as e:
        st.error(f"Error revealing confession: {e}")
        return False
    finally:
        conn.close()


def delete_confession(code: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM confessions WHERE code = %s", (code,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        if deleted:
            _clear_confession_cache()
        return deleted
    except Exception as e:
        st.error(f"Error deleting confession: {e}")
        return False
    finally:
        conn.close()


def delete_expired_confessions() -> int:
    conn = create_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM confessions
               WHERE status = 'revealed'
                 AND revealed_at IS NOT NULL
                 AND revealed_at < DATE_SUB(NOW(), INTERVAL reveal_window_secs SECOND)"""
        )
        conn.commit()
        count = cur.rowcount
        cur.close()
        if count:
            _clear_confession_cache()
        return count
    except Exception:
        return 0
    finally:
        conn.close()


def _parse_confession_row(row):
    if not row:
        return None
    for col in ("sender_questions", "recipient_questions", "recipient_answers", "sender_answers"):
        val = row.get(col)
        if val and isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = []
        elif val is None:
            row[col] = []
    return row


# ─── CONFESSION REACTIONS ─────────────────────────────────────────────────────

def save_reaction(confession_code: str, user_id: int, emoji: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO confession_reactions (confession_code, user_id, emoji) VALUES (%s, %s, %s)",
            (confession_code, user_id, emoji)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def load_reactions(confession_code: str, user_id: int) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT emoji FROM confession_reactions WHERE confession_code = %s AND user_id = %s",
            (confession_code, user_id)
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception:
        return []
    finally:
        conn.close()


def count_reactions(confession_code: str, emoji: str) -> int:
    conn = create_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM confession_reactions WHERE confession_code = %s AND emoji = %s",
            (confession_code, emoji)
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


# ─── SCREENSHOT ALERTS ────────────────────────────────────────────────────────

def save_screenshot_alert(confession_code: str, screenshotter_id: int,
                           screenshotter_username: str, other_username: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO screenshot_alerts
               (confession_code, screenshotter_id, screenshotter_username, other_username)
               VALUES (%s, %s, %s, %s)""",
            (confession_code, screenshotter_id, screenshotter_username, other_username)
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving screenshot alert: {e}")
        return False
    finally:
        conn.close()


def load_screenshot_alerts(user_id: int) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return []
        username = row["username"]
        cur.execute(
            """SELECT id, confession_code, screenshotter_username, created_at
               FROM screenshot_alerts
               WHERE other_username = %s AND dismissed = 0
               ORDER BY created_at DESC""",
            (username,)
        )
        alerts = cur.fetchall()
        cur.close()
        return alerts
    except Exception as e:
        st.error(f"Error loading screenshot alerts: {e}")
        return []
    finally:
        conn.close()


def dismiss_screenshot_alert(alert_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE screenshot_alerts SET dismissed = 1 WHERE id = %s", (alert_id,))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error dismissing alert: {e}")
        return False
    finally:
        conn.close()


# ─── INTERACTIONS ─────────────────────────────────────────────────────────────

def save_interaction(user_id: int, interaction_type: str, payload: dict) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO interactions (user_id, interaction_type, payload) VALUES (%s, %s, %s)",
            (user_id, interaction_type, json.dumps(payload, default=str))
        )
        conn.commit()
        cur.close()
        try:
            load_interactions.clear()
        except Exception:
            pass
        return True
    except Exception:
        return False
    finally:
        conn.close()


@st.cache_data(ttl=120, show_spinner=False)
def load_interactions(user_id: int, interaction_type: str = None) -> list:
    """Cached 2 min. Cleared on new interaction save."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        if interaction_type:
            cur.execute(
                """SELECT * FROM interactions
                   WHERE user_id = %s AND interaction_type = %s
                   ORDER BY created_at DESC""",
                (user_id, interaction_type)
            )
        else:
            cur.execute(
                "SELECT * FROM interactions WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
        rows = cur.fetchall()
        cur.close()
        result = []
        for row in rows:
            p = row.get("payload")
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except Exception:
                    p = {}
            row["payload"] = p or {}
            result.append(row)
        return result
    except Exception:
        return []
    finally:
        conn.close()


def upsert_shadow_score(user_id: int, hypocrisy_idx: int = None,
                         conflict_idx: int = None, freak_score: int = None) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM shadow_scores WHERE user_id = %s", (user_id,))
        existing = cur.fetchone() or {}
        h = hypocrisy_idx if hypocrisy_idx is not None else existing.get("hypocrisy_idx", 0)
        c = conflict_idx  if conflict_idx  is not None else existing.get("conflict_idx", 0)
        f = freak_score   if freak_score   is not None else existing.get("freak_score", 0)
        cur.execute(
            """INSERT INTO shadow_scores (user_id, hypocrisy_idx, conflict_idx, freak_score)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 hypocrisy_idx = VALUES(hypocrisy_idx),
                 conflict_idx  = VALUES(conflict_idx),
                 freak_score   = VALUES(freak_score)""",
            (user_id, h, c, f)
        )
        conn.commit()
        cur.close()
        try:
            get_shadow_score.clear()
        except Exception:
            pass
        return True
    except Exception:
        return False
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_shadow_score(user_id: int) -> dict:
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM shadow_scores WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return row or {}
    except Exception:
        return {}
    finally:
        conn.close()


# ─── PUBLIC BOARD ─────────────────────────────────────────────────────────────

def save_public_confession(author_id: int, content: str, vice: str = None) -> int | None:
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO public_confessions (author_id, content, vice) VALUES (%s, %s, %s)",
            (author_id, content.strip(), vice),
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.close()
        load_public_confessions.clear()
        return new_id
    except Exception as e:
        st.error(f"Error saving public confession: {e}")
        return None
    finally:
        conn.close()


@st.cache_data(ttl=30, show_spinner=False)
def load_public_confessions(limit: int = 20, offset: int = 0, vice: str = None) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        if vice:
            cur.execute(
                """SELECT id, content, vice, reply_count, created_at
                   FROM public_confessions WHERE vice = %s
                   ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (vice, limit, offset),
            )
        else:
            cur.execute(
                """SELECT id, content, vice, reply_count, created_at
                   FROM public_confessions
                   ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (limit, offset),
            )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception:
        return []
    finally:
        conn.close()


def save_public_reply(confession_id: int, author_id: int, content: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO public_confession_replies (confession_id, author_id, content) VALUES (%s, %s, %s)",
            (confession_id, author_id, content.strip()),
        )
        cur.execute(
            "UPDATE public_confessions SET reply_count = reply_count + 1 WHERE id = %s",
            (confession_id,),
        )
        conn.commit()
        cur.close()
        load_public_confessions.clear()
        return True
    except Exception as e:
        st.error(f"Error saving reply: {e}")
        return False
    finally:
        conn.close()


def load_public_replies(confession_id: int) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id, content, created_at
               FROM public_confession_replies
               WHERE confession_id = %s
               ORDER BY created_at ASC""",
            (confession_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception:
        return []
    finally:
        conn.close()


# ─── COMMUNITY QUIZ PULSE ─────────────────────────────────────────────────────

def record_community_answer(question_hash: str, opt_index: int) -> None:
    conn = create_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO community_quiz_answers (question_hash, opt_index, tally)
               VALUES (%s, %s, 1)
               ON DUPLICATE KEY UPDATE tally = tally + 1""",
            (question_hash, opt_index),
        )
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        conn.close()


@st.cache_data(ttl=10, show_spinner=False)
def get_community_answers(question_hash: str) -> dict:
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT opt_index, tally FROM community_quiz_answers WHERE question_hash = %s",
            (question_hash,),
        )
        rows = cur.fetchall()
        cur.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}
    finally:
        conn.close()


# ─── LEGACY QUIZ SAVES ────────────────────────────────────────────────────────

def save_read_between_lines_result(user_id, profile_name, profile_meta, dim_scores,
                                    recommendations, total_pct, questions, answers) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, profile_name, profile_meta, dim_scores,
                recommendations, total_pct, questions, answers)
               VALUES (%s, 'read_between_lines', %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, profile_name, profile_meta, json.dumps(dim_scores),
             json.dumps(recommendations), total_pct,
             json.dumps(questions, default=str), json.dumps(answers))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving RBTL result: {e}")
        return False
    finally:
        conn.close()


# ─── VICE LOG — single entry delete ──────────────────────────────────────────

def delete_vice_entry(entry_id: int, user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM vice_log WHERE id = %s AND user_id = %s",
            (entry_id, user_id)
        )
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        if deleted:
            try:
                load_vice_log.clear()
                load_social_feed.clear()
            except Exception:
                pass
        return deleted
    except Exception as e:
        st.error(f"Error deleting entry: {e}")
        return False
    finally:
        conn.close()


# ─── CLEAN DAYS PER VICE ──────────────────────────────────────────────────────

def get_last_logged_per_vice(user_id: int) -> dict:
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT vice, MAX(logged_at) AS last_logged
               FROM vice_log
               WHERE user_id = %s
               GROUP BY vice""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return {r["vice"]: r["last_logged"] for r in rows}
    except Exception:
        return {}
    finally:
        conn.close()


# ─── DATA EXPORT ──────────────────────────────────────────────────────────────

def export_user_data(user_id: int) -> dict:
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username, email, created_at FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone() or {}
        if user.get("created_at"):
            user["created_at"] = str(user["created_at"])

        cur.execute(
            "SELECT vice, logged_at, details FROM vice_log WHERE user_id = %s ORDER BY logged_at DESC",
            (user_id,)
        )
        vice_log = []
        for row in cur.fetchall():
            d = row.get("details") or {}
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception:
                    d = {}
            vice_log.append({"vice": row["vice"], "logged_at": str(row["logged_at"]), "details": d})

        cur.execute(
            """SELECT quiz_type, completed_at, result_name, openness_pct, dim_scores
               FROM quiz_results WHERE user_id = %s ORDER BY completed_at DESC""",
            (user_id,)
        )
        quiz_results = []
        for row in cur.fetchall():
            ds = row.get("dim_scores") or {}
            if isinstance(ds, str):
                try:
                    ds = json.loads(ds)
                except Exception:
                    ds = {}
            quiz_results.append({
                "quiz_type":    row["quiz_type"],
                "completed_at": str(row["completed_at"]),
                "result_name":  row["result_name"],
                "openness_pct": row["openness_pct"],
                "dim_scores":   ds,
            })

        cur.execute("SELECT vice, weekly_limit FROM vice_goals WHERE user_id = %s", (user_id,))
        goals = {r["vice"]: r["weekly_limit"] for r in cur.fetchall()}

        cur.execute(
            "SELECT interaction_type, created_at, payload FROM interactions WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        interactions = []
        for row in cur.fetchall():
            p = row.get("payload") or {}
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except Exception:
                    p = {}
            interactions.append({"type": row["interaction_type"], "created_at": str(row["created_at"]), "payload": p})

        cur.close()
        return {
            "user":         user,
            "vice_log":     vice_log,
            "quiz_results": quiz_results,
            "goals":        goals,
            "interactions": interactions,
            "exported_at":  __import__("datetime").datetime.now().isoformat(),
        }
    except Exception as e:
        st.error(f"Export error: {e}")
        return {}
    finally:
        conn.close()


# ─── ACCOUNT DELETION ─────────────────────────────────────────────────────────

def delete_user_account(user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user_row = cur.fetchone() or {}
        cur.execute("SELECT vice, logged_at, details FROM vice_log WHERE user_id = %s", (user_id,))
        vice_log_rows = []
        for r in cur.fetchall():
            d = r.get("details") or {}
            if isinstance(d, str):
                try: d = json.loads(d)
                except Exception: d = {}
            vice_log_rows.append({"vice": r["vice"], "logged_at": str(r["logged_at"]), "details": d})
        cur.execute(
            """SELECT quiz_type, completed_at, result_name, openness_pct,
                      dim_scores, recommendations, answers
               FROM quiz_results WHERE user_id = %s""",
            (user_id,)
        )
        quiz_rows = []
        for r in cur.fetchall():
            for col in ("dim_scores", "recommendations", "answers"):
                v = r.get(col)
                if isinstance(v, str):
                    try: r[col] = json.loads(v)
                    except Exception: r[col] = {}
            r["completed_at"] = str(r.get("completed_at", ""))
            quiz_rows.append(r)
        cur.execute("SELECT vice, weekly_limit FROM vice_goals WHERE user_id = %s", (user_id,))
        goals_rows = {r["vice"]: r["weekly_limit"] for r in cur.fetchall()}
        cur.execute("SELECT interaction_type, created_at, payload FROM interactions WHERE user_id = %s", (user_id,))
        interaction_rows = []
        for r in cur.fetchall():
            p = r.get("payload") or {}
            if isinstance(p, str):
                try: p = json.loads(p)
                except Exception: p = {}
            interaction_rows.append({"type": r["interaction_type"], "created_at": str(r["created_at"]), "payload": p})
        cur.execute("SELECT * FROM shadow_scores WHERE user_id = %s", (user_id,))
        shadow_row = cur.fetchone() or {}

        cur.close()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO deleted_user_archive
               (original_user_id, username, email,
                vice_log, quiz_results, goals, interactions, shadow_scores)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                user_row.get("username", ""),
                user_row.get("email", ""),
                json.dumps(vice_log_rows,    default=str),
                json.dumps(quiz_rows,        default=str),
                json.dumps(goals_rows,       default=str),
                json.dumps(interaction_rows, default=str),
                json.dumps(shadow_row,       default=str),
            )
        )
        for table in ["vice_log", "quiz_results", "vice_goals", "interactions", "shadow_scores", "session_tokens"]:
            try:
                cur.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            except Exception:
                pass
        try:
            cur.execute("DELETE FROM confessions WHERE sender_id = %s AND status = 'sent'", (user_id,))
            cur.execute("UPDATE public_confessions SET author_id = 0 WHERE author_id = %s", (user_id,))
            # Remove from friend requests
            cur.execute("DELETE FROM friend_requests WHERE sender_id = %s OR recipient_id = %s", (user_id, user_id))
        except Exception:
            pass
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()
        try:
            load_vice_log.clear()
            load_confessions_inbox.clear()
            load_confessions_outbox.clear()
            load_friends.clear()
            load_friend_requests.clear()
        except Exception:
            pass
        return True
    except Exception as e:
        st.error(f"Account deletion error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


# ─── DO OR DRINK ROOMS ────────────────────────────────────────────────────────

def create_dod_room(host_id: int, host_username: str, mode: str) -> str | None:
    import secrets, string
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        for _ in range(10):
            code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            host_player = json.dumps([{"username": host_username, "user_id": host_id, "is_host": True}])
            try:
                cur.execute(
                    """INSERT INTO dod_rooms (room_code, host_id, host_username, players, mode)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (code, host_id, host_username, host_player, mode)
                )
                conn.commit()
                cur.close()
                return code
            except mysql.connector.IntegrityError:
                continue
        cur.close()
        return None
    except Exception as e:
        st.error(f"Room creation error: {e}")
        return None
    finally:
        conn.close()


def join_dod_room(room_code: str, user_id: int, username: str) -> dict | None:
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM dod_rooms WHERE room_code = %s AND status = 'waiting'", (room_code.upper(),))
        room = cur.fetchone()
        if not room:
            cur.close()
            return "not_found"
        players = room.get("players") or []
        if isinstance(players, str):
            try:
                players = json.loads(players)
            except Exception:
                players = []
        if any(p.get("user_id") == user_id for p in players):
            cur.close()
            return "already_in"
        players.append({"username": username, "user_id": user_id, "is_host": False})
        cur.execute("UPDATE dod_rooms SET players = %s WHERE room_code = %s", (json.dumps(players), room_code.upper()))
        conn.commit()
        room["players"] = players
        cur.close()
        return room
    except Exception as e:
        st.error(f"Room join error: {e}")
        return None
    finally:
        conn.close()


def get_dod_room(room_code: str) -> dict | None:
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM dod_rooms WHERE room_code = %s", (room_code.upper(),))
        room = cur.fetchone()
        cur.close()
        if room:
            players = room.get("players") or []
            if isinstance(players, str):
                try:
                    room["players"] = json.loads(players)
                except Exception:
                    room["players"] = []
        return room
    except Exception:
        return None
    finally:
        conn.close()


def close_dod_room(room_code: str) -> None:
    conn = create_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("UPDATE dod_rooms SET status = 'closed' WHERE room_code = %s", (room_code,))
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        conn.close()


def cleanup_old_dod_rooms() -> None:
    conn = create_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM dod_rooms WHERE created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)")
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        conn.close()


# ─── RBTL RESULT HISTORY ──────────────────────────────────────────────────────

def load_rbtl_history(user_id: int, limit: int = 5) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT result_name, result_meta, openness_pct, total_pts, completed_at, dim_scores
               FROM quiz_results
               WHERE user_id = %s AND quiz_type = 'rbtl_v4_profile_complete'
               ORDER BY completed_at DESC
               LIMIT %s""",
            (user_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
        for row in rows:
            row["completed_at"] = str(row.get("completed_at", ""))[:16]
            ds = row.get("dim_scores") or {}
            if isinstance(ds, str):
                try:
                    ds = json.loads(ds)
                except Exception:
                    ds = {}
            row["dim_scores"] = ds
        return rows
    except Exception:
        return []
    finally:
        conn.close()


def authenticate_user(username: str, password: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if not user:
            return None
        stored = user.get("password_hash", "")
        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            try:
                import bcrypt
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    return user
            except Exception:
                pass
            return None
        if len(stored) == 64:
            import hashlib
            if hashlib.sha256(password.encode()).hexdigest() == stored:
                return user
            return None
        if stored == password:
            return user
        return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None
    finally:
        conn.close()


# ─── FRIENDS / SOCIAL ─────────────────────────────────────────────────────────

def send_friend_request(sender_id: int, recipient_id: int) -> str:
    """
    Returns: 'sent' | 'already_friends' | 'already_sent' | 'error'

    Bug fix: previously the cursor was closed inside the `if row:` block and
    then re-used for the INSERT when status was 'declined', causing an
    OperationalError. Now the check returns early for terminal states and
    the cursor stays open until the INSERT is done.
    """
    conn = create_connection()
    if not conn:
        return "error"
    try:
        cur = conn.cursor(dictionary=True)
        # Check existing relationship in either direction
        cur.execute(
            """SELECT id, status, sender_id FROM friend_requests
               WHERE (sender_id = %s AND recipient_id = %s)
                  OR (sender_id = %s AND recipient_id = %s)""",
            (sender_id, recipient_id, recipient_id, sender_id)
        )
        row = cur.fetchone()

        if row:
            existing_status = row["status"]
            existing_id     = row["id"]

            if existing_status == "accepted":
                cur.close()
                return "already_friends"

            if existing_status == "pending":
                cur.close()
                return "already_sent"

            # Status is 'declined' — update the existing row in-place
            # (keeps the original direction; either party can re-initiate)
            cur.execute(
                "UPDATE friend_requests SET sender_id=%s, recipient_id=%s, status='pending', updated_at=NOW() WHERE id=%s",
                (sender_id, recipient_id, existing_id)
            )
            conn.commit()
            cur.close()
        else:
            # Fresh request — no prior relationship
            cur.close()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO friend_requests (sender_id, recipient_id, status)
                   VALUES (%s, %s, 'pending')""",
                (sender_id, recipient_id)
            )
            conn.commit()
            cur.close()

        try:
            load_friend_requests.clear()
            load_friends.clear()
        except Exception:
            pass
        return "sent"
    except Exception as e:
        st.error(f"Friend request error: {e}")
        return "error"
    finally:
        conn.close()


def respond_friend_request(request_id: int, user_id: int, accept: bool) -> bool:
    """Accept or decline a friend request. user_id must be the recipient."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        new_status = "accepted" if accept else "declined"
        cur.execute(
            """UPDATE friend_requests
               SET status = %s, updated_at = NOW()
               WHERE id = %s AND recipient_id = %s AND status = 'pending'""",
            (new_status, request_id, user_id)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        if changed:
            try:
                load_friend_requests.clear()
                load_friends.clear()
            except Exception:
                pass
        return changed
    except Exception:
        return False
    finally:
        conn.close()


def remove_friend(user_id: int, friend_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM friend_requests
               WHERE (sender_id = %s AND recipient_id = %s)
                  OR (sender_id = %s AND recipient_id = %s)""",
            (user_id, friend_id, friend_id, user_id)
        )
        conn.commit()
        removed = cur.rowcount > 0
        cur.close()
        if removed:
            try:
                load_friends.clear()
                load_friend_requests.clear()
            except Exception:
                pass
        return removed
    except Exception:
        return False
    finally:
        conn.close()


@st.cache_data(ttl=30, show_spinner=False)
def load_friend_requests(user_id: int) -> list:
    """Pending requests where user_id is the recipient."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT fr.id, fr.sender_id, fr.created_at, u.username AS sender_username
               FROM friend_requests fr
               JOIN users u ON u.id = fr.sender_id
               WHERE fr.recipient_id = %s AND fr.status = 'pending'
               ORDER BY fr.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception:
        return []
    finally:
        conn.close()


@st.cache_data(ttl=30, show_spinner=False)
def load_friends(user_id: int) -> list:
    """
    Returns list of accepted friends with basic public stats.
    Each item: {user_id, username, freak_score, top_vice, session_count_30d, rbtl_name}
    """
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT
                 CASE WHEN fr.sender_id = %s THEN fr.recipient_id ELSE fr.sender_id END AS friend_id,
                 CASE WHEN fr.sender_id = %s THEN ru.username ELSE su.username END AS username,
                 fr.id AS request_id
               FROM friend_requests fr
               JOIN users su ON su.id = fr.sender_id
               JOIN users ru ON ru.id = fr.recipient_id
               WHERE (fr.sender_id = %s OR fr.recipient_id = %s)
                 AND fr.status = 'accepted'""",
            (user_id, user_id, user_id, user_id)
        )
        friends = cur.fetchall()

        result = []
        for f in friends:
            fid = f["friend_id"]
            # Shadow score (freak score)
            cur.execute("SELECT freak_score FROM shadow_scores WHERE user_id = %s", (fid,))
            ss = cur.fetchone()
            freak = ss["freak_score"] if ss else None

            # Vice summary (last 30 days)
            cur.execute(
                """SELECT vice, COUNT(*) AS cnt FROM vice_log
                   WHERE user_id = %s AND logged_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   GROUP BY vice ORDER BY cnt DESC""",
                (fid,)
            )
            vice_rows = cur.fetchall()
            total_sessions = sum(r["cnt"] for r in vice_rows)
            top_vice       = vice_rows[0]["vice"] if vice_rows else None
            vice_counts    = {r["vice"]: r["cnt"] for r in vice_rows}

            # Last RBTL result
            cur.execute(
                """SELECT result_name FROM quiz_results
                   WHERE user_id = %s AND quiz_type = 'rbtl_v4_profile_complete'
                   ORDER BY completed_at DESC LIMIT 1""",
                (fid,)
            )
            rbtl = cur.fetchone()

            # Days clean per vice
            cur.execute(
                """SELECT vice, MAX(logged_at) AS last_logged
                   FROM vice_log WHERE user_id = %s GROUP BY vice""",
                (fid,)
            )
            last_per_vice = {r["vice"]: r["last_logged"] for r in cur.fetchall()}

            result.append({
                "user_id":         fid,
                "username":        f["username"],
                "request_id":      f["request_id"],
                "freak_score":     freak,
                "top_vice":        top_vice,
                "session_count":   total_sessions,
                "vice_counts":     vice_counts,
                "rbtl_name":       rbtl["result_name"] if rbtl else None,
                "last_per_vice":   {k: v.isoformat() if hasattr(v, "isoformat") else str(v)
                                    for k, v in last_per_vice.items()},
            })

        cur.close()
        return result
    except Exception as e:
        st.error(f"Error loading friends: {e}")
        return []
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_user_public_stats(user_id: int) -> dict:
    """
    Fetch aggregated public stats for a single user.
    Used in the compare view. No individual session details exposed.
    """
    conn = create_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        u = cur.fetchone()
        if not u:
            cur.close()
            return {}

        cur.execute("SELECT freak_score, conflict_idx FROM shadow_scores WHERE user_id = %s", (user_id,))
        ss = cur.fetchone() or {}

        cur.execute(
            """SELECT vice, COUNT(*) AS cnt FROM vice_log
               WHERE user_id = %s AND logged_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
               GROUP BY vice ORDER BY cnt DESC""",
            (user_id,)
        )
        vice_rows = cur.fetchall()
        vice_counts  = {r["vice"]: r["cnt"] for r in vice_rows}
        total        = sum(vice_counts.values())
        top_vice     = vice_rows[0]["vice"] if vice_rows else None

        cur.execute(
            """SELECT vice, MAX(logged_at) AS last_logged
               FROM vice_log WHERE user_id = %s GROUP BY vice""",
            (user_id,)
        )
        last_per_vice = {}
        for r in cur.fetchall():
            last_per_vice[r["vice"]] = r["last_logged"]

        cur.execute(
            """SELECT result_name, result_meta, openness_pct FROM quiz_results
               WHERE user_id = %s AND quiz_type = 'rbtl_v4_profile_complete'
               ORDER BY completed_at DESC LIMIT 1""",
            (user_id,)
        )
        rbtl = cur.fetchone()

        cur.close()
        return {
            "username":      u["username"],
            "freak_score":   ss.get("freak_score"),
            "conflict_idx":  ss.get("conflict_idx"),
            "vice_counts":   vice_counts,
            "total_sessions": total,
            "top_vice":      top_vice,
            "last_per_vice": {k: v.isoformat() if hasattr(v, "isoformat") else str(v)
                              for k, v in last_per_vice.items()},
            "rbtl_name":     rbtl["result_name"]    if rbtl else None,
            "rbtl_meta":     rbtl["result_meta"]    if rbtl else None,
            "rbtl_openness": rbtl["openness_pct"]   if rbtl else None,
        }
    except Exception:
        return {}
    finally:
        conn.close()
