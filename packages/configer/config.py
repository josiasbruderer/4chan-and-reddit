import json
import os.path
from packages import logger

log = logger.setup(__name__, None, logger.DEBUG)

def setup(file_path):
    return Config(file_path)


class Config:
    config_file = None
    config = None

    def __init__(self, file_path):
        self.config_file = file_path
        self.config = self.read_config()

    def read_config(self):
        try:
            return json.load(open(self.config_file, 'r'))
        except FileNotFoundError:
            log.critical(f'Config file {self.config_file} not found')
        except json.decoder.JSONDecodeError:
            log.critical(f'Config file {self.config_file} is not valid JSON')
        return None

    def get_from_import_run_mode(self, param=None):
        cfg = self.get("import")
        if cfg["run_mode"] in cfg["run_modes"]:
            if param is None:
                return cfg["run_modes"][cfg["run_mode"]]
            if param in cfg["run_modes"][cfg["run_mode"]]:
                return cfg["run_modes"][cfg["run_mode"]][param]
        return False

    def get(self, domain, param=None):
        if param is None and domain in self.config:
            return self.config[domain]
        if domain in self.config and param in self.config[domain]:
            return self.config[domain][param]
        return False

    def set(self, domain, param, value):
        self.create_domain(domain)
        self.config[domain][param] = value

    def create_domain(self, domain):
        if domain not in self.config:
            self.config[domain] = {}

    def as_path(self, path_part):
        if not str.startswith(path_part, "/"):
            path_part = os.path.join(self.get("general", "root_dir"), path_part)
        return os.path.abspath(path_part)
