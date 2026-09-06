import types
from typing import List, Optional, TypedDict

from keyrings.cryptfile.cryptfile import CryptFileKeyring

from s2ctl.click import BaseFailException
from s2ctl.config import ConfigManager

SERVICE_NAME = 'serverspace'

_CONTEXTS_CONFIG = 'contexts'
_CURRENT_CONTEXT_CONFIG = 'current_context'


class ContextEntity(TypedDict):
    name: str
    current: bool


class BaseContextManager(object):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager

    def get_current_context_name(self) -> str:
        config = self.config_manager.get_config()
        return config[_CURRENT_CONTEXT_CONFIG]

    def set_context(self, curr_context: str) -> None:
        config = self.config_manager.get_config()
        if curr_context not in config.get(_CONTEXTS_CONFIG, []):
            raise RuntimeError("context doesn't exist")
        config[_CURRENT_CONTEXT_CONFIG] = curr_context
        self.config_manager.save_config(config)

    def contexts_list(self) -> List[ContextEntity]:
        config = self.config_manager.get_config()
        contexts = config.get(_CONTEXTS_CONFIG, [])
        current_context = config.get(_CURRENT_CONTEXT_CONFIG, '')

        return [
            {'name': context_name, 'current': context_name == current_context}
            for context_name in contexts
        ]

    def remove_context_from_config(self, context_name: str) -> List[str]:
        config = self.config_manager.get_config()
        contexts = config.get(_CONTEXTS_CONFIG, [])
        curr_context = config.get(_CURRENT_CONTEXT_CONFIG)
        if context_name not in contexts:
            raise RuntimeError("context doesn't exist")

        if curr_context == context_name:
            config[_CURRENT_CONTEXT_CONFIG] = ''

        contexts.remove(context_name)
        self.config_manager.save_config(config)
        return contexts

    def add_context_to_config(self, context_name: str) -> List[str]:
        config = self.config_manager.get_config()
        contexts = config.get(_CONTEXTS_CONFIG, [])
        if context_name in contexts:
            raise Exception('Context with same name already exists')
        contexts.append(context_name)
        config[_CONTEXTS_CONFIG] = contexts
        self.config_manager.save_config(config)
        return contexts


_KEY_IS_BLANK = (
    "The keyring key is empty: set 'keyring_key' in this configuration file "
    'or the S2CTL_CONTEXT_KEY environment variable.'
)
_KEY_DOES_NOT_FIT = (
    "Can't unlock the keyring '{path}': it was created with another key than the "
    "'keyring_key' of this configuration file (or S2CTL_CONTEXT_KEY)."
)
_FILE_IS_ALIEN = (
    "Can't read the keyring '{path}': the file was written by another tool or another "
    "version of it ({reason}). Point the 'keyring' configuration value to another file."
)
_UNKNOWN_FAILURE = "Can't unlock the keyring '{path}': {reason}."

# `keyrings.cryptfile` не различает отказы типом — только текстом ValueError.
_FAILURE_MESSAGES = types.MappingProxyType({
    'blank password': _KEY_IS_BLANK,
    'incorrect password': _KEY_DOES_NOT_FIT,
    'encryption scheme': _FILE_IS_ALIEN,
})


class KeyringUnlockError(BaseFailException):
    def __init__(self, keyring_path: str, failure: ValueError) -> None:
        super().__init__(_unlock_failure_message(keyring_path, failure))


def _unlock_failure_message(keyring_path: str, failure: ValueError) -> str:
    reason = str(failure)
    lowered = reason.lower()
    for marker, message in _FAILURE_MESSAGES.items():
        if marker in lowered:
            return message.format(path=keyring_path, reason=reason)
    return _UNKNOWN_FAILURE.format(path=keyring_path, reason=reason)


class ContextManager(BaseContextManager):
    def __init__(
        self, config_manager: ConfigManager, keyring_key: str, keyring_path: str,
    ) -> None:
        super().__init__(config_manager)
        self._keyring_key = keyring_key
        self._keyring_path = keyring_path
        self._keyring: Optional[CryptFileKeyring] = None

    @property
    def keyring(self) -> CryptFileKeyring:
        """Хранилище ключей, открываемое при первом обращении.

        Открытие расшифровывает файл и стоит argon2 — доли секунды на каждый
        вызов CLI. Большинству команд keyring не нужен вовсе: ключ приходит
        из `--apikey`/`S2CTL_APIKEY`, а справка и разбор аргументов не трогают
        контексты. Поэтому хранилище открывается там, где действительно
        читается, а не в конструкторе.
        """
        if self._keyring is not None:
            return self._keyring

        keyring = CryptFileKeyring()
        # `file_path` у keyring — NonDataProperty: присваивание и есть его способ
        # задать файл хранилища, но описать это в типах библиотека не может.
        keyring.file_path = self._keyring_path  # pyright: ignore[reportAttributeAccessIssue]
        try:
            # Ключ проверяется расшифровкой файла прямо здесь.
            keyring.keyring_key = self._keyring_key
        except ValueError as exc:
            raise KeyringUnlockError(self._keyring_path, exc) from exc

        self._keyring = keyring
        return keyring

    def add_context(self, context_name: str, apikey: str) -> None:
        self.keyring.set_password(SERVICE_NAME, context_name, apikey)
        self.add_context_to_config(context_name)
        if len(self.contexts_list()) == 1:
            self.set_context(context_name)

    def get_current_apikey(self) -> Optional[str]:
        config = self.config_manager.get_config()
        curr_context = config.get(_CURRENT_CONTEXT_CONFIG)
        if not curr_context:
            raise RuntimeError("context doesn't exist")
        return self.keyring.get_password(SERVICE_NAME, curr_context)

    def delete_context(self, context_name: str) -> None:
        self.remove_context_from_config(context_name)
        self.keyring.delete_password(SERVICE_NAME, context_name)
