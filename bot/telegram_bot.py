from __future__ import annotations

from typing import Callable

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update


class Bot(object):
    update: Update = None
    context: CallbackContext = None
    reply_markup: list[InlineKeyboardButton] = None

    def init(self, update: Update, context: CallbackContext):
        self.reply_markup = []
        self.update = update
        self.context = context

    def reply(self, text: str) -> None:
        reply_markup = InlineKeyboardMarkup([self.reply_markup]) if self.reply_markup else None
        self.update.effective_message.reply_text(text=text, reply_markup=reply_markup)

    def add_button(self, text: str, callback: str) -> None:
        self.reply_markup.append(InlineKeyboardButton(text=text, callback_data=callback))
