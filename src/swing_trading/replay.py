"""Deterministic event-time replay clock; no wall-clock or future-data fallback."""
from dataclasses import dataclass
from datetime import datetime, timezone


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError("Expected timezone-aware UTC")
    return value


@dataclass
class ReplayClock:
    as_of_utc: datetime

    def __setattr__(self, name: str, value: object) -> None:
        """Apply the same UTC/monotonic invariant to direct clock assignments.

        The public dataclass field and advance_to() API remain unchanged.
        A new ReplayClock may still be created for a separate earlier snapshot.
        """
        if name == "as_of_utc":
            require_utc(value)
            previous = self.__dict__.get("as_of_utc")
            if previous is not None and value < previous:
                raise ValueError("Replay clock cannot go backwards")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        require_utc(self.as_of_utc)

    def advance_to(self, next_time_utc: datetime) -> None:
        require_utc(next_time_utc)
        if next_time_utc < self.as_of_utc:
            raise ValueError("Replay clock cannot go backwards")
        self.as_of_utc = next_time_utc

    def known(self, first_known_time_utc: datetime) -> bool:
        return require_utc(first_known_time_utc) <= self.as_of_utc
