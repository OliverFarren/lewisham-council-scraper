---
title: Spike Findings — Independent UPRN Resolution
description: Results of spike_002_uprn_resolution investigation into whether Lewisham's AddressFinder endpoint can be replaced with an independent address-to-UPRN resolver.
created: 2026-06-28
status: complete
---

# Spike Findings — Independent UPRN Resolution

## Central finding

No freely available, documented source currently satisfies every requirement for
a drop-in replacement of Lewisham's `AddressFinder` endpoint as the default
resolver in a public FOSS self-hosted service.

The most capable candidates either restrict caching to 24 hours or require a
paid account that a self-hoster cannot obtain without a commercial relationship.
The best open datasets contain UPRNs but not the human-readable address labels a
resident needs to select their property. Community address enrichment projects
have immature coverage even for prominent civic buildings.

**Recommendation: Option 2 — Create a provider boundary but retain
Lewisham AddressFinder as the default.**

The architectural separation is worthwhile. Lewisham's `AddressFinder` should
become the default implementation of a well-defined interface, allowing
documented alternatives to be injected by operators who have their own
credentials. The endpoint continues to work for the stated scope (Lewisham bin
lookups), and no viable open replacement exists today.

---

## Candidate comparison

| Candidate | Address labels | UPRN in response | Postcode search | Open licence | Server-side caching to 7 days | No credentials required | Public self-hosting viable |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Lewisham AddressFinder | Yes | Yes | Yes | Unknown | Unknown | Yes | Yes (no docs or SLA) |
| OS Open UPRN (download) | No | Yes | No | Yes (OGL) | N/A — local | N/A — local | Yes, but no addresses |
| ONS UPRN products (NSUL/ONSUD) | No | Yes | Via postcode field | Yes (OGL) | N/A — local | N/A — local | Yes, but no addresses |
| OS Places API | Yes | Yes | Yes | No — commercial | **No** (max 24 h) | No (account required) | **No** |
| AddressBase Core (download) | Yes (single-line) | Yes | Via postcode field | No — OS licence | N/A — local | No (PSGA or trial only) | No |
| GeoPlace FindMyAddress | Yes | Yes | Yes | Unknown | No (browser UI) | No (browser UI) | **No** — not an API |
| Postcodes.io | No | No | Yes | Yes (OGL) | Yes | Yes | Partial — postcode validation only |
| UPRN.org.uk | Community (incomplete) | Yes | No | Yes (OGL) | Yes | Yes | No — no postcode search, poor coverage |
| Ideal Postcodes | Yes | Yes | Yes | No — commercial | Unknown | No (paid account) | No — per-lookup cost |

---

## Candidate detail

### Lewisham AddressFinder — baseline

**What it does.**
Two endpoint modes: postcode/street search returns an array of
`{"Uprn": int, "Title": string}` candidates; a UPRN variant reverse-resolves a
known identifier to its address. `national=False` (the default) limits results
to Lewisham. `national=True` extends coverage to Great Britain. Northern Ireland
postcodes returned zero results in all tests.

**Live observations (civic fixtures only, 2026-06-28).**

| Location | Postcode | national=False | national=True |
|---|---|---|---|
| Catford Civic Suite, Lewisham | SE6 4RU | 57 addresses | 57 addresses |
| Manchester Town Hall | M60 2LA | 0 (not Lewisham) | 2 addresses |
| Edinburgh City Chambers | EH1 1YJ | 0 (not Lewisham) | 1 address |
| Cardiff City Hall | CF10 3ND | 0 (not Lewisham) | 1 address |
| Belfast City Hall | BT1 5GS | 0 | 0 — **NI not supported** |
| Partial postcode SE6 | — | HTTP 500 | HTTP 500 |

UPRN reverse-lookup confirmed working: `POST /api/AddressFinder?uprn=10070773887`
returned `{"Uprn": 10070773887, "Title": "Civic Suite, Catford Road, SE6 4RU, London"}`.

Typical response time: ~390 ms. No rate-limit headers observed. No documented
terms, SLA, data provenance, or update policy. Breakage would be silent and
potentially hard to diagnose. Its `national=True` capability is an undocumented
boolean on a council website and must not be treated as a supported national
service.

---

### OS Open UPRN

**Fields:** `UPRN`, `X_COORDINATE` (BNG easting), `Y_COORDINATE` (BNG
northing), `LATITUDE`, `LONGITUDE` — nothing else. No address labels, no
postcodes, no street names. Approximately 40 million addressable locations
across Great Britain.

**Licence:** Open Government Licence v3.0. Free for any use.

**Distribution:** Download-only CSV / GeoPackage. Updated every six weeks.

**Usability verdict:** A list of coordinates cannot let a resident identify
which UPRN is theirs when multiple properties share the same coordinates (common
for blocks of flats). Address discovery requires supplementary data that is not
open under the same terms. This product could validate that a UPRN belongs to a
real location, or support a local spatial index, but it cannot replace a
postcode-to-address resolver.

---

### ONS UPRN products (ONSUD and NSUL)

**Fields:** UPRN, postcode (since October 2020), plus statistical and
administrative geography codes (LSOA, MSOA, local authority district, health
geography, etc.). No human-readable address labels.

**Licence:** Open Government Licence v3.0. Postcodes are drawn from OS
Code-Point Open and checked before publication, so they are genuinely open. The
products are available from the ONS Open Geography Portal and updated every six
weeks.

**Usability verdict:** Provides an open postcode-to-UPRN index, but only the
set of UPRNs that fall within a postcode. No address labels, no sub-premise
disambiguation. A building with ten flats would appear as ten bare UPRNs, none
distinguishable without supplementary address data. Not usable alone as an
address resolver.

---

### OS Places API

**What it does.**
Full-featured address resolution backed by AddressBase Premium: postcode search,
free-text address search, UPRN lookup, bounding-box and geographic queries.
Covers Great Britain plus the Channel Islands and Isle of Man. Daily updates.
Rich response including structured address components, single-line address,
classification, UPRN, and coordinates.

**Access.** Requires an OS Data Hub account (free to register). Places API is
explicitly excluded from the standard £1,000/month free premium credit. A
60-day, 2,000-transaction trial is available. Ongoing access is priced
separately from other premium APIs.

**Licence and caching terms (from published API terms):**
- End users must not store cached data for more than 24 hours after a
  transaction. This conflicts directly with the service's 7-day UPRN-to-address
  cache policy.
- Results may not be redistributed or downloaded except as expressly permitted.
  Serving address data through a public REST API would require explicit OS
  permission.
- Derived data may not be used to build competing commercial applications.

**Usability verdict:** Technically the strongest replacement candidate. Fatally
incompatible with this project's caching requirements and redistribution model.
A public FOSS service that caches UPRN-to-address mappings for seven days and
returns them via a REST endpoint would require a separate OS data licence, not
just an API key. The 24-hour cache ceiling makes it unsuitable as a default
resolver without a custom commercial agreement.

---

### AddressBase Core (download)

**What it provides.**
Over 33 million addresses across Great Britain, each with a UPRN, a
single-line address attribute, property-level coordinates, postcode, and
classification. Updated weekly.

**Access.** Public sector bodies (PSGA members) receive free unlimited access.
Others can request a free 3-month Data Exploration licence trial from OS or
purchase through OS partner resellers. There is no freely redistributable
download for the general public.

**Licence.** Not OGL. A formal OS licence agreement is required. The data may
not be redistributed openly or included in a public FOSS container image without
that agreement.

**Usability verdict:** Would technically support postcode-to-address lookup and
UPRN reverse resolution as a self-hosted dataset. Unsuitable for this project's
public self-hosting model: the operator must hold an OS licence that cannot be
transferred to end users, and the data may not be embedded in a publicly
distributed server image.

---

### GeoPlace FindMyAddress

A browser-based lookup tool for individual, non-commercial personal use. Not
an API. Confirmed: scraping it would replace one fragile dependency with
another under less suitable terms. Excluded from further consideration.

---

### Postcodes.io

**What it does.**
Open-source, unauthenticated API. Returns postcode-level geography: local
authority, ward, parliamentary constituency, NHS region, LSOA, MSOA, longitude,
latitude, and administrative codes. No UPRNs, no property-level data.

**Confirmed live (2026-06-28):** `GET /postcodes/SE61QA` returned geographic
metadata only. No UPRN or address candidate field exists in the response schema.

**Usability verdict:** Useful for postcode validation and normalization upstream
of an address resolver. Not a resolver itself.

---

### UPRN.org.uk

**What it does.**
Independent community project that adds crowdsourced house numbers and street
associations to OS Open UPRN coordinates. API endpoints: individual UPRN lookup
(`GET /uprns/{uprn}.json`) and bounding-box search (`GET /uprns.json?min_lat=...`).
No postcode search endpoint.

**Confirmed live (2026-06-28):** Two known Lewisham civic UPRNs returned
`has_address: false, address: null` — the Civic Suite at Catford Road
(UPRN 10070773887) and the Old Town Hall at Catford Road (UPRN 100023278218).
Response time: ~280 ms.

**Licence:** OGL v3.0 for community contributions; OS Open UPRN base data
under OGL.

**Usability verdict:** Three compounding problems. There is no postcode search
(the starting point for the user journey). Address coverage is incomplete even
for prominent civic buildings, meaning completeness for residential properties
cannot be assumed. Governance is informal, with no documented update schedule or
availability commitment. Not viable as a default resolver.

---

### Ideal Postcodes

**What it does.**
Commercial address API backed by Royal Mail PAF and OS datasets. Daily updates.
Supports postcode search, free-text address search, UPRN lookup, and
international addresses. Returns UPRNs with every UK address at no extra charge.

**Pricing.** Pay-as-you-go credits: approximately £0.028–£0.045 per lookup
depending on volume. 50 free trial credits, no credit card required. No
free production tier.

**Self-hosting model.** Each self-hoster would need their own paid account. API
keys cannot be distributed to end users of a FOSS project; every operator would
need to purchase and configure their own key. For a project whose server-hosting
principle is zero cost to the operator, this is a structural mismatch.

**Usability verdict:** Technically well-suited. Operationally incompatible as a
default because it cannot be made available without a commercial relationship.
Worthwhile as a documented optional adapter for operators who already have
credentials, but cannot replace the current free endpoint as a default.

---

## Test matrix — public/civic locations

Live requests were limited to a small set of public, non-residential locations
to observe response shapes and confirm national coverage claims. Raw addresses
are not recorded; findings describe counts, shapes, and boolean outcomes only.

| Location | Postcode | Nation | AF national=True result | AF national=False result | UPRN.org.uk |
|---|---|---|---|---|---|
| Catford Civic Suite | SE6 4RU | England (Lewisham) | 57 candidates | 57 candidates | UPRN known, no address |
| Old Town Hall, Catford | SE6 4RU | England (Lewisham) | Within above | Within above | UPRN known, no address |
| Manchester Town Hall | M60 2LA | England (non-Lewisham) | 2 candidates | 0 | Not tested |
| Edinburgh City Chambers | EH1 1YJ | Scotland | 1 candidate | 0 | Not tested |
| Cardiff City Hall | CF10 3ND | Wales | 1 candidate | 0 | Not tested |
| Belfast City Hall | BT1 5GS | **Northern Ireland** | **0** | 0 | Not tested |
| Partial postcode SE6 | — | — | HTTP 500 | HTTP 500 | — |
| Postcode SE6 1QA | — | England (Lewisham) | — | — | Postcodes.io: no UPRN field |

**Key observations:**
- Lewisham AddressFinder `national=True` covers England, Scotland, and Wales in
  these tests.
- Belfast (BT1 5GS) returned zero results, confirming no Northern Ireland
  coverage. This is expected: UPRNs are a Great Britain standard. The spike doc
  correctly noted NI as a deliberate boundary test.
- Partial postcode input (SE6) returned HTTP 500, confirming that input
  validation must run before any call to the endpoint.
- UPRN.org.uk returned `has_address: false` for both tested Lewisham civic
  UPRNs, confirming incomplete coverage.

---

## Architectural analysis

### Current request paths

**Cold lookup (no cache):**
```
Caller → GET /bins/addresses?postcode=X
  → Lewisham AddressFinder (1 request to lewisham.gov.uk)
     ← address list with UPRNs

Caller → GET /bins/addresses/{uprn}/collections
  → Lewisham roundsinformation (1 request to lewisham.gov.uk)
     ← collection schedule
```

**Cold lookup with unknown UPRN (UPRN presented directly, not cached):**
```
Caller → GET /bins/addresses/{uprn}/collections
  → Lewisham AddressFinder with uprn= (1 reverse-resolve request)
  → Lewisham roundsinformation (1 schedule request)
= 2 Lewisham requests
```

### With an independent resolver

**Cold address lookup:**
```
Caller → GET /bins/addresses?postcode=X
  → Independent resolver (1 request to non-Lewisham service)
     ← address list with UPRNs
```

**Cold schedule fetch (UPRN already in cache or provided directly):**
```
Caller → GET /bins/addresses/{uprn}/collections
  → Lewisham roundsinformation only (1 Lewisham request)
= 1 Lewisham request
```

The address lookup path removes one Lewisham call per uncached postcode search.
The UPRN path remains unchanged because the reverse-resolve step is triggered
only when the UPRN is unknown; a functional replacement resolver would similarly
need to answer that query.

**Requests transferred vs. eliminated:** Replacing Lewisham AddressFinder with
any live API substitutes one upstream dependency for another rather than
eliminating the request. The practical benefit is stability (documented API,
no Sitecore coupling) rather than a net reduction in upstream traffic. Requests
removed from Lewisham equal requests added to the replacement provider, minus
any requests eliminated by the replacement's own caching.

---

## Provider boundary design

A clean separation should express address resolution as an interface regardless
of whether the default implementation changes. The smallest viable boundary:

```python
class AddressResolver(Protocol):
    async def search(self, query: str) -> list[AddressCandidate]: ...
    async def resolve(self, uprn: str) -> AddressCandidate: ...
```

`AddressCandidate` is already in the domain model (`uprn: str`, `title: str`).
The `LewishamAddressResolver` wraps the existing `LewishamClient` methods and
is registered as the default. An `OSPlacesResolver` or `IdealPostcodesResolver`
could be dropped in by operators who hold credentials, without changing any
route or service logic.

This work is deferred — implementing the boundary is not part of this spike —
but the interface design is small enough to be captured here so that the follow-up
ticket does not need to re-derive it.

---

## Recommendation

**Option 2: Create a provider boundary, retain Lewisham AddressFinder as the
default.**

No open or zero-cost alternative satisfies all of:
- Postcode-to-address search returning human-readable candidates
- UPRN included with every candidate
- Caching allowed for seven days
- No account or payment required for self-hosters
- Documented API contract with a clear update policy

The Lewisham endpoint continues to serve the primary use case (Lewisham bin
lookups) and has proven stable in practice. Moving to an undocumented national
mode would be a regression in reliability posture, not an improvement.

The provider boundary is worth introducing because it:
- Makes the dependency explicit rather than implicit
- Allows a well-credentialled operator to substitute a more stable resolver
  without forking the project
- Isolates future diagnostic work (address failures vs. schedule failures)

### Conditions for revisiting

The decision should be revisited if any of the following occur:

1. **OS releases address data under OGL.** If AddressBase or a successor
   product were made available under open terms comparable to OS Open UPRN, a
   self-hosted index would become viable.
2. **OS Places API terms change.** If the 24-hour cache ceiling and
   redistribution restrictions were relaxed for open public services, Places
   would be the strongest replacement.
3. **Lewisham's AddressFinder breaks or restricts access.** Breaking or
   credential-gating the endpoint is the most likely forcing event.
4. **An open community dataset achieves reliable residential coverage.** If
   UPRN.org.uk or an equivalent project reached consistently complete coverage
   and added postcode search, it would be worth re-evaluating.
5. **OS NGD Address Layer API becomes available.** OS has signalled that the
   National Geographic Database will expose new APIs. If any of these include an
   address search with permissive terms, the picture changes.

---

## Follow-up implementation ticket

**Introduce an address resolver interface and register Lewisham as the default.**

Scope:
- Define `AddressResolver` protocol in `domain/` (two methods: `search` and
  `resolve`).
- Refactor `BinsService` to accept an `AddressResolver` via dependency
  injection rather than calling `LewishamClient` address methods directly.
- Wrap the existing client methods in a `LewishamAddressResolver` adapter in
  `clients/lewisham/`.
- Wire the default in `api/dependencies.py`.
- Update tests to inject the resolver rather than patching the client directly.

No new external dependency. No change to public routes or response schemas.
The change enables future adapter work; it does not implement any adapter.

---

## References

Documentation reviewed and live tests conducted on 2026-06-28.

- OS Open UPRN product: <https://www.ordnancesurvey.co.uk/products/os-open-uprn>
- OS Places API documentation: <https://docs.os.uk/os-apis/accessing-os-apis/os-places-api>
- OS Data Hub API Terms & Conditions: <https://osdatahub.os.uk/legal/apiTermsConditions>
- OS Data Hub plans: <https://osdatahub.os.uk/plans>
- AddressBase Core documentation: <https://docs.os.uk/os-downloads/products/addresses-and-names-portfolio/addressbase-core>
- ONS National Statistics UPRN Products: <https://www.ons.gov.uk/methodology/geography/geographicalproducts/nationalstatisticsaddressproducts>
- ONS postcode inclusion in ONSUD/NSUL: <https://www.ons.gov.uk/aboutus/transparencyandgovernance/freedomofinformationfoi/inclusionofpostcodesintheonsudandnsulproducts>
- Postcodes.io API reference: <https://postcodes.io/docs>
- UPRN.org.uk about: <https://uprn.org.uk/about>
- Ideal Postcodes pricing: <https://ideal-postcodes.co.uk/pricing>
- Ideal Postcodes addresses API: <https://docs.ideal-postcodes.co.uk/docs/api/addresses/>
