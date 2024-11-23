import json
from os import path


class Config:
    CONFIG_PATH = "config/config.json"

    @staticmethod
    def load_config(config_path):
        if not path.exists(config_path):
            return None
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        return config
