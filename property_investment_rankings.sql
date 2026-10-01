-- Run after schema.sql on a new database. The current Supabase view already exists.
CREATE VIEW public.property_investment_rankings AS
SELECT
    name,
    bedrooms,
    bathrooms,
    rating,
    price,
    RANK() OVER (PARTITION BY bedrooms ORDER BY price DESC) AS price_rank_in_category,
    ROUND((AVG(price) OVER (PARTITION BY bedrooms))::NUMERIC, 2) AS avg_category_price
FROM public.airbnb_listings
WHERE price > 0::DOUBLE PRECISION;
