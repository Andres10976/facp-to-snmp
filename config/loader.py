import yaml
import os
from src.classes.schema import Config

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    return Config(**config_dict)