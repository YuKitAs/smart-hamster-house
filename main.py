#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import subprocess
import time
from configparser import ConfigParser

from telegram import ReplyKeyboardRemove
from telegram.ext import run_async

from strings import Strings
from telegram_bot import TelegramBot

# python-telegram-bot transition guild to 12.0:
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Transition-guide-to-Version-12.0#commandhandler
strings = Strings()

# logging
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
LOGDIR_PATH = os.path.join(PROJECT_PATH, "logs")
LOGFILE_PATH = os.path.join(LOGDIR_PATH, "bot.log")

if not os.path.exists(LOGDIR_PATH):
    os.makedirs(LOGDIR_PATH)

logging.basicConfig(filename=LOGFILE_PATH, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

# config
config = ConfigParser()
config.read("configuration.ini")

OUTPUT_PATH = config["camera"]["PATH"]

if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

DEFAULT_VIDEO_LENGTH = int(config["camera"]["VIDEO_LENGTH"])

BOT_TOKEN = config["telegram.bot"]["TOKEN"]
ADMIN_CHAT_ID = json.loads(config.get("telegram.bot", "ADMIN_CHAT_ID"))
READ_ONLY_CHAT_ID = json.loads(config.get("telegram.bot", "READ_ONLY_CHAT_ID"))
SEND_TIMEOUT = int(config["telegram.bot"]["SEND_TIMEOUT"])


def _valid_user(chat_id):
    return chat_id in ADMIN_CHAT_ID or chat_id in READ_ONLY_CHAT_ID


def _valid_admin(chat_id):
    return chat_id in ADMIN_CHAT_ID


def check_permission(update, chat_id, callback):
    if not callback(chat_id):
        logging.getLogger(check_permission.__name__).warning("Checking permission for {} failed".format(chat_id))

        update.message.reply_text(strings.get("error", "permission_denied"))
        return


@run_async
def handle_start(update, _context):
    check_permission(update, update.message.chat_id, _valid_user)

    update.message.reply_text(strings.get("text", "greeting"), reply_markup=ReplyKeyboardRemove())


@run_async
def handle_default_message(update, context):
    check_permission(update, update.message.chat_id, _valid_user)

    if update.message.text[0] == "/":
        update.message.reply_text(strings.get("error", "not_found"))
        context.bot.send_sticker(chat_id=update.message.chat_id, sticker=strings.get("sticker", "not_found"))
    else:
        update.message.reply_text(strings.get("text", "default"))


@run_async
def handle_take_photo(update, context):
    check_permission(update, update.message.chat_id, _valid_admin)

    update.message.reply_text(strings.get("text", "take_photo"))

    logging.getLogger(handle_take_photo.__name__).info("Taking photo")

    photo_path = os.path.join(OUTPUT_PATH, "jun-{}.png".format(time.strftime("%Y%m%d%H%M%S", time.localtime())))
    cmd = "raspistill -vf -n -o {}".format(photo_path)
    subprocess.call(cmd, shell=True)

    # TODO send error message when failed

    logging.getLogger(handle_take_photo.__name__).info("Sending photo stored at '{}'".format(photo_path))

    context.bot.send_photo(chat_id=update.message.chat_id, photo=open(photo_path, "rb"), timeout=SEND_TIMEOUT)


# handle unknown errors
def handle_error(update, context):
    error_message = strings.get("error", "general").format(context.error)

    if update:
        update.message.reply_text(error_message)

    logging.getLogger(handle_error.__name__).error(error_message)


@run_async
def handle_view_log(update, _context):
    check_permission(update, update.message.chat_id, _valid_admin)

    # TODO only return logs on WARNING level
    result = ""
    result += subprocess.run(['tail', LOGFILE_PATH], stdout=subprocess.PIPE).stdout.decode('utf-8')

    update.message.reply_text(result)


def main():
    # command descriptions can be set with @BotFather
    TelegramBot.with_token(BOT_TOKEN) \
        .add_command_handler("start", handle_start) \
        .add_command_handler("photo", handle_take_photo) \
        .add_command_handler("viewlog", handle_view_log) \
        .add_default_message_handler(handle_default_message) \
        .add_error_handler(handle_error) \
        .start()


if __name__ == "__main__":
    main()
