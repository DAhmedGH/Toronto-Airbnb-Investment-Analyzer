import pandas as pd
from sqlalchemy import create_engine, text

# 1. Load the clean spreadsheet we just made
print("Loading clean CSV...")
df = pd.read_csv('cleaned_airbnb_data.csv')

# 2. Our Supabase Connection String
DATABASE_URI = "postgresql://postgres:"YOUR_SUPABASE_PASSWORD_HERE"@db.luyytzdynxryelqykptp.supabase.co:5432/postgres"

# 3. Connect to the cloud database
print("Connecting to Supabase PostgreSQL...")
engine = create_engine(DATABASE_URI)

with engine.begin() as conn:
    print("Sweeping out the old data...")
    conn.execute(text("DELETE FROM airbnb_listings;"))

# 4. Push the data 
df.to_sql('airbnb_listings', engine, if_exists='append', index=False)

print(f"Success! {len(df)} properties pushed to the cloud database.")