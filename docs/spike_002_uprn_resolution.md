---
title: Spike - Independent UPRN Resolution
description: Investigation plan for resolving addresses to UPRNs without depending on Lewisham Council's undocumented AddressFinder endpoint.
created: 2026-06-28
status: complete
result: spike_002_findings.md
---

# Spike - Independent UPRN Resolution

> **Investigation complete:** See
> [Spike 002 Findings](spike_002_findings.md).

## Context

The first scraping spike established the minimum flow needed to retrieve a bin
collection schedule from Lewisham Council. A resident enters a postcode or
street, selects their address, and receives their collection information. That
looks like one bin-related interaction, but it crosses two distinct data
domains.

Behind the form, Lewisham's website first calls its undocumented
`/api/AddressFinder` endpoint. The endpoint turns the resident's search into a
list of human-readable addresses and Unique Property Reference Numbers
(UPRNs). Once the resident selects an address, the chosen UPRN is sent to the
separate `/api/roundsinformation` endpoint, which returns the bin schedule.

The UPRN is therefore not bin data. It is the common identifier that lets the
bin service say which addressable location the request concerns. Lewisham's
website happens to perform both operations, but that does not mean this project
must obtain both kinds of data from Lewisham.

This spike asks whether address-to-UPRN resolution can come from a more stable,
independent source, leaving Lewisham Council responsible only for the
Lewisham-specific information that no national dataset can provide: the
collection schedule itself.

## What is a UPRN?

A Unique Property Reference Number is a persistent numeric identifier for an
addressable location in Great Britain.[^1] A house or commercial building can
have one, but so can an individual flat, a property that is still being
developed, or an object without a conventional postal address, such as an
electricity substation or bus shelter. The address, name, use, or physical
state of a location may change during its lifetime; its UPRN provides the
stable reference through those changes.

Local authorities have maintained authoritative local address and street
records for decades as part of their street naming and numbering
responsibilities. They allocate UPRNs to new addressable locations and maintain
Local Land and Property Gazetteers. GeoPlace, a partnership between the Local
Government Association and Ordnance Survey, brings those local records
together into national address and street data.[^2]

The identifier became substantially more useful outside those systems in 2020.
The government announced that UPRNs and Unique Street Reference Numbers would
be released under the Open Government Licence, and the Open Standards Board
adopted them as the government standard for referencing and sharing property
and street information.[^3] The purpose is interoperability: services can keep
their own domain-specific records while using the same identifier to agree
which physical location they describe.

That history makes the UPRN nationally shared and domain-independent, but not
universal in every sense. The formal standard covers addressable locations in
Great Britain: England, Scotland, and Wales. Northern Ireland has different
addressing arrangements and must be investigated separately rather than
silently included under the word "UK". A UPRN should also be treated as an
opaque identifier, not as a number from which facts about a property can be
decoded.

There is a further distinction at the centre of this spike:

> **An identifier being open does not necessarily make the address record
> attached to it open.**

OS Open UPRN provides UPRNs and their coordinates under an open licence, but it
does not provide the house numbers, building names, streets, or complete
address labels needed for a resident to choose their home from a postcode
search.[^4] Rich address products can include data from local authorities,
Ordnance Survey, and Royal Mail's Postcode Address File, with different access
and licensing conditions. The technical problem is not simply obtaining a
list of UPRNs. It is reliably matching ordinary address input to the correct
one.

## Why revisit the current source?

### Reduce the scraper's drift surface

Both Lewisham endpoints are internal website plumbing rather than published
public APIs. Either can change without notice when the council updates its
Sitecore implementation or replaces a supplier. The bin schedule will remain
an unavoidable Lewisham dependency, but address resolution may not need to be.

Moving that responsibility to a documented source would mean that a change to
Lewisham's AddressFinder no longer breaks the first half of the user journey.
It would also isolate future diagnostic work: failures resolving an address
would belong to the address provider, while failures retrieving a collection
schedule would belong to the Lewisham scraper.

### Reflect the real domain boundary

UPRNs are intended to link otherwise separate public services. Planning,
property, highways, energy, emergency response, and waste collection can all
refer to the same location without making address discovery part of any one
of those domains. Treating UPRN resolution as an independent capability would
make the code and eventual REST surface more honest about that relationship.

This remains useful even if the replacement initially supports only Lewisham
addresses. Wider Great Britain coverage would be an additional benefit, not a
reason to force a national product into the first implementation.

### Reduce avoidable requests to Lewisham

On an uncached interactive lookup, the current journey makes one Lewisham
request to resolve the postcode or street and one to retrieve the schedule.
When a caller begins with a UPRN that is not already cached, the service may
similarly resolve the UPRN through AddressFinder before requesting the
schedule.

An independent resolver would leave only the schedule request hitting
Lewisham, reducing those uncached Lewisham request paths from two calls to one.
This is not a promise that total upstream traffic will always fall by exactly
50 percent: successful addresses are cached for seven days and schedules for
24 hours, so the real reduction depends on cache state and usage patterns. It
is nevertheless a meaningful application of the project's server-conservation
principle.

## Central question

**Is there a documented, dependable, and licence-compatible way to turn a
postcode or address search into human-readable address candidates and UPRNs
without requiring users to buy access or configure a commercial API key?**

The comparison should not assume that "official", "open", and "usable as an
address finder" mean the same thing. A candidate may contain authoritative
UPRNs but no address labels, expose an excellent API under terms unsuitable for
public self-hosting, or be free for interactive personal use while prohibiting
automated use.

A complete replacement should support:

* Search by at least a full postcode, with street or partial-address search
  assessed as an additional capability.
* Human-readable candidates that allow a user to distinguish properties,
  including sub-premises where the source supports them.
* A UPRN for each candidate.
* Reverse lookup of a known UPRN, or a clearly documented reason to split that
  operation from address discovery.
* Reliable Lewisham coverage, with wider Great Britain coverage measured
  rather than assumed.
* Terms that permit server-side use and the caching needed for responsible
  operation.
* A documented contract, update policy, and failure model.

## Candidate landscape

The spike should examine categories of source rather than selecting the first
API that returns a plausible result.

### Lewisham AddressFinder - the baseline

The existing endpoint provides exactly the response shape the application
currently needs and requires no project-managed credentials. The first spike
also found a `national=True` mode capable of returning addresses outside
Lewisham, although that mode is not used in production.

It remains the baseline for result quality and request count, but its national
mode must not be mistaken for a supported national service. The spike should
test its coverage and failure behaviour using a very small public sample, and
should try to establish whether its data provenance or usage terms are
documented anywhere. An undocumented boolean on a council website is not by
itself a durable national architecture.

### OS Open UPRN and ONS UPRN products

OS Open UPRN is the clearest fully open source of the identifiers themselves.
It supplies Great Britain-wide UPRNs and coordinates as downloadable CSV and
GeoPackage data.[^4] The Office for National Statistics also publishes UPRN
directories that associate UPRNs with statistical and administrative
geographies, and may include postcodes where open licensing permits.[^5]

These products may be useful for validation, geographic scoping, or a
self-hosted index. The investigation must determine whether they can support
the actual user journey. A postcode-to-UPRN list without property-level address
labels cannot safely tell a resident which UPRN is theirs, particularly for
blocks of flats or postcodes shared by many premises.

### OS Places API and AddressBase Core

Ordnance Survey describes AddressBase as the authoritative source for Great
Britain address data. OS Places API supports searches by full or partial
address, postcode, UPRN, and geographic area, backed by AddressBase Premium.[^6]
AddressBase Core offers a downloadable, regularly updated address dataset with
UPRNs, classifications, coordinates, and single-line addresses.[^7]

These are the strongest capability benchmark because they are documented,
authoritative, and designed for address resolution. They also expose the
central trade-off: access to the rich address data is not equivalent to access
to OS Open UPRN. The spike must record authentication, current pricing or
eligibility, redistribution constraints, permitted caching, and whether a
public FOSS service can offer a reasonable setup experience. No purchase should
be made as part of the investigation.

### GeoPlace FindMyAddress

[FindMyAddress](https://www.findmyaddress.co.uk/) demonstrates that the public
can retrieve an official address and UPRN free of charge for individual use.
Its published service is intended for limited personal, non-commercial
searches rather than as a public application API.[^8]

It is useful as a manual reference when checking public fixtures, but the spike
must not scrape it or treat a browser-facing service as an undocumented API.
Doing so would merely replace one fragile dependency with another under less
suitable terms.

### Postcodes.io

Postcodes.io is a documented, unauthenticated, open-source API for postcode
validation and postcode-level geography.[^9] It is operationally attractive
and may help validate, normalise, or geographically classify a postcode.
However, postcode data describes an area or group of delivery points rather
than a selectable property. The spike should confirm whether it exposes any
property-level UPRN capability before considering it a resolver.

### Open and community datasets

The search should include genuinely open projects rather than considering only
government and commercial services. For example, UPRN.org.uk combines OS Open
UPRN coordinates with community-contributed address information and exposes
open downloads and lookup endpoints.[^10] Its independence and licence are
interesting, but completeness, freshness, governance, postcode search, and
long-term operation all need measurement.

Other open candidates should be admitted only when their source, licence, and
maintenance model can be established. Combining an approximate geocoder with
the nearest UPRN coordinate is not an acceptable shortcut: several premises
can share coordinates, and individual flats can have separate UPRNs.

### A commercial address API

One established commercial provider, such as Ideal Postcodes, should be
included as a capability and usability benchmark. Such services offer
property-level postcode or address search and return UPRNs through documented
APIs.[^11]

This does not presume that the project should adopt one. Requiring every
self-hoster to obtain a key, accept third-party terms, manage a secret, and
possibly pay per lookup would be an immediate disadvantage compared with the
current Lewisham endpoint. The comparison is useful because it shows what a
complete managed solution provides and helps reveal what is missing from open
alternatives.

## Evaluation criteria

Each candidate should be assessed against the same questions:

| Area | Questions |
|---|---|
| Discovery | Can a full postcode return all distinguishable address candidates? Can it search by street or partial address? |
| Resolution | Does every usable candidate include a UPRN? Can a known UPRN be resolved back to its current address? |
| Coverage | Does it cover Lewisham, England, Wales, and Scotland? What happens for Northern Ireland, non-postal objects, new builds, historic records, and sub-premises? |
| Authority | Who creates and maintains the data? Is provenance visible in the response or documentation? |
| Currency | How often is the source updated, and how are retired or changed addresses represented? |
| Access | Is authentication required? Are keys available to public FOSS users, and can a self-hoster obtain one without a commercial agreement? |
| Cost | Are development and production requests free, metered, trial-only, or contract-priced? |
| Licence | May the project display, cache, persist, and redistribute returned addresses and UPRNs? |
| Operations | Are rate limits, timeouts, availability, versioning, and error responses documented? Is self-hosting practical? |
| Privacy | Can the integration avoid logging or retaining residential searches beyond the intended cache policy? |

## Proposed investigation

### 1. Establish the legal and data boundary

Read the licence and technical documentation before probing APIs. Record
separately:

* Whether the UPRN, coordinate, postcode, and human-readable address fields
  come from different licensed datasets.
* Whether automated server-side access is permitted.
* Whether responses may be cached for seven days or longer.
* Whether address results may be returned by this project's public REST API.
* Whether credentials can be distributed to, or independently obtained by,
  self-hosters.

If those questions cannot be answered from published terms, mark the candidate
as requiring clarification rather than inferring permission.

### 2. Build a small, non-residential fixture matrix

Use public or civic locations only:

* One Lewisham public building to compare with the existing local flow.
* One public location elsewhere in England.
* One in Wales.
* One in Scotland.
* One in Northern Ireland, treated as a deliberate boundary test rather than
  assumed UPRN coverage.
* Where an official provider publishes test fixtures, one example that
  exercises sub-premise or multi-unit behaviour.
* Invalid, empty, partial-postcode, and unknown-UPRN inputs.

Do not commit residential addresses or UPRNs. Findings should record schemas,
candidate counts, booleans, timings, and anonymised differences rather than raw
address lists. Public UPRNs should also be omitted unless a provider publishes
them expressly as test data and including one materially improves the
documentation.

### 3. Compare behaviour with bounded live checks

For candidates that permit automated evaluation:

1. Search by a full postcode.
2. Search by street or partial address where supported.
3. Resolve a returned public UPRN back to an address.
4. Compare whether the selected UPRN and normalized address round-trip.
5. Exercise documented invalid-input and not-found behaviour.
6. Record response shape, latency, rate-limit headers, and source metadata.

Keep traffic deliberately small. Do not probe rate limits by exhausting them,
crawl postcode areas, or download bulk products unless their size and terms
have first been reviewed. Never commit API keys or raw residential responses.

### 4. Assess self-hosted options

For downloadable open data, determine:

* Download and extracted size.
* Update frequency and whether incremental updates exist.
* The minimum index needed for postcode and normalized-address search.
* Whether the available fields can actually distinguish properties.
* Memory, storage, build-time, and maintenance costs for the server image.
* Whether derived indexes or address strings can be redistributed.

A self-hosted solution is only stronger if it can be kept current and operated
by ordinary users of the project. Replacing one HTTP request with a large,
licensed data pipeline is not automatically a simplification.

### 5. Quantify the architectural benefit

Document the current cold and cached request paths and compare them with each
viable alternative. The findings should distinguish:

* Requests removed from Lewisham.
* Requests merely transferred to another upstream service.
* Requests eliminated by local data or caching.
* New operational work introduced by credentials, persistence, or scheduled
  dataset updates.

The comparison should also describe the smallest provider boundary the
application would need, likely address search and exact UPRN resolution, without
implementing that boundary during the spike.

## Decision framework

The spike should end with one of three recommendations:

1. **Adopt an independent source.** A candidate provides adequate address
   selection, clear terms, better stability, and acceptable operational cost.
2. **Create a provider boundary but retain Lewisham by default.** Decoupling is
   architecturally useful, but no alternative yet beats the current source for
   public self-hosting. An optional authenticated provider may still be worth
   supporting later.
3. **Retain the current implementation.** Available alternatives are
   incomplete, prohibit the required use, impose disproportionate cost, or
   introduce more fragility than they remove.

A negative result is valid. The project should not adopt a nominally official
source if doing so makes installation expensive, requires every user to enter a
paid contract, or prevents the cache policy needed for responsible operation.
Likewise, it should not prefer a free source whose address coverage is too
incomplete to select the correct property safely.

## Goals

* Explain the role and governance of UPRNs well enough to support the
  architectural decision.
* Determine whether a stable public address-to-UPRN resolver exists.
* Separate open identifier data from licensed address-discovery data.
* Compare viable sources using consistent technical, operational, and
  licensing criteria.
* Quantify the likely reduction in Lewisham traffic.
* Recommend whether and how the current AddressFinder dependency should
  change.

## Non-goals

* Changing the REST routes or public response schemas.
* Implementing an address-provider abstraction.
* Adding an API key, commercial dependency, database, or bulk address dataset.
* Turning the project into a nationwide address service.
* Scraping FindMyAddress, Royal Mail, or another browser-facing lookup tool.
* Collecting or publishing residential addresses and UPRNs.
* Replacing the Lewisham collection-schedule endpoint.

## Risks

* **Open identifier, restricted address:** The UPRN may be reusable while the
  address needed to discover it is governed by different terms.
* **False completeness:** A postcode-level or coordinate-only source may look
  sufficient in simple tests but fail for flats, shared postcodes, or
  non-postal locations.
* **Credential burden:** A high-quality API may require secrets, payment, or an
  agreement that conflicts with simple public self-hosting.
* **New upstream drift:** Moving to another undocumented free endpoint would
  relocate fragility rather than remove it.
* **Stale community data:** Open community sources may have uneven coverage or
  no dependable update path.
* **National ambiguity:** Great Britain coverage must not be described as
  United Kingdom coverage without separately proving Northern Ireland.
* **Sensitive searches:** Postcodes, addresses, and UPRNs remain sensitive
  operational data regardless of which provider resolves them.
* **Self-hosting cost:** Bulk national data may add storage, indexing, update,
  and container-distribution costs disproportionate to a bin scraper.

## Deliverables

The spike should produce:

* `docs/spike_002_findings.md`, recording source research and bounded live
  observations.
* A candidate comparison table covering capability, provenance, access, cost,
  licensing, caching, and operations.
* An anonymised test matrix for public locations across the investigated
  nations.
* A clear recommendation using the decision framework above.
* If a replacement is recommended, a proposed provider contract and follow-up
  implementation tickets.
* If no replacement is recommended, the conditions that would justify
  revisiting the decision.

---

## References

[^1]: UK Government. *Identifying property and street information*. <https://www.gov.uk/government/publications/open-standards-for-government/identifying-property-and-street-information>

[^2]: Local Government Association. *Using the Unique Property Reference Number (UPRN) - a guide for councils*. <https://www.local.gov.uk/our-support/research-and-data/data-standards-and-transparency/using-unique-property-reference>

[^3]: Cabinet Office and Geospatial Commission. (2020). *Geospatial Commission to release core identifiers under Open Government Licence*. <https://www.gov.uk/government/news/geospatial-commission-to-release-core-identifiers-under-open-government-licence/>

[^4]: Ordnance Survey. *OS Open UPRN*. <https://osdatahub.os.uk/downloads/open/OpenUPRN>

[^5]: Office for National Statistics. *National Statistics UPRN Products*. <https://www.ons.gov.uk/methodology/geography/geographicalproducts/nationalstatisticsaddressproducts>. See also *Inclusion of postcodes in the ONSUD and NSUL products*. <https://www.ons.gov.uk/aboutus/transparencyandgovernance/freedomofinformationfoi/inclusionofpostcodesintheonsudandnsulproducts>

[^6]: Ordnance Survey. *OS Places API*. <https://docs.os.uk/os-apis/accessing-os-apis/os-places-api>

[^7]: Ordnance Survey. *AddressBase Core Documentation*. <https://docs.os.uk/os-downloads/products/addresses-and-names-portfolio/addressbase-core>

[^8]: Chichester District Council. *Unique Property Reference Numbers*. <https://www.chichester.gov.uk/article/34179/Unique-Property-Reference-Numbers>

[^9]: Postcodes.io. *API Reference*. <https://postcodes.io/docs/api/api-reference-postcodes-io/>

[^10]: UPRN.org.uk. *About UPRN.org.uk*. <https://uprn.org.uk/about>

[^11]: Ideal Postcodes. *Extract Addresses*. <https://docs.ideal-postcodes.co.uk/docs/api/addresses/>
