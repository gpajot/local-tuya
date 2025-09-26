from pydantic import BaseModel

from local_tuya.backoff import SequenceBackoff

DRIVER_PREFIX = "local-tuya"


def get_state_topic(device_id: str) -> str:
    return f"{DRIVER_PREFIX}/get/{device_id}"


def get_status_topic(device_id: str) -> str:
    return f"{DRIVER_PREFIX}/status/{device_id}"


class MQTTConfig(BaseModel):
    discovery_prefix: str
    hostname: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    timeout: float = 5
    keepalive: int = 60
    backoff: SequenceBackoff = SequenceBackoff(0, 1, 5, 10, 30, 60, 300)
