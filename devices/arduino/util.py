import time


def get_epoch_time_from_string(time_string):  # e.g. '2020-06-01T12:59:38.334163852Z
    return time.mktime(time.strptime(time_string[:19], "%Y-%m-%dT%H:%M:%S"))
