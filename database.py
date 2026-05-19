# database.py
import json
import streamlit as st

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    from config import DB_CONFIG
except ImportError:
    DB_CONFIG = {}


def create_connection():
    if not MYSQL_AVAILABLE:
        return None
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG.get('host', ''),
            port=int(DB_CONFIG.get('port', 3306)),
            user=DB_CONFIG.get('user', ''),
            password=DB_CONFIG.get('password', ''),
            database=DB_CONFIG.get('database', ''),
            connection_timeout=30,
            autocommit=False,
            ssl_disabled=True,
        )
        return conn
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
            quiz_type       VARCHAR(32)  NOT NULL,
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
    ]

    try:
        cur = conn.cursor()
        for ddl in ddl_statements:
            cur.execute(ddl)
        conn.commit()

        try:
            cur.execute("ALTER TABLE confessions ADD COLUMN revealed_at DATETIME DEFAULT NULL")
            conn.commit()
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE confessions ADD COLUMN reveal_window_secs INT NOT NULL DEFAULT 60")
            conn.commit()
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE confessions MODIFY COLUMN recipient_id INT DEFAULT NULL")
            conn.commit()
        except Exception:
            pass

        try:
            cur.execute("ALTER TABLE confessions ADD COLUMN recipient_email VARCHAR(255) DEFAULT NULL")
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
        return new_id
    except Exception as e:
        st.error(f"Error saving vice entry: {e}")
        return None
    finally:
        conn.close()


def load_vice_log(user_id: int) -> list:
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
        return True
    except Exception as e:
        st.error(f"Error deleting vice log: {e}")
        return False
    finally:
        conn.close()


# ─── SOCIAL FEED ──────────────────────────────────────────────────────────────

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
        return True
    except Exception as e:
        st.error(f"Error saving vice goal: {e}")
        return False
    finally:
        conn.close()


# ─── QUIZ RESULTS ─────────────────────────────────────────────────────────────

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


def save_what_would_you_do_result(user_id, result_name, result_meta,
                                   openness_pct, total_pts, questions, answers) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, result_name, result_meta,
                openness_pct, total_pts, questions, answers)
               VALUES (%s, 'what_would_you_do', %s, %s, %s, %s, %s, %s)""",
            (user_id, result_name, result_meta, openness_pct, total_pts,
             json.dumps(questions, default=str), json.dumps(answers))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving WWYD result: {e}")
        return False
    finally:
        conn.close()


def save_read_between_lines_v4(
    user_id:         int,
    phase:           str,
    result_name:     str,
    result_meta:     str,
    openness_pct:    int,
    total_pts:       int,
    questions:       list,
    answers:         dict,
    dim_scores:      dict,
    recommendations: list,
) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type,
                result_name, result_meta,
                openness_pct, total_pts,
                questions, answers,
                dim_scores, recommendations)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                f"read_between_lines_v4_{phase}",
                result_name[:128] if result_name else "",
                result_meta[:255] if result_meta else "",
                max(0, min(255, openness_pct)),
                max(0, min(65535, total_pts)),
                json.dumps(questions,       default=str),
                json.dumps(answers,         default=str),
                json.dumps(dim_scores,      default=str),
                json.dumps(recommendations, default=str),
            )
        )
        conn.commit()
        cur.close()
        return True          # plain bool — callers must NOT unpack as tuple
    except Exception:
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
               WHERE user_id = %s AND quiz_type LIKE 'read_between_lines_v4%%'
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
        return True          # plain bool — callers must NOT unpack as tuple
    except Exception:
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
               WHERE user_id = %s AND quiz_type LIKE 'read_between_lines_v4%'
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


def load_confessions_inbox(user_id: int) -> list:
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


def load_confessions_outbox(user_id: int) -> list:
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
        return count
    except Exception as e:
        st.error(f"Error cleaning up confessions: {e}")
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


# ─── INTERACTIONS TABLE ───────────────────────────────────────────────────────

INTERACTIONS_DDL = """
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
"""

SHADOW_SCORE_DDL = """
CREATE TABLE IF NOT EXISTS shadow_scores (
    user_id          INT NOT NULL PRIMARY KEY,
    hypocrisy_idx    TINYINT UNSIGNED DEFAULT 0,
    conflict_idx     TINYINT UNSIGNED DEFAULT 0,
    freak_score      TINYINT UNSIGNED DEFAULT 0,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def ensure_interactions_table():
    conn = create_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(INTERACTIONS_DDL)
        cur.execute(SHADOW_SCORE_DDL)
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        conn.close()


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
        return True
    except Exception:
        return False
    finally:
        conn.close()


def load_interactions(user_id: int, interaction_type: str = None) -> list:
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
        return True
    except Exception:
        return False
    finally:
        conn.close()


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
