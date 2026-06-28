# lewisham-server

FastAPI REST adapter over `lewisham-council-client`. Exposes Lewisham Council civic
data over HTTP. Useful when a non-Python consumer needs the data, or when
several independent processes should share one upstream cache.

## Routes

```
GET /addresses?query={postcode_or_street}
```

Returns address candidates with UPRNs for a postcode or street search.

```json
[
  { "uprn": "100000000001", "title": "1 Example Street, Catford, SE6 1SQ, London" }
]
```

---

```
GET /bins/{uprn}/collections
```

Returns the parsed waste collection schedule for one Lewisham UPRN.

```json
{
  "uprn": "100000000001",
  "address": "1 Example Street, Catford, SE6 1SQ, London",
  "collections": [
    {
      "waste_type": "Refuse",
      "frequency": "FORTNIGHTLY",
      "day": "Thursday",
      "next_collection": "2026-07-03",
      "next_collection_basis": "published"
    },
    {
      "waste_type": "Recycling",
      "frequency": "WEEKLY",
      "day": "Thursday",
      "next_collection": "2026-07-03",
      "next_collection_basis": "weekday_derived"
    }
  ],
  "source_url": "https://lewisham.gov.uk/myservices/recycling-and-rubbish/your-bins/collection",
  "fetched_at": "2026-06-26T12:00:00Z"
}
```

`next_collection_basis` is `"published"` when Lewisham explicitly stated the
date, or `"weekday_derived"` when it was computed as the next occurrence of the
collection weekday. It is `null` for fortnightly streams without a published
anchor date, in which case `next_collection` is also `null`.

## Configuration

Runtime behaviour is controlled entirely by environment variables. The
`LEWISHAM_SERVER_` prefix is used for all service-specific variables. `PORT` is
also accepted because many container platforms inject it automatically.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LEWISHAM_SERVER_HOST` | `0.0.0.0` | Bind host for the bundled uvicorn runner. |
| `LEWISHAM_SERVER_PORT` | `8000` | Bind port. Takes precedence over `PORT`. |
| `PORT` | `8000` | Common platform port fallback. |
| `LEWISHAM_SERVER_LOG_LEVEL` | `info` | Log level: `trace`, `debug`, `info`, `warning`, `error`, `critical`. |
| `LEWISHAM_SERVER_LOG_FORMAT` | `text` | Log renderer: `text` for terminals, `json` for aggregators. |
| `LEWISHAM_SERVER_LOG_INCLUDE_RAW_UPSTREAM` | `false` | Include truncated upstream payload previews in parser drift logs. Requires debug logging. |
| `LEWISHAM_SERVER_LOG_RAW_UPSTREAM_MAX_CHARS` | `4096` | Maximum characters in opt-in upstream payload previews. |
| `LEWISHAM_SERVER_UPSTREAM_BASE_URL` | `https://lewisham.gov.uk` | Lewisham upstream origin. |
| `LEWISHAM_SERVER_UPSTREAM_COLLECTION_PAGE_URL` | Lewisham bin collection page | Public page that backs the scraped endpoint. |
| `LEWISHAM_SERVER_UPSTREAM_ROUNDS_INFORMATION_ITEM_GUID` | Sitecore item GUID | Sitecore rendering ID for the rounds-information endpoint. See spike findings if this needs updating. |
| `LEWISHAM_SERVER_UPSTREAM_USER_AGENT` | `lewisham-council-scraper/0.1` | User-Agent sent to Lewisham. |
| `LEWISHAM_SERVER_UPSTREAM_REQUEST_TIMEOUT_SECONDS` | `10.0` | Outbound request timeout in seconds. |
| `LEWISHAM_SERVER_CACHE_SCHEDULE_TTL_SECONDS` | `86400` | Collection schedule cache TTL (24 h). |
| `LEWISHAM_SERVER_CACHE_ADDRESS_SEARCH_TTL_SECONDS` | `604800` | Address search results cache TTL (7 d). |
| `LEWISHAM_SERVER_CACHE_UPRN_TTL_SECONDS` | `2592000` | Resolved UPRN cache TTL (30 d). |
| `LEWISHAM_SERVER_CACHE_NEGATIVE_TTL_SECONDS` | `3600` | Negative result cache TTL (1 h). |

## Logging

Logs are split by severity across the container streams: `DEBUG` and `INFO` go
to stdout, `WARNING` and above go to stderr. Uvicorn access logs are suppressed
in favour of one sanitised `http_request` event per request.

By default, logs do not include UPRNs, addresses, postcode queries, client IPs,
or raw upstream response bodies.

Text format (for terminals):

```
2026-06-26T12:00:00Z [info     ] http_request                   method=GET route=/bins/{uprn}/collections status_code=200 duration_ms=45.2
```

JSON format (for log aggregators such as Vector, Promtail, or ELK):

```json
{"method":"GET","route":"/bins/{uprn}/collections","status_code":200,"duration_ms":45.2,"event":"http_request","level":"info","timestamp":"2026-06-26T12:00:00Z"}
```

If Lewisham changes its response shape and a `parser_contract_drift` error
appears, enable the payload preview temporarily to capture a failing response:

```bash
LEWISHAM_SERVER_LOG_LEVEL=debug
LEWISHAM_SERVER_LOG_INCLUDE_RAW_UPSTREAM=true
```

The drift log includes payload size, SHA-256, and a truncated preview suitable
for filing a bug report. Turn the raw payload option off after capturing the
response.

## Running

```bash
# Development (hot reload)
make server-dev

# Production entrypoint
make server

# Docker
make docker-build-server
docker run -p 8000:8000 lewisham-server
```
