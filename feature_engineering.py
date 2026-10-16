import sqlite3
import pandas as pd

def build_features():
    print("Connecting to database...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    
    pricing_da = pd.read_sql_query("SELECT * FROM day_ahead_pricing", conn)
    pricing_rt = pd.read_sql_query("SELECT * FROM real_time_pricing", conn)
    weather_df = pd.read_sql_query("SELECT * FROM weather_hourly", conn)
    outages_df = pd.read_sql_query("SELECT * FROM transmission_outages", conn)
    
    # Merge Day-Ahead and Real-Time Pricing
    print("Merging Day-Ahead and Real-Time prices...")
    master_df = pd.merge(pricing_da, pricing_rt, on=['Date', 'Node', 'Hour'], how='inner')
    
    # Real-Time vs. Day-Ahead Arbitrage Spread
    print("Calculating True Arbitrage Spread (RT - DA)...")
    master_df['True_Price_Spread'] = master_df['RT_Energy_Price'] - master_df['Energy_Price']
    
    #  Weather Merging
    print("Merging Weather Data...")
    master_df = pd.merge(
        master_df, 
        weather_df[['date', 'hour', 'temp_c', 'rel_humidity', 'wind_spd_kmh']], 
        left_on=['Date', 'Hour'], 
        right_on=['date', 'hour'], 
        how='left'
    ).drop(columns=['date', 'hour'])
    
    #  Outage Integration (Grid Strain Metric)
    print("Integrating Transmission Outages...")
    daily_outages = outages_df.groupby('Date').size().reset_index(name='Active_Grid_Outages')
    master_df = pd.merge(master_df, daily_outages, on='Date', how='left')
    master_df['Active_Grid_Outages'] = master_df['Active_Grid_Outages'].fillna(0)
    
    # Temporal Lags & Spatial Spillovers (Grid Momentum)
    print("Calculating Temporal & Spatial Spillovers...")
    master_df = master_df.sort_values(['Node', 'Date', 'Hour'])
    
    master_df['Price_t_1'] = master_df.groupby('Node')['Energy_Price'].shift(1)
    master_df['Spatial_Lag_t_1'] = master_df.groupby(['Date', 'Hour'])['Price_t_1'].transform('mean')
    
    # Clean up empty rows from the lag calculation
    final_df = master_df.dropna()
    
    print("\nPhase 2 Complete! Master ML Table Ready:")
    print(final_df[['Date', 'Hour', 'Node', 'Energy_Price', 'RT_Energy_Price', 'True_Price_Spread', 'temp_c']].head())
    
    final_df.to_sql('model_features', conn, if_exists='replace', index=False)
    
    conn.close()
    return final_df

if __name__ == "__main__":
    df = build_features()