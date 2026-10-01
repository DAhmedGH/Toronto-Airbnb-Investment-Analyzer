-- Fresh-table definition matching the verified Supabase schema.
-- The existing Supabase table is already configured; do not rerun this there.
CREATE TABLE public.airbnb_listings (
    id TEXT PRIMARY KEY,
    name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    price DOUBLE PRECISION,
    rating DOUBLE PRECISION,
    bedrooms BIGINT,
    bathrooms NUMERIC(4, 1),
    stay_qualifier TEXT,
    checkin DATE,
    checkout DATE,
    listing_type TEXT,
    location_label TEXT,
    currency_symbol TEXT
);
