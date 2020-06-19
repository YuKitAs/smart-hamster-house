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
WEIGHT_EVAL_THRESHOLD = 150  # evaluate weight only when it's above this threshold
HAMSTER_WEIGHT_EVAL_THRESHOLD = 180  # evaluate hamster weight once it's above this threshold
WRITE_HAMSTER_INTERVAL = 86400  # write hamster weight at most once every 24h
READ_INTERVAL = 3600  # evaluate weight every 1h
TARE_WEIGHT_DEFAULT = 165  # an approximate value if no tare weight has been recorded before
TARE_WEIGHT_OFFSET = 20  # max. offset of last tare weight


# The basic idea is, due to the floating weight of the food bowl + food, the actual hamster weight should always be
# compared to the actual tare weight (actual_hamster_weight =~ actual_total_weight - last_tare_weight).
# The tare weight will be evaluated and updated every 1 hour, when the total weight is above WEIGHT_EVAL_THRESHOLD.
# The hamster weight will be evaluated if
# 1. the total weight is above HAMSTER_WEIGHT_EVAL_THRESHOLD
# 2. the difference between the total weight and last tare weight is greater than TARE_WEIGHT_OFFSET
# but the hamster weight will only be recorded once every 24 hours (according to the time of the last hamster weight).
# The weight value recorded is the mean value of several (defined by NUM_READ_WEIGHTS) consecutive weights,
# when the standard deviation of them is smaller than 1.


class WeighingScale:
    read_hamster_weights = []
    read_tare_weights = []
    last_eval_time = 0

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

    def __get_last_tare_weight_value(self):
        last_tare_weight = self.__read_last_weight(TAG_TARE)
        return last_tare_weight['last_value'] if last_tare_weight is not None else TARE_WEIGHT_DEFAULT

    def __delete_last_tare_weight(self):
        self.client.switch_database(DB_NAME)
        self.client.query(
            "DELETE FROM {} WHERE type = '{}' AND time < now() - 1h".format(MEASUREMENT_NAME, TAG_TARE))

    def __evaluate_weight(self, weight, read_weights, tare_weight=True, last_tare_weight_value=TARE_WEIGHT_DEFAULT):
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

                read_weights.clear()
                self.last_eval_time = time.time()
            else:
                read_weights.pop(0)

    def __check_hamster_weight(self, weight, current_time):
        last_tare_weight_value = self.__get_last_tare_weight_value()

        if weight - last_tare_weight_value > TARE_WEIGHT_OFFSET:
            last_hamster_weight = self.__read_last_weight(TAG_HAMSTER)
            last_hamster_weight_update_time = util.get_epoch_time_from_string(last_hamster_weight['time']) \
                if last_hamster_weight is not None else 0

            if current_time - last_hamster_weight_update_time > WRITE_HAMSTER_INTERVAL:
                log.debug('Evaluating hamster weight')
                self.__evaluate_weight(weight, self.read_hamster_weights, False, last_tare_weight_value)

    def __check_tare_weight(self, weight):
        last_tare_weight_value = self.__get_last_tare_weight_value()

        if 1 < abs(weight - last_tare_weight_value) <= TARE_WEIGHT_OFFSET:
            log.debug('Evaluating tare weight')
            self.__evaluate_weight(weight, self.read_tare_weights)

    def process_weight(self, weight, current_time):
        if weight > HAMSTER_WEIGHT_EVAL_THRESHOLD:
            self.__check_hamster_weight(weight, current_time)
        elif current_time - self.last_eval_time >= READ_INTERVAL and weight > WEIGHT_EVAL_THRESHOLD:
            self.__check_tare_weight(weight)

    @staticmethod
    def __valid_weights(values):
        return statistics.stdev(values) < 1  # calculate standard deviation of given weight values
