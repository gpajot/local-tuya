from typing import Optional

from pydantic import BaseModel, ConfigDict

from local_tuya.backoff import Backoff, SequenceBackoff

DRIVER_PREFIX = "local-tuya"


def get_state_topic(device_id: str) -> str:
    return f"{DRIVER_PREFIX}/get/{device_id}"


def get_status_topic(device_id: str) -> str:
    return f"{DRIVER_PREFIX}/status/{device_id}"


class MQTTConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    discovery_prefix: str
    hostname: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: float = 5
    keepalive: int = 60
    backoff: Backoff = SequenceBackoff(0, 1, 5, 10, 30, 60, 300)
