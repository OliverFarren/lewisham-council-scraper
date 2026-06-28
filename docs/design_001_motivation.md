---
title: Design Motivation
description: Why lewisham-council-scraper exists, why no official API exists, the scraping approach, and the MCP integration layer.
created: 2026-06-26
status: accepted
---

# Design Motivation

> **Architecture update:** The motivation in this document remains current,
> while the API-first integration shape is evolved by
> [Design 002: Client-First Integration Architecture](design_002_client_first_architecture.md).

## Why this project exists

Bin collection schedules in Lewisham follow a regular weekly pattern, but they change. Bank holidays shift them, and operational disruptions cause unexpected adjustments. While the [London Borough of Lewisham's website](https://www.lewisham.gov.uk/) is the definitive authority for these dates, checking a web page manually creates a point of friction that doesn't fit into a modern software ecosystem.

Lewisham contains over 300,000 residents. A growing number of them maintain home automation setups, run smart home dashboards, or interact with conversational AI interfaces. For these setups, asking *"when do my bins go out?"* should return a clean data object rather than requiring a browser lookup. This project acts as a small, reliable translation layer between a public web page and machine-readable data.

---

## Why not use an official API

The short answer is that one doesn't exist.

The neat solution would be for Lewisham to publish a stable, documented endpoint for household waste collections. Instead, the UK's local government data landscape remains structurally decentralized. When a resident uses the national [GOV.UK](https://www.gov.uk/) portal to look up their bin day, the central site acts strictly as an index router. It simply matches the postcode against a lookup table, then redirects the user's browser to the homepage of one of the **317 local authorities** across England. From that point on, every council is entirely on its own IT stack.

This is where the problem shifts from a technical issue to a governance issue. Without an official API, developers are forced to rely on web scraping, which always feels a bit rogue. It operates without formal authorization, relies on implicit good faith, and can break instantly if a frontend developer changes an HTML class name.

A public API provides legitimacy and control. It establishes a formal framework for data exchange by issuing API keys, tracking system health, setting up structured data-sharing agreements, and enforcing fair-use rate limits.

We know this governed model works because the pattern already exists elsewhere in UK public infrastructure. A clear example is the [**Rail Data Marketplace (RDM)**](https://raildata.org.uk/), a centralized platform funded by the Department for Transport (DfT) and managed by the Rail Delivery Group. Instead of forcing independent app developers or tech firms to scrape data from disparate train operating companies, the RDM provides a single, official port of call. Anyone can request an account, get an API key, and access live public rail data under formalized, structured rate limits and clear governance guidelines. It turns public infrastructure data into an authorized, safely managed ecosystem.

The reason councils don't build these governed endpoints for local services comes down to money and risk:

* **Extreme Fiscal Pressure:** The UK local government sector operates under severe financial strain.[^2] Dozens of councils have required Exceptional Financial Support or have been forced to issue Section 114 notices—effectively declaring structural insolvency (such as Birmingham, Nottingham, Woking, and Croydon).[^1]
* **Prioritization of Statutory Obligations:** When a council's budget is consumed almost entirely by mandatory statutory services like adult social care and children's welfare, discretionary digital engineering is completely stripped out.[^2][^3]
* **The Governance Overhead:** A static web page satisfies a council's legal obligation to inform residents with very low ongoing overhead. Conversely, a production-grade public API forces an organization to inherit permanent engineering and data governance commitments: uptime monitoring, rate limiting, security compliance, and developer support.

For a resource-strapped local authority, the risk and cost of managing a public data product simply cannot be justified. As a result, municipal bin data remains a missing layer of civic infrastructure.

---

## On scraping

Scraping a local authority portal sits in a legal and operational grey area. Lewisham's terms of service do not explicitly authorize automated data harvesting. However, this project operates on several core pragmatic principles:

> ### Data Use & Infrastructure Principles
> 
> 
> * **Public and Personal Ownership:** The data is entirely public, non-commercial, and belongs to the resident in any practical sense, as it relates directly to their own property address and public services.
> * **Server Conservation:** To eliminate any noticeable load on public servers, the scraping utility executes on a highly conservative cadence (at most once every 24 hours) and caches responses downstream.
> * **Precedent:** Community-driven projects like [**UKBinCollectionData**](https://github.com/robbrad/UKBinCollectionData) have successfully maintained over 200 separate council scraping modules for years on this exact basis without issue.
> 
> 

This code follows that established community precedent in good faith. It exists simply because the data is public, but poorly formatted for modern tools.

---

## References

[^1]: Brackley, J. (2025). Audit and financial reporting under austerity localism—the case of the Birmingham City Council 'bankruptcy'. *Public Money & Management*, 1–11. <https://doi.org/10.1080/09540962.2025.2466494>

[^2]: Ogden, K., & Phillips, D. (2024). *How have English councils' funding and spending changed? 2010 to 2024*. Institute for Fiscal Studies. <https://doi.org/10.1920/re.ifs.2024.0318>

[^3]: Phillips, D. (2024). *Reforming local government funding in England: the issues and options*. Institute for Fiscal Studies. <https://doi.org/10.1920/re.ifs.2024.0948>

---

## Beyond bins

Local authority sites host a vast amount of high-utility information that citizens routinely need—such as local planning notices, road closures, and traffic adjustments. This server architecture is decoupled from the start. It is organized around separate routers, where `/bins` acts as the initial proof of concept. The underlying framework is designed to easily accommodate additional civic data modules as they are developed.

---

## The MCP layer

The core server is a lightweight REST API that returns structured JSON. It can be used directly by custom scripts, webhooks, or native smart home platforms like Home Assistant via a standard [`rest` sensor](https://www.home-assistant.io/integrations/rest/).

The Model Context Protocol (MCP) package included in this repository is an entirely optional integration layer. MCP is an [open standard](https://modelcontextprotocol.io/) designed to safely connect large language models (LLMs) to local developer tools and data sources. By wrapping this API in an MCP server, conversational assistants can interact with the endpoints natively. Instead of configuring rigid API calls or brittle parsing logic, a home assistant or LLM can interpret natural language queries directly:

```json
// Example of an MCP tool invocation behind the scenes
{
  "name": "get_next_collection",
  "arguments": {
    "uprn": "100022031422"
  }
}

```

This setup translates raw web elements into contextual, fluid answers—such as telling a user that their recycling collection has been pushed back by 24 hours due to a bank holiday—lowering the technical barrier for smart home automation.
