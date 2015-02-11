import json
from os import path, makedirs


# TODO Config is a misleading name, maybe change to something like values
class ValueConfig:
    def __init__(self, config_path,
                 default_min_hue=0, default_min_sat=0, default_min_val=0,
                 default_max_hue=360, default_max_sat=0, default_max_val=0):
        """
        Creates a new config from a json config file.
        If the file doesn't exist, makes a default config and create the file.
        :param config_path: Path to json config
        """
        # Set defaults
        self.min_hue = default_min_hue
        self.max_hue = default_max_hue
        self.min_sat = default_min_sat
        self.max_sat = default_max_sat
        self.min_val = default_min_val
        self.max_val = default_max_val

        if path.isfile(config_path):  # File exists, load what it has
            with open(config_path, 'r') as config_file:
                json_data = config_file.read()
                parsed_json = json.loads(json_data)
                if 'minVal' in parsed_json:
                    self.min_val = parsed_json['minVal']
                if 'minSat' in parsed_json:
                    self.min_sat = parsed_json['minSat']
                if 'minHue' in parsed_json:
                    self.min_hue = parsed_json['minHue']
                if 'maxVal' in parsed_json:
                    self.max_val = parsed_json['maxVal']
                if 'maxSat' in parsed_json:
                    self.max_sat = parsed_json['maxSat']
                if 'maxHue' in parsed_json:
                    self.max_hue = parsed_json['maxHue']
        else:  # File doesn't exist, create one with default values
            self.save(config_path)

    def save(self, config_path):
        """
        Saves the config to a json file. Creates a file if one doesn't exist.
        :param config_path: Path of file to save to
        """
        if not path.exists(path.dirname(config_path)):
            makedirs(path.dirname(config_path))  # Create parent directories
        with open(config_path, 'w+') as config_file:
            json_text = json.dumps(
                {
                    'minVal': self.min_val,
                    'minSat': self.min_sat,
                    'minHue': self.min_hue,
                    'maxVal': self.max_val,
                    'maxSat': self.max_sat,
                    'maxHue': self.max_hue,
                },
                sort_keys=True,
                indent=2,
                separators=(',', ': ')
            )
            config_file.write(json_text)