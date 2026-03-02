# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

from pathlib import Path
from pyrogram import filters, types

from anony import anon, app, config, db, lang, queue, tg, yt
from anony.helpers import buttons, utils
from anony.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text


@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & (filters.group | filters.channel)
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:

    # ================= CHAT DETECTION =================

    chat_id = m.chat.id

    # Jika dari channel dan punya linked group → pakai group untuk VC
    if m.chat.type == "channel" and m.chat.linked_chat:
        chat_id = m.chat.linked_chat.id

    # ================= USER / CHANNEL MENTION =================

    if m.from_user:
        mention = m.from_user.mention
    elif m.sender_chat:
        mention = m.sender_chat.title
    else:
        mention = "Channel"

    # ================= START =================

    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    # ================= MEDIA REPLY =================

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    # ================= M3U8 =================

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    # ================= URL =================

    elif url:
        if "playlist" in url:
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    # ================= QUERY TEXT =================

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    # ================= DURATION LIMIT =================

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    # ================= LOGGER =================

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    file.user = mention

    # ================= QUEUE SYSTEM =================

    if force:
        queue.force_add(chat_id, file)
    else:
        position = queue.add(chat_id, file)

        if position != 0 or await db.get_call(chat_id):
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    mention,
                ),
                reply_markup=buttons.play_queued(
                    chat_id, file.id, m.lang["play_now"]
                ),
            )

            if tracks:
                added = playlist_to_queue(chat_id, tracks)
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + added,
                )
            return

    # ================= DOWNLOAD =================

    if not file.file_path:
        fname = f"downloads/{file.id}.{'mp4' if video else 'webm'}"

        if Path(fname).exists():
            file.file_path = fname
        else:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.download(file.id, video=video)

    # ================= PLAY =================

    await anon.play_media(chat_id=chat_id, message=sent, media=file)

    if tracks:
        added = playlist_to_queue(chat_id, tracks)
        await app.send_message(
            chat_id=m.chat.id,
            text=m.lang["playlist_queued"].format(len(tracks)) + added,
    )
