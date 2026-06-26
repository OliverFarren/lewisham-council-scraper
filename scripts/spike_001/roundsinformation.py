#!/usr/bin/env python3
"""
Spike 001 — prove the stateless roundsinformation flow.

Confirms that /api/roundsinformation is callable with no session or cookies,
using the stable Sitecore component GUID discovered via browser DevTools.

Run from repo root:
    uv run python scripts/spike_001/roundsinformation.py
"""

import json
import re
import httpx

BASE_URL = "https://lewisham.gov.uk"
COLLECTION_PAGE = f"{BASE_URL}/myservices/recycling-and-rubbish/your-bins/collection"
TEST_POSTCODE = "SE6 1SQ"

# Stable Sitecore component GUID — see docs/spike_001_findings.md for discovery method
DATA_ITEM = "{23423835-d2a6-41b1-9637-29e5e8cc2df7}"

UA = "lewisham-council-scraper/spike"
AJAX_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/html, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": COLLECTION_PAGE,
}

SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def main() -> None:
    with httpx.Client(follow_redirects=True, timeout=30) as client:

        # Look up addresses to get residential and civic UPRNs dynamically
        section(f"0. AddressFinder: {TEST_POSTCODE}")
        af = client.post(
            f"{BASE_URL}/api/AddressFinder",
            params={"postcodeOrStreet": TEST_POSTCODE, "national": "False"},
            headers=AJAX_HEADERS,
        )
        print(f"Status: {af.status_code}")
        addresses = af.json() if af.status_code == 200 else []
        print(f"Addresses found: {len(addresses)}")

        residential_uprn = next(
            (str(a["Uprn"]) for a in addresses if a.get("Title", "").split()[0].rstrip(",").isdigit()),
            None,
        )
        civic_uprn = next(
            (str(a["Uprn"]) for a in addresses if not a.get("Title", "").split()[0].rstrip(",").isdigit()),
            None,
        )
        print(f"Residential UPRN: {'found' if residential_uprn else 'NOT FOUND'}")
        print(f"Civic UPRN: {'found' if civic_uprn else 'NOT FOUND'}")

        if not residential_uprn:
            print("Cannot proceed — no residential UPRN found for test postcode")
            return

        # ── 1. With braces ────────────────────────────────────────────────
        section("1. roundsinformation with {braces} item GUID")
        ri1 = client.post(
            f"{BASE_URL}/api/roundsinformation",
            params={"item": DATA_ITEM, "uprn": residential_uprn},
            headers=AJAX_HEADERS,
        )
        print(f"Status: {ri1.status_code}")
        print(f"Content-Type: {ri1.headers.get('content-type', '?')}")
        print(f"Body:\n{ri1.text[:2000]}")

        # ── 2. Without braces ─────────────────────────────────────────────
        section("2. roundsinformation without {braces}")
        ri2 = client.post(
            f"{BASE_URL}/api/roundsinformation",
            params={"item": DATA_ITEM.strip("{}"), "uprn": residential_uprn},
            headers=AJAX_HEADERS,
        )
        print(f"Status: {ri2.status_code}")
        print(f"Body:\n{ri2.text[:500]}")

        # ── 3. Civic UPRN ─────────────────────────────────────────────────
        if civic_uprn:
            section("3. roundsinformation with civic UPRN")
            ri3 = client.post(
                f"{BASE_URL}/api/roundsinformation",
                params={"item": DATA_ITEM, "uprn": civic_uprn},
                headers=AJAX_HEADERS,
            )
            print(f"Status: {ri3.status_code}")
            print(f"Body:\n{ri3.text[:500]}")

        # ── 4. No cookies (fresh client) — proves stateless ───────────────
        section("4. roundsinformation without any cookies (fresh client)")
        with httpx.Client(timeout=30) as c2:
            ri4 = c2.post(
                f"{BASE_URL}/api/roundsinformation",
                params={"item": DATA_ITEM, "uprn": residential_uprn},
                headers=AJAX_HEADERS,
            )
            print(f"Status: {ri4.status_code}")
            print(f"Body:\n{ri4.text[:1000]}")

        # ── 5. Parse the response ─────────────────────────────────────────
        section("5. Parse response structure")
        best = next((r for r in [ri1, ri2] if r.status_code == 200), None)
        if not best:
            print("No successful response to parse")
            return

        html = json.loads(best.text) if best.text.startswith('"') else best.text

        print("Collection entries:")
        for m in re.finditer(
            r'<strong>([^<]+)</strong>[^<]*is collected\s*<span class="RoundsTransform">([^<]+)</span>\s*on\s*([^.<]+)',
            html,
            re.IGNORECASE,
        ):
            waste_type = m.group(1).replace("\xa0", " ").strip()
            frequency = m.group(2).strip()
            day = m.group(3).strip().rstrip(".")
            print(f"  type={waste_type!r}, frequency={frequency!r}, day={day!r}")

        date_m = re.search(r"next collection date is\s*([\d/]+)", html, re.IGNORECASE)
        if date_m:
            print(f"  next_collection_date={date_m.group(1)!r}")

        print(f"\nRaw JSON body:\n{best.text!r}")


if __name__ == "__main__":
    main()
