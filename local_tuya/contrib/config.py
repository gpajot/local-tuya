from pydantic import BaseModel

from local_tuya.contrib.airton_ac import AirtonACDevice
from local_tuya.contrib.ceiling_fan import CeilingFanDevice
from local_tuya.device import Device, DeviceConfig

_DEVICE_MODEL_MAPPING = {
    AirtonACDevice.DISCOVERY.model: AirtonACDevice,
    CeilingFanDevice.DISCOVERY.model: CeilingFanDevice,
}


class FullDeviceConfig(BaseModel):
    name: str
    model: str
    config: DeviceConfig

    def infer(self) -> type[Device]:
        if self.model not in _DEVICE_MODEL_MAPPING:
            ValueError(f"no device found for {self.name}:{self.model}")
        return _DEVICE_MODEL_MAPPING[self.model]
