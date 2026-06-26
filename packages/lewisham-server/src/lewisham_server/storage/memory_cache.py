from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


def _default_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class _CacheEntry[ValueT]:
    value: ValueT
    expires_at: datetime


class MemoryTtlCache[KeyT: Hashable, ValueT]:
    def __init__(self, clock: Callable[[], datetime] = _default_clock) -> None:
        self._clock = clock
        self._entries: dict[KeyT, _CacheEntry[ValueT]] = {}

    def get(self, key: KeyT) -> ValueT | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.expires_at <= self._clock():
            self.delete(key)
            return None

        return entry.value

    def set(self, key: KeyT, value: ValueT, ttl: timedelta) -> None:
        if ttl <= timedelta(0):
            self.delete(key)
            return

        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=self._clock() + ttl,
        )

    def delete(self, key: KeyT) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()
