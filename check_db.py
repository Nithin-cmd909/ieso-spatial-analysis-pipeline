import sqlite3
import pandas as pd

# Connect to the database and grab the first 10 rows of the master table
conn = sqlite3.connect('ieso_nodal_data.db')
master_df = pd.read_sql_query("SELECT * FROM model_features LIMIT 10", conn)

print("--- EXACT COLUMNS IN MASTER TABLE ---")
print(master_df.columns.tolist())

print("\n--- FIRST 5 ROWS ---")
print(master_df.head())

conn.close()