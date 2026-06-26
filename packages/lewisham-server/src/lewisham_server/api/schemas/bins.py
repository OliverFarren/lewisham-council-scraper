from datetime import date, datetime

from pydantic import BaseModel, Field

from lewisham_server.domain.models import (
    AddressCandidate,
    CollectionEntry,
    CollectionSchedule,
)


class AddressCandidateResponse(BaseModel):
    """A selectable address candidate for a bin collection lookup."""

    uprn: str = Field(
        description="Unique Property Reference Number for the address.",
        examples=["100000000001"],
    )
    title: str = Field(
        description="Human-readable address label returned by Lewisham.",
        examples=["1 Example Street, Catford, SE6 1SQ, London"],
    )

    @classmethod
    def from_domain(cls, address: AddressCandidate) -> "AddressCandidateResponse":
        return cls(uprn=address.uprn, title=address.title)


class CollectionEntryResponse(BaseModel):
    """One collection stream in the property's schedule."""

    waste_type: str = Field(
        description="Waste stream label exactly as normalized from Lewisham.",
        examples=["Refuse"],
    )
    frequency: str = Field(
        description="Collection cadence reported by Lewisham.",
        examples=["FORTNIGHTLY"],
    )
    day: str = Field(
        description="Named weekday on which this waste stream is collected.",
        examples=["Thursday"],
    )

    @classmethod
    def from_domain(cls, entry: CollectionEntry) -> "CollectionEntryResponse":
        return cls(
            waste_type=entry.waste_type,
            frequency=entry.frequency,
            day=entry.day,
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
    next_collection: date | None = Field(
        description=(
            "Next collection date when Lewisham publishes one. Some civic or "
            "partial schedules include collection streams without a date."
        ),
        examples=["2026-07-02"],
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
            next_collection=schedule.next_collection,
            source_url=schedule.source_url,
            fetched_at=schedule.fetched_at,
        )
