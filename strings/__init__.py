import json


class Strings:

    def __init__(self):
        with open('strings/messages.json') as file:
            self.message_strings = json.load(file)

    def get(self, string_type, string_id):
        return self.message_strings[string_type][string_id]
