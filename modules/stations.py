import pandas as pd
import json

file_name = 'stations.json'

print(f"Loading {file_name}...")
with open(file_name, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Flatten the GeoJSON data
if 'features' in data:
    df = pd.json_normalize(data['features'])
else:
    df = pd.json_normalize(data)

print("Columns found in JSON:", df.columns.tolist())

# 2. Rename the 'properties' columns
df = df.rename(columns={
    'properties.code': 'code',
    'properties.name': 'Station'
})

# 3. Extract Latitude and Longitude from 'geometry.coordinates'
# GeoJSON standard stores coordinates as [Longitude, Latitude]
if 'geometry.coordinates' in df.columns:
    # Get the first item (Index 0) for Longitude, second item (Index 1) for Latitude
    df['Longitude'] = df['geometry.coordinates'].apply(lambda x: x[0] if isinstance(x, list) and len(x) == 2 else None)
    df['Latitude'] = df['geometry.coordinates'].apply(lambda x: x[1] if isinstance(x, list) and len(x) == 2 else None)
else:
    print("⚠️ Error: Could not find 'geometry.coordinates'.")
    exit()

# 4. Clean the data
df = df.dropna(subset=['code', 'Station', 'Latitude', 'Longitude'])

# 5. Automatically tag Junctions
df['is_junction'] = df['Station'].astype(str).str.upper().str.contains(' JN|JUNCTION')

# 6. Save the final CSV
final_df = df[['code', 'Station', 'Latitude', 'Longitude', 'is_junction']]
final_df.to_csv('all_india_stations.csv', index=False)

print(f"✅ Success! Extracted and formatted {len(final_df)} stations into 'all_india_stations.csv'.")