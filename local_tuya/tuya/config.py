from enum import Enum

from pydantic import BaseModel, ConfigDict

from local_tuya.backoff import Backoff, SequenceBackoff


class TuyaVersion(bytes, Enum):
    """Supported versions."""

    v33 = b"3.3"


class TuyaConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id_: str
    address: str
    key: bytes
    port: int = 6668
    version: TuyaVersion = TuyaVersion.v33
    # How long to wait between reconnection attempts.
    connection_backoff: Backoff = SequenceBackoff(0, 1, 5, 10, 30, 60, 300)
    # Seconds to wait until command can be confirmed.
    # This excludes time waiting for the connection to be established.
    timeout: float = 5
    # Seconds between each heartbeat interval keeping the connection alive.
    heartbeat_interval: float = 15
    # How long to keep the state until a refresh is done.
    # State is maintained via status updates so a low value shouldn't be required.
    state_refresh_interval: float = 3600
