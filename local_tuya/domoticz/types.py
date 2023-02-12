"""
Minimal Domoticz types for static typing and mocking in tests.
"""
from typing import Dict, Optional


class DomoticzUnit:
    def __init__(
        self,
        Name: str,
        DeviceID: str,
        Unit: int,
        TypeName: str,
        Image: Optional[int] = 0,
        Options: Optional[Dict[str, str]] = None,
    ):
        self.nValue: int = 0
        self.sValue: str = ""
        self.Color: str = ""
        self.Image: Optional[int] = 0
        self.Options: Optional[Dict[str, str]] = None

    def Create(self) -> None:
        ...

    def Update(self, Log: bool) -> None:
        ...

    def Delete(self) -> None:
        ...


class DomoticzEx:
    @classmethod
    def Debug(cls, s: str) -> None:
        ...

    @classmethod
    def Log(cls, s: str) -> None:
        ...

    @classmethod
    def Status(cls, s: str) -> None:
        ...

    @classmethod
    def Error(cls, s: str) -> None:
        ...

    @classmethod
    def Heartbeat(cls, i: int) -> None:
        ...

    @classmethod
    def Debugging(cls, i: int) -> None:
        ...

    Unit = DomoticzUnit


class DomoticzDevice:
    Units: Dict[int, DomoticzUnit] = {}


Parameters: Dict[str, str] = {}
Devices: Dict[str, DomoticzDevice] = {}
