import sqlite3
import pandas as pd
import numpy as np

def inject_macro_demand():
    print("Connecting to database...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    # Load your existing features
    df = pd.read_sql_query("SELECT * FROM model_features", conn)
    
    print("Simulating IESO Provincial Hourly Demand data for the dataset dates...")
    # In a live environment, this would pull directly from the IESO XML/CSV reports.
    # For now, we will synthesize a realistic provincial demand curve based on the hour and temperature.
    
    # Base load is around 13,000 MW, peaking up to 18,000+ MW depending on time of day
    np.random.seed(42)
    df['Provincial_Demand_MW'] = 13000 + (df['Hour'] * 150) + (df['temp_c'] * 80) + np.random.normal(0, 500, len(df))
    
    # Calculate the change in demand from the previous hour (the "Ramp")
    df['Demand_Delta_MW'] = df.groupby('Node')['Provincial_Demand_MW'].diff().fillna(0)
    
    # Save the updated features back to the database
    df.to_sql('model_features', conn, if_exists='replace', index=False)
    
    print("Successfully injected 'Provincial_Demand_MW' and 'Demand_Delta_MW' into the model features.")
    conn.close()

if __name__ == "__main__":
    inject_macro_demand()