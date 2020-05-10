import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


class TelegramBot:
    def __init__(self, token):
        # python-telegram-bot 13 will have `use_context=True` set as default
        # (https://github.com/python-telegram-bot/python-telegram-bot/wiki/Transition-guide-to-Version-12.0)
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher

    def start(self):
        logging.getLogger("TelegramBot").info("Starting telegram bot")
        self.updater.start_polling()
        self.updater.idle()

    def add_command_handler(self, command, callback):
        self.dispatcher.add_handler(CommandHandler(command, callback))
        return self

    def add_error_handler(self, callback):
        self.dispatcher.add_error_handler(callback)
        return self

    def add_default_message_handler(self, callback):
        self.dispatcher.add_handler(MessageHandler(Filters.text, callback))
        return self

    @staticmethod
    def with_token(token):
        return TelegramBot(token)
