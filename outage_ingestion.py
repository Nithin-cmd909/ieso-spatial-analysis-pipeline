import sqlite3
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_transmission_outages():
    url = "https://reports-public.ieso.ca/public/TxOutagesTodayAll/PUB_TxOutagesTodayAll.xml"
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pinging official IESO Transmission Outage XML endpoint...")
    response = requests.get(url, timeout=15)
    
    if response.status_code == 200:
        # Parse the raw XML string
        root = ET.fromstring(response.content)
        
        # The IESO uses a strict schema namespace. We must define it to find the tags.
        ns = {'ieso': 'http://www.ieso.ca/schema'}
        
        outage_records = []
        
        # Find every single OutageRequest block in the document
        outages = root.findall('.//ieso:OutageRequest', ns)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(outages)} total outage requests. Flattening equipment lists...")
        
        for outage in outages:
            # Extract the core outage metadata
            outage_id = outage.find('ieso:OutageID', ns).text if outage.find('ieso:OutageID', ns) is not None else None
            start = outage.find('ieso:PlannedStart', ns).text if outage.find('ieso:PlannedStart', ns) is not None else None
            end = outage.find('ieso:PlannedEnd', ns).text if outage.find('ieso:PlannedEnd', ns) is not None else None
            status = outage.find('ieso:OutageRequestStatus', ns).text if outage.find('ieso:OutageRequestStatus', ns) is not None else None
            
            # Loop through the nested equipment blocks and create a flat record for each
            for equip in outage.findall('ieso:EquipmentRequested', ns):
                eq_name = equip.find('ieso:EquipmentName', ns).text if equip.find('ieso:EquipmentName', ns) is not None else None
                eq_type = equip.find('ieso:EquipmentType', ns).text if equip.find('ieso:EquipmentType', ns) is not None else None
                eq_volt = equip.find('ieso:EquipmentVoltage', ns).text if equip.find('ieso:EquipmentVoltage', ns) is not None else None
                
                outage_records.append({
                    'Outage_ID': outage_id,
                    'Planned_Start': start,
                    'Planned_End': end,
                    'Equipment_Name': eq_name,
                    'Equipment_Type': eq_type,
                    'Equipment_Voltage': eq_volt,
                    'Status': status
                })
        
        # Convert the flattened list of dictionaries into a clean pandas DataFrame
        df = pd.DataFrame(outage_records)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Success! Flattened into {len(df)} specific equipment outages.")
        return df
        
    else:
        print(f"Failed to fetch XML data. HTTP status: {response.status_code}")
        return None

if __name__ == "__main__":
    outage_df = fetch_transmission_outages()
    
    if outage_df is not None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Warehousing into SQLite...")
        
        conn = sqlite3.connect('ieso_nodal_data.db')
        outage_df.to_sql('transmission_outages', conn, if_exists='replace', index=False)
        conn.close()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Phase 1 Complete. Table 'transmission_outages' added to ieso_nodal_data.db.")