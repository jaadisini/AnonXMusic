# TagAll Pro Final
# Production Ready

import asyncio
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message
)

from anony import app
from anony.helpers._admins import admin_check


async def admin_filter_func(_, __, obj: Message | CallbackQuery) -> bool:
    msg = obj.message if isinstance(obj, CallbackQuery) else obj
    if not msg.from_user:
        return False
    return await is_admin(msg.chat.id, msg.from_user.id)


admin_filter = filters.create(admin_filter_func)


# =========================
# CONFIG
# =========================

DELAY_BETWEEN_MESSAGES = 2
USERS_PER_MESSAGE = 5

# =========================
# RUNTIME STORAGE
# =========================

ACTIVE_TAG = {}

# =========================
# KEYBOARD
# =========================

def duration_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("1m", callback_data="tag_1"),
                InlineKeyboardButton("2m", callback_data="tag_2"),
                InlineKeyboardButton("3m", callback_data="tag_3"),
            ],
            [
                InlineKeyboardButton("4m", callback_data="tag_4"),
                InlineKeyboardButton("5m", callback_data="tag_5"),
                InlineKeyboardButton("10m", callback_data="tag_10"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="tag_cancel")
            ]
        ]
    )

def running_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⛔ Stop TagAll", callback_data="tag_cancel")]
        ]
    )

# =========================
# MESSAGE BUILDER
# =========================

async def build_tag_message(title: str, users: list, bot_username: str):
    text = f"**{title}  ”**\n\n"
    text += "```\n"
    for user in users:
        text += f"• {user}\n"
    text += "```\n\n"
    text += f"@{bot_username}"
    return text

# =========================
# COMMAND
# =========================

@app.on_message(filters.command(["utag", "all", "mention"]) & filters.group & admin_filter)
@admin_check
async def tagall_menu(client, message: Message):

    chat_id = message.chat.id

    if ACTIVE_TAG.get(chat_id):
        return await message.reply_text("⚠️ TagAll masih berjalan!")

    await message.reply_text(
        "🚀 **TagAll Pro Mode**\n\nPilih durasi Auto Cancel:",
        reply_markup=duration_keyboard()
    )

# =========================
# CALLBACK HANDLER
# =========================

@app.on_callback_query(filters.regex("^tag_"))
async def tag_callback(client, query: CallbackQuery):

    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # Cancel
    if query.data == "tag_cancel":
        ACTIVE_TAG[chat_id] = False
        return await query.message.edit_text("⛔ TagAll dihentikan.")

    if ACTIVE_TAG.get(chat_id):
        return await query.answer("TagAll sudah berjalan!", show_alert=True)

    minutes = int(query.data.split("_")[1])
    duration = minutes * 60

    ACTIVE_TAG[chat_id] = True

    await query.message.edit_text(
        f"✅ TagAll dimulai\n⏳ Auto stop dalam {minutes} menit",
        reply_markup=running_keyboard()
    )

    end_time = datetime.now() + timedelta(seconds=duration)

    bot = await client.get_me()

    while ACTIVE_TAG.get(chat_id):

        if datetime.now() >= end_time:
            ACTIVE_TAG[chat_id] = False
            await client.send_message(chat_id, "⛔ TagAll otomatis dihentikan.")
            break

        members = []

        async for member in client.get_chat_members(chat_id):
            if not member.user.is_bot:
                mention = f"[{member.user.first_name}](tg://user?id={member.user.id})"
                members.append(mention)

        # Kirim per chunk
        for i in range(0, len(members), USERS_PER_MESSAGE):

            if not ACTIVE_TAG.get(chat_id):
                break

            chunk = members[i:i+USERS_PER_MESSAGE]

            text = await build_tag_message(
                "tes",
                chunk,
                bot.username
            )

            await client.send_message(
                chat_id,
                text,
                disable_web_page_preview=True
            )

            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)

        await asyncio.sleep(5)

    ACTIVE_TAG[chat_id] = False
