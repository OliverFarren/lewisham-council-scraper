from importlib.metadata import version

BASE_URL = "https://lewisham.gov.uk"
COLLECTION_PAGE_URL = (
    f"{BASE_URL}/myservices/recycling-and-rubbish/your-bins/collection"
)
ADDRESS_FINDER_PATH = "/api/AddressFinder"
ROUNDS_INFORMATION_PATH = "/api/roundsinformation"

# Sitecore component item ID for the rounds-information rendering. If this
# changes, re-run the browser discovery flow in docs/spike_001_findings.md and
# read the data-item attribute from the js-find-collection-result element.
ROUNDS_INFORMATION_ITEM_GUID = "{23423835-d2a6-41b1-9637-29e5e8cc2df7}"

REQUEST_TIMEOUT_SECONDS = 10.0
USER_AGENT = f"lewisham-client/{version('lewisham-council-client')}"
