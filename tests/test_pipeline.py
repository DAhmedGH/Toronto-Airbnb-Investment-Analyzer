"""Small checks for the saved-data pipeline and failed extractions."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import requests


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bulk_extract import extract_to_file  # noqa: E402
from clean_data import clean_listings  # noqa: E402
from database_upload import load_validated_data  # noqa: E402


def home(listing_id="one", price="$1,000.25", rooms=None, rating="New"):
    return {
        "demandStayListing": {
            "id": listing_id,
            "location": {"coordinate": {"latitude": 43.65, "longitude": -79.4}},
        },
        "nameLocalized": {"localizedStringWithTranslationPreference": "Sample stay"},
        "structuredDisplayPrice": {
            "primaryLine": {"price": price, "qualifier": "for 5 nights"},
        },
        "structuredContent": {"primaryLine": [{"body": body} for body in (rooms or [])]},
        "avgRatingLocalized": rating,
        "listingParamOverrides": {"checkin": "2026-10-01", "checkout": "2026-10-06"},
        "title": "Apartment in Toronto",
    }


def test_regular_and_discounted_prices_keep_stay_context():
    regular = home()
    discounted = home("two")
    discounted["structuredDisplayPrice"]["primaryLine"] = {
        "discountedPrice": "$719", "originalPrice": "$790", "qualifier": "for 5 nights",
    }
    cleaned, rejected = clean_listings([regular, discounted])
    assert list(cleaned.price) == [1000.25, 719]
    assert cleaned.stay_qualifier.tolist() == ["for 5 nights"] * 2
    assert cleaned.currency_symbol.tolist() == ["$"] * 2
    assert cleaned.listing_type.tolist() == ["Apartment"] * 2
    assert cleaned.location_label.tolist() == ["Toronto"] * 2
    assert sum(rejected.values()) == 0


def test_fractional_baths_studio_unknown_bedrooms_and_missing_ratings():
    studio = home("studio", rooms=["Studio", "2.5 baths"])
    unknown = home("unknown", rooms=["1.5 baths"], rating=None)
    reviewed = home("reviewed", rooms=["2 bedrooms", "2 baths"], rating="4.92 (30)")
    cleaned, _ = clean_listings([studio, unknown, reviewed])
    assert cleaned.bedrooms.iloc[0] == 0
    assert pd.isna(cleaned.bedrooms.iloc[1])
    assert cleaned.bedrooms.iloc[2] == 2
    assert cleaned.bathrooms.tolist() == [2.5, 1.5, 2]
    assert cleaned.rating.isna().tolist() == [True, True, False]
    assert cleaned.rating.iloc[2] == 4.92


def test_malformed_records_duplicates_and_empty_input():
    valid = home()
    missing_id = home("")
    invalid_price = home("bad-price", price="call for price")
    cleaned, rejected = clean_listings([None, {}, missing_id, invalid_price, valid, valid])
    assert cleaned.id.tolist() == ["one"]
    assert rejected == {
        "malformed_record": 1, "missing_id": 2,
        "invalid_price": 1, "duplicate_id": 1,
    }
    empty, empty_rejected = clean_listings([])
    assert empty.empty and list(empty.columns) == list(cleaned.columns)
    assert not empty_rejected
    with pytest.raises(ValueError, match="JSON list"):
        clean_listings({"data": []})


class Response:
    def __init__(self, payload=None, http_error=False):
        self.payload = payload
        self.http_error = http_error

    def raise_for_status(self):
        if self.http_error:
            raise requests.HTTPError("unavailable")

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class Requester:
    def __init__(self, responses):
        self.responses = responses
        self.pages = []

    def get(self, _url, *, headers, params, timeout):
        assert headers["x-rapidapi-key"] == "test-key"
        assert timeout > 0
        self.pages.append(params["page"])
        return self.responses[params["page"] - 1]


def page(number, total, ids):
    return Response({
        "status": True, "currentPage": number, "totalPages": total,
        "data": {"homes": [{"demandStayListing": {"id": item}} for item in ids]},
    })


def test_complete_pagination_saves_snapshot(tmp_path):
    destination = tmp_path / "bulk.json"
    requester = Requester([page(1, 2, ["one", "two"]), page(2, 2, ["two", "three"])])
    homes = extract_to_file("test-key", destination, requester)
    assert requester.pages == [1, 2]
    assert len(homes) == 4
    assert len({item["demandStayListing"]["id"] for item in homes}) == 3
    assert json.loads(destination.read_text(encoding="utf-8")) == homes


@pytest.mark.parametrize("failure", [
    Response(http_error=True), Response(ValueError("bad JSON")), Response(None),
    Response({"status": False, "data": {"homes": []}}),
])
def test_failed_second_page_preserves_existing_snapshot(tmp_path, failure):
    destination = tmp_path / "bulk.json"
    destination.write_text('[{"saved": true}]', encoding="utf-8")
    requester = Requester([page(1, 2, ["one"]), failure])
    with pytest.raises(RuntimeError):
        extract_to_file("test-key", destination, requester)
    assert destination.read_text(encoding="utf-8") == '[{"saved": true}]'


def test_repeated_page_is_detected(tmp_path):
    destination = tmp_path / "bulk.json"
    requester = Requester([page(1, 2, ["one"]), page(2, 2, ["one"])])
    with pytest.raises(RuntimeError, match="repeats"):
        extract_to_file("test-key", destination, requester)
    assert not destination.exists()


def test_upload_rejects_empty_csv_before_connecting(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("id,price\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_validated_data(path)


def test_corrected_csv_passes_upload_validation():
    data = load_validated_data(Path(__file__).resolve().parents[1] / "cleaned_airbnb_data.csv")
    assert len(data) == 149
    assert (data.bathrooms.dropna() % 1 != 0).sum() == 26
    assert data.id.is_unique
