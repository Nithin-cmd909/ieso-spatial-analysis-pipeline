import sqlite3
import pandas as pd
import numpy as np
from statsmodels.tsa.api import VAR
from sklearn.metrics import mean_absolute_error, mean_squared_error

def train_svar_baseline():
    conn = sqlite3.connect('ieso_nodal_data.db')
    df = pd.read_sql_query("SELECT * FROM model_features", conn)
    conn.close()

    # Isolate a single node to create a continuous time-series
    node_name = 'ABITIBISF-LT.AG_T1'
    node_df = df[df['Node'] == node_name].copy()
    
    # Sort by Date and Hour to ensure strict chronological integrity
    node_df = node_df.sort_values(by=['Date', 'Hour']).reset_index(drop=True)
    
    # Select our endogenous variables (the variables that influence each other)
    ts_data = node_df[['True_Price_Spread', 'Spatial_Lag_t_1', 'wind_spd_kmh']].dropna()

    print(f"Training Spatial VAR Baseline for {node_name} on {len(ts_data)} chronological hours...")

    # Split into 80% train, 20% test (maintaining chronological order)
    split_idx = int(len(ts_data) * 0.8)
    train_data = ts_data.iloc[:split_idx]
    test_data = ts_data.iloc[split_idx:]

    # Fit the VAR model 
    # We test up to 3 hourly lags to find the best fit now that we have 30 days of data
    model = VAR(train_data)
    fitted_model = model.fit(maxlags=3)    
    print("\nOptimal Lag Order Selected:", fitted_model.k_ar)

    # Forecast the out-of-sample testing period
    lag_order = fitted_model.k_ar
    forecast_input = train_data.values[-lag_order:]
    steps = len(test_data)
    
    forecast = fitted_model.forecast(y=forecast_input, steps=steps)
    
    # Extract the predictions specifically for the True_Price_Spread (Column 0)
    predictions = forecast[:, 0]
    actuals = test_data['True_Price_Spread'].values

    # Calculate Error Metrics
    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))

    print("\n--- SVAR BASELINE PERFORMANCE ---")
    print(f"Mean Absolute Error: ${mae:.2f} per MWh")
    print(f"Root Mean Squared Error: ${rmse:.2f} per MWh")

if __name__ == "__main__":
    train_svar_baseline()