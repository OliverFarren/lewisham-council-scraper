from collections.abc import Hashable
from datetime import timedelta
from typing import Protocol, TypeVar

KeyT = TypeVar("KeyT", bound=Hashable)
KeyT_contra = TypeVar("KeyT_contra", bound=Hashable, contravariant=True)
ValueT = TypeVar("ValueT")


class TtlCache(Protocol[KeyT_contra, ValueT]):
    def get(self, key: KeyT_contra) -> ValueT | None:
        """Return a cached value, or None when the key is absent or expired."""

    def set(self, key: KeyT_contra, value: ValueT, ttl: timedelta) -> None:
        """Store a value until the TTL expires."""

    def delete(self, key: KeyT_contra) -> None:
        """Remove a key if present."""

    def clear(self) -> None:
        """Remove every cached value."""
