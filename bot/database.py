# bot/database.py
import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "sessions.json")

# buat file jika belum ada
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump([], f)

# --- helper ---
def _load():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def _save(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --- add session ---
def add_session(data):
    db = _load()
    data["id"] = len(db) + 1
    data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.append(data)
    _save(db)
    return data["id"]

# --- get sessions by owner ---
def get_sessions_by_owner(owner_id: int):
    db = _load()
    return [s for s in db if s["owner_id"] == owner_id]

# --- get all sessions (admin) ---
def get_all_sessions():
    return _load()

# --- delete session by owner ---
def delete_sessions_by_owner(owner_id: int):
    db = _load()
    newdb = [s for s in db if s["owner_id"] != owner_id]
    deleted = len(db) - len(newdb)

    _save(newdb)
    return deleted

# --- mark all inactive ---
def mark_all_inactive(owner_id: int):
    db = _load()
    for s in db:
        if s["owner_id"] == owner_id:
            s["is_active"] = 0
    _save(db)
    return True

# --- get sessions for disconnect ---
def get_sessions_for_disconnect(owner_id: int):
    db = _load()
    return [
        s for s in db 
        if s["owner_id"] == owner_id and s.get("is_active", 1) == 1
    ]
