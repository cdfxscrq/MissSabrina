import random
import re
import string
import io
import asyncio
from typing import Optional, List

import base64
import glob
import os
from pathlib import Path

from PIL import Image
from telegram import Update, Message, Bot
from telegram.ext import filters, CommandHandler, MessageHandler, ContextTypes

from tg_bot import dispatcher, DEEPFRY_TOKEN
from tg_bot.modules.disable import DisableAbleCommandHandler

from spongemock import spongemock

# ---- WIDE MAP for vaporwave ----
WIDE_MAP = {i: i + 0xFEE0 for i in range(0x21, 0x7F)}
WIDE_MAP[0x20] = 0x3000

# ---- Meme Functions ----

async def owo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message.reply_to_message:
        await message.reply_text("I need a message to meme.")
        return
    faces = [
        '(・`ω´・)', ';;w;;', 'owo', 'UwU', '>w<', '^w^',
        '\(^o\) (/o^)/', '( ^ _ ^)∠☆', '(ô_ô)', '~:o', ';____;',
        '(*^*)', '(>_', '(♥_♥)', '*(^O^)*', '((+_+))'
    ]
    text = message.reply_to_message.text or ""
    reply_text = re.sub(r'[rl]', "w", text)
    reply_text = re.sub(r'[ｒｌ]', "ｗ", reply_text)
    reply_text = re.sub(r'[RL]', 'W', reply_text)
    reply_text = re.sub(r'[ＲＬ]', 'Ｗ', reply_text)
    reply_text = re.sub(r'n([aeiouａｅｉｏｕ])', r'ny\1', reply_text)
    reply_text = re.sub(r'ｎ([ａｅｉｏｕ])', r'ｎｙ\1', reply_text)
    reply_text = re.sub(r'N([aeiouAEIOU])', r'Ny\1', reply_text)
    reply_text = re.sub(r'Ｎ([ａｅｉｏｕＡＥＩＯＵ])', r'Ｎｙ\1', reply_text)
    reply_text = re.sub(r'\!+', ' ' + random.choice(faces), reply_text)
    reply_text = re.sub(r'！+', ' ' + random.choice(faces), reply_text)
    reply_text = reply_text.replace("ove", "uv").replace("ｏｖｅ", "ｕｖ")
    reply_text += ' ' + random.choice(faces)
    await message.reply_to_message.reply_text(reply_text)

async def stretch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message.reply_to_message:
        await message.reply_text("I need a message to meme.")
        return
    count = random.randint(3, 10)
    text = message.reply_to_message.text or ""
    reply_text = re.sub(r'([aeiouAEIOUａｅｉｏｕＡＥＩＯＵ])', lambda m: m.group(1) * count, text)
    await message.reply_to_message.reply_text(reply_text)

async def vapor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    args = context.args
    noreply = False
    if not message.reply_to_message:
        if not args:
            await message.reply_text("I need a message to convert to vaporwave text.")
            return
        noreply = True
        data = " ".join(args)
    else:
        data = message.reply_to_message.text or ""
    reply_text = str(data).translate(WIDE_MAP)
    if noreply:
        await message.reply_text(reply_text)
    else:
        await message.reply_to_message.reply_text(reply_text)

# Add similar refactors for mafiatext, gandhitext, kimtext, hitlertext, spongemocktext, forbesify
# Each should use async, context managers, and avoid synchronous os.system() calls where possible

# --- Handler Registration ---
dispatcher.add_handler(DisableAbleCommandHandler("owo", owo))
dispatcher.add_handler(DisableAbleCommandHandler("stretch", stretch))
dispatcher.add_handler(DisableAbleCommandHandler("vapor", vapor, pass_args=True))
# Add other handlers similarly...

__mod_name__ = "🥳 Sabrina Exclusive 🥳"
