from dataclasses import dataclass
from datetime import datetime

from lewisham_client.domain.models import CollectionEntry


@dataclass(frozen=True, slots=True)
class CollectionScheduleRaw:
    uprn: str
    body: str
    source_url: str
    fetched_at: datetime


@dataclass(slots=True)
class ParsedCollectionSchedule:
    collections: list[CollectionEntry]
