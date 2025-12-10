# main.py

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

from bot.config import *
from database import (
    init_db,
    add_session,
    get_sessions_by_owner,
    get_all_sessions,
    delete_sessions_by_owner,
    mark_all_inactive,
    get_sessions_for_disconnect,
)

# --- init db & folder sessions ---
os.makedirs("sessions", exist_ok=True)
init_db()

app = Client(
    "bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

# state login & pending
user_states: Dict[int, str] = {}
pending_logins: Dict[int, Dict[str, Any]] = {}


def main_keyboard() -> InlineKeyboardMarkup:
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
        "• Forward pesan kode dari **@Telegram (777000)** ke sini sebelum menekan READ CODE.",
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


# ---------- CALLBACK HANDLER UTAMA ----------


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
    elif data == "reset_pw":
        await q.answer("Fitur reset password belum diimplementasikan.", show_alert=True)
    else:
        await q.answer("Unknown action")


# ---------- CALLBACK IMPLEMENTATION ----------


async def handle_connect(q: CallbackQuery):
    uid = q.from_user.id
    user_states[uid] = "awaiting_phone"

    await q.message.reply(
        "Kirim nomor telepon akun Telegram yang ingin login.\n"
        "Format internasional tanpa +, contoh: `6281234567890`",
        parse_mode=enums.ParseMode.MARKDOWN,
    )
    await q.answer()


async def handle_read_code(q: CallbackQuery):
    uid = q.from_user.id
    pending = pending_logins.get(uid)

    if not pending:
        await q.answer("Tidak ada proses login yang aktif.", show_alert=True)
        return

    code = pending.get("code")
    if not code:
        await q.answer(
            "Belum ada kode yang terbaca.\n"
            "Forward pesan kode dari @Telegram (777000) ke bot dulu.",
            show_alert=True,
        )
        return

    await q.answer("Mencoba login dengan kode yang tersimpan...")
    await do_sign_in(q.message, uid)


async def handle_list_sesi(q: CallbackQuery):
    uid = q.from_user.id
    sessions = get_sessions_by_owner(uid)
    if not sessions:
        await q.message.reply("List Active Session\nTotal users: 0")
        await q.answer()
        return

    lines = [f"List Active Session\nTotal users: {len(sessions)}\n"]
    for row in sessions:
        (
            sid,
            owner_id,
            phone,
            session_name,
            _session_string,
            tg_user_id,
            username,
            first_name,
            device,
            is_active,
            created_at,
        ) = row

        status_icon = "✅" if is_active else "❌"
        lines.append(
            f"ID DB: {sid}\n"
            f"STATUS: {status_icon}\n"
            f"TG ID: {tg_user_id}\n"
            f"USERNAME: @{username if username else '-'}\n"
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
    for sid, session_string in rows:
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
            # jika gagal logout, lanjut saja
            continue

    mark_all_inactive(uid)
    await q.message.reply(
        f"DISCONNECT selesai.\nBerhasil logout dari {success} session."
    )
    await q.answer("Disconnect selesai.")


async def handle_clear_chats(q: CallbackQuery):
    # hapus histori chat user dengan bot (sejauh kemampuan bot)
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
        phone = row[2]  # kolom phone
        tg_user_id = row[5]
        username = row[6] or "-"
        phones.append(f"{phone} → {tg_user_id} (@{username})")
    text = "Daftar nomor yang tersimpan:\n\n" + "\n".join(phones)
    await q.message.reply(text)
    await q.answer()


# ---------- MESSAGE HANDLER UNTUK PHONE & FORWARD KODE ----------


@app.on_message(filters.private & ~filters.command(["start", "users", "admin_users"]))
async def generic_message_handler(_, m: Message):
    uid = m.from_user.id
    state = user_states.get(uid)

    # Step 1: user sedang diminta kirim nomor HP
    if state == "awaiting_phone":
        phone = re.sub(r"[^\d]", "", m.text or "")
        if len(phone) < 7:
            await m.reply(
                "Nomor tidak valid.\n"
                "Kirim lagi dengan format angka saja, contoh: `6281234567890`",
                parse_mode=enums.ParseMode.MARKDOWN,
            )
            return

        await start_login_process(m, phone)
        return

    # Step 2: user forward kode dari 777000
    if state == "waiting_code_forward":
        if m.forward_from and m.forward_from.id == 777000 and (m.text or ""):
            match = re.search(r"\d{5}", m.text)
            if not match:
                await m.reply("Tidak menemukan kode 5 digit di pesan itu.")
                return

            code = match.group(0)
            pending = pending_logins.get(uid)
            if not pending:
                await m.reply("Tidak ada proses login yang aktif.")
                return

            pending["code"] = code
            await m.reply(
                f"Kode berhasil dibaca: `{code}`\n"
                "Sekarang tekan tombol **READ CODE** untuk melanjutkan login.",
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=main_keyboard(),
            )
        else:
            await m.reply(
                "Kirim/forward pesan kode dari **@Telegram (777000)** ke bot ini.",
                parse_mode=enums.ParseMode.MARKDOWN,
            )


# ---------- LOGIN FLOW HELPER ----------


async def start_login_process(m: Message, phone: str):
    uid = m.from_user.id

    await m.reply(
        f"Mengirim kode ke nomor: `{phone}`\n"
        "Jika sudah menerima kode dari @Telegram (777000), forward ke bot ini,\n"
        "lalu tekan tombol **READ CODE**.",
        parse_mode=enums.ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )

    # siapkan client user sementara
    session_name = os.path.join(
        "sessions", f"{uid}_{int(datetime.now().timestamp())}"
    )

    user_client = Client(
        session_name,
        api_id=config.API_ID,
        api_hash=config.API_HASH,
    )

    try:
        await user_client.connect()
        sent = await user_client.send_code(phone)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        sent = await user_client.send_code(phone)
    except Exception as e:
        await m.reply(f"Gagal mengirim kode: `{e}`")
        try:
            await user_client.disconnect()
        except Exception:
            pass
        return

    pending_logins[uid] = {
        "client": user_client,
        "phone": phone,
        "session_name": session_name,
        "phone_code_hash": sent.phone_code_hash,
        "code": None,
    }
    user_states[uid] = "waiting_code_forward"


async def do_sign_in(msg: Message, uid: int):
    pending = pending_logins.get(uid)
    if not pending:
        await msg.reply("Tidak ada proses login yang aktif.")
        return

    client: Client = pending["client"]
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
        await msg.reply("Kode salah. Forward ulang kode dari 777000 lalu READ CODE lagi.")
        return
    except SessionPasswordNeeded:
        await msg.reply(
            "Akun ini menggunakan verifikasi dua langkah (password).\n"
            "Fitur ini belum mendukung login akun dengan 2FA."
        )
        return
    except FloodWait as e:
        await msg.reply(f"FloodWait {e.value}s, menunggu sebentar...")
        await asyncio.sleep(e.value)
        return
    except Exception as e:
        await msg.reply(f"Gagal login: `{e}`")
        return

    # login sukses, ambil info dan simpan
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

    # simpan string session ke file txt supaya bisa diunduh
    txt_path = pending["session_name"] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(session_string)

    # file .session yang dibuat Pyrogram
    session_file_path = pending["session_name"] + ".session"

    summary = (
        "✅ Session berhasil dibuat!\n\n"
        f"STATUS: ✅ Aktif\n"
        f"ID: `{me.id}`\n"
        f"USERNAME: @{me.username if me.username else '-'}\n"
        f"NAMA: {me.first_name}\n"
        f"NOHP: `{phone}`\n"
        f"TANGGAL: {created_at}\n"
    )

    await msg.reply(
        summary,
        parse_mode=enums.ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )

    # kirim file string session + file .session kalau ada
    await app.send_document(
        msg.chat.id,
        txt_path,
        caption="String session kamu (jaga baik-baik).",
    )

    if os.path.exists(session_file_path):
        await app.send_document(
            msg.chat.id,
            session_file_path,
            caption="File .session Pyrogram kamu.",
        )

    # beres, bersihkan state
    try:
        await client.disconnect()
    except Exception:
        pass

    pending_logins.pop(uid, None)
    user_states.pop(uid, None)


# ---------- MAIN ----------

if __name__ == "__main__":
    print("BOT SESSION MANAGER BERJALAN...")
    app.run()
