import secrets
import string
import types
from pathlib import Path
from typing import Any, Dict

import config_path
import yaml


def generate_password(length: int = 10):
    """Ключ шифрования нового keyring: секрет, поэтому источник — `secrets`, не `random`."""
    char_seq = string.ascii_letters + string.digits + string.punctuation + string.whitespace
    return ''.join(secrets.choice(char_seq) for _ in range(length))


KEYRING_FILE_NAME = 'keyring.cfg'

_CONFIG_PATH = config_path.ConfigPath('s2ctl', 'serverspace', '.yaml')
DEFAULT_CONFIG_DIR = Path(_CONFIG_PATH.saveFolderPath(mkdir=True))
DEFAULT_CONFIG_PATH: Path = DEFAULT_CONFIG_DIR / 'config.yaml'
DEFAULT_CONFIG = types.MappingProxyType({
    'contexts': [],
    'current_context': '',
})


class ConfigManager(object):
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_config(self) -> Dict[str, Any]:
        self._init_config()
        with open(self.path)as config:
            stored = yaml.safe_load(config) or {}
        return self._fill_defaults(stored)

    def save_config(self, config: Dict[str, Any]) -> None:
        with open(self.path, 'w') as config_file:
            yaml.dump(config, config_file)

    def _fill_defaults(self, stored: Dict[str, Any]) -> Dict[str, Any]:
        """Недостающие значения дописываются в файл: сгенерированный ключ обязан пережить вызов."""
        missing = {
            key: default
            for key, default in self._defaults().items()
            if key not in stored
        }
        if not missing:
            return stored
        filled = {**stored, **missing}
        self.save_config(filled)
        return filled

    def _defaults(self) -> Dict[str, Any]:
        """Значения, которых нет в файле; keyring — рядом с ним, а не в каталоге по умолчанию.

        Ключ шифрования свой у каждого файла конфигурации, поэтому и keyring у каждого
        свой: общий файл keyring второй конфигурации уже не расшифровать.
        """
        return {
            **DEFAULT_CONFIG,
            'keyring': str(self.path.parent / KEYRING_FILE_NAME),
            'keyring_key': generate_password(),
        }

    def _init_config(self):
        if not self.path.exists():
            self.save_config(self._defaults())
