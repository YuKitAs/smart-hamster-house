import json
import logging
import statistics
import time

import serial
from influxdb import InfluxDBClient

logging.basicConfig(filename='logs/weight-and-water.log', format='%(asctime)s - %(levelname)s - %(message)s',
                    level='DEBUG')

ser = serial.Serial('/dev/ttyACM0', 9600)

# InfluxDB
client = InfluxDBClient('localhost', 8086)
db_water = "water"
db_weight = "weight"
measurement_weight = "weight"
tag_hamster_weight = "hamster_weight"
tag_tare_weight = "tare_weight"

num_read_weights = 5
tare_weight_threshold = 150
tare_weight_default = 165
time_default = 0
write_interval = 86400
read_interval = 3600


def write_water_alarm():
    client.switch_database(db_water)

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


def write_weight(tag, value):
    if value:
        client.switch_database(db_weight)

        json_body = [{
            "measurement": measurement_weight,
            "tags": {
                "location": "home",
                "type": tag
            },
            "fields": {
                "value": value
            }
        }]

        client.write_points(json_body)


def read_last_weight(tag):
    client.switch_database(db_weight)
    query_result = client.query("SELECT last(*) FROM {} WHERE type = '{}'".format(measurement_weight, tag))
    logging.debug("Last weight query result for tag '{}': {}".format(tag, query_result))
    return next(query_result.get_points())


read_hamster_weights = []
read_tare_weights = []
last_read_time = 0

while True:
    try:
        raw_value = ser.readline().strip().decode('ascii')
        logging.debug("Serial: {}".format(raw_value))  # e.g. {"liquid_alarm":false,"weight":0.005319}

        json_value = json.loads(raw_value)

        if json_value['liquid_alarm']:
            logging.debug('[Water] Writing water alarm')
            write_water_alarm()

        weight = json_value['weight']
        current_time = time.time()

        if weight > tare_weight_threshold and current_time - last_read_time >= read_interval:
            last_tare_weight = read_last_weight(tag_tare_weight)

            last_tare_weight_update_time = time.mktime(
                time.strptime(last_tare_weight['time'][:19], "%Y-%m-%dT%H:%M:%S")) \
                if last_tare_weight is not None else time_default

            last_tare_weight_value = last_tare_weight['last_value'] \
                if last_tare_weight is not None else tare_weight_default

            last_hamster_weight = read_last_weight(tag_hamster_weight)
            last_hamster_weight_update_time = time.mktime(
                time.strptime(last_hamster_weight['time'][:19], "%Y-%m-%dT%H:%M:%S")) \
                if last_hamster_weight is not None else time_default

            if 1 < abs(weight - last_tare_weight_value) <= 20:  # check tare weight
                if len(read_tare_weights) < num_read_weights:
                    read_tare_weights.append(weight)
                    continue
                else:
                    if valid_weights(read_tare_weights):
                        mean_value = statistics.mean(read_tare_weights)
                        logging.debug('[Weight] Writing tare weight: {}'.format(mean_value))
                        write_weight(tag_tare_weight, mean_value)

                        read_tare_weights = []
                        last_read_time = time.time()
                    else:
                        read_tare_weights = read_tare_weights[1:]
            elif abs(weight - last_tare_weight_value) > 20 \
                    and current_time - last_hamster_weight_update_time > write_interval:  # check hamster weight
                if len(read_hamster_weights) < num_read_weights:
                    read_hamster_weights.append(weight - last_tare_weight_value)
                    continue
                else:
                    if valid_weights(read_hamster_weights):
                        mean_value = statistics.mean(read_hamster_weights)
                        logging.debug('[Weight] Writing hamster weight: {}'.format(mean_value))
                        write_weight(tag_hamster_weight, mean_value)

                        read_hamster_weights = []
                        last_read_time = time.time()
                    else:
                        read_hamster_weights = read_hamster_weights[1:]
    except Exception as ex:
        logging.error(ex)
