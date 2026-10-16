import io
import sqlite3
from datetime import datetime
import pandas as pd
import requests

def fetch_weather_data():
    """Fetches and cleans hourly weather observations for Toronto Pearson."""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    url = f"https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=51459&Year={current_year}&Month={current_month}&Day=1&timeframe=1&submit=Download+Data"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pinging Environment Canada servers...")
    
    response = requests.get(url, timeout=15)
    
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        
        target_columns = ['Date/Time (LST)', 'Temp (°C)', 'Rel Hum (%)', 'Wind Spd (km/h)']
        clean_df = df[target_columns].copy()
        clean_df = clean_df.dropna(subset=['Temp (°C)'])
        
        # Standardize column headers for SQL storage
        clean_df.columns = ['datetime_lst', 'temp_c', 'rel_humidity', 'wind_spd_kmh']
        
        # Parse datetime and extract Date and Hour (1-24) to match IESO format
        dt_series = pd.to_datetime(clean_df['datetime_lst'])
        clean_df['date'] = dt_series.dt.strftime('%Y-%m-%d')
        # Environment Canada hours are 00:00 to 23:00; add 1 to map to IESO Hour 1-24
        clean_df['hour'] = dt_series.dt.hour + 1
        clean_df['station_id'] = '51459'
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingested {len(clean_df)} weather rows.")
        return clean_df
    else:
        print(f"Failed to fetch weather data. Status: {response.status_code}")
        return None

if __name__ == "__main__":
    weather_df = fetch_weather_data()
    
    if weather_df is not None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warehousing into SQLite...")
        
        conn = sqlite3.connect('ieso_nodal_data.db')
        # Replace or append table
        weather_df.to_sql('weather_hourly', conn, if_exists='replace', index=False)
        conn.close()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed. Table 'weather_hourly' updated in ieso_nodal_data.db")