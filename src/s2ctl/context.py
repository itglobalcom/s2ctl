from typing import List, Optional, TypedDict

from keyrings.cryptfile.cryptfile import CryptFileKeyring

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


class ContextManager(BaseContextManager):
    def __init__(
        self, config_manager: ConfigManager, keyring_key: str, keyring_path: str,
    ) -> None:
        super().__init__(config_manager)
        self.keyring = CryptFileKeyring()
        self.keyring.file_path = keyring_path  # type: ignore
        self.keyring.keyring_key = keyring_key  # type: ignore

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
