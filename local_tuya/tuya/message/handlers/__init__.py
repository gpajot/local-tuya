from typing import List, Type

from local_tuya.tuya.config import TuyaConfig
from local_tuya.tuya.message.handlers.handler import MessageHandler
from local_tuya.tuya.message.handlers.v33 import V33MessageHandler

HANDLERS: List[Type[MessageHandler]] = [
    V33MessageHandler,
]


def get_handler(config: TuyaConfig) -> MessageHandler:
    for handler_class in HANDLERS:
        if handler_ := handler_class.from_config(config):
            return handler_
    raise ValueError(f"unsupported device: {config!r}")
