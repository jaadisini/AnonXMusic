import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram.errors import FloodWait
from pyrogram.enums import ChatMemberStatus

from anony import app
from anony.helpers._admins import is_admin


# ================= ADMIN FILTER =================

async def admin_filter_func(_, __, obj: Message | CallbackQuery) -> bool:
    msg = obj.message if isinstance(obj, CallbackQuery) else obj
    if not msg.from_user:
        return False
    return await is_admin(msg.chat.id, msg.from_user.id)


admin_filter = filters.create(admin_filter_func)

# ================= GLOBAL =================

active_tags = {}  
pending_tags = {}  


# ================= START COMMAND =================

@app.on_message(filters.command(["utag", "all", "mention"]) & filters.group & admin_filter)
async def choose_duration(client: Client, message: Message):
    chat_id = message.chat.id
    text = message.text.split(None, 1)[1] if len(message.command) > 1 else ""

    if not text and not message.reply_to_message:
        return await message.reply(
            "⚠️ **Reply pesan atau berikan teks untuk tag semua!**"
        )

    pending_tags[chat_id] = {"text": text}

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏱ 1 Menit", callback_data=f"starttag:{chat_id}:60"),
                InlineKeyboardButton("⏱ 2 Menit", callback_data=f"starttag:{chat_id}:120"),
                InlineKeyboardButton("⏱ 3 Menit", callback_data=f"starttag:{chat_id}:180"),
            ],
            [
                InlineKeyboardButton("⏱ 4 Menit", callback_data=f"starttag:{chat_id}:240"),
                InlineKeyboardButton("⏱ 5 Menit", callback_data=f"starttag:{chat_id}:300"),
                InlineKeyboardButton("🔥 10 Menit", callback_data=f"starttag:{chat_id}:600"),
            ],
        ]
    )

    await message.reply(
        "🚀 **MODE TAG SEMUA**\n\n"
        "📌 Pilih durasi sebelum auto cancel berjalan:",
        reply_markup=keyboard,
    )


# ================= START TAGGING =================

@app.on_callback_query(filters.regex(r"starttag:(-?\d+):(\d+)"))
async def start_tagging(client: Client, query: CallbackQuery):
    chat_id = int(query.data.split(":")[1])
    duration = int(query.data.split(":")[2])

    if chat_id in active_tags:
        return await query.answer("⚠️ Tagging sedang berjalan!", show_alert=True)

    if chat_id not in pending_tags:
        return await query.answer("⏳ Sesi sudah kadaluarsa!", show_alert=True)

    text = pending_tags[chat_id]["text"]
    pending_tags.pop(chat_id, None)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛑 Hentikan Sekarang", callback_data=f"cancel:{chat_id}")]
        ]
    )

    await query.message.edit_text(
        "🚀 **TAGGING DIMULAI...**\n\n"
        "📢 Sedang memanggil semua member...",
        reply_markup=keyboard,
    )

    active_tags[chat_id] = {"running": True}

    async def auto_stop():
        await asyncio.sleep(duration)
        if chat_id in active_tags:
            active_tags[chat_id]["running"] = False
            try:
                await query.message.edit_text(
                    f"⏳ **AUTO STOP**\n\n"
                    f"🛑 Tagging dihentikan otomatis setelah {duration//60} menit."
                )
            except:
                pass

    asyncio.create_task(auto_stop())

    total = 0
    buffer = []

    try:
        async for member in client.get_chat_members(chat_id):

            if not active_tags.get(chat_id, {}).get("running"):
                break

            if not member.user or member.user.is_bot:
                continue

            total += 1
            buffer.append(
                f"👤 [{member.user.first_name}](tg://user?id={member.user.id})"
            )

            if len(buffer) == 5:
                caption = (
                    f"💬 **{text}**\n\n"
                    + "\n".join(buffer)
                    + f"\n\n📊 Progress: `{total}` users"
                )

                try:
                    await query.message.edit_text(
                        caption,
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value)

                await asyncio.sleep(2)
                buffer.clear()

        if active_tags.get(chat_id, {}).get("running"):
            await query.message.edit_text(
                f"✅ **TAGGING SELESAI!**\n\n"
                f"📢 Total Member Ditag: `{total}`"
            )

    except:
        pass
    finally:
        active_tags.pop(chat_id, None)


# ================= MANUAL CANCEL =================

@app.on_callback_query(filters.regex(r"cancel:(-?\d+)"))
async def cancel_tagging(client: Client, query: CallbackQuery):
    chat_id = int(query.data.split(":")[1])

    if chat_id not in active_tags:
        return await query.answer("⚠️ Tidak ada tagging aktif!", show_alert=True)

    active_tags[chat_id]["running"] = False

    await query.message.edit_text(
        "🚫 **TAGGING DIHENTIKAN**\n\n"
        "🛑 Proses berhasil dibatalkan."
    )
    await query.answer("Berhasil dihentikan ✅")
