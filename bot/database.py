# database.py (JSON Storage Version)

import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")

# Pastikan file JSON ada
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)


# ---- Helper internal ----

def _load_db():
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---- Public API ----

def init_db():
    """Compatibility only. JSON does not need schema."""
    pass


def add_session(data):
    db = _load_db()

    # Auto-increment ID
    data["id"] = (db[-1]["id"] + 1) if db else 1

    # Timestamp jika belum ada
    if "created_at" not in data:
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Default is_active
    if "is_active" not in data:
        data["is_active"] = 1

    db.append(data)
    _save_db(db)
    return data["id"]


def get_sessions_by_owner(owner_id: int):
    db = _load_db()
    return [x for x in db if x["owner_id"] == owner_id]


def get_all_sessions():
    return _load_db()


def delete_sessions_by_owner(owner_id: int):
    db = _load_db()
    new_db = [x for x in db if x["owner_id"] != owner_id]
    deleted = len(db) - len(new_db)
    _save_db(new_db)
    return deleted


def mark_all_inactive(owner_id: int):
    db = _load_db()
    for sess in db:
        if sess["owner_id"] == owner_id:
            sess["is_active"] = 0
    _save_db(db)
    return True


def get_sessions_for_disconnect(owner_id: int):
    db = _load_db()
    return [x for x in db if x["owner_id"] == owner_id and x.get("is_active", 1) == 1]
