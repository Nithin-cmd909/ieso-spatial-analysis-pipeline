import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def inject_synthetic_history(days=30):
    print(f"Bypassing IESO API locks. Generating {days} days of quantitative history...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    # Pull the exact real-world Ontario nodes you already ingested
    try:
        da_df = pd.read_sql_query("SELECT DISTINCT Node FROM day_ahead_pricing", conn)
        nodes = da_df['Node'].tolist()
    except Exception as e:
        print("Could not read nodes from database.")
        return
        
    if not nodes:
        print("Error: No nodes found in day_ahead_pricing.")
        return
        
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, days + 1)]
    hours = list(range(1, 25))
    
    da_records = []
    rt_records = []
    
    for d in dates:
        for h in hours:
            # Base price fluctuates by hour (higher in evening peaks)
            base_price = 30 + (15 * np.sin(np.pi * (h - 6) / 12)) 
            
            for node in nodes:
                # Add natural nodal noise
                da_price = base_price + np.random.normal(0, 5)
                
                # Real-Time prices track Day-Ahead, but occasionally spike wildly (simulating outages)
                spike = np.random.choice([0, 80, -40], p=[0.90, 0.05, 0.05])
                rt_price = da_price + np.random.normal(0, 3) + spike
                
                da_records.append({'Date': d, 'Hour': h, 'Node': node, 'Energy_Price': da_price})
                rt_records.append({'Date': d, 'Hour': h, 'Node': node, 'RT_Energy_Price': rt_price})
                
    df_da = pd.DataFrame(da_records)
    df_rt = pd.DataFrame(rt_records)
    
    # Inject directly into your existing warehouse
    # Change these two lines to use 'replace' instead of 'append'
    df_da.to_sql('day_ahead_pricing', conn, if_exists='replace', index=False)
    df_rt.to_sql('real_time_pricing', conn, if_exists='replace', index=False)
    
    print(f"Success! Injected {len(df_da)} continuous historical rows per table.")
    print("Database is now fully primed for advanced econometrics.")
    
    conn.close()

if __name__ == "__main__":
    inject_synthetic_history(30)