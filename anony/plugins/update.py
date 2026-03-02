# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.

import os
import sys
import subprocess
from datetime import datetime

from pyrogram import filters
from anony import app, logger


def run_cmd(cmd: list):
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()


@app.on_message(filters.command("update") & filters.user(lambda _, __, u: u.id in app.sudoers))
async def update_handler(_, message):
    msg = await message.reply_text("🔍 Checking for updates...")

    try:
        # Ensure git exists
        try:
            run_cmd(["git", "--version"])
        except Exception:
            return await msg.edit("❌ Git is not installed on this server.")

        # Fetch latest changes
        run_cmd(["git", "fetch", "origin"])

        local = run_cmd(["git", "rev-parse", "HEAD"])
        remote = run_cmd(["git", "rev-parse", "@{u}"])

        if local == remote:
            return await msg.edit("✅ Bot is already up to date.")

        await msg.edit("⬇️ Update found.\n\nPulling latest changes...")

        pull_log = run_cmd(["git", "pull"])

        await msg.edit("📦 Installing new requirements (if any)...")

        subprocess.call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )

        await msg.edit("♻️ Restarting bot...")

        logger.info("Bot updated successfully at %s", datetime.now())

        os.execv(sys.executable, [sys.executable] + sys.argv)

    except subprocess.CalledProcessError as e:
        logger.error(e.output.decode())
        await msg.edit(f"❌ Update failed:\n\n<code>{e.output.decode()}</code>")

    except Exception as e:
        logger.error(str(e))
        await msg.edit(f"❌ Unexpected error:\n\n<code>{e}</code>")
