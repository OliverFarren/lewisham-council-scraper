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


@dataclass(frozen=True, slots=True)
class DataQualitySummary:
    """A count of collection entries by how their next_collection was determined."""

    total_collections: int
    published_count: int
    weekday_derived_count: int
    missing_next_collection_count: int


@dataclass(slots=True)
class CollectionSchedule:
    """A parsed collection schedule ready for API serialization."""

    uprn: str
    address: str
    collections: list[CollectionEntry]
    source_url: str
    fetched_at: datetime

    def data_quality(self) -> DataQualitySummary:
        """Summarize how confidently each entry's next_collection was determined.

        Owned here rather than by a consumer because it counts against the
        next_collection_basis Literal defined on CollectionEntry above; if
        that Literal ever grows a new value, this is the one place that has
        to change, rather than every downstream consumer's own tally
        silently under-counting the new category.
        """
        return DataQualitySummary(
            total_collections=len(self.collections),
            published_count=sum(
                1 for c in self.collections if c.next_collection_basis == "published"
            ),
            weekday_derived_count=sum(
                1
                for c in self.collections
                if c.next_collection_basis == "weekday_derived"
            ),
            missing_next_collection_count=sum(
                1 for c in self.collections if c.next_collection is None
            ),
        )


@dataclass(frozen=True, slots=True)
class ContractDriftDiagnostics:
    """Structured detail about an upstream contract-drift failure.

    Attached to DomainError.diagnostics (see domain.errors) so a consumer can
    build a rich failure report without intercepting structlog output.

    source tells a consumer which fields to expect, rather than having to
    guess based on which ones happen to be set: "client" failures (an
    unexpected HTTP status, or a response LewishamClient itself couldn't
    decode or make sense of) always populate status_code and endpoint;
    "parser" failures (LewishamParser couldn't find any collection entries
    in the decoded HTML) never do.

    payload_size_bytes and payload_sha256 carry no PII and are always
    populated. payload_preview is only populated for "parser" failures when
    the caller opted in via LewishamParser(include_raw_upstream=True); it may
    contain PII scraped from the upstream page and callers should treat it
    accordingly.
    """

    error_type: str
    error_message: str
    source: Literal["client", "parser"]
    payload_size_bytes: int | None = None
    payload_sha256: str | None = None
    payload_preview: str | None = None
    payload_truncated: bool = False
    status_code: int | None = None
    endpoint: str | None = None
