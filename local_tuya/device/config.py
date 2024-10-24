from typing import Optional

from pydantic import BaseModel

from local_tuya.tuya import TuyaConfig


class DeviceConfig(BaseModel):
    tuya: TuyaConfig
    enable_discovery: bool = True
    included_components: Optional[set[str]] = None
    # Seconds to wait for more update commands in order to group them.
    debounce_updates: float = 0.5
    # Seconds to wait for state updates to confirm the command has been acknowledged.
    # 0 disables confirmation.
    confirm_timeout: float = 5
