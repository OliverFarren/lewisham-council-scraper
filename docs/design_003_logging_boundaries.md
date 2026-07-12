---
title: Logging Across Application and Library Boundaries
description: Why structured logging remains useful in the optional server, why the reusable client must defer to its host, and which layer should report an operation's outcome.
created: 2026-07-04
status: accepted
---

# Logging Across Application and Library Boundaries

## Relationship to Design 002

[Design 002](design_002_client_first_architecture.md) changed the centre of the
project. Code that originally ran only inside a FastAPI service became a
reusable Python client that could also run inside the
[Home Assistant integration](https://github.com/OliverFarren/lewisham-council-bins-home-assistant)
and other applications.

That change created a logging boundary which Design 002 did not discuss. The
server owns its process and can choose how that process writes logs. The client
runs inside a process owned by somebody else. It can provide diagnostic
events, but it cannot assume that it controls their formatting, destination, or
visibility.

This document records how that distinction affects
`lewisham-council-client`, `lewisham-server`, and the Home Assistant
integration.

## What the existing logging design provides

The original logging design was created for a self-hosted API service. A
developer might run the service as a container on a NAS and inspect it with:

```bash
docker logs lewisham-server
```

The same developer might already collect container output with Fluentd,
Promtail, or another log router and send it to Elasticsearch or a similar
system. The server therefore supports two representations of the same events.
An environment variable selects readable terminal output or JSON:

```bash
LEWISHAM_SERVER_LOG_FORMAT=text
LEWISHAM_SERVER_LOG_FORMAT=json
```

The text representation is suitable for direct inspection:

```text
2026-06-26T12:00:00Z [info     ] http_request                   method=GET route=/bins/{uprn}/collections status_code=200 duration_ms=45.2
```

The JSON representation gives a log collector stable fields to index:

```json
{
  "method": "GET",
  "route": "/bins/{uprn}/collections",
  "status_code": 200,
  "duration_ms": 45.2,
  "event": "http_request",
  "level": "info",
  "timestamp": "2026-06-26T12:00:00Z"
}
```

This remains useful. It follows the common service pattern of writing an event
stream to standard output while leaving storage and routing to the execution
environment. The [Twelve-Factor App guidance on
logs](https://12factor.net/logs) describes both direct terminal inspection and
routing through systems such as Fluentd.

`structlog` is a good fit at this layer. The server owns:

- The choice between text and JSON.
- The process-wide logging level.
- The stdout and stderr handlers.
- Privacy filtering for addresses, UPRNs, and raw upstream content.
- Application events such as startup, shutdown, and HTTP request completion.

The decision in this document preserves those capabilities.

## How the boundary moved

The repository history explains how the current behaviour arose.

Structured logging was added on 26 June 2026. At that point, the upstream
client, parser, service, and FastAPI routes all lived inside
`lewisham-server`. A single application owned both the event calls and the
logging configuration.

The reusable client package was extracted on 28 June 2026 as part of the
client-first architecture. The extraction moved the existing event calls into
`lewisham-council-client` and added `structlog` to that package's dependencies.
This preserved the server's behaviour because the server configures structlog
when it starts.

It also changed an important assumption. The same client could now be imported
by a process that had never configured structlog.

## The concrete failure outside the server

At the time of this decision, the client created its module loggers like this:

```python
import structlog

logger = structlog.get_logger(__name__)
```

When `lewisham-server` starts, its `configure_logging()` function tells
structlog to send events through Python's standard logging system. The server
then applies its own levels, processors, handlers, renderers, and privacy
filter.

That configuration does not exist when the client is used directly. A local
probe with an in-memory source performed one successful address lookup. No
logging configuration was installed. The operation printed four lines:

```text
2026-07-04 11:48:18 [debug    ] cache_miss                     namespace=address_search
2026-07-04 11:48:18 [debug    ] cache_store                    cache_type=positive candidate_count=1 namespace=address_search
2026-07-04 11:48:18 [debug    ] cache_store                    cache_type=positive namespace=address
2026-07-04 11:48:18 [info     ] address_lookup_completed       candidate_count=1
```

The `DEBUG` events are significant. A host application normally expects its
logging level to suppress them. These events were written by structlog's
fallback output instead, so the host never received a standard
`logging.LogRecord` to filter.

The [structlog standard-library
documentation](https://www.structlog.org/en/stable/standard-library.html)
supports forwarding structlog events through Python logging. It also notes that
`structlog.stdlib.get_logger()` does not configure or verify that integration.
The application still has to install the configuration.

The client cannot safely install it. Configuring structlog from an embedded
library would change process-wide behaviour for the host and for unrelated
libraries.

## Why Home Assistant made the problem visible

Home Assistant embeds `lewisham-council-client` directly. It already owns its
HTTP session, polling schedule, retry state, entity availability, and logging
configuration.

Its `DataUpdateCoordinator` also owns an important user-facing behaviour. When
the upstream service becomes unavailable, the coordinator reports that
transition once. When the service recovers, it reports the recovery once.
Repeated polling failures should not produce repeated warnings.

Before this decision was implemented, the client logged a transport failure
before raising it:

```python
except httpx.TransportError as exc:
    logger.warning(
        "upstream_transport_error",
        endpoint=endpoint_name,
        duration_ms=_duration_ms(start_time),
        error_type=type(exc).__name__,
    )
    raise UpstreamUnavailableError("Lewisham request failed.") from exc
```

The Home Assistant coordinator then translates the typed exception:

```python
except UpstreamUnavailableError as err:
    raise _update_failed("schedule_unavailable", error=str(err)) from err
```

The result is more than a formatting problem. The client reports the failure,
then the coordinator reports the same failed operation according to Home
Assistant's retry policy. During setup retries this bypasses the host's
intended suppression entirely.

Home Assistant's [availability logging
rule](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/log-when-unavailable/)
states that coordinator integrations should raise `UpdateFailed` and use the
coordinator's built-in log-once behaviour. Its [setup failure
guidance](https://developers.home-assistant.io/docs/integration_setup_failures/)
also says that integrations should not emit additional non-debug messages for
a retry.

Home Assistant did not create the architectural issue. It provided a second
host with sufficiently different operational rules to expose it.

## What common Python practice tells us

There is no general rule that a library may only emit `DEBUG` events.

Python's logging levels give `INFO` a legitimate meaning: confirmation that an
operation is working as expected. HTTPX is one established example. Its
high-level `httpx` logger records a completed HTTP request at `INFO`, while
`httpcore` records connection and protocol details at `DEBUG`. The [HTTPX
logging documentation](https://www.python-httpx.org/logging/) exposes both and
lets the host configure them separately.

There is a clearer convention about configuration. Python's [guidance for
library authors](https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library)
recommends named standard-library loggers and leaves handlers to the
application developer. The application knows whether the destination is a
terminal, a file, a container stream, a test capture, or an external system.

There is also useful guidance about failures. The same Python documentation
distinguishes between two cases:

- Report an operation's failure by raising an exception.
- Use error-level logging when an error is handled or suppressed.

These are conventions rather than mechanical rules. An intermediate layer may
have unique context that deserves recording before an exception escapes. It
should first consider whether that context can travel with the exception. In
this project, `DomainError.diagnostics` already carries contract-drift details
such as the endpoint, payload size, and payload hash. A host can therefore
decide how to report the failure without scraping a lower-level log message.

The lesson from the mixed practice is that level names alone do not decide the
design. The purpose of the event and the responsibility of the layer matter
more.

## Four kinds of event in this project

The current events become easier to place when separated by purpose.

### Diagnostic trace

A diagnostic trace explains how an operation was performed. Examples include
cache hits, cache misses, upstream request timing, response size, and parser
decisions.

These events are mainly useful while investigating a problem. They belong at
`DEBUG`.

### Domain outcome

A domain outcome explains what the Lewisham operation produced. Examples
include the number of address candidates or collection entries.

This may be useful at `INFO` in the API service. It is not necessarily useful
as a visible event in every process that imports the client.

### Access event

An access event describes an inbound HTTP transaction. The server's
`http_request` event records the route template, response status, and duration.
It answers a different question from a domain outcome.

For example, these two events are related but not duplicates:

```json
{"event":"schedule_lookup_completed","collection_count":3,"level":"info"}
{"event":"http_request","route":"/bins/{uprn}/collections","status_code":200,"duration_ms":45.2,"level":"info"}
```

The first describes the work. The second describes the HTTP delivery of that
work. A log collector may aggregate them differently.

### Operational failure

An operational failure describes an outcome that needs attention. The correct
severity depends on what the application does with it.

A contract change is an error for the API service because the service cannot
fulfil its request. Temporary upstream unavailability is a warning because a
later request may recover. Home Assistant has a more specific model because it
tracks unavailable and recovered states over time.

## Decision: the client uses standard-library logging

**Decided: `lewisham-council-client` will create named log records with
Python's standard `logging` package. It will not configure handlers,
formatters, destinations, or process-wide levels.**

The concrete client pattern is:

```python
import logging

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug(
    "cache_miss",
    extra={"namespace": "schedule"},
)
```

The event name remains stable. Structured fields remain attached to the
`LogRecord` through `extra`. A simple host may render only the message. A
structured host may copy the extra fields into JSON.

This removes the client's runtime dependency on structlog. More importantly,
it makes the client participate in the host's existing logging hierarchy.

## Decision: existing client events become diagnostic

**Decided: the client's existing cache, request, response, completion, missing
result, transport failure, and contract-drift events will be emitted at
`DEBUG`. A failure that is raised to the caller will not also produce a
non-debug event from the client.**

This is not a permanent ban on higher-severity library events.

A future client condition may deserve `WARNING` if all of the following are
true:

1. The client handles the condition internally.
2. The caller still receives a normal result.
3. The condition may affect correctness, performance, or future reliability.
4. The caller has no other way to observe it.

For example, discarding a corrupt cache entry and successfully fetching fresh
data could meet those conditions. A network error that becomes
`UpstreamUnavailableError` does not. The caller already receives the failure
and owns the next decision.

## Decision: applications own visible operational events

**Decided: each application will assign user-visible severity when it turns a
client result or exception into an application outcome.**

For `lewisham-server`, the relevant boundary is the FastAPI adapter. It turns a
domain result into a response schema and a domain exception into an HTTP
response.

The server will retain these domain events:

| Event | Level | Reason |
| --- | --- | --- |
| `address_lookup_completed` | `INFO` | Records the number of candidates returned by a successful API operation. |
| `schedule_lookup_completed` | `INFO` | Records collection count and safe schedule provenance for a successful API operation. |
| `upstream_unavailable` | `WARNING` | The server could not complete the request, but the condition may be temporary. |
| `parser_schedule_empty` | `WARNING` | A fresh response contained no parseable entries and may represent either a genuinely empty schedule or upstream drift. |
| `upstream_contract_drift` | `ERROR` | The server cannot satisfy its contract because the upstream response no longer matches the client. |
| `unhandled_exception` | `ERROR` | An unexpected exception escaped the application's normal error mapping. |

Expected client input and lookup outcomes do not need a second domain event:

- `InvalidAddressSearchError` and `InvalidUprnError` become HTTP 400 responses.
- `AddressNotFoundError` becomes an HTTP 404 response.
- A cached negative schedule result becomes an HTTP 404 response.

The `http_request` access event records those statuses.

A freshly parsed empty schedule is slightly different from a cached negative
result. The fresh `CollectionScheduleNotFoundError` carries parser diagnostics.
The cached error does not. The server can use that distinction to emit
`parser_schedule_empty` for the fresh observation without repeating it for
every cache hit.

The server will continue to emit one access event for each HTTP request. A
domain event and an access event may both exist because they describe
different facts. The client will not add a third visible report of the same
operation.

## Decision: the server retains structlog

**Decided: `lewisham-server` will continue to use structlog for application
events, privacy filtering, and text or JSON rendering.**

The server already configures standard logging and structlog through one
`ProcessorFormatter` pipeline. Standard-library records from the client can
enter the same pipeline.

To preserve values supplied through `logging`'s `extra` argument, the server's
foreign-record processor chain must include:

```python
structlog.stdlib.ExtraAdder()
```

The server's existing `redact_log_fields` processor remains authoritative.
Structured fields from either logging API pass through the same allowlist and
sensitive-field handling before rendering.

Raw upstream previews remain subject to two separate controls. The operator
must explicitly enable `LEWISHAM_SERVER_LOG_INCLUDE_RAW_UPSTREAM`, and the
server logger must be enabled for `DEBUG`. A warning or error event may include
the payload size and SHA-256 at normal levels, but it must not include the
preview unless both controls permit it. Moving the event to the application
boundary does not weaken the existing privacy gate.

This arrangement keeps structlog where its process-wide capabilities are
useful. It does not require every library imported by the server to depend on
structlog.

## Behaviour in each runtime

The accepted decisions above produce the following behaviour. The probe shown
earlier records the behaviour before the change.

### Direct client use

Importing and calling the client without logging configuration produces no
routine console output. The caller receives return values or typed
`DomainError` exceptions.

A developer can enable diagnostics with standard logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("lewisham_client").setLevel(logging.DEBUG)
```

### Dockerised API service

The server continues to select text or JSON output from its environment
configuration. It emits high-value domain outcomes, access events, lifecycle
events, and operational failures. Client internals appear when the server log
level is set to `DEBUG`.

Container users may inspect the same stream directly or send it to a log
router. No client-specific logging setup is required.

### Home Assistant

The client passes standard records into Home Assistant's logging hierarchy.
Routine client details remain at `DEBUG`.

Typed client exceptions are translated into Home Assistant exceptions.
`DataUpdateCoordinator` owns the unavailable and recovered transitions, so
retries follow Home Assistant's log-once behaviour.

Contract-drift diagnostics remain available on the exception chain and through
the integration's downloadable diagnostics. Home Assistant decides whether
and how to expose them.

### Future adapters

A future MCP adapter or command-line application receives the same choice. It
can ignore diagnostic records, render them with standard logging, or route
them through its own structured logging system.

The client does not require the adapter to adopt the server's presentation
policy.

## Alternatives considered

### Keep structlog in the client and require every host to configure it

This preserves the current event-call syntax and works inside
`lewisham-server`. It makes correct behaviour depend on undocumented startup
work in every other host. A library cannot assume that Home Assistant or an
unrelated Python application uses structlog.

### Configure structlog when the client is imported

This would prevent the fallback output, but it would let a reusable library
modify global logging policy. It could alter unrelated structlog users in the
same process. Importing the client should not have that side effect.

### Configure or replace the client loggers inside Home Assistant

An integration-specific shim could suppress the current output or replace the
three module loggers. It would depend on private implementation details and
would leave the same issue for other consumers.

### Inject a logger through every client, parser, and service constructor

Logger injection gives each host explicit control and can support non-standard
logging APIs. It also expands several public constructors and makes logging a
dependency of object assembly.

No current consumer needs that flexibility. Named standard-library loggers
already provide host control. Injection can be reconsidered if a real consumer
cannot integrate through standard logging.

### Remove client logging entirely

This avoids output conflicts but loses useful cache, transport, and parser
diagnostics. Standard-library `DEBUG` records retain that evidence without
making it visible by default.

### Keep the current event levels after switching to standard logging

This would restore host filtering, but it would still make the client decide
that every successful lookup is an application-level `INFO` event. It would
also retain warning and error events immediately before typed exceptions are
raised.

That policy is valid for some libraries. HTTPX demonstrates that routine
`INFO` events can be useful. It is not the best fit here because this client is
embedded in hosts with different polling, retry, and availability models.

## Consequences

The client becomes easier to embed because it no longer assumes a logging
framework or writes routine events directly.

The server keeps its text and JSON output, privacy controls, and operational
event model. Some high-level events move from the client package to the server
adapter because the server is the layer that assigns their visible meaning.
