"""Save a complete snapshot of Toronto search results from RapidAPI."""

import json
import os
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv


API_URL = "https://airbnb-search.p.rapidapi.com/property/search"
DESTINATION = Path(__file__).resolve().parent / "bulk_airbnb_data.json"
MAX_PAGES = 100


def fetch_homes(api_key, requester=requests):
    """Return all reported pages, failing before any snapshot is replaced."""
    headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": "airbnb-search.p.rapidapi.com"}
    homes = []
    seen_ids = set()
    page_signatures = set()
    total_pages = None
    page = 1

    while page <= MAX_PAGES:
        try:
            response = requester.get(
                API_URL,
                headers=headers,
                params={"query": "Toronto, Ontario, Canada", "page": page},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Page {page} could not be fetched or decoded") from exc

        if not isinstance(payload, dict) or payload.get("status") is not True:
            raise RuntimeError(f"Page {page} reported an API error or invalid status")
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("homes"), list):
            raise RuntimeError(f"Page {page} has no valid homes list")

        has_pagination = "currentPage" in payload and "totalPages" in payload
        if has_pagination:
            try:
                reported_page = int(payload["currentPage"])
                reported_total = int(payload["totalPages"])
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Page {page} has invalid pagination metadata") from exc
            if reported_page != page or reported_total < page or reported_total > MAX_PAGES:
                raise RuntimeError(f"Page {page} has inconsistent pagination metadata")
            if total_pages is None:
                total_pages = reported_total
            elif reported_total != total_pages:
                raise RuntimeError(f"Page {page} changed the reported page count")
        elif "currentPage" in payload or "totalPages" in payload or total_pages is not None:
            raise RuntimeError(f"Page {page} has incomplete pagination metadata")

        page_homes = data["homes"]
        if not page_homes:
            if total_pages is None and page > 1:
                print(f"Fetched {len(homes)} records and {len(seen_ids)} distinct listing IDs")
                return homes
            raise RuntimeError(f"Page {page} is unexpectedly empty")
        if not all(isinstance(home, dict) for home in page_homes):
            raise RuntimeError(f"Page {page} contains a malformed listing")

        listings = [home.get("demandStayListing") for home in page_homes]
        if not all(isinstance(listing, dict) for listing in listings):
            raise RuntimeError(f"Page {page} contains a listing without an ID")
        ids = [listing.get("id") for listing in listings]
        if any(not isinstance(listing_id, str) or not listing_id.strip() for listing_id in ids):
            raise RuntimeError(f"Page {page} contains a listing without an ID")
        signature = tuple(ids)
        if signature in page_signatures:
            raise RuntimeError(f"Page {page} repeats a previous page")
        page_signatures.add(signature)
        seen_ids.update(ids)
        homes.extend(page_homes)
        print(f"Page {page}/{total_pages or '?'}: {len(page_homes)} records")
        if page == total_pages:
            print(f"Fetched {len(homes)} records and {len(seen_ids)} distinct listing IDs")
            return homes
        page += 1

    raise RuntimeError(f"Extraction exceeded the {MAX_PAGES}-page safety limit")


def save_snapshot(homes, destination=DESTINATION):
    """Replace the snapshot only after a complete extraction succeeds."""
    destination = Path(destination)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", prefix=".bulk-",
            dir=destination.parent, delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(homes, temporary, ensure_ascii=False, indent=2)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def extract_to_file(api_key, destination=DESTINATION, requester=requests):
    homes = fetch_homes(api_key, requester=requester)
    save_snapshot(homes, destination)
    return homes


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise SystemExit("RAPIDAPI_KEY is required")
    extract_to_file(api_key)
    print(f"Saved complete snapshot to {DESTINATION}")


if __name__ == "__main__":
    main()
