#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import json
import logging
import os
import subprocess
import time
from configparser import ConfigParser
from subprocess import CalledProcessError

import pytz
from influxdb import InfluxDBClient
from telegram import ReplyKeyboardRemove
from telegram.error import NetworkError
from telegram.ext import run_async

from strings import Strings
from telegram_bot import TelegramBot

# python-telegram-bot transition guild to 12.0:
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Transition-guide-to-Version-12.0#commandhandler

strings = Strings()
client = InfluxDBClient('localhost', 8086)

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
MAX_RETRY = 3


def _valid_user(chat_id):
    return chat_id in ADMIN_CHAT_ID or chat_id in READ_ONLY_CHAT_ID


def _valid_admin(chat_id):
    return chat_id in ADMIN_CHAT_ID


def check_permission(update, context, callback):
    if not callback(update.message.chat_id):
        logging.getLogger(check_permission.__name__).warning(
            "Checking permission for [user={}, chat_id={}] failed".format(update.effective_user.username,
                                                                          update.message.chat_id))

        update.message.reply_text(strings.get("error", "permission_denied"))
        context.bot.send_sticker(chat_id=update.message.chat_id, sticker=strings.get("sticker", "permission_denied"))
        return 0
    return 1


@run_async
def handle_start(update, context):
    if not check_permission(update, context, _valid_user):
        return

    update.message.reply_text(strings.get("text", "greeting"), reply_markup=ReplyKeyboardRemove())


@run_async
def handle_default_message(update, context):
    if not check_permission(update, context, _valid_user):
        return

    if update.message.text[0] == "/":
        update.message.reply_text(strings.get("error", "not_found"))
        context.bot.send_sticker(chat_id=update.message.chat_id, sticker=strings.get("sticker", "not_found"))
    else:
        update.message.reply_text(strings.get("text", "default"))


@run_async
def handle_take_photo(update, context):
    if not check_permission(update, context, _valid_admin):
        return

    update.message.reply_text(strings.get("text", "take_photo"))

    logging.getLogger(handle_take_photo.__name__).debug("Taking photo")

    photo_path = os.path.join(OUTPUT_PATH, "jun-{}.png".format(time.strftime("%Y%m%d%H%M%S", time.localtime())))
    cmd = "raspistill -n -o {}".format(photo_path)

    error_message = None
    try:
        subprocess.call(cmd, shell=True)
    except CalledProcessError as e:
        logging.getLogger(handle_take_photo.__name__).error("Taking photo failed due to: {}".format(e))
        error_message = strings.get("error", "take_photo_failed")

    if not os.path.exists(photo_path):
        logging.getLogger(handle_take_photo.__name__).error("Saving photo failed")
        error_message = strings.get("error", "take_photo_failed")
    else:
        logging.getLogger(handle_take_photo.__name__).info("Sending photo stored at '{}'".format(photo_path))

        retry = 0
        while retry < MAX_RETRY:
            try:
                context.bot.send_photo(chat_id=update.message.chat_id, photo=open(photo_path, "rb"),
                                       timeout=SEND_TIMEOUT)
                break
            except NetworkError as e:
                logging.getLogger(handle_take_photo.__name__).warning(
                    "Sending photo '{}' timed out: {}. Retrying...".format(photo_path, e))
                retry += 1

        if retry >= MAX_RETRY:
            logging.getLogger(handle_take_photo.__name__).error(
                "Sending photo '{}' failed after {} retries.".format(photo_path, retry))
            error_message = strings.get("error", "send_photo_failed")

    if error_message is not None:
        update.message.reply_text("Something went wrong: {}\nPlease check logs for more info.".format(error_message))


@run_async
def handle_get_weight(update, context):
    if not check_permission(update, context, _valid_user):
        return

    client.switch_database('weight')

    record_num = 1
    if len(context.args) > 0:
        record_num = context.args[0]
    query_result = client.query("SELECT * FROM weight WHERE time > now() - {}d".format(record_num))

    logging.getLogger(handle_get_weight.__name__).info("Retrieved weight record(s) in the last {} day(s): {}".format(record_num, query_result))

    points = query_result.get_points(tags={'type': 'hamster'})
    records = ""
    for point in points:
        # convert rfc3339 timestamp string to localtime
        localtime = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(point['time'][:19], "%Y-%m-%dT%H:%M:%S"))).replace(tzinfo=pytz.utc).astimezone(
            pytz.timezone("Europe/Berlin")).strftime("%Y-%m-%d %H:%M")
        weight = float(point['value'])
        records += "\\[{}] *{:.1f}g*\n".format(localtime, weight)

    if records:
        update.message.reply_text(records, parse_mode='Markdown')
    else:
        update.message.reply_text("No weight recorded in the last day")


def handle_calc_age(update, context):
    if not check_permission(update, context, _valid_user):
        return

    num_days = (datetime.date.today() - datetime.date(2019, 12, 27)).days
    logging.getLogger(handle_calc_age.__name__).debug("Ages in days: {}".format(num_days))

    years = num_days // 365
    months = (num_days % 365) // 30
    days = (num_days % 365) % 30
    years_result = str(years) + "Y " if years != 0 else ""
    months_result = str(months) + "M " if months != 0 else ""
    days_result = str(days) + "D"

    update.message.reply_text("Your hamster is {} old.".format(years_result + months_result + days_result))


# handle unknown errors
def handle_error(update, context):
    error_message = strings.get("error", "general").format(context.error)

    if update:
        update.message.reply_text(error_message)

    logging.getLogger(handle_error.__name__).error(error_message)


@run_async
def handle_view_log(update, context):
    if not check_permission(update, context, _valid_admin):
        return

    # TODO only return logs on WARNING level
    result = ""
    result += subprocess.run(['tail', LOGFILE_PATH], stdout=subprocess.PIPE).stdout.decode('utf-8')

    update.message.reply_text(result)


def main():
    # command descriptions can be set with @BotFather
    TelegramBot.with_token(BOT_TOKEN) \
        .add_command_handler("start", handle_start) \
        .add_command_handler("photo", handle_take_photo) \
        .add_command_handler("weight", handle_get_weight, pass_args=True) \
        .add_command_handler("age", handle_calc_age) \
        .add_command_handler("viewlog", handle_view_log) \
        .add_default_message_handler(handle_default_message) \
        .add_error_handler(handle_error) \
        .start()


if __name__ == "__main__":
    main()
