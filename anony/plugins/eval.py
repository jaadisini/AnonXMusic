# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import io
import os
import re
import sys
import uuid
import asyncio
import traceback
from html import escape
from typing import Any, Optional, Tuple

from pyrogram import filters, types

from anony import anon, app, config, db, lang, userbot
from anony.helpers import format_exception, meval


# ===================================================
# EVAL / EXEC
# ===================================================

@app.on_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@app.on_edited_message(filters.command(["eval", "exec"]) & filters.user(app.owner))
@lang.language()
async def eval_handler(_, message: types.Message):
    if len(message.command) < 2:
        return await message.reply_text(message.lang["eval_inp"])

    code = message.text.split(None, 1)[1]
    out_buf = io.StringIO()

    async def _eval_code() -> Tuple[str, Optional[str]]:
        async def send(*args: Any, **kwargs: Any) -> types.Message:
            return await message.reply_text(*args, **kwargs)

        def _print(*args: Any, **kwargs: Any) -> None:
            kwargs.setdefault("file", out_buf)
            print(*args, **kwargs)

        eval_vars = {
            "m": message,
            "r": message.reply_to_message,
            "chat": message.chat,
            "user": message.from_user,
            "app": app,
            "anon": anon,
            "db": db,
            "client": app,
            "ub": userbot,
            "ikb": types.InlineKeyboardButton,
            "ikm": types.InlineKeyboardMarkup,
            "send": send,
            "config": config,
            "print": _print,
            "os": os,
            "re": re,
            "sys": sys,
            "tb": traceback,
        }

        try:
            result = await meval(code, globals(), **eval_vars)
            return "", result
        except Exception as e:
            tb_data = traceback.extract_tb(e.__traceback__)
            snippet_tb = next(
                (i for i, f in enumerate(tb_data) if f.filename == "<string>"), -1
            )
            formatted_tb = format_exception(
                e, tb_data[snippet_tb:] if snippet_tb != -1 else tb_data
            )
            return message.lang["eval_error"], formatted_tb

    _, result = await _eval_code()

    if result is not None or not out_buf.getvalue():
        print(result, file=out_buf)

    output = out_buf.getvalue().strip()
    response = message.lang["eval_out"].format(escape(output))

    if len(response) > 4096:
        with io.BytesIO(output.encode()) as out_file:
            out_file.name = f"{uuid.uuid4().hex[:8].lower()}.txt"
            return await message.reply_document(
                document=out_file,
                disable_notification=True
            )

    await message.reply_text(response)


# ===================================================
# UPDATE SYSTEM
# ===================================================

@app.on_message(filters.command("update") & filters.user(app.owner))
@app.on_edited_message(filters.command("update") & filters.user(app.owner))
@lang.language()
async def update_handler(_, message: types.Message):
    msg = await message.reply_text("🔄 Checking for updates...")

    try:
        # Get current commit
        commit_process = await asyncio.create_subprocess_shell(
            "git log -1 --pretty=format:'%h - %s (%cr)'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        commit_stdout, _ = await commit_process.communicate()
        old_commit = commit_stdout.decode().strip()

        # Git pull
        pull_process = await asyncio.create_subprocess_shell(
            "git pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await pull_process.communicate()
        output = (stdout or stderr).decode().strip()

        if "Already up to date." in output:
            return await msg.edit_text(
                "✅ Bot sudah versi terbaru.\n\n"
                f"<b>Current Commit:</b>\n<code>{escape(old_commit)}</code>"
            )

        # Install requirements silently
        await asyncio.create_subprocess_shell(
            "pip install -r requirements.txt",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Get new commit
        new_commit_process = await asyncio.create_subprocess_shell(
            "git log -1 --pretty=format:'%h - %s (%cr)'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        new_commit_stdout, _ = await new_commit_process.communicate()
        new_commit = new_commit_stdout.decode().strip()

        await msg.edit_text(
            "✅ <b>Update Berhasil!</b>\n\n"
            f"<b>Old:</b>\n<code>{escape(old_commit)}</code>\n\n"
            f"<b>New:</b>\n<code>{escape(new_commit)}</code>\n\n"
            "♻️ Restarting bot..."
        )

        # Restart process (VPS / Railway / Docker safe)
        os.execl(sys.executable, sys.executable, *sys.argv)

    except Exception:
        error = traceback.format_exc()
        await msg.edit_text(
            "❌ <b>Update Gagal!</b>\n\n"
            f"<code>{escape(error)}</code>"
        )
