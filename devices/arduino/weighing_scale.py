import statistics
import time

import util
from log import logging

log = logging.getLogger('weighing_scale')

DB_NAME = "weight"
MEASUREMENT_NAME = "weight"
TAG_HAMSTER = "hamster"
TAG_TARE = "tare"

NUM_READ_WEIGHTS = 5
WEIGHT_THRESHOLD = 150
TARE_WEIGHT_DEFAULT = 165
WRITE_INTERVAL = 86400
READ_INTERVAL = 3600


class WeighingScale:
    read_hamster_weights = []
    read_tare_weights = []
    last_read_time = 0

    def __init__(self, client):
        self.client = client

    def __write_weight(self, tag, value):
        if value:
            self.client.switch_database(DB_NAME)

            json_body = [{
                "measurement": MEASUREMENT_NAME,
                "tags": {
                    "type": tag
                },
                "fields": {
                    "value": value
                }
            }]

            self.client.write_points(json_body)

    def __read_last_weight(self, tag):
        self.client.switch_database(DB_NAME)
        query_result = self.client.query("SELECT last(*) FROM {} WHERE type = '{}'".format(MEASUREMENT_NAME, tag))
        log.debug("Last weight query result for tag '{}': {}".format(tag, query_result))
        return next(query_result.get_points())

    def __delete_last_tare_weight(self):
        self.client.switch_database(DB_NAME)
        self.client.query(
            "DELETE FROM {} WHERE type = '{}' AND time < now() - 1h".format(MEASUREMENT_NAME, TAG_TARE))

    def process_weight(self, weight):
        current_time = time.time()

        if weight > WEIGHT_THRESHOLD and current_time - self.last_read_time >= READ_INTERVAL:
            last_tare_weight = self.__read_last_weight(TAG_TARE)

            last_tare_weight_value = last_tare_weight['last_value'] \
                if last_tare_weight is not None else TARE_WEIGHT_DEFAULT

            last_hamster_weight = self.__read_last_weight(TAG_HAMSTER)
            last_hamster_weight_update_time = util.get_epoch_time_from_string(last_hamster_weight['time']) \
                if last_hamster_weight is not None else 0

            if 1 < abs(weight - last_tare_weight_value) <= 20:  # check tare weight
                if len(self.read_tare_weights) < NUM_READ_WEIGHTS:
                    self.read_tare_weights.append(weight)
                else:
                    if self.__valid_weights(self.read_tare_weights):
                        mean_value = statistics.mean(self.read_tare_weights)
                        log.info('Writing tare weight: {}'.format(mean_value))
                        self.__write_weight(TAG_TARE, mean_value)

                        log.info('Deleting last tare weight')
                        self.__delete_last_tare_weight()

                        self.read_tare_weights = []
                        self.last_read_time = time.time()
                    else:
                        self.read_tare_weights = self.read_tare_weights[1:]
            elif abs(weight - last_tare_weight_value) > 20 \
                    and current_time - last_hamster_weight_update_time > WRITE_INTERVAL:  # check hamster weight
                if len(self.read_hamster_weights) < NUM_READ_WEIGHTS:
                    self.read_hamster_weights.append(weight - last_tare_weight_value)
                else:
                    if self.__valid_weights(self.read_hamster_weights):
                        mean_value = statistics.mean(self.read_hamster_weights)
                        log.info('Writing hamster weight: {}'.format(mean_value))
                        self.__write_weight(TAG_HAMSTER, mean_value)

                        self.read_hamster_weights = []
                        self.last_read_time = time.time()
                    else:
                        self.read_hamster_weights = self.read_hamster_weights[1:]

    @staticmethod
    def __valid_weights(values):
        return statistics.stdev(values) < 1  # calculate standard deviation
