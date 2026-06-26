#!/usr/bin/env python3
"""
Spike 001 — enumerate failure modes for both Lewisham AJAX endpoints.

Tests error cases: invalid inputs, missing params, non-Lewisham postcodes,
invalid UPRNs. Useful for verifying parser assumptions still hold.

Run from repo root:
    uv run python scripts/spike_001/failure_modes.py
"""

import json
import re
import httpx

BASE_URL = "https://lewisham.gov.uk"
COLLECTION_PAGE = f"{BASE_URL}/myservices/recycling-and-rubbish/your-bins/collection"
DATA_ITEM = "{23423835-d2a6-41b1-9637-29e5e8cc2df7}"
TEST_POSTCODE = "SE6 1SQ"

UA = "lewisham-council-scraper/spike"
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/html, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": COLLECTION_PAGE,
}

SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def af(client: httpx.Client, postcode_or_street: str, national: str = "False") -> tuple[int, object]:
    r = client.post(
        f"{BASE_URL}/api/AddressFinder",
        params={"postcodeOrStreet": postcode_or_street, "national": national},
        headers=HEADERS,
    )
    return r.status_code, r.json() if r.status_code == 200 else r.text


def ri(client: httpx.Client, uprn: str) -> tuple[int, str]:
    r = client.post(
        f"{BASE_URL}/api/roundsinformation",
        params={"item": DATA_ITEM, "uprn": uprn},
        headers=HEADERS,
    )
    return r.status_code, r.text


def main() -> None:
    with httpx.Client(follow_redirects=True, timeout=30) as client:

        # Look up a residential UPRN dynamically for use in later tests
        af_resp = client.post(
            f"{BASE_URL}/api/AddressFinder",
            params={"postcodeOrStreet": TEST_POSTCODE, "national": "False"},
            headers=HEADERS,
        )
        addresses = af_resp.json() if af_resp.status_code == 200 else []
        residential_uprn = next(
            (str(a["Uprn"]) for a in addresses if a.get("Title", "").split()[0].rstrip(",").isdigit()),
            None,
        )
        print(f"Residential UPRN for {TEST_POSTCODE}: {'found' if residential_uprn else 'NOT FOUND'}")

        # ── AddressFinder failure modes ───────────────────────────────────
        section("1. AddressFinder: non-Lewisham and invalid postcodes")
        for postcode in ["SW1A 1AA", "M1 1AE", "INVALID", "", "SE6"]:
            status, resp = af(client, postcode)
            if isinstance(resp, list):
                print(f"  {postcode!r}: {status}, {len(resp)} addresses")
                if resp:
                    print(f"    first title: {resp[0].get('Title', '?')}")
            else:
                print(f"  {postcode!r}: {status}, body={str(resp)[:100]!r}")

        section("2. AddressFinder: national=True for non-Lewisham postcode")
        status, resp = af(client, "SW1A 1AA", national="True")
        if isinstance(resp, list):
            print(f"  SW1A 1AA (national=True): {status}, {len(resp)} addresses")
            for a in resp[:3]:
                print(f"    {a.get('Title', '?')}")
        else:
            print(f"  SW1A 1AA: {status}, body={str(resp)[:100]!r}")

        section("3. AddressFinder: street name search")
        status, resp = af(client, "Abbotshall Road")
        if isinstance(resp, list):
            print(f"  'Abbotshall Road': {status}, {len(resp)} addresses")
        else:
            print(f"  'Abbotshall Road': {status}, body={str(resp)[:80]!r}")

        # ── roundsinformation failure modes ───────────────────────────────
        section("4. roundsinformation: invalid UPRNs")
        for uprn in ["0", "99999999999", "abc", ""]:
            status, body = ri(client, uprn)
            print(f"  uprn={uprn!r}: {status}, body={body[:150]!r}")

        section("5. roundsinformation: missing uprn param")
        r = client.post(
            f"{BASE_URL}/api/roundsinformation",
            params={"item": DATA_ITEM},
            headers=HEADERS,
        )
        print(f"  No uprn param: {r.status_code}, body={r.text[:150]!r}")

        section("6. roundsinformation: missing item param")
        r = client.post(
            f"{BASE_URL}/api/roundsinformation",
            params={"uprn": "0"},
            headers=HEADERS,
        )
        print(f"  No item param: {r.status_code}, body={r.text[:100]!r}")

        section("7. AddressFinder: UPRN lookup variant")
        if residential_uprn:
            r = client.post(
                f"{BASE_URL}/api/AddressFinder",
                params={"uprn": residential_uprn},
                headers=HEADERS,
            )
            print(f"  AddressFinder?uprn={{...}}: {r.status_code}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    # Print without the actual UPRN value
                    title = data.get("Title", "?") if isinstance(data, dict) else str(data)[:100]
                    print(f"  Title: {title!r}")
                except Exception:
                    print(f"  Body: {r.text[:200]!r}")
        else:
            print("  Skipped — no residential UPRN found")

        # ── Annotated response structure ──────────────────────────────────
        section("8. Annotated response structure (fresh client, no session)")
        if not residential_uprn:
            print("  Skipped — no residential UPRN found")
            return

        with httpx.Client(timeout=30) as c:
            status, body = ri(c, residential_uprn)
        print(f"Status: {status}")

        try:
            html = json.loads(body)
        except Exception:
            html = body

        print("\nCollection entries:")
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

        print(f"\nFull raw JSON body:\n{body!r}")


if __name__ == "__main__":
    main()
