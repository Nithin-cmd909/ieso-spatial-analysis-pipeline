import requests
import pandas as pd
import io
from datetime import datetime, timedelta
import sqlite3
import re

def fetch_realtime_backfill(days_back=30):
    conn = sqlite3.connect('ieso_nodal_data.db')
    start_date = datetime.now() - timedelta(days=1)
    
    print("Fetching master directory listing from IESO servers...")
    dir_url = "https://reports-public.ieso.ca/public/RealtimeEnergyLMP/"
    response = requests.get(dir_url)
    
    if response.status_code != 200:
        print("Failed to access IESO directory.")
        return
        
    all_files = set(re.findall(r'PUB_RealtimeEnergyLMP_[0-9]+(?:_v[0-9]+)?\.csv', response.text))
    
    for i in range(days_back):
        target_date = start_date - timedelta(days=i)
        url_date = target_date.strftime('%Y%m%d')
        db_date = target_date.strftime('%Y-%m-%d')
        
        day_files = [f for f in all_files if f"PUB_RealtimeEnergyLMP_{url_date}" in f]
        
        if not day_files:
            print(f"[{db_date}] No files found. Moving to next day.")
            continue
            
        latest_hourly_files = {}
        for f in day_files:
            match = re.search(r'PUB_RealtimeEnergyLMP_\d{8}(\d{2})(?:_v(\d+))?\.csv', f)
            if match:
                hour = match.group(1)
                version = int(match.group(2)) if match.group(2) else 0
                if hour not in latest_hourly_files or version > latest_hourly_files[hour][1]:
                    latest_hourly_files[hour] = (f, version)
        
        print(f"[{db_date}] Downloading {len(latest_hourly_files)} hourly files...")
        daily_df_list = []
        
        for hour, (filename, ver) in latest_hourly_files.items():
            url = f"https://reports-public.ieso.ca/public/RealtimeEnergyLMP/{filename}"
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    # FIXED: Explicitly naming the columns because the file lacks headers
                    col_names = ['Hour', 'Interval', 'Node', 'RT_Energy_Price', 'Loss_Price', 'Congestion_Price']
                    df = pd.read_csv(io.StringIO(res.text), skiprows=3, names=col_names)
                    
                    hourly_df = df.groupby(['Hour', 'Node'])['RT_Energy_Price'].mean().reset_index()
                    daily_df_list.append(hourly_df)
            except Exception as e:
                pass
                
        if daily_df_list:
            final_daily_df = pd.concat(daily_df_list, ignore_index=True)
            final_daily_df.insert(0, 'Date', db_date)
            final_daily_df.to_sql('real_time_pricing', conn, if_exists='append', index=False)
            print(f" -> Saved {len(final_daily_df)} Real-Time rows to database.")
            
    print("\nRunning deduplication cleanup...")
    try:
        conn.execute("""
            DELETE FROM real_time_pricing 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM real_time_pricing 
                GROUP BY Date, Hour, Node
            )
        """)
        conn.commit()
        cursor = conn.execute("SELECT COUNT(*) FROM real_time_pricing")
        print(f"\nReal-Time backfill complete! Total unique rows: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Cleanup skipped or failed: {e}")
        
    conn.close()

if __name__ == "__main__":
    fetch_realtime_backfill(30)