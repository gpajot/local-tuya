from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Collection, Optional, Union

from typing_extensions import TypeAlias

Value: TypeAlias = Union[bool, int, float, str]
Values: TypeAlias = dict[str, Value]


@dataclass
class ComponentDiscovery(ABC):
    name: str
    icon: str
    property: str


@dataclass
class SwitchComponentDiscovery(ComponentDiscovery): ...


@dataclass
class SensorComponentDiscovery(ComponentDiscovery):
    class_: str
    unit: str = "°C"


@dataclass
class SelectComponentDiscovery(ComponentDiscovery):
    options: type[Enum]


@dataclass
class TemperatureSetPointComponentDiscovery(ComponentDiscovery):
    min: float
    max: float
    step: float
    unit: str = "C"


@dataclass
class DeviceDiscovery:
    model: str
    components: Collection[ComponentDiscovery]

    def filter_components(
        self,
        included: Optional[Collection[str]],
    ) -> "DeviceDiscovery":
        if included is None:
            return self
        return DeviceDiscovery(
            model=self.model,
            components=tuple(c for c in self.components if c.property in included),
        )


class Protocol(ABC):
    timeout: float

    @abstractmethod
    def receive_commands(self) -> AsyncIterator[tuple[str, Values]]: ...
    @abstractmethod
    async def set_availability(self, device_id: str, status: bool) -> None: ...
    @abstractmethod
    async def send_state(self, device_id: str, payload: Values) -> None: ...
    @abstractmethod
    async def send_discovery(
        self,
        device: DeviceDiscovery,
        device_id: str,
        device_name: str,
    ) -> None: ...
