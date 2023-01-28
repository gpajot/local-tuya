from dataclasses import dataclass

from local_tuya.protocol import ProtocolConfig


@dataclass
class DeviceConfig:
    protocol: ProtocolConfig
    # Seconds to wait for more update commands in order to group them.
    debounce_updates: float = 0
    # Seconds to wait for state updates to confirm the command has been acknowledged.
    # 0 disables confirmation.
    confirm_timeout: float = 5
