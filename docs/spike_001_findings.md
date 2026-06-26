---
title: Spike Findings — Scraping Lewisham Website
description: Results of spike_001_scraping_lewisham_website investigation.
created: 2026-06-26
status: complete
---

# Spike Findings — Scraping Lewisham Website

## Key finding: the form is backed by an internal AJAX API

The bin collection page at lewisham.gov.uk is a Sitecore Experience Form. Through inspection of the JavaScript bundle and browser DevTools, the spike found that when a user submits the form the browser makes two undocumented internal AJAX calls — one to look up addresses by postcode and one to fetch the collection schedule for a given property. These endpoints are not a published public API; they are internal plumbing that the website's own JavaScript happens to call.

This finding directly answers the question of whether Playwright is needed. **Because there is a callable API surface, the scraping approach shifts from browser automation (rendering the page and simulating user interaction) to reverse-engineering the internal API calls.** The Sitecore form layer and all of its session management complexity can be bypassed entirely.

The endpoints are undocumented and carry no stability guarantee. They may change if Lewisham Council restructures the page, upgrades their CMS, or changes their hosting infrastructure. The scraper should be designed to detect breakage quickly — unexpected status codes or response structure changes should surface as clear errors rather than silent failures or stale data.

## Decision

**Use direct HTTP with `httpx`. Playwright is not required for production.**

Both endpoints are stateless and callable without cookies, a session, or any prior form submission.

## Confirmed production flow

```
1. POST /api/AddressFinder?postcodeOrStreet={postcode_or_street}&national=False
   → JSON array of { "Uprn": int, "Title": string }

2. POST /api/roundsinformation?item={23423835-d2a6-41b1-9637-29e5e8cc2df7}&uprn={uprn}
   → application/json; charset=utf-8
   → body is a JSON-encoded HTML string
```

Neither call requires cookies, a session, or a prior form submission.

## AddressFinder — observed behaviour

**Request:**
```
POST https://lewisham.gov.uk/api/AddressFinder?postcodeOrStreet={value}&national=False
```

**Response (200, JSON array):**
```json
[
  { "Uprn": 100000000000, "Title": "1, Example Street, Catford, SE6 1SQ, London" }
]
```
*(Values anonymised — real UPRN and address withheld per spike security constraints.)*

`national=False` (the default on the page) limits results to Lewisham addresses.  
`national=True` returns UK-wide results for the same input.

**UPRN lookup variant:**
```
POST /api/AddressFinder?uprn={uprn}
```
Returns a single `{ "Uprn": int, "Title": string }` object for a known UPRN.

**Failure modes:**

| Input | Status | Result |
|---|---|---|
| Valid Lewisham postcode | 200 | Array of addresses |
| Valid non-Lewisham postcode (`national=False`) | 200 | Empty array `[]` |
| Street name (e.g. `Abbotshall Road`) | 200 | Array of addresses |
| Unrecognised string (e.g. `INVALID`) | 200 | Empty array `[]` |
| Empty string | 500 | HTML 500 page |
| Partial postcode (e.g. `SE6`) | 500 | HTML 500 page |

Input must be validated before calling: empty and very short inputs should be rejected before the HTTP call is made.

## roundsinformation — observed behaviour

**Request:**
```
POST https://lewisham.gov.uk/api/roundsinformation?item={23423835-d2a6-41b1-9637-29e5e8cc2df7}&uprn={uprn}
```

**Response (200):**
- `Content-Type: application/json; charset=utf-8`
- Body: a JSON-encoded string whose content is an HTML fragment

**Example decoded HTML (residential address, anonymised):**
```html
<h2>When your bins are collected:</h2>
<strong>Food waste</strong>&nbsp;is collected <span class="RoundsTransform">WEEKLY</span> on Thursday.
<br><br>
<strong>Recycling</strong>&nbsp;is collected <span class="RoundsTransform">WEEKLY</span> on Thursday.
<br><br>
<strong>Refuse</strong>&nbsp;is collected <span class="RoundsTransform">FORTNIGHTLY</span> on Thursday.
Your next collection date is 02/07/2026.
<br><br>
<p>If you think the above is incorrect or is missing <a href="https://lewisham.gov.uk/web-problems/bins-collection">please notify us</a></p>
```

The response structure uses the same HTML for every UPRN. The collection schedule is embedded as plain text and `<span class="RoundsTransform">` elements.

**Failure modes:**

| Input | Status | Result |
|---|---|---|
| Valid residential UPRN | 200 | HTML with collection schedule |
| Valid civic/commercial UPRN | 200 | HTML with partial or no domestic schedule |
| Invalid or non-existent UPRN (e.g. `0`, `99999999999`) | 200 | Empty schedule HTML (just the report link, no collection entries) |
| Empty UPRN string | 500 | HTML 500 page |
| Missing `uprn` parameter | 404 | HTML 404 page |
| Missing `item` parameter | 404 | HTML 404 page |

An invalid UPRN does not produce an error status. The parser must detect a schedule HTML that contains no collection entries and treat it as an `AddressNotFoundError` or equivalent.

## The `item` parameter

The `item` value `{23423835-d2a6-41b1-9637-29e5e8cc2df7}` is a Sitecore item GUID for the rounds-information rendering component on the bin collection page.

**How it was found:** The Sitecore formbuilder renders a `<div class="js-find-collection-result" data-item="{23423835-d2a6-41b1-9637-29e5e8cc2df7}">` element in the AJAX form response, after a UPRN is submitted. The JavaScript module that calls `roundsinformation` reads this `data-item` attribute at runtime. The element is not present in the static page HTML.

**Stability:** This GUID is a Sitecore content item that identifies the page component. It will not change between user sessions or daily requests. It could change if a Lewisham content editor moves, republishes, or replaces the component. If `roundsinformation` starts returning unexpected results or errors, re-checking this value using the browser DevTools method below should be the first diagnostic step.

**To re-discover `data-item` via browser:**
1. Open https://lewisham.gov.uk/myservices/recycling-and-rubbish/your-bins/collection
2. Enter a Lewisham postcode and select any address.
3. Open browser DevTools → Elements.
4. Find the element with class `js-find-collection-result`.
5. Read its `data-item` attribute.

Braces are optional: both `{23423835-...}` and `23423835-...` work.

## Civic and non-residential UPRNs

Public buildings can be found by the AddressFinder but typically return only commercial collection types (e.g. Recycling) without domestic collections (Food waste, Refuse) and without a next collection date. This is expected behaviour, not a scraper failure.

Example: a civic building in SE6 1SQ returns Recycling only.

Public buildings are still useful for AddressFinder smoke testing.

## Collection data schema — parsed from HTML

The HTML fragment should be parsed to produce structured collection data. The relevant patterns:

- Collection entry: `<strong>{type}</strong>&nbsp;is collected <span class="RoundsTransform">{frequency}</span> on {day}.`
- Waste types observed: `Food waste`, `Recycling`, `Refuse`, `Garden waste`
- Frequencies observed: `WEEKLY`, `FORTNIGHTLY`
- Day: plain text following "on" (e.g. `Thursday`)
- Next collection date: `Your next collection date is {DD/MM/YYYY}.`
  - Date format is `DD/MM/YYYY`, not ISO 8601 — normalise to `YYYY-MM-DD` for the API response
- Report link: `https://lewisham.gov.uk/web-problems/bins-collection` (not useful to surface in the API)

Garden waste does not appear for all residential properties — it depends on subscription state. The parser should handle zero or more entries per type.

Bank holiday and service alert handling is unknown. The next collection date likely reflects any bank holiday delay, but no separate alert field was observed in any test response.

## What was investigated but not needed

**Sitecore formbuilder (`POST /formbuilder`):** Investigated extensively. Returns 400 when the `FormSessionId` hidden field from the initial page is included. This appears to be a consequence of the server using machine-key-encrypted form tokens that are only valid on the server instance that rendered the page — a load-balancer / state-sharding problem. The form submission is not needed for the production scraper. The only reason to revisit it would be to re-discover the `item` GUID after a site change, which is easier to do via browser.

**Playwright:** Explored as a fallback for the form session issue. Not needed given the stateless endpoint discovery. The `playwright` package has been added to dev dependencies but no browser is installed and none is needed for production use. Can be removed from dev deps if preferred.

## Sitecore Observations

The page is rendered by Sitecore Experience with jQuery Unobtrusive AJAX form handling. The Sitecore FormItemId is `cc81fd29-2b6b-4087-a5a9-e62d90ae8d74` and the page item is `9a245151-07aa-4f1a-89e7-d8f04a93f384`. These do not appear in the `roundsinformation` request but are useful reference values for future drift diagnosis.

The `robots.txt` has no `Disallow` rules (confirmed 2026-06-26).

## Recommended implementation tickets

1. **Add `httpx` to production dependencies** for `lewisham-server`.
2. **Implement `LewishamClient`** (`clients/lewisham/client.py`):
   - `lookup_addresses(postcode_or_street: str) -> list[AddressCandidate]`
   - `get_collection_schedule(uprn: str) -> CollectionScheduleRaw`
   - Set a project `User-Agent` header on all requests.
   - Validate that input is non-empty and at least 3 characters before calling AddressFinder.
   - Treat 500 from either endpoint as `UpstreamScraperChangedError`.
3. **Implement `LewishamParser`** (`clients/lewisham/parser.py`):
   - Parse the JSON-encoded HTML string from `roundsinformation`.
   - Extract collection entries (type, frequency, day) via regex.
   - Extract next collection date and normalise to ISO 8601.
   - Detect empty schedule (no entries) and raise `CollectionScheduleNotFoundError`.
   - Detect and normalise the `\xa0` (non-breaking space) in waste type text.
4. **Implement domain models** (`domain/models.py`):
   - `AddressCandidate(uprn: str, title: str)`
   - `CollectionEntry(waste_type: str, frequency: str, day: str)`
   - `CollectionSchedule(uprn: str, address: str, collections: list[CollectionEntry], next_collection: date, source_url: str, fetched_at: datetime)`
5. **Implement `BinsService`** (`services/bins_service.py`):
   - Orchestrate address lookup + schedule fetch.
   - Apply cache policy (24h for schedules, 7 days for UPRN-to-address, 1h for negatives).
6. **Wire up FastAPI routes** (`api/routers/bins.py`):
   - `GET /bins/addresses?postcode={postcode}` → address list
   - `GET /bins/addresses/{uprn}/collections` → collection schedule
7. **Add a configuration constant** for the `data-item` GUID with a comment explaining how to re-discover it via browser if the value changes.
8. **Add integration tests** that mock the two Lewisham endpoints and verify the parser handles: residential schedule, empty schedule, partial civic schedule, and the FORTNIGHTLY/WEEKLY frequency normalisation.

## Spike artefacts

Scratch scripts are in `scratch/` (gitignored):
- `spike_scraping.py` — initial endpoint probing
- `spike_js_analysis.py` — JS bundle analysis
- `spike_html_dump.py` — HTML form structure dump
- `spike_form_post.py`, `spike_field_debug.py`, `spike_no_session_id.py`, `spike_two_step.py`, `spike_cookie_debug.py` — form session investigation
- `spike_roundsinformation.py` — confirmed stateless roundsinformation call
- `spike_failure_modes.py` — error and edge case enumeration

No residential UPRNs are committed to the repository. Test fixtures that need a residential UPRN should pass it via environment variable or a gitignored local file.
