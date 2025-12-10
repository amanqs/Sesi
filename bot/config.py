import os
from typing import List


API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")


def _parse_admins(env_value: str) -> List[int]:
    result: List[int] = []
    for part in env_value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


ADMINS: List[int] = _parse_admins(os.getenv("ADMINS", ""))

DB_PATH = os.getenv("DB_PATH", "sessions.db")
