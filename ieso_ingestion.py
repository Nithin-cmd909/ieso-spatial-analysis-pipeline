import requests
import pandas as pd 
import io
from datetime import datetime 
import sqlite3

def fetch_day_ahead_lmp(): 
    url = "https://reports-public.ieso.ca/public/DAHourlyEnergyLMP/PUB_DAHourlyEnergyLMP.csv"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pinging IESO servers...")

    response = requests.get(url)

    if response.status_code == 200:
        raw_csv = response.text
        # We skip the 3 lines of metadata and assign our own clean column names
        column_names = ['Hour', 'Node', 'Energy_Price', 'Loss_Price', 'Congestion_Price']
        df = pd.read_csv(io.StringIO(raw_csv), skiprows=3, names=column_names)
        return df 

    else: 
        print(f"Failed to fetch data. HTTP status: {response.status_code}")
        return None 

if __name__ == "__main__":
    lmp_data = fetch_day_ahead_lmp()

    if lmp_data is not None: 
        # Add today's date so we can track daily data separately
        lmp_data.insert(0, 'Date', datetime.now().strftime('%Y-%m-%d'))
        
        print("\nData Snapshot:")
        print(lmp_data.columns.tolist())
        print(lmp_data.head())

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to SQLite database...")
        conn = sqlite3.connect('ieso_nodal_data.db')

        # Save to database
        lmp_data.to_sql('day_ahead_pricing', conn, if_exists='append', index=False)

        # Instantly delete any duplicates based on Date, Hour, and Node
        conn.execute("""
            DELETE FROM day_ahead_pricing 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM day_ahead_pricing 
                GROUP BY Date, Hour, Node
            )
        """)
        conn.commit()
        conn.close()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Success! Clean data saved to ieso_nodal_data.db")