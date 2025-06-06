import os
import re
import requests
import urllib
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup

from typing import List, Optional
from telegram import Update, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

from tg_bot import application  # Assume PTB v20+ using Application

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/75.0.3770.38 Safari/537.36"
)

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', USER_AGENT)]


def parse_sauce(googleurl: str) -> dict:
    """Parse/Scrape the HTML code for the info we want."""
    source = opener.open(googleurl).read()
    soup = BeautifulSoup(source, 'html.parser')

    results = {
        'similar_images': '',
        'override': '',
        'best_guess': ''
    }

    try:
        for bess in soup.findAll('a', {'class': 'PBorbe'}):
            url = 'https://www.google.com' + bess.get('href')
            results['override'] = url
    except Exception:
        pass

    for similar_image in soup.findAll('input', {'class': 'gLFyf'}):
        url = 'https://www.google.com/search?tbm=isch&q=' + urllib.parse.quote_plus(similar_image.get('value'))
        results['similar_images'] = url

    for best_guess in soup.findAll('div', attrs={'class': 'r5a77d'}):
        results['best_guess'] = best_guess.get_text()

    return results


def scam(imgspage: str, lim: int) -> List[str]:
    """Parse/Scrape Google similar images page for image links."""
    single = opener.open(imgspage).read()
    decoded = single.decode('utf-8')
    lim = min(int(lim), 10)

    imglinks = []
    pattern = r'\["(https?://[^"]+\.(?:png|jpg|jpeg))",\d+,\d+\]'
    oboi = re.findall(pattern, decoded, re.I)

    for idx, imglink in enumerate(oboi):
        imglinks.append(imglink)
        if idx + 1 >= lim:
            break

    return imglinks


async def reverse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    imagename = "okgoogle.png"
    msg = update.effective_message
    chat_id = update.effective_chat.id

    # Clean up any old image file
    if os.path.isfile(imagename):
        os.remove(imagename)

    reply = msg.reply_to_message
    lim = 2
    img_link: Optional[str] = None

    if reply:
        file_id = None
        if reply.sticker:
            file_id = reply.sticker.file_id
        elif reply.photo:
            file_id = reply.photo[-1].file_id
        elif reply.document and reply.document.mime_type.startswith("image/"):
            file_id = reply.document.file_id
        else:
            await msg.reply_text("Reply to an image or sticker to lookup.")
            return

        image_file = await context.bot.get_file(file_id)
        await image_file.download_to_drive(imagename)
        try:
            if context.args:
                lim = int(context.args[0])
        except Exception:
            lim = 2

    elif context.args and not reply:
        if len(context.args) >= 1:
            img_link = context.args[0]
            if len(context.args) > 1:
                try:
                    lim = int(context.args[1])
                except Exception:
                    lim = 2
        else:
            await msg.reply_text("/reverse <link> <amount of images to return.>")
            return
        try:
            urllib.request.urlretrieve(img_link, imagename)
        except HTTPError as HE:
            if HE.reason == 'Not Found':
                await msg.reply_text("Image not found.")
            elif HE.reason == 'Forbidden':
                await msg.reply_text(
                    "Couldn't access the provided link. The website might have blocked access, or the website doesn't exist."
                )
            else:
                await msg.reply_text(f"HTTP Error: {HE}")
            return
        except URLError as UE:
            await msg.reply_text(f"URL Error: {UE.reason}")
            return
        except ValueError as VE:
            await msg.reply_text(f"{VE}\nPlease try again using http or https protocol.")
            return
    else:
        await msg.reply_markdown(
            "Please reply to a sticker or an image to search it!\n"
            "You can also search with a link: `/reverse [picturelink] <amount>`."
        )
        return

    try:
        searchUrl = 'https://www.google.com/searchbyimage/upload'
        with open(imagename, 'rb') as image_file:
            multipart = {'encoded_image': (imagename, image_file), 'image_content': ''}
            response = requests.post(searchUrl, files=multipart, allow_redirects=False)
        fetchUrl = response.headers.get('Location')

        if response.status_code != 400 and fetchUrl:
            xx = await context.bot.send_message(
                chat_id, "Image was successfully uploaded to Google.\nParsing source now. Maybe.",
                reply_to_message_id=msg.message_id
            )
        else:
            await context.bot.send_message(chat_id, "Google told me to go away.", reply_to_message_id=msg.message_id)
            if os.path.isfile(imagename):
                os.remove(imagename)
            return

        if os.path.isfile(imagename):
            os.remove(imagename)

        match = parse_sauce(fetchUrl + "&hl=en")
        guess = match['best_guess']
        imgspage = match['override'] or match['similar_images']

        if guess and imgspage:
            await xx.edit_text(f"[{guess}]({fetchUrl})\nLooking for images...",
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            await xx.edit_text("Couldn't find anything.")
            return

        images = scam(imgspage, lim)
        if not images:
            await xx.edit_text(
                f"[{guess}]({fetchUrl})\n[Visually similar images]({imgspage})"
                "\nCouldn't fetch any images.",
                parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
            )
            return

        imglinks = [InputMediaPhoto(media=link) for link in images]
        await context.bot.send_media_group(
            chat_id=chat_id, media=imglinks, reply_to_message_id=msg.message_id
        )
        await xx.edit_text(
            f"[{guess}]({fetchUrl})\n[Visually similar images]({imgspage})",
            parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

    except Exception as e:
        await msg.reply_text(f"An error occurred: {e}")
        print(e)
    finally:
        if os.path.isfile(imagename):
            os.remove(imagename)


__help__ = """
- /reverse: Does a reverse image search of the media it is replied to, or of a given image URL.
"""

__mod_name__ = "Image Lookup"

# For PTB v20+
REVERSE_HANDLER = CommandHandler("reverse", reverse)

application.add_handler(REVERSE_HANDLER)
