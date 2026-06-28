from datetime import date, datetime
from typing import Literal

from lewisham_client.domain.models import (
    CollectionEntry,
    CollectionSchedule,
)
from pydantic import BaseModel, Field


class CollectionEntryResponse(BaseModel):
    """One collection stream in the property's schedule."""

    waste_type: str = Field(
        description="Waste stream label exactly as normalized from Lewisham.",
        examples=["Refuse"],
    )
    frequency: Literal["WEEKLY", "FORTNIGHTLY"] = Field(
        description="Collection cadence reported by Lewisham.",
        examples=["FORTNIGHTLY"],
    )
    day: str = Field(
        description="Named weekday on which this waste stream is collected.",
        examples=["Thursday"],
    )
    next_collection: date | None = Field(
        description=(
            "Next collection date for this waste stream. Present for fortnightly "
            "streams when Lewisham publishes an anchor date, and for all weekly "
            "streams via weekday derivation. Null for fortnightly streams without "
            "a published anchor."
        ),
        examples=["2026-07-03"],
    )
    next_collection_basis: Literal["published", "weekday_derived"] | None = Field(
        description=(
            "'published' means Lewisham explicitly stated the date on the schedule "
            "page. 'weekday_derived' means the date was computed as the next "
            "occurrence of the collection weekday from the fetch timestamp. Null "
            "when next_collection is null."
        ),
        examples=["published"],
    )

    @classmethod
    def from_domain(cls, entry: CollectionEntry) -> "CollectionEntryResponse":
        return cls(
            waste_type=entry.waste_type,
            frequency=entry.frequency,
            day=entry.day,
            next_collection=entry.next_collection,
            next_collection_basis=entry.next_collection_basis,
        )


class CollectionScheduleResponse(BaseModel):
    """A parsed bin collection schedule for one Lewisham address."""

    uprn: str = Field(
        description="Unique Property Reference Number used for the lookup.",
        examples=["100000000001"],
    )
    address: str = Field(
        description="Human-readable address for the UPRN.",
        examples=["1 Example Street, Catford, SE6 1SQ, London"],
    )
    collections: list[CollectionEntryResponse] = Field(
        description="Waste collection streams parsed from Lewisham's response.",
    )
    source_url: str = Field(
        description="Lewisham web page that backs the scraped endpoint.",
        examples=[
            "https://lewisham.gov.uk/myservices/recycling-and-rubbish/your-bins/collection"
        ],
    )
    fetched_at: datetime = Field(
        description="UTC timestamp when this schedule was fetched upstream.",
        examples=["2026-06-26T12:00:00Z"],
    )

    @classmethod
    def from_domain(cls, schedule: CollectionSchedule) -> "CollectionScheduleResponse":
        return cls(
            uprn=schedule.uprn,
            address=schedule.address,
            collections=[
                CollectionEntryResponse.from_domain(entry)
                for entry in schedule.collections
            ],
            source_url=schedule.source_url,
            fetched_at=schedule.fetched_at,
        )
