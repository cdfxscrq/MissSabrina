import os
import math
import urllib.request as urllib
from io import BytesIO
from typing import List
from PIL import Image

from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes, CommandHandler
from telegram.helpers import escape_markdown

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler


async def stickerid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        await msg.reply_text(f"Sticker ID:\n```{escape_markdown(msg.reply_to_message.sticker.file_id)}```",
                             parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.reply_text("Please reply to a sticker to get its ID.")


async def getsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        file_id = msg.reply_to_message.sticker.file_id
        sticker_file = await context.bot.get_file(file_id)
        await sticker_file.download_to_drive('sticker.png')
        with open('sticker.png', 'rb') as f:
            await context.bot.send_document(chat_id=chat_id, document=f)
        os.remove('sticker.png')
    else:
        await msg.reply_text("Please reply to a sticker for me to upload its PNG.")


async def kang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    bot = context.bot
    args = context.args
    user_id = user.id
    bot_username = (await bot.get_me()).username

    packnum = 0
    base_packname = f"a{user_id}_by_{bot_username}"
    packname = base_packname
    max_stickers = 120

    while True:
        try:
            stickerset = await bot.get_sticker_set(packname)
            if len(stickerset.stickers) >= max_stickers:
                packnum += 1
                packname = f"a{packnum}_{user_id}_by_{bot_username}"
            else:
                break
        except TelegramError:
            break

    kang_path = 'kangsticker.png'
    sticker_emoji = "🤔"

    file_id = None
    if msg.reply_to_message:
        if msg.reply_to_message.sticker:
            file_id = msg.reply_to_message.sticker.file_id
            sticker_emoji = msg.reply_to_message.sticker.emoji or sticker_emoji
        elif msg.reply_to_message.photo:
            file_id = msg.reply_to_message.photo[-1].file_id
        elif msg.reply_to_message.document:
            file_id = msg.reply_to_message.document.file_id
        else:
            return await msg.reply_text("I can't kang this type of content.")

        await (await bot.get_file(file_id)).download_to_drive(kang_path)

    elif args:
        try:
            png_url = args[0]
            if len(args) > 1:
                sticker_emoji = args[1]
            urllib.urlretrieve(png_url, kang_path)
        except Exception as e:
            return await msg.reply_text("Invalid image URL.")
    else:
        return await msg.reply_text("Reply to a sticker/image or provide a URL to kang it.")

    try:
        im = Image.open(kang_path)
        maxsize = (512, 512)
        im.thumbnail(maxsize)
        im.save(kang_path, format="PNG")
    except Exception:
        return await msg.reply_text("Only images are supported.")

    try:
        with open(kang_path, 'rb') as sticker_file:
            await bot.add_sticker_to_set(
                user_id=user_id,
                name=packname,
                png_sticker=sticker_file,
                emojis=sticker_emoji
            )
        await msg.reply_text(
            f"*Sticker added!*\n[Click here to view pack](https://t.me/addstickers/{packname})\nEmoji: {sticker_emoji}",
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError as e:
        if "Stickerset_invalid" in str(e):
            await makepack_internal(msg, user, kang_path, sticker_emoji, bot, packname, packnum)
        elif "Sticker_png_dimensions" in str(e):
            im.save(kang_path, format="PNG")
            with open(kang_path, 'rb') as sticker_file:
                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=packname,
                    png_sticker=sticker_file,
                    emojis=sticker_emoji
                )
            await msg.reply_text(
                f"Sticker added to [pack](https://t.me/addstickers/{packname})\nEmoji: {sticker_emoji}",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "Invalid sticker emojis" in str(e):
            await msg.reply_text("Invalid emoji provided.")
        elif "Stickers_too_much" in str(e):
            await msg.reply_text("Maximum number of stickers in the pack reached.")
        else:
            await msg.reply_text("Failed to add sticker. Error: " + str(e))
    finally:
        if os.path.exists(kang_path):
            os.remove(kang_path)


async def makepack_internal(msg, user, path, emoji, bot, packname, packnum):
    try:
        name = (user.first_name or "User")[:50]
        title = f"{name}'s Sticker Pack" + (f" {packnum}" if packnum > 0 else "")
        with open(path, 'rb') as sticker_file:
            await bot.create_new_sticker_set(
                user.id, packname, title, png_sticker=sticker_file, emojis=emoji
            )
        await msg.reply_text(
            f"Sticker pack created!\n[Click here to view pack](https://t.me/addstickers/{packname})",
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError as e:
        if "already occupied" in str(e):
            await msg.reply_text(f"Your pack is [here](https://t.me/addstickers/{packname})", parse_mode=ParseMode.MARKDOWN)
        elif "Peer_id_invalid" in str(e):
            await msg.reply_text(
                "Please contact me in PM first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Start", url=f"t.me/{(await bot.get_me()).username}")]
                ])
            )
        else:
            await msg.reply_text("Failed to create sticker pack: " + str(e))


__help__ = """
- /stickerid: Reply to a sticker to get its file ID.
- /getsticker: Reply to a sticker to get its PNG file.
- /kang: Reply to a sticker or image or send a PNG URL to add it to your sticker pack.
"""

__mod_name__ = "Stickers"

STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)
KANG_HANDLER = DisableAbleCommandHandler("kang", kang, pass_args=True, admin_ok=True)

dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
dispatcher.add_handler(KANG_HANDLER)
