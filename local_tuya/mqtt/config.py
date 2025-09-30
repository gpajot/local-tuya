from pydantic import BaseModel

from local_tuya.backoff import SequenceBackoff


def get_state_topic(driver_prefix: str, device_id: str) -> str:
    return f"{driver_prefix}/get/{device_id}"


def get_status_topic(driver_prefix: str, device_id: str) -> str:
    return f"{driver_prefix}/status/{device_id}"


class MQTTConfig(BaseModel):
    discovery_prefix: str = "local-tuya"
    driver_prefix: str = "local-tuya"
    hostname: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    timeout: float = 5
    keepalive: int = 60
    backoff: SequenceBackoff = SequenceBackoff(0, 1, 5, 10, 30, 60, 300)
