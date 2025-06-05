import pyowm
from pyowm.commons.exceptions import NotFoundError
from telegram import Update, ParseMode
from telegram.ext import CommandHandler, CallbackContext
from tg_bot import dispatcher, API_WEATHER, BAN_STICKER
from tg_bot.modules.disable import DisableAbleCommandHandler

def weather(update: Update, context: CallbackContext):
    if not context.args:
        update.effective_message.reply_text("Write a location to check the weather.")
        return

    location = " ".join(context.args)
    bot = context.bot

    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("I will keep an eye on both happy and sad times!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    try:
        owm = pyowm.OWM(API_WEATHER)
        mgr = owm.weather_manager()
        observation = mgr.weather_at_place(location)
        weather = observation.weather
        location_name = observation.location.name or "Unknown"
        temperature = weather.temperature("celsius").get("temp", "Unknown")

        code = weather.weather_code
        # Map weather codes to emojis
        if code < 232:
            emoji = "⛈️"
        elif code < 321:
            emoji = "🌧️"
        elif code < 504:
            emoji = "🌦️"
        elif code < 531:
            emoji = "⛈️"
        elif code < 622:
            emoji = "🌨️"
        elif code < 781:
            emoji = "🌪️"
        elif code == 800:
            emoji = "🌤️"
        elif code == 801:
            emoji = "⛅️"
        elif code <= 804:
            emoji = "☁️"
        else:
            emoji = ""

        status = f"{emoji} {weather.detailed_status.capitalize()}"

        reply = f"Today in {location_name} is {status}, around {temperature}°C."
        update.message.reply_text(reply)

    except NotFoundError:
        update.effective_message.reply_text("Sorry, location not found.")
    except Exception as e:
        update.effective_message.reply_text(f"An error occurred: {e}")

__help__ = """
 - /weather <city>: Get weather info for a particular place.
"""

__mod_name__ = "Weather"

WEATHER_HANDLER = DisableAbleCommandHandler("weather", weather)
dispatcher.add_handler(WEATHER_HANDLER)
