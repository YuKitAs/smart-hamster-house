#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time

import serial
from influxdb import InfluxDBClient

from log import logging
from water_alarm import WaterAlarm
from weighing_scale import WeighingScale

log = logging.getLogger('main')

ser = serial.Serial('/dev/ttyACM0', 9600)

# InfluxDB
client = InfluxDBClient('localhost', 8086)

waterAlarm = WaterAlarm(client)
weighingScale = WeighingScale(client)

while True:
    try:
        raw_value = ser.readline().strip().decode('ascii')
        log.debug("Serial: {}".format(raw_value))  # e.g. {"liquid_alarm":false,"weight":0.005319}

        json_value = json.loads(raw_value)

        waterAlarm.process_water_alarm(json_value['liquid_alarm'])
        weighingScale.process_weight(json_value['weight'], time.time())
    except Exception as ex:
        log.error(ex)
