import sqlite3
import pandas as pd
import requests
import io
from datetime import datetime

def fetch_real_time_lmps():
    url = "https://reports-public.ieso.ca/public/RealtimeEnergyLMP/PUB_RealtimeEnergyLMP.csv"
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pinging official IESO Real-Time LMP endpoint...")
    
    response = requests.get(url, timeout=15)
    
    if response.status_code == 200:
        raw_text = response.text
        
        # 1. Extract the Date hidden in the first line (e.g., "CREATED AT ... FOR 2026/10/11")
        first_line = raw_text.split('\n')[0]
        date_str_raw = first_line.strip().split('FOR ')[-1] # Grabs the "2026/10/11" part
        clean_date = date_str_raw.replace('/', '-') # Formats to "2026-10-11" to match your DB
        
        # 2. Skip exactly 1 row to hit the true headers
        df = pd.read_csv(io.StringIO(raw_text), skiprows=1)
        
        # 3. Clean and map the exact columns we found in the diagnostic
        df.columns = df.columns.str.strip()
        column_mapping = {
            'Delivery Hour': 'Hour',
            'Pricing Location': 'Node',
            'LMP': 'RT_Energy_Price',
            'Energy Loss Price': 'RT_Loss_Price',
            'Energy Congestion Price': 'RT_Congestion_Price'
        }
        
        df = df.rename(columns=lambda x: column_mapping.get(x, x))
        
        # Inject the parsed date into every row so it can join with your Day-Ahead data
        df['Date'] = clean_date
        
        df = df.dropna(subset=['RT_Energy_Price'])
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingested {len(df)} 5-minute intervals for {clean_date}. Aggregating...")
        
        # Ensure prices are treated as numbers
        for col in ['RT_Energy_Price', 'RT_Loss_Price', 'RT_Congestion_Price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 4. Roll the 12 five-minute intervals into single hourly blocks
        hourly_rt_df = df.groupby(['Date', 'Hour', 'Node']).agg({
            'RT_Energy_Price': 'mean',
            'RT_Loss_Price': 'mean',
            'RT_Congestion_Price': 'mean'
        }).reset_index()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Success! Rolled up into {len(hourly_rt_df)} hourly real-time observations.")
        return hourly_rt_df
        
    else:
        print(f"Failed to fetch Real-Time data. HTTP status: {response.status_code}")
        return None

if __name__ == "__main__":
    rt_df = fetch_real_time_lmps()
    
    if rt_df is not None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warehousing into SQLite...")
        
        conn = sqlite3.connect('ieso_nodal_data.db')
        rt_df.to_sql('real_time_pricing', conn, if_exists='replace', index=False)
        conn.close()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed. Table 'real_time_pricing' added to ieso_nodal_data.db")