import requests
import json
import time

url = "https://airbnb-search.p.rapidapi.com/property/search"

headers = {
	"x-rapidapi-key": "YOUR_RAPIDAPI_KEY_HERE",
	"x-rapidapi-host": "airbnb-search.p.rapidapi.com",
	"Content-Type": "application/json"
}

all_homes = [] 

print("Initiating Bulk Extraction Pipeline...")

# Loop through Page 1 to Page 10
for page in range(1, 11):
    print(f"Fetching properties on Page {page}...")
    
    querystring = {
        "query": "Toronto, Ontario, Canada",
        "page": str(page)
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()
    
    homes_on_page = data.get('data', {}).get('homes', [])
    
    if not homes_on_page:
        print(f"Page {page} came back empty. Stopping early.")
        break
        
    all_homes.extend(homes_on_page)
    
    time.sleep(2)

with open('bulk_airbnb_data.json', 'w', encoding='utf-8') as f:
    json.dump(all_homes, f, indent=4)

print(f"Pipeline Complete! We successfully extracted {len(all_homes)} properties.")