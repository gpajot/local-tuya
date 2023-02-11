from enum import IntEnum
from typing import Optional, Set


class UnitId(IntEnum):
    @classmethod
    def names(cls) -> str:
        return ",".join(e.name.lower() for e in cls)

    @classmethod
    def included(cls, names: Optional[str]) -> Set["UnitId"]:
        if not names:
            return set(cls)
        included_names = names.split(",")
        return {e for e in cls if e.name.lower() in included_names}
