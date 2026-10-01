"""Flatten saved search results into advertised stay-price observations."""

import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd


DIRECTORY = Path(__file__).resolve().parent
RAW_PATH = DIRECTORY / "bulk_airbnb_data.json"
OUTPUT_PATH = DIRECTORY / "cleaned_airbnb_data.csv"
COLUMNS = [
    "id", "name", "latitude", "longitude", "price", "rating", "bedrooms",
    "bathrooms", "stay_qualifier", "checkin", "checkout", "listing_type",
    "location_label", "currency_symbol",
]
MONEY = re.compile(r"^\s*(?P<symbol>[$€£])\s*(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)\s*$")
BEDROOMS = re.compile(r"\b(\d+)\s+bedrooms?\b")
BATHROOMS = re.compile(r"\b(\d+(?:\.\d+)?)\s+baths?\b")
RATING = re.compile(r"^(\d+(?:\.\d+)?)\b")


def parse_price(home):
    display = home.get("structuredDisplayPrice") or {}
    primary = display.get("primaryLine") if isinstance(display, dict) else None
    if not isinstance(primary, dict):
        raise ValueError("missing_price")
    raw_price = primary.get("discountedPrice") or primary.get("price")
    if raw_price is None:
        raise ValueError("missing_price")
    match = MONEY.fullmatch(raw_price) if isinstance(raw_price, str) else None
    if match is None:
        raise ValueError("invalid_price")
    try:
        price = Decimal(match.group("amount").replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("invalid_price") from exc
    if price <= 0:
        raise ValueError("nonpositive_price")
    qualifier = primary.get("qualifier")
    return price, match.group("symbol"), qualifier if isinstance(qualifier, str) else None


def parse_rooms(home):
    content = home.get("structuredContent") or {}
    lines = content.get("primaryLine") if isinstance(content, dict) else None
    bedrooms = bathrooms = None
    if not isinstance(lines, list):
        return bedrooms, bathrooms
    for item in lines:
        if not isinstance(item, dict) or not isinstance(item.get("body"), str):
            continue
        body = item["body"].lower()
        bedroom_match = BEDROOMS.search(body)
        bathroom_match = BATHROOMS.search(body)
        if bedroom_match:
            bedrooms = int(bedroom_match.group(1))
        elif "studio" in body and bedrooms is None:
            bedrooms = 0
        if bathroom_match:
            bathrooms = float(bathroom_match.group(1))
    return bedrooms, bathrooms


def parse_rating(value):
    if not isinstance(value, str) or value.strip().lower() == "new":
        return None
    match = RATING.match(value.strip())
    if match is None:
        return None
    rating = float(match.group(1))
    return rating if 0 <= rating <= 5 else None


def parse_coordinate(value, lower, upper):
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    return coordinate if lower <= coordinate <= upper else None


def parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def clean_listings(homes):
    if not isinstance(homes, list):
        raise ValueError("Expected a JSON list of listings")
    rows = []
    rejected = Counter()
    seen_ids = set()

    for home in homes:
        if not isinstance(home, dict):
            rejected["malformed_record"] += 1
            continue
        listing = home.get("demandStayListing")
        if not isinstance(listing, dict):
            rejected["missing_id"] += 1
            continue
        listing_id = listing.get("id")
        if not isinstance(listing_id, str) or not listing_id.strip():
            rejected["missing_id"] += 1
            continue
        if listing_id in seen_ids:
            rejected["duplicate_id"] += 1
            continue
        try:
            price, currency_symbol, qualifier = parse_price(home)
        except ValueError as exc:
            rejected[str(exc)] += 1
            continue

        name_data = home.get("nameLocalized") or {}
        name = name_data.get("localizedStringWithTranslationPreference") if isinstance(name_data, dict) else None
        location = listing.get("location") or {}
        coordinates = location.get("coordinate") if isinstance(location, dict) else None
        coordinates = coordinates if isinstance(coordinates, dict) else {}
        params = home.get("listingParamOverrides") or {}
        params = params if isinstance(params, dict) else {}
        title = home.get("title")
        listing_type, separator, location_label = title.partition(" in ") if isinstance(title, str) else ("", "", "")
        bedrooms, bathrooms = parse_rooms(home)

        rows.append({
            "id": listing_id,
            "name": name if isinstance(name, str) and name.strip() else None,
            "latitude": parse_coordinate(coordinates.get("latitude"), -90, 90),
            "longitude": parse_coordinate(coordinates.get("longitude"), -180, 180),
            "price": price,
            "rating": parse_rating(home.get("avgRatingLocalized")),
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "stay_qualifier": qualifier,
            "checkin": parse_date(params.get("checkin")),
            "checkout": parse_date(params.get("checkout")),
            "listing_type": listing_type if separator else None,
            "location_label": location_label if separator else None,
            "currency_symbol": currency_symbol,
        })
        seen_ids.add(listing_id)

    return pd.DataFrame(rows, columns=COLUMNS), rejected


def main():
    with RAW_PATH.open(encoding="utf-8") as source:
        homes = json.load(source)
    cleaned, rejected = clean_listings(homes)
    cleaned.to_csv(OUTPUT_PATH, index=False)
    print(f"Raw records: {len(homes)}")
    print(f"Saved listings: {len(cleaned)} to {OUTPUT_PATH}")
    print(f"Rejected records: {sum(rejected.values())}")
    for reason, count in sorted(rejected.items()):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()
