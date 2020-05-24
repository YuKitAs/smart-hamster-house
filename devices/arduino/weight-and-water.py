import json
import logging
import statistics
import time

import serial
from influxdb import InfluxDBClient

logging.basicConfig(filename='weight-and-water.log', format='%(asctime)s - %(levelname)s - %(message)s', level='DEBUG')

ser = serial.Serial('/dev/ttyACM0', 9600)
client = InfluxDBClient('localhost', 8086)

num_read_weights = 5
tare_weight = 180  # a rough value as threshold
interval = 86400


def write_water_alarm():
    client.switch_database('water')

    json_body = [{
        "measurement": "level",
        "tags": {
            "location": "home"
        },
        "fields": {
            "value": 0
        }
    }]

    client.write_points(json_body)


def valid_weights(values):
    return statistics.stdev(values) < 1


def write_weight(value):
    if value:
        client.switch_database('weight')

        json_body = [{
            "measurement": "weight",
            "tags": {
                "location": "home"
            },
            "fields": {
                "value": value
            }
        }]

        client.write_points(json_body)


read_weights = []
weight_update_time = 0

while True:
    try:
        raw_value = ser.readline().strip().decode('ascii')
        logging.debug("Serial: {}".format(raw_value))  # e.g. {"liquid_alarm":false,"weight":0.005319}

        json_value = json.loads(raw_value)
        logging.debug(json_value)

        if json_value['liquid_alarm']:
            logging.debug('Writing water alarm')
            write_water_alarm()

        weight = json_value['weight']
        if weight > tare_weight and (time.time() - weight_update_time) >= interval:
            if len(read_weights) < num_read_weights:
                read_weights.append(weight)
                continue
            else:
                if valid_weights(read_weights):
                    logging.debug('Writing weight: {}'.format(statistics.mean(read_weights)))
                    write_weight(statistics.mean(read_weights))

                    current_time = time.time()
                    logging.debug('Updating time: {}'.format(time.ctime(current_time)))
                    weight_update_time = current_time
                else:
                    read_weights = read_weights[1:]
    except Exception as ex:
        logging.error(ex)
