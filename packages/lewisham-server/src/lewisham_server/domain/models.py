from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class AddressCandidate:
    """A UPRN and human-readable address returned by Lewisham AddressFinder."""

    uprn: str
    title: str


@dataclass(frozen=True, slots=True)
class CollectionEntry:
    """One waste collection stream parsed from Lewisham's schedule HTML."""

    waste_type: str
    frequency: str
    day: str


@dataclass(slots=True)
class CollectionSchedule:
    """A parsed collection schedule ready for API serialization."""

    uprn: str
    address: str
    collections: list[CollectionEntry]
    next_collection: date | None
    source_url: str
    fetched_at: datetime
