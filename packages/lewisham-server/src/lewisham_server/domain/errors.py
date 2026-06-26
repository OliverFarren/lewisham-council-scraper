class DomainError(Exception):
    """Base class for application-level failures."""


class InvalidAddressSearchError(ValueError, DomainError):
    """Raised when an address search input is unsafe to send upstream."""


class InvalidUprnError(ValueError, DomainError):
    """Raised when a UPRN value is structurally invalid."""


class AddressNotFoundError(DomainError):
    """Raised when Lewisham cannot resolve an address for the requested input."""


class CollectionScheduleNotFoundError(DomainError):
    """Raised when a property has no parseable public collection schedule."""


class UpstreamScraperChangedError(DomainError):
    """Raised when Lewisham's response contract no longer matches expectations."""


class UpstreamUnavailableError(DomainError):
    """Raised when Lewisham cannot be reached reliably."""
