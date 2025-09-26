from pydantic import BaseModel

from local_tuya.backoff import SequenceBackoff
from local_tuya.tuya import TuyaConfig


class DeviceConfig(BaseModel):
    tuya: TuyaConfig
    enable_discovery: bool = True
    included_components: set[str] | None = None
    # Seconds to wait for more update commands in order to group them.
    debounce_updates: float = 0.5
    # Determines how often to retry updates until the state matches.
    # `retries` can be set to 0 to disable retries.
    retries: int = 5
    retry_backoff: SequenceBackoff = SequenceBackoff(5, 10, 30, 60)
