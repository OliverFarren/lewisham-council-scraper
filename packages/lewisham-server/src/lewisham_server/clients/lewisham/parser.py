import html
import json
import re
from datetime import date, datetime

from lewisham_server.clients.lewisham.models import ParsedCollectionSchedule
from lewisham_server.domain.errors import (
    CollectionScheduleNotFoundError,
    UpstreamScraperChangedError,
)
from lewisham_server.domain.models import CollectionEntry

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


class LewishamParser:
    """Parse Lewisham's JSON-encoded Sitecore schedule HTML."""

    def parse_collection_schedule(self, raw_body: str) -> ParsedCollectionSchedule:
        """Return structured collection entries from a roundsinformation response."""

        decoded_html = self._decode_json_html(raw_body)
        normalised_html = self._normalise_html(decoded_html)
        collections = self._parse_entries(normalised_html)
        if not collections:
            raise CollectionScheduleNotFoundError(
                "Lewisham returned no collection entries for this UPRN."
            )

        return ParsedCollectionSchedule(
            collections=collections,
            next_collection=self._parse_next_collection(normalised_html),
        )

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
    def _parse_entries(cls, normalised_html: str) -> list[CollectionEntry]:
        entries: list[CollectionEntry] = []
        for match in _ENTRY_PATTERN.finditer(normalised_html):
            waste_type = cls._clean_text(match.group("waste_type"))
            frequency = cls._clean_text(match.group("frequency")).upper()
            day = cls._clean_text(match.group("day")).rstrip(".")
            if not waste_type or not frequency or not day:
                raise UpstreamScraperChangedError(
                    "roundsinformation returned an incomplete collection entry."
                )

            entries.append(
                CollectionEntry(
                    waste_type=waste_type,
                    frequency=frequency,
                    day=day,
                )
            )

        return entries

    @classmethod
    def _parse_next_collection(cls, normalised_html: str) -> date | None:
        exact_match = _NEXT_DATE_PATTERN.search(normalised_html)
        if exact_match is None:
            phrase_match = _NEXT_DATE_PHRASE_PATTERN.search(normalised_html)
            if phrase_match is None:
                return None

            raise UpstreamScraperChangedError(
                "roundsinformation returned an unparseable next collection date."
            )

        date_text = exact_match.group("date")
        try:
            return datetime.strptime(date_text, "%d/%m/%Y").date()
        except ValueError as exc:
            raise UpstreamScraperChangedError(
                "roundsinformation returned an invalid next collection date."
            ) from exc

    @staticmethod
    def _clean_text(value: str) -> str:
        without_tags = _TAG_PATTERN.sub(" ", value)
        return " ".join(html.unescape(without_tags).replace("\xa0", " ").split())
