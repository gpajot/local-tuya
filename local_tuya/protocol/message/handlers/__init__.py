from typing import List, Type

from local_tuya.protocol.config import ProtocolConfig
from local_tuya.protocol.message.handlers.handler import MessageHandler
from local_tuya.protocol.message.handlers.v33 import V33MessageHandler

HANDLERS: List[Type[MessageHandler]] = [
    V33MessageHandler,
]


def get_handler(config: ProtocolConfig) -> MessageHandler:
    for handler_class in HANDLERS:
        handler_ = handler_class.from_config(config)
        if handler_:
            return handler_
    raise ValueError(f"unsupported device: {config!r}")
