from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟢 CONNECT", callback_data="connect"),
                InlineKeyboardButton("📄 LIST SESI", callback_data="list_sessions"),
            ],
            [
                InlineKeyboardButton("🧾 LIST ACTIVE", callback_data="list_active"),
            ],
        ]
    )


def session_actions_keyboard(session_id:
