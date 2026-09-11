import json
import pandas as pd
import re

print("Loading Bulk JSON data...")
with open('bulk_airbnb_data.json', 'r', encoding='utf-8') as f:
    homes = json.load(f) 

print(f"Found {len(homes)} properties to clean.")
clean_listings = []

for home in homes:
    listing = home.get('demandStayListing') or {}
    listing_id = listing.get('id')
    
    name_loc = home.get('nameLocalized') or {}
    name = name_loc.get('localizedStringWithTranslationPreference', 'Unknown')
    
    loc_data = listing.get('location') or {}
    coord = loc_data.get('coordinate') or {}
    lat = coord.get('latitude')
    lon = coord.get('longitude')
    
    price_data = home.get('structuredDisplayPrice') or {}
    primary_price = price_data.get('primaryLine') or {}
    price_str = primary_price.get('price', '0')

    if price_str:
        clean_price = float(price_str.replace('$', '').replace(',', '').strip())
    else:
        clean_price = 0.0
    
    rating_str = home.get('avgRatingLocalized') or ''
    if rating_str == 'New' or not rating_str:
        rating = None 
    else:
        try:
            rating = float(rating_str.split(' ')[0])
        except:
            rating = None
        
    bedrooms = 0
    bathrooms = 0
    
    structured_content = home.get('structuredContent') or {}
    primary_line = structured_content.get('primaryLine') or []
    
    for item in primary_line:
        item = item or {}
        body = item.get('body') or ''
        body = body.lower()
        
        if 'bedroom' in body or 'studio' in body:
            nums = re.findall(r'\d+', body)
            bedrooms = int(nums[0]) if nums else 1 
        elif 'bath' in body:
            nums = re.findall(r'\d+', body)
            bathrooms = int(nums[0]) if nums else 1
            
    if clean_price > 0:
        clean_listings.append({
            'id': listing_id,
            'name': name,
            'latitude': lat,
            'longitude': lon,
            'price': clean_price,
            'rating': rating,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms
        })

df = pd.DataFrame(clean_listings)

df['rating'] = df['rating'].fillna(df['rating'].mean()).round(2)
df = df.drop_duplicates(subset=['id']) 

df.to_csv('cleaned_airbnb_data.csv', index=False)
print(f"Data cleaned! {len(df)} properties saved perfectly to cleaned_airbnb_data.csv")