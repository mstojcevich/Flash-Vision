from os import path
import json


class Obj:
    was_setup = False

    def __init__(self, config_path):
        if not path.exists(config_path):
            raise IOError("Config file not found")
        else:
            try:
                with open(config_path, 'r') as config_file:
                    json_data = config_file.read()
                    parsed_json = json.loads(json_data)
                    if 'width' not in parsed_json:
                        raise IOError("No width in config")
                    if 'height' not in parsed_json:
                        raise IOError("No height in config")
                    self.width = parsed_json['width']
                    self.height = parsed_json['height']
            except Exception:
                raise IOError("Failed to read config file")

        self.aspect_ratio = self.width / self.height