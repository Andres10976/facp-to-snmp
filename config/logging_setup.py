import yaml
import logging.config
import os

def setup_logging():
    with open(os.path.join(os.path.dirname(__file__), 'logging.yml'), 'r') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)