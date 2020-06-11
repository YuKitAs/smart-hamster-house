from log import logging

log = logging.getLogger('water_alarm')

DB_NAME = "water"
MEASUREMENT_NAME = "level"


class WaterAlarm:
    def __init__(self, client):
        self.client = client

    def __write_water_alarm(self):
        self.client.switch_database(DB_NAME)

        json_body = [{
            "measurement": MEASUREMENT_NAME,
            "tags": {
                "location": "home"
            },
            "fields": {
                "value": 0
            }
        }]

        self.client.write_points(json_body)

    def process_water_alarm(self, alarm):
        if alarm:
            log.info('Writing water alarm')
            self.__write_water_alarm()
