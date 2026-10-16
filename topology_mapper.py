import sqlite3
import pandas as pd
import re
from difflib import get_close_matches

def map_topology():
    print("Starting NLP Topology Mapping...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    # 1. Load the raw outages and the unique grid nodes
    outages = pd.read_sql_query("SELECT * FROM transmission_outages", conn)
    nodes_df = pd.read_sql_query("SELECT DISTINCT Node FROM model_features", conn)
    unique_nodes = nodes_df['Node'].tolist()
    
    # 2. NLP Cleaning: Strip suffixes to find the geographic base name
    # E.g., 'ABITIBISF-LT.AG_T1' becomes 'ABITIBISF'
    def clean_node(n):
        return re.split(r'[-.]', n)[0].upper()
        
    node_lookup = {clean_node(n): n for n in unique_nodes}
    clean_node_list = list(node_lookup.keys())
    
    print(f"Attempting to map {len(outages['Equipment_Type'].unique())} unique equipment logs to {len(unique_nodes)} physical nodes...")
    
    # 3. Fuzzy String Matching
    mapped_records = []
    for _, row in outages.iterrows():
        date = row['Date']
        equip = str(row['Equipment_Type']).upper()
        
        # Grab the primary location word from the equipment text
        equip_base = equip.split()[0] if equip else ""
        
        # Find the closest matching node using Levenshtein distance (70% similarity cutoff)
        matches = get_close_matches(equip_base, clean_node_list, n=1, cutoff=0.7)
        
        if matches:
            actual_node = node_lookup[matches[0]]
            mapped_records.append({'Date': date, 'Node': actual_node, 'Node_Outage_Flag': 1})
    
    # 4. Save the localized mappings
    local_outages = pd.DataFrame(mapped_records).drop_duplicates()
    local_outages.to_sql('localized_outages', conn, if_exists='replace', index=False)
    print(f" -> Successfully locked in {len(local_outages)} localized outage events.")
    
    # 5. Inject the new highly-specific feature into your ML Master Table
    print("Injecting localized congestion flags into `model_features`...")
    cursor = conn.cursor()
    
    # Create the new column safely
    try:
        cursor.execute("ALTER TABLE model_features ADD COLUMN Node_Outage_Flag INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        cursor.execute("UPDATE model_features SET Node_Outage_Flag = 0")
        
    # Update the master table where a local outage occurred
    cursor.execute("""
        UPDATE model_features 
        SET Node_Outage_Flag = 1 
        WHERE EXISTS (
            SELECT 1 FROM localized_outages lo 
            WHERE lo.Date = model_features.Date 
            AND lo.Node = model_features.Node
        )
    """)
    conn.commit()
    conn.close()
    print("Topology mapping complete! Your nodes are now geographically aware of broken equipment.")

if __name__ == "__main__":
    map_topology()