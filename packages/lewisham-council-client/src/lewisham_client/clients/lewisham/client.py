import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import NoReturn

import httpx
import structlog

from lewisham_client.clients.lewisham.config import (
    ADDRESS_FINDER_PATH,
    BASE_URL,
    COLLECTION_PAGE_URL,
    REQUEST_TIMEOUT_SECONDS,
    ROUNDS_INFORMATION_ITEM_GUID,
    ROUNDS_INFORMATION_PATH,
    USER_AGENT,
)
from lewisham_client.clients.lewisham.models import CollectionScheduleRaw
from lewisham_client.domain.errors import (
    AddressNotFoundError,
    InvalidAddressSearchError,
    InvalidUprnError,
    UpstreamScraperChangedError,
    UpstreamUnavailableError,
)
from lewisham_client.domain.models import AddressCandidate, ContractDriftDiagnostics

logger = structlog.get_logger(__name__)


def _default_clock() -> datetime:
    return datetime.now(UTC)


class LewishamClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        base_url: str = BASE_URL,
        collection_page_url: str = COLLECTION_PAGE_URL,
        rounds_information_item_guid: str = ROUNDS_INFORMATION_ITEM_GUID,
        user_agent: str = USER_AGENT,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._http_client = http_client
        self._owns_http_client = http_client is None
        self._base_url = base_url.rstrip("/")
        self._collection_page_url = collection_page_url
        self._rounds_information_item_guid = rounds_information_item_guid
        self._user_agent = user_agent
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    async def lookup_addresses(
        self,
        postcode_or_street: str,
    ) -> list[AddressCandidate]:
        """Call AddressFinder for a postcode or street search."""

        search_text = self._validate_address_search(postcode_or_street)
        response = await self._post(
            ADDRESS_FINDER_PATH,
            endpoint_name="AddressFinder",
            params={"postcodeOrStreet": search_text, "national": "False"},
        )
        self._ensure_success(response, endpoint_name="AddressFinder")

        payload = self._read_json(response, endpoint_name="AddressFinder")
        if not isinstance(payload, list):
            self._raise_contract_drift(
                "AddressFinder returned a non-list response.",
                endpoint_name="AddressFinder",
                response=response,
            )

        return [self._parse_address_candidate(item, response) for item in payload]

    async def get_address(self, uprn: str) -> AddressCandidate:
        """Resolve a single UPRN through AddressFinder's UPRN lookup variant."""

        clean_uprn = self._validate_uprn(uprn)
        response = await self._post(
            ADDRESS_FINDER_PATH,
            endpoint_name="AddressFinder UPRN lookup",
            params={"uprn": clean_uprn},
        )
        self._ensure_success(response, endpoint_name="AddressFinder UPRN lookup")

        payload = self._read_json(
            response,
            endpoint_name="AddressFinder UPRN lookup",
        )
        if isinstance(payload, list) and not payload:
            raise AddressNotFoundError(
                f"No Lewisham address found for UPRN {clean_uprn}."
            )

        if isinstance(payload, dict) and not payload:
            raise AddressNotFoundError(
                f"No Lewisham address found for UPRN {clean_uprn}."
            )

        return self._parse_address_candidate(payload, response)

    async def get_collection_schedule(self, uprn: str) -> CollectionScheduleRaw:
        """Fetch the raw JSON-encoded Sitecore HTML schedule for one UPRN."""

        clean_uprn = self._validate_uprn(uprn)
        response = await self._post(
            ROUNDS_INFORMATION_PATH,
            endpoint_name="roundsinformation",
            params={"item": self._rounds_information_item_guid, "uprn": clean_uprn},
        )
        self._ensure_success(response, endpoint_name="roundsinformation")

        return CollectionScheduleRaw(
            uprn=clean_uprn,
            body=response.text,
            source_url=self._collection_page_url,
            fetched_at=self._clock(),
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client when this instance owns one."""

        if self._http_client is None or not self._owns_http_client:
            return

        await self._http_client.aclose()
        self._http_client = None

    async def _post(
        self,
        path: str,
        *,
        endpoint_name: str,
        params: dict[str, str],
    ) -> httpx.Response:
        start_time = perf_counter()
        logger.debug(
            "upstream_request",
            endpoint=endpoint_name,
            upstream_path=path,
        )
        try:
            response = await self._client.post(
                self._build_url(path),
                params=params,
                headers=self._headers,
            )
            logger.debug(
                "upstream_response",
                endpoint=endpoint_name,
                status_code=response.status_code,
                duration_ms=_duration_ms(start_time),
                response_size_bytes=len(response.content),
            )
            return response
        except httpx.TimeoutException as exc:
            logger.warning(
                "upstream_timeout",
                endpoint=endpoint_name,
                duration_ms=_duration_ms(start_time),
                error_type=type(exc).__name__,
            )
            raise UpstreamUnavailableError("Lewisham request timed out.") from exc
        except httpx.TransportError as exc:
            logger.warning(
                "upstream_transport_error",
                endpoint=endpoint_name,
                duration_ms=_duration_ms(start_time),
                error_type=type(exc).__name__,
            )
            raise UpstreamUnavailableError("Lewisham request failed.") from exc

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=True,
            )
            self._owns_http_client = True

        return self._http_client

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self._collection_page_url,
        }

    def _build_url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    @staticmethod
    def _validate_address_search(postcode_or_street: str) -> str:
        search_text = " ".join(postcode_or_street.replace("\xa0", " ").split())
        if len(search_text) < 3:
            raise InvalidAddressSearchError(
                "Address search must contain at least 3 non-whitespace characters."
            )

        return search_text

    @staticmethod
    def _validate_uprn(uprn: str) -> str:
        clean_uprn = uprn.strip()
        if not clean_uprn:
            raise InvalidUprnError("UPRN must be non-empty.")

        if not clean_uprn.isdecimal():
            raise InvalidUprnError("UPRN must contain only decimal digits.")

        return clean_uprn

    @staticmethod
    def _ensure_success(response: httpx.Response, *, endpoint_name: str) -> None:
        if response.status_code == 200:
            return

        if response.status_code == 500:
            message = f"{endpoint_name} returned HTTP 500 for a validated request."
        else:
            status_code = response.status_code
            message = f"{endpoint_name} returned unexpected HTTP {status_code}."

        LewishamClient._raise_contract_drift(
            message, endpoint_name=endpoint_name, response=response
        )

    @staticmethod
    def _read_json(response: httpx.Response, *, endpoint_name: str) -> object:
        try:
            return response.json()
        except ValueError as exc:
            LewishamClient._raise_contract_drift(
                f"{endpoint_name} returned invalid JSON.",
                endpoint_name=endpoint_name,
                response=response,
                cause=exc,
            )

    @staticmethod
    def _parse_address_candidate(
        payload: object, response: httpx.Response
    ) -> AddressCandidate:
        if not isinstance(payload, dict):
            LewishamClient._raise_contract_drift(
                "AddressFinder returned an address item that is not an object.",
                endpoint_name="AddressFinder",
                response=response,
            )

        uprn_value: object = payload.get("Uprn")
        title_value: object = payload.get("Title")

        if isinstance(uprn_value, bool) or not isinstance(uprn_value, int | str):
            LewishamClient._raise_contract_drift(
                "AddressFinder address item is missing a usable Uprn value.",
                endpoint_name="AddressFinder",
                response=response,
            )

        if not isinstance(title_value, str):
            LewishamClient._raise_contract_drift(
                "AddressFinder address item is missing a Title value.",
                endpoint_name="AddressFinder",
                response=response,
            )

        uprn = str(uprn_value).strip()
        title = " ".join(title_value.replace("\xa0", " ").split())
        if not uprn or not title:
            LewishamClient._raise_contract_drift(
                "AddressFinder returned an address item with empty fields.",
                endpoint_name="AddressFinder",
                response=response,
            )

        return AddressCandidate(uprn=uprn, title=title)

    @staticmethod
    def _raise_contract_drift(
        message: str,
        *,
        endpoint_name: str,
        response: httpx.Response,
        cause: BaseException | None = None,
    ) -> NoReturn:
        """Log and raise UpstreamScraperChangedError with diagnostics attached.

        The single raise point for every upstream contract-drift failure in
        this client, so every drift raise site — present and future — gets a
        ContractDriftDiagnostics for free instead of needing its own opt-in.
        """
        logger.error(
            "upstream_contract_drift",
            endpoint=endpoint_name,
            status_code=response.status_code,
            response_size_bytes=len(response.content),
        )
        error = UpstreamScraperChangedError(
            message,
            diagnostics=ContractDriftDiagnostics(
                error_type="UpstreamScraperChangedError",
                error_message=message,
                source="client",
                status_code=response.status_code,
                endpoint=endpoint_name,
                payload_size_bytes=len(response.content),
                payload_sha256=hashlib.sha256(response.content).hexdigest(),
            ),
        )
        if cause is not None:
            raise error from cause
        raise error


def _duration_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 2)
