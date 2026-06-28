from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class AddressCandidate:
    """A UPRN and human-readable address label for a selectable property."""

    uprn: str
    title: str


@dataclass(frozen=True, slots=True)
class CollectionEntry:
    """One waste collection stream parsed from Lewisham's schedule HTML."""

    waste_type: str
    frequency: Literal["WEEKLY", "FORTNIGHTLY"]
    day: str
    next_collection: date | None
    next_collection_basis: Literal["published", "weekday_derived"] | None


@dataclass(slots=True)
class CollectionSchedule:
    """A parsed collection schedule ready for API serialization."""

    uprn: str
    address: str
    collections: list[CollectionEntry]
    source_url: str
    fetched_at: datetime
