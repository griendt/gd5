from __future__ import annotations

from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update


class Bot(object):
    update: Update = None
    context: CallbackContext = None

    def init(self, update: Update, context: CallbackContext):
        self.update = update
        self.context = context

    def reply(self, text: str) -> None:
        self.context.bot.send_message(chat_id=self.update.effective_chat.id, text=text)
