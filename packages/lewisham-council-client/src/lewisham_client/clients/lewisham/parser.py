import hashlib
import html
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Literal

from lewisham_client.clients.lewisham.models import ParsedCollectionSchedule
from lewisham_client.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
)
from lewisham_client.domain.models import CollectionEntry, ContractDriftDiagnostics

_ENTRY_PATTERN = re.compile(
    r"<strong[^>]*>\s*(?P<waste_type>.*?)\s*</strong>\s*"
    r"is\s+collected\s*"
    r"<span[^>]*class=[\"']RoundsTransform[\"'][^>]*>\s*"
    r"(?P<frequency>.*?)\s*</span>\s*"
    r"on\s*(?P<day>[^.<\n\r]+)",
    re.IGNORECASE | re.DOTALL,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_NEXT_DATE_PATTERN = re.compile(
    r"your\s+next\s+collection\s+date\s+is\s*"
    r"(?P<date>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)
_NEXT_DATE_PHRASE_PATTERN = re.compile(
    r"your\s+next\s+collection\s+date\s+is\s*(?P<date>[^.<\n\r]+)",
    re.IGNORECASE,
)


def _parse_frequency(value: str) -> Literal["WEEKLY", "FORTNIGHTLY"]:
    if value == "WEEKLY":
        return "WEEKLY"
    if value == "FORTNIGHTLY":
        return "FORTNIGHTLY"
    raise UpstreamScraperChangedError(
        "roundsinformation returned an unrecognised collection frequency."
    )


_WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_LOGGER = logging.getLogger(__name__)


class LewishamParser:
    """Parse Lewisham's JSON-encoded Sitecore schedule HTML."""

    def __init__(
        self,
        *,
        include_raw_upstream: bool = False,
        raw_upstream_max_chars: int = 4_096,
    ) -> None:
        self._include_raw_upstream = include_raw_upstream
        self._raw_upstream_max_chars = raw_upstream_max_chars

    def parse_collection_schedule(
        self,
        raw_body: str,
        *,
        reference_date: date,
    ) -> ParsedCollectionSchedule:
        """Return structured collection entries from a roundsinformation response.

        reference_date is used to derive next-occurrence dates for weekly streams
        that Lewisham does not accompany with an explicit date.
        """

        try:
            decoded_html = self._decode_json_html(raw_body)
            normalised_html = self._normalise_html(decoded_html)
            collections = self._parse_entries(normalised_html, reference_date)
            if not collections:
                raise CollectionScheduleNotFoundError(
                    "Lewisham returned no collection entries for this UPRN."
                )

            return ParsedCollectionSchedule(collections=collections)
        except UpstreamScraperChangedError as exc:
            exc.diagnostics = self._build_drift_diagnostics(raw_body, exc)
            self._log_contract_drift(exc.diagnostics)
            raise
        except CollectionScheduleNotFoundError as exc:
            exc.diagnostics = self._build_drift_diagnostics(raw_body, exc)
            self._log_empty_schedule(exc.diagnostics)
            raise

    @staticmethod
    def _decode_json_html(raw_body: str) -> str:
        try:
            decoded: object = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise UpstreamScraperChangedError(
                "roundsinformation returned invalid JSON."
            ) from exc

        if not isinstance(decoded, str):
            raise UpstreamScraperChangedError(
                "roundsinformation returned JSON that is not an HTML string."
            )

        return decoded

    @staticmethod
    def _normalise_html(raw_html: str) -> str:
        return html.unescape(raw_html).replace("\xa0", " ")

    @classmethod
    def _parse_entries(
        cls,
        normalised_html: str,
        reference_date: date,
    ) -> list[CollectionEntry]:
        matches = list(_ENTRY_PATTERN.finditer(normalised_html))
        entries: list[CollectionEntry] = []

        for i, match in enumerate(matches):
            waste_type = cls._clean_text(match.group("waste_type"))
            raw_frequency = cls._clean_text(match.group("frequency")).upper()
            frequency = _parse_frequency(raw_frequency)
            day = cls._clean_text(match.group("day")).rstrip(".")
            if not waste_type or not day:
                raise UpstreamScraperChangedError(
                    "roundsinformation returned an incomplete collection entry."
                )

            segment_start = match.end()
            segment_end = (
                matches[i + 1].start() if i + 1 < len(matches) else len(normalised_html)
            )
            segment = normalised_html[segment_start:segment_end]

            next_collection, basis = cls._parse_entry_date(
                segment, frequency, day, reference_date
            )

            entries.append(
                CollectionEntry(
                    waste_type=waste_type,
                    frequency=frequency,
                    day=day,
                    next_collection=next_collection,
                    next_collection_basis=basis,
                )
            )

        return entries

    @classmethod
    def _parse_entry_date(
        cls,
        segment: str,
        frequency: str,
        day: str,
        reference_date: date,
    ) -> tuple[date | None, Literal["published", "weekday_derived"] | None]:
        exact_match = _NEXT_DATE_PATTERN.search(segment)
        if exact_match is not None:
            date_text = exact_match.group("date")
            try:
                return datetime.strptime(date_text, "%d/%m/%Y").date(), "published"
            except ValueError as exc:
                raise UpstreamScraperChangedError(
                    "roundsinformation returned an invalid next collection date."
                ) from exc

        if _NEXT_DATE_PHRASE_PATTERN.search(segment) is not None:
            raise UpstreamScraperChangedError(
                "roundsinformation returned an unparseable next collection date."
            )

        if frequency == "WEEKLY":
            derived = cls._next_weekday(day, reference_date)
            if derived is not None:
                return derived, "weekday_derived"

        return None, None

    @staticmethod
    def _next_weekday(day: str, reference_date: date) -> date | None:
        target = _WEEKDAY_NAMES.get(day.strip().lower())
        if target is None:
            return None
        days_ahead = (target - reference_date.weekday()) % 7
        return reference_date + timedelta(days=days_ahead)

    @staticmethod
    def _clean_text(value: str) -> str:
        without_tags = _TAG_PATTERN.sub(" ", value)
        return " ".join(html.unescape(without_tags).replace("\xa0", " ").split())

    def _build_drift_diagnostics(
        self,
        raw_body: str,
        error: UpstreamScraperChangedError | CollectionScheduleNotFoundError,
    ) -> ContractDriftDiagnostics:
        """Build a structured, returnable diagnostics snapshot for a drift failure.

        payload_sha256/payload_size_bytes carry no PII and are always
        included. payload_preview is included whenever the caller opted in
        via include_raw_upstream, independent of the current logger level —
        unlike logging (see _log_contract_drift), a caller inspecting
        exc.diagnostics has already made an explicit choice to receive a
        (truncated) slice of the raw payload.
        """
        preview: str | None = None
        truncated = False
        if self._include_raw_upstream and self._raw_upstream_max_chars > 0:
            preview = raw_body[: self._raw_upstream_max_chars]
            truncated = len(raw_body) > self._raw_upstream_max_chars

        encoded_body = raw_body.encode("utf-8")
        return ContractDriftDiagnostics(
            error_type=type(error).__name__,
            error_message=str(error),
            source="parser",
            payload_size_bytes=len(encoded_body),
            payload_sha256=hashlib.sha256(encoded_body).hexdigest(),
            payload_preview=preview,
            payload_truncated=truncated,
        )

    def _log_contract_drift(self, diagnostics: ContractDriftDiagnostics) -> None:
        event: dict[str, object] = {
            "payload_size_bytes": diagnostics.payload_size_bytes,
            "payload_sha256": diagnostics.payload_sha256,
            "error_type": diagnostics.error_type,
            "error_message": diagnostics.error_message,
        }
        if self._should_include_raw_upstream():
            event["payload_preview"] = diagnostics.payload_preview
            event["payload_truncated"] = diagnostics.payload_truncated

        _LOGGER.debug("parser_contract_drift", extra=event)

    def _log_empty_schedule(self, diagnostics: ContractDriftDiagnostics) -> None:
        """Emit a distinct debug event for a freshly parsed zero-entry result.

        A schedule can come back with no entries because the upstream
        contract broke, or simply because nothing is published for that
        UPRN — the parser cannot tell those apart from the HTML alone.
        Keeping a separate event name lets the host distinguish that ambiguity
        from a parse failure it knows represents contract drift.
        """
        event: dict[str, object] = {
            "payload_size_bytes": diagnostics.payload_size_bytes,
            "payload_sha256": diagnostics.payload_sha256,
        }
        if self._should_include_raw_upstream():
            event["payload_preview"] = diagnostics.payload_preview
            event["payload_truncated"] = diagnostics.payload_truncated

        _LOGGER.debug("parser_schedule_empty", extra=event)

    def _should_include_raw_upstream(self) -> bool:
        return (
            self._include_raw_upstream
            and self._raw_upstream_max_chars > 0
            and _LOGGER.isEnabledFor(logging.DEBUG)
        )
