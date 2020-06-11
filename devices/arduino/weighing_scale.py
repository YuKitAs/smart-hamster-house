import statistics
import time

import util
from log import logging

log = logging.getLogger('weighing_scale')

DB_NAME = "weight"
MEASUREMENT_NAME = "weight"
TAG_HAMSTER = "hamster"
TAG_TARE = "tare"

NUM_READ_WEIGHTS = 5  # number of consecutive weights to evaluate
WEIGHT_THRESHOLD = 150  # evaluate weight only when it's above the threshold
WRITE_INTERVAL = 86400  # write hamster weight at most once every 24h
READ_INTERVAL = 3600  # evaluate weight every 1h
TARE_WEIGHT_DEFAULT = 165  # an approximate value if no tare weight has been recorded before


class WeighingScale:
    read_hamster_weights = []
    read_tare_weights = []
    last_read_time = 0

    def __init__(self, client):
        self.client = client

    def __write_weight(self, tag, value):
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
        return next(query_result.get_points()) if len(query_result) > 0 else None

    def __delete_last_tare_weight(self):
        self.client.switch_database(DB_NAME)
        self.client.query(
            "DELETE FROM {} WHERE type = '{}' AND time < now() - 1h".format(MEASUREMENT_NAME, TAG_TARE))

    def __evaluate_weight(self, weight, read_weights, tare_weight=True, last_tare_weight_value=TARE_WEIGHT_DEFAULT):
        log.debug('Read weights: {}'.format(read_weights))

        if len(read_weights) < NUM_READ_WEIGHTS:
            read_weights.append(weight if tare_weight else weight - last_tare_weight_value)
        else:
            if self.__valid_weights(read_weights):
                mean_value = statistics.mean(read_weights)
                log.info('Writing {} weight: {}'.format('tare' if tare_weight else 'hamster', mean_value))
                self.__write_weight(TAG_TARE if tare_weight else TAG_HAMSTER, mean_value)

                if tare_weight:
                    log.info('Deleting last tare weight')
                    self.__delete_last_tare_weight()

                read_weights = []
                self.last_read_time = time.time()
            else:
                read_weights = read_weights[1:]

    def process_weight(self, weight):
        current_time = time.time()

        if weight > WEIGHT_THRESHOLD and current_time - self.last_read_time >= READ_INTERVAL:
            last_tare_weight = self.__read_last_weight(TAG_TARE)
            last_tare_weight_value = last_tare_weight['last_value'] \
                if last_tare_weight is not None else TARE_WEIGHT_DEFAULT

            if 1 < abs(weight - last_tare_weight_value) <= 20:  # check tare weight
                log.debug('Evaluating tare weight')
                self.__evaluate_weight(weight, self.read_tare_weights)
            elif abs(weight - last_tare_weight_value) > 20:  # check hamster weight
                last_hamster_weight = self.__read_last_weight(TAG_HAMSTER)
                last_hamster_weight_update_time = util.get_epoch_time_from_string(last_hamster_weight['time']) \
                    if last_hamster_weight is not None else 0

                if current_time - last_hamster_weight_update_time > WRITE_INTERVAL:
                    log.debug('Evaluating hamster weight')
                    self.__evaluate_weight(weight, self.read_hamster_weights, False, last_tare_weight_value)

    @staticmethod
    def __valid_weights(values):
        return statistics.stdev(values) < 1  # calculate standard deviation of given weight values
