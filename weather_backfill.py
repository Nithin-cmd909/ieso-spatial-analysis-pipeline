import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

def fetch_weather_backfill(days_back=30):
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Fetching historical weather data from {start_str} to {end_str}...")
    
    # Open-Meteo free historical API for Toronto coordinates
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude=43.7001&longitude=-79.4163&"
        f"start_date={start_str}&end_date={end_str}&"
        f"hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=America%2FToronto"
    )
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        df = pd.DataFrame({
            'time': data['hourly']['time'],
            'temp_c': data['hourly']['temperature_2m'],
            'rel_humidity': data['hourly']['relative_humidity_2m'],
            'wind_spd_kmh': data['hourly']['wind_speed_10m']
        })
        
        df['time'] = pd.to_datetime(df['time'])
        df['date'] = df['time'].dt.strftime('%Y-%m-%d')
        
        # Standard APIs log hours as 0-23. The IESO logs hours as 1-24. 
        # We must add 1 so the merge aligns perfectly.
        df['hour'] = df['time'].dt.hour + 1 
        
        final_df = df[['date', 'hour', 'temp_c', 'rel_humidity', 'wind_spd_kmh']]
        
        final_df.to_sql('weather_hourly', conn, if_exists='replace', index=False)
        print(f" -> Successfully saved {len(final_df)} hours of weather data to database.")
    else:
        print(f"Failed to fetch weather data. Status code: {response.status_code}")
        
    conn.close()

if __name__ == "__main__":
    fetch_weather_backfill(30)