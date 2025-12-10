# database.py
import os
import sqlite3
from .config import DB_PATH

# Pastikan folder tempat DB berada ada
db_dir = os.path.dirname(DB_PATH)
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

# Buat file DB jika belum ada
if not os.path.exists(DB_PATH):
    open(DB_PATH, "a").close()

# Pastikan permission aman
os.chmod(DB_PATH, 0o666)

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_cur = _conn.cursor()



def init_db():
    _cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            phone TEXT,
            session_name TEXT,
            session_string TEXT,
            tg_user_id INTEGER,
            username TEXT,
            first_name TEXT,
            device TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    _conn.commit()


def add_session(data: Dict[str, Any]) -> int:
    _cur.execute(
        """
        INSERT INTO sessions (
            owner_id, phone, session_name, session_string,
            tg_user_id, username, first_name, device,
            is_active, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["owner_id"],
            data.get("phone"),
            data["session_name"],
            data["session_string"],
            data.get("tg_user_id"),
            data.get("username"),
            data.get("first_name"),
            data.get("device", "PyrogramClient"),
            data.get("is_active", 1),
            data.get("created_at"),
        ),
    )
    _conn.commit()
    return _cur.lastrowid


def get_sessions_by_owner(owner_id: int) -> List[sqlite3.Row]:
    _cur.execute(
        "SELECT * FROM sessions WHERE owner_id = ? ORDER BY id DESC", (owner_id,)
    )
    return _cur.fetchall()


def get_all_sessions() -> List[sqlite3.Row]:
    _cur.execute("SELECT * FROM sessions ORDER BY id DESC")
    return _cur.fetchall()


def delete_sessions_by_owner(owner_id: int) -> int:
    _cur.execute("DELETE FROM sessions WHERE owner_id = ?", (owner_id,))
    changes = _conn.total_changes
    _conn.commit()
    return changes


def mark_all_inactive(owner_id: int) -> int:
    _cur.execute(
        "UPDATE sessions SET is_active = 0 WHERE owner_id = ? AND is_active = 1",
        (owner_id,),
    )
    changes = _conn.total_changes
    _conn.commit()
    return changes


def get_sessions_for_disconnect(owner_id: int):
    _cur.execute(
        "SELECT id, session_string FROM sessions WHERE owner_id = ? AND is_active = 1",
        (owner_id,),
    )
    return _cur.fetchall()
