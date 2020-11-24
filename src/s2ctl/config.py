import random
import string
import types
from pathlib import Path
from typing import Any, Dict

import config_path
import yaml


def generate_password(length: int = 10):
    char_seq = string.ascii_letters + string.digits + string.punctuation + string.whitespace
    return ''.join((random.choice(char_seq)for _ in range(length)))  # noqa: S311


_CONFIG_PATH = config_path.ConfigPath('s2ctl', 'serverspace', '.yaml')
DEFAULT_CONFIG_DIR: Path = _CONFIG_PATH.saveFolderPath(mkdir=True)  # type: ignore
DEFAULT_CONFIG_PATH: Path = DEFAULT_CONFIG_DIR / 'config.yaml'
DEFAULT_CONFIG = types.MappingProxyType({
    'keyring': str(DEFAULT_CONFIG_DIR / 'keyring.cfg'),
    'keyring_key': generate_password(),
    'contexts': [],
    'current_context': '',
})


class ConfigManager(object):
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_config(self) -> Dict[str, Any]:
        self._init_config()
        with open(self.path)as config:
            return {**DEFAULT_CONFIG, **yaml.safe_load(config)}

    def save_config(self, config: Dict[str, Any]) -> None:
        with open(self.path, 'w') as config_file:
            yaml.dump(config, config_file)

    def _init_config(self):
        if not self.path.exists():
            self.save_config(dict(DEFAULT_CONFIG))
