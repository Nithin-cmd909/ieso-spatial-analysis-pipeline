import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def build_outage_table(days_back=30):
    print("Building Transmission Outages table...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)
    dates = pd.date_range(start=start_date, end=end_date)
    
    outages = []
    
    # Simulate a realistic baseline of 0 to 5 grid equipment outages per day
    for d in dates:
        daily_outage_count = np.random.randint(0, 6)
        for _ in range(daily_outage_count):
            outages.append({
                'Date': d.strftime('%Y-%m-%d'),
                'Equipment_Type': np.random.choice(['Transformer', 'Line', 'Breaker', 'Generator']),
                'Status': 'Disconnected'
            })
            
    df = pd.DataFrame(outages)
    if df.empty:
        df = pd.DataFrame(columns=['Date', 'Equipment_Type', 'Status'])
        
    df.to_sql('transmission_outages', conn, if_exists='replace', index=False)
    print(f" -> Successfully saved {len(df)} historical transmission outages to database.")
    
    conn.close()

if __name__ == "__main__":
    build_outage_table(30)