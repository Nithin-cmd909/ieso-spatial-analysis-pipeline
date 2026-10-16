import requests
import re
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

def fetch_real_outages(days_back=30):
    print("Fetching real historical transmission outages from IESO...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days_back)
    dates = pd.date_range(start=start_date, end=end_date)
    
    outage_records = []
    
    for d in dates:
        date_str = d.strftime('%Y%m%d')
        # Target the planned outages public report
        url = f"https://reports-public.ieso.ca/public/TxOutages1to30DaysPlanned/PUB_TxOutages1to30DaysPlanned_{date_str}.xml"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # BRUTE FORCE: Ignore XML rules, just rip anything inside an EquipmentName tag
                equipments = re.findall(r'EquipmentName>([^<]+)</', response.text)
                
                for eq in equipments:
                    outage_records.append({
                        'Date': d.strftime('%Y-%m-%d'),
                        'Equipment_Type': eq.strip()
                    })
        except Exception:
            continue

    df = pd.DataFrame(outage_records)
    if not df.empty:
        df.to_sql('transmission_outages', conn, if_exists='replace', index=False)
        print(f" -> Successfully brute-forced {len(df)} real historical grid outages.")
    else:
        print(" -> Warning: Could not rip data. Retaining existing table.")

    conn.close()

if __name__ == "__main__":
    fetch_real_outages(30)