from lewisham_client.domain.models import ContractDriftDiagnostics


class DomainError(Exception):
    """Base class for application-level failures.

    diagnostics carries a structured snapshot of an upstream contract-drift
    failure (payload hash/size, an opt-in raw preview, and/or the offending
    HTTP status/endpoint) when the failure occurred while parsing or
    requesting a payload. It defaults to None and is set by LewishamParser
    and LewishamClient on the specific errors they raise for drift; other
    DomainError subclasses (e.g. validation errors) simply never populate it.
    It lives on the base class, not on individual subclasses, so callers can
    always do `error.diagnostics` without needing to know which concrete
    DomainError subtype they caught.
    """

    def __init__(
        self,
        *args: object,
        diagnostics: ContractDriftDiagnostics | None = None,
    ) -> None:
        super().__init__(*args)
        self.diagnostics = diagnostics


class _ValueErrorDomainError(ValueError, DomainError):
    """Shared base for DomainError subclasses that also need to be a ValueError.

    Why be both? InvalidAddressSearchError and InvalidUprnError are bad-input
    errors, so it's useful for callers to catch them as a plain ValueError
    without knowing about this library — but they should also be catchable as
    a DomainError like every other error we raise, so `error.diagnostics` is
    always available.

    Why the explicit __init__ below, instead of just inheriting one? When a
    class has two parents like this, Python has to pick which parent's
    __init__ actually runs. We tested this directly: on CPython 3.12 and
    3.13, Python picks ValueError's __init__ — which doesn't know about our
    `diagnostics` argument and raises a confusing "unexpected keyword
    argument" error. (On 3.14 it happens to pick the right one, because
    ValueError and Exception share the same __init__ there — but we can't
    rely on that being true for every Python version.) So instead of letting
    Python choose, we call DomainError.__init__ ourselves to guarantee
    `diagnostics` is always handled correctly.
    """

    def __init__(
        self,
        *args: object,
        diagnostics: ContractDriftDiagnostics | None = None,
    ) -> None:
        DomainError.__init__(self, *args, diagnostics=diagnostics)


class InvalidAddressSearchError(_ValueErrorDomainError):
    """Raised when an address search input is unsafe to send upstream."""


class InvalidUprnError(_ValueErrorDomainError):
    """Raised when a UPRN value is structurally invalid."""


class AddressNotFoundError(DomainError):
    """Raised when no address can be resolved for the requested input."""


class CollectionScheduleNotFoundError(DomainError):
    """Raised when a property has no parseable public collection schedule.

    This can happen for two different reasons that look identical to the
    parser: the address genuinely has nothing published, or the page's shape
    changed and broke parsing. Since the parser can't tell those apart, both
    cases still get a diagnostics snapshot attached. Applications can use that
    snapshot to distinguish a fresh parser result from a negative-cache hit and
    decide how visibly to report it.

    diagnostics is None only when this error came from the negative cache
    instead — i.e. a repeat lookup that never touched the parser at all.
    """


class UpstreamScraperChangedError(DomainError):
    """Raised when Lewisham's response contract no longer matches expectations.

    diagnostics carries structured drift detail (payload hash/size, an
    opt-in truncated preview, and/or the offending HTTP status/endpoint) so
    callers can build rich failure reports without intercepting log output.
    """


class UpstreamUnavailableError(DomainError):
    """Raised when Lewisham cannot be reached reliably."""


def find_diagnostics(error: BaseException) -> ContractDriftDiagnostics | None:
    """Walk an exception's chain for the first attached diagnostics.

    If a consumer catches one of our errors and wraps it in their own
    exception type, they lose direct access to `.diagnostics`. This walks
    back through "what caused what" to recover it, so the consumer doesn't
    have to reimplement that walk themselves.

    Python links a wrapping exception back to the original one of two ways:
    explicitly, via `raise NewError(...) from original_error`, or
    implicitly, just by raising a new exception inside an `except:` block
    without `from`. This function follows either kind of link — preferring
    the explicit one when both are present, since that's the more deliberate
    signal — and stops early if the link was intentionally cut with
    `raise ... from None`. It also stops if it ever loops back to an
    exception already seen, rather than getting stuck.
    """
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, DomainError) and current.diagnostics is not None:
            return current.diagnostics
        if current.__cause__ is not None:
            current = current.__cause__
        elif current.__suppress_context__:
            current = None
        else:
            current = current.__context__
    return None
