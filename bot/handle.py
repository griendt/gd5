from __future__ import annotations

from typing import Callable

from telegram.ext import Updater, CommandHandler
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from telegram_bot import Bot
from secrets import bot_token

updater = Updater(token=bot_token)
bot = Bot()


def add_context(func: Callable[[], None]) -> Callable[[Update, CallbackContext], None]:
    """Decorator to automatically use the bot in the appropriate update and context in command callbacks, without
    having to worry about specifying them each time as arguments."""

    def decorator(update: Update, context: CallbackContext):
        bot.init(update, context)
        return func()

    return decorator


@add_context
def start():
    bot.reply("Argh!")


start_handler = CommandHandler('start', start)
dispatcher = updater.dispatcher
dispatcher.add_handler(start_handler)

if __name__ == "__main__":
    updater.start_polling()
