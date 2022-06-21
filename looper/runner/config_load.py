from typing import Optional
import os
from pathlib import Path

import yaml
from nuclear.sublog import log

from looper.runner.config import Config

DEFAULT_CONFIG_FILENAME = 'default.config.yaml'
CONFIG_FILE_ENV = 'CONFIG_FILE'


def load_config(config_file_path: Optional[str] = None) -> Config:
    if not config_file_path:
        config_file_path = os.environ.get(CONFIG_FILE_ENV)
    if not config_file_path:
        path = Path(DEFAULT_CONFIG_FILENAME)
        if path.is_file():
            log.info(f'found "{path}" file at default config path')
            return load_config_from_file(path)

        log.info('CONFIG_FILE env is unspecified, loading default config')
        return Config()

    path = Path(config_file_path)
    return load_config_from_file(path)


def load_config_from_file(path: Path) -> Config:
    if not path.is_file():
        raise FileNotFoundError(f"config file {path} doesn't exist")

    try:
        with path.open() as file:
            config_dict = yaml.load(file, Loader=yaml.FullLoader)
            if not config_dict:
                log.info('config file is empty, loading default config')
                return Config()
                
            config = Config.parse_obj(config_dict)
            log.info(f'config loaded from {path}', **config_dict)
            return config
    except Exception as e:
        raise RuntimeError('loading config failed') from e
