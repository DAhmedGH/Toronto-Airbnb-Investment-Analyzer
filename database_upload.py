"""Replace the listings table with a validated local snapshot."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import MetaData, Numeric, Table, create_engine, text
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from clean_data import COLUMNS


DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = DIRECTORY / "cleaned_airbnb_data.csv"


def load_validated_data(path=CSV_PATH):
    data = pd.read_csv(path, dtype={"id": "string"})
    if data.empty:
        raise ValueError("The cleaned CSV is empty; the database was not changed")
    missing = set(COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"The cleaned CSV is missing columns: {', '.join(sorted(missing))}")
    if data["id"].isna().any() or data["id"].str.strip().eq("").any():
        raise ValueError("The cleaned CSV contains a missing listing ID")
    if data["id"].duplicated().any():
        raise ValueError("The cleaned CSV contains duplicate listing IDs")

    for column in ("latitude", "longitude", "price", "rating", "bedrooms", "bathrooms"):
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not np.isfinite(data[column].dropna().to_numpy(dtype=float)).all():
            raise ValueError(f"The cleaned CSV contains nonfinite {column} values")
    if data["price"].isna().any() or data["price"].le(0).any():
        raise ValueError("Every listing needs a positive advertised stay price")
    if data["rating"].dropna().lt(0).any() or data["rating"].dropna().gt(5).any():
        raise ValueError("Ratings must be between 0 and 5")
    if data["bedrooms"].dropna().lt(0).any() or data["bedrooms"].dropna().mod(1).ne(0).any():
        raise ValueError("Bedroom counts must be nonnegative whole numbers")
    if data["bathrooms"].dropna().lt(0).any():
        raise ValueError("Bathroom counts must be nonnegative")

    for column in ("checkin", "checkout"):
        data[column] = pd.to_datetime(data[column], format="%Y-%m-%d", errors="raise").dt.date
    return data[COLUMNS]


def replace_listings(data, database_url):
    """Validate the destination schema and refresh it in one transaction."""
    engine = create_engine(database_url, connect_args={"connect_timeout": 10})
    try:
        with engine.begin() as connection:
            try:
                table = Table("airbnb_listings", MetaData(), schema="public", autoload_with=connection)
            except NoSuchTableError as exc:
                raise ValueError("public.airbnb_listings is missing; apply schema.sql first") from exc
            missing = set(COLUMNS) - set(table.columns.keys())
            if missing:
                raise ValueError(f"Database table is missing columns: {', '.join(sorted(missing))}")
            if {column.name for column in table.primary_key.columns} != {"id"}:
                raise ValueError("Database table needs id as its primary key; apply schema.sql first")
            if not isinstance(table.c.bathrooms.type, Numeric):
                raise ValueError("Database bathrooms column must be NUMERIC; apply schema.sql first")
            connection.execute(text("DELETE FROM public.airbnb_listings"))
            data.to_sql("airbnb_listings", connection, schema="public", if_exists="append", index=False)
    finally:
        engine.dispose()


def main():
    load_dotenv(DIRECTORY / ".env")
    try:
        data = load_validated_data()
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is required for database upload")
        replace_listings(data, database_url)
    except ValueError as exc:
        raise SystemExit(f"Upload aborted: {exc}") from None
    except SQLAlchemyError as exc:
        raise SystemExit(f"Upload failed ({type(exc).__name__}); the transaction was rolled back") from None
    print(f"Uploaded {len(data)} listings to public.airbnb_listings")


if __name__ == "__main__":
    main()
