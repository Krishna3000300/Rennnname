from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from pyrogram.emoji import *
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, convert, humanbytes
from helper.database import db
from asyncio import sleep
from PIL import Image
import os, time, asyncio
import shutil
import json
import shlex
from plugins.utils import get_media_file_name, get_file_attr
from config import Config
from typing import Tuple

LOG_CHANNEL = Config.LOG_CHANNEL

@Client.on_message(filters.text & filters.private & ~filters.command(['start','help','about','showthumbnail','deletethumbnail','set_caption','get_caption','del_caption','change_mode','get_mode','stats','restart','broadcast',]))
def send_text(client, message):
    user = message.text
    first_60_letters = user[:60]
    client.send_message(message.chat.id, f"`{first_60_letters}.mkv`")
    
@Client.on_message(filters.command("change_mode") & filters.private & filters.incoming)
async def set_mode(client, message):
    upload_mode = await db.get_upload_mode(message.from_user.id)
    if upload_mode:
        await db.set_upload_mode(message.from_user.id, False)
        text = f"**From Now all Files will be Uploaded as Files {FILE_FOLDER}**"
    else:
        await db.set_upload_mode(message.from_user.id, True)
        text = f"**From Now all Files will be Uploaded as Video 🎥**"
    await message.reply_text(text, quote=True)

@Client.on_message(filters.command("get_mode") & filters.private & filters.incoming)
async def get_mode(client, message):
    user_id = message.from_user.id
    upload_mode = await db.get_upload_mode(user_id)

    if upload_mode:
        text = "**Your current Upload mode :- Video Mode 🎥**"
    else:
        text = "**Your Current Upload mode :- File Mode 📂**"

    await message.reply_text(text, quote=True)

@Client.on_message(filters.private & (filters.document | filters.audio | filters.video))
async def rename_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name
    mention = message.from_user.mention
    if file.file_size > 2000 * 1024 * 1024:
        await message.reply_text(f"**Sorry {mention} This Bot Doesn't Support Uploading Files Bigger Than 2GB. You Can Use [4GB Rename Star Bots](https://t.me/Rename_4GB_Star_Bot)**")
        return

    try:
        await message.reply_text(
            text=f"**Please Enter New File Name...\n\nOld File Name :-** `{filename}`",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(True)
        )
        await sleep(30)
    except FloodWait as e:
        await sleep(e.value)
        await message.reply_text(
            text=f"**Please Enter New File Name...\n\nOld File Name :-** `{filename}`",
            reply_to_message_id=message.id,
            reply_markup=ForceReply(True)
        )
    except:
        pass

@Client.on_message(filters.private & filters.reply)
async def refunc(client, message):
    user_id = message.from_user.id
    if not os.path.isdir("Metadata"):
        os.mkdir("Metadata")
    reply_message = message.reply_to_message
    if (reply_message.reply_markup) and isinstance(reply_message.reply_markup, ForceReply):
        new_filename = message.text[:60]
        file_caption = message.text
        await message.delete()
        msg = await client.get_messages(message.chat.id, reply_message.id)
        file = msg.reply_to_message
        media = getattr(file, file.media.value)
        if not ".m" in new_filename:
            extn = media.file_name.rsplit('.', 1)[-1] if "." in media.file_name else "mkv"
            new_filename = f"{new_filename}.{extn}"
        if not any(ext in file_caption for ext in [".mp4", ".mkv"]):
            extn = media.file_name.rsplit('.', 1)[-1] if "." in media.file_name else "mkv"
            file_caption = f"{file_caption}.{extn}"
        await reply_message.delete()
        file_path = f"downloads/{new_filename}"
        upload_mode = await db.get_upload_mode(message.from_user.id)
        ms = await message.reply_text(f"**Trying to 📥 Downloading...**")
        try:
            path = await client.download_media(
                message=file, file_name=f"downloads/{new_filename}",
                progress=progress_for_pyrogram, progress_args=("<b>📥 Downloading...</b>", ms, time.time())
            )
        except Exception as e:
            await ms.edit(str(e))
            return

    _bool_metadata = await db.get_metadata_mode(user_id)
    if (_bool_metadata):
        metadata_path = f"Metadata/{new_filename}"
        metadata = await db.get_metadata_code(user_id)
        if metadata:
            await ms.edit("I Fᴏᴜɴᴅ Yᴏᴜʀ Mᴇᴛᴀᴅᴀᴛᴀ\n\n__**Pʟᴇᴀsᴇ Wᴀɪᴛ...**__\n**Aᴅᴅɪɴɢ Mᴇᴛᴀᴅᴀᴛᴀ Tᴏ Fɪʟᴇ....**")
            cmd = f"""ffmpeg -i {path} {metadata} {metadata_path}"""
            process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            er = stderr.decode()
            try:
                if er:
                    return await ms.edit(str(er) + "\n\n**Error**")
            except BaseException:
                pass
        await ms.edit("**Metadata added to the file successfully ✅**\n\n**Trying to 📤 Uploading...**")
    else:
        await ms.edit("**Trying to 📤 Uploading...**")
        
        duration = 0
        try:
            metadata = extractMetadata(createParser(file_path))
            if metadata.has("duration"):
               duration = metadata.get('duration').seconds
        except:
            pass

        # Set Caption and Thumbnail
        ph_path = None
        user_id = int(message.chat.id)
        c_caption = await db.get_caption(message.chat.id)
        c_thumb = await db.get_thumbnail(message.chat.id)

        if c_caption:
            try:
                caption = c_caption.format(
                    filename=file_caption, filesize=humanbytes(media.file_size), duration=convert(duration)
                )
            except Exception as e:
                return await ms.edit(text=f"**Your Caption Error Except Keyword Argument ({e})**")
        else:
            caption = f"**{file_caption}**"

        if media.thumbs or c_thumb:
            if c_thumb:
                ph_path = await client.download_media(c_thumb)
            else:
                ph_path = await client.download_media(media.thumbs[0].file_id)
                Image.open(ph_path).convert("RGB").save(ph_path)
                img = Image.open(ph_path)
                img.resize((320, 320))
                img.save(ph_path, "JPEG")

        await ms.edit("**Trying to 📤 Uploading...**")

        try:
            if upload_mode:
                await client.send_video(
                    chat_id=message.chat.id, video=metadata_path if _bool_metadata else file_path, caption=caption, thumb=ph_path,
                    duration=duration, progress=progress_for_pyrogram,
                    progress_args=("<b>📤 Uploading...</b>", ms, time.time())
                )
                # Additional handling for LOG_CHANNEL, modify as needed
                await client.send_video(
                    chat_id=LOG_CHANNEL, video=metadata_path if _bool_metadata else file_path, caption=caption,
                    thumb=ph_path, duration=duration
                )
            else:
                await client.send_document(
                    chat_id=message.chat.id, document=metadata_path if _bool_metadata else file_path, thumb=ph_path,
                    caption=caption, progress=progress_for_pyrogram,
                    progress_args=("<b>📤 Uploading...</b>", ms, time.time())
                )
                # Additional handling for LOG_CHANNEL, modify as needed
                await client.send_document(
                    chat_id=LOG_CHANNEL, document=metadata_path if _bool_metadata else file_path, thumb=ph_path, caption=caption
                )

        except Exception as e:
            # Clean up and handle the error
            os.remove(path)
            await ms.edit(f"**Error: {e}**")
            return

        await ms.delete()
        os.remove(path)
