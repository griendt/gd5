from __future__ import annotations

import logging
from typing import Callable, TypeVar

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from functools import wraps

from secrets import bot_token
from telegram_bot import Bot

T = TypeVar('T')
U = TypeVar('U')

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

updater = Updater(token=bot_token)
dispatcher = updater.dispatcher
bot = Bot()
bot_commands: list[Callable[[], None]] = []


def add_context(func: Callable[[], None]) -> Callable[[Update, CallbackContext], None]:
    """Decorator to automatically use the bot in the appropriate update and context in command callbacks, without
    having to worry about specifying them each time as arguments."""

    @wraps(func)
    def decorator(update: Update, context: CallbackContext):
        bot.init(update, context)
        return func()

    return decorator


def bot_command(func: Callable[[], None]) -> Callable[[Update, CallbackContext], None]:
    """Automatically initializes the bot with the current message and registers a command handler."""

    @wraps(func)
    @add_context
    def new_func(*args, **kwargs):
        return func(*args, **kwargs)

    bot_commands.append(new_func)
    return new_func


def bot_answer(func: Callable[[T], U]) -> Callable[[T], U]:
    """Decorator that makes the bot automatically answer (i.e. resolve) callback queries."""

    @add_context
    def func_with_context(*args, **kwargs):
        return func(*args, **kwargs)

    @wraps(func_with_context)
    def decorator(*args, **kwargs):
        ret_value = func_with_context(*args, **kwargs)
        bot.update.callback_query.answer()
        return ret_value

    return decorator


@bot_command
def start():
    bot.reply("You have started the bot.")


@bot_command
def button():
    bot.add_button("foo", "x")
    bot.add_button("bar", "y")
    bot.reply("Select an option")


@bot_answer
def parse_button():
    # Corresponding values can be "x" and "y", see button() above
    bot.reply(f"Corresponding value was: {bot.update.callback_query.data}")


dispatcher.add_handler(CallbackQueryHandler(parse_button))
for command in bot_commands:
    dispatcher.add_handler(CommandHandler(command.__name__, command))


if __name__ == "__main__":
    updater.start_polling()
