import sqlite3
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

def train_xgboost_challenger():
    conn = sqlite3.connect('ieso_nodal_data.db')
    df = pd.read_sql_query("SELECT * FROM model_features", conn)
    conn.close()

    node_name = 'ABITIBISF-LT.AG_T1'
    node_df = df[df['Node'] == node_name].copy()
    node_df = node_df.sort_values(by=['Date', 'Hour']).reset_index(drop=True)
    
    features = ['Spatial_Lag_t_1', 'wind_spd_kmh', 'Hour']
    target = 'True_Price_Spread'
    
    model_data = node_df[features + [target]].dropna()
    
    X = model_data[features]
    y = model_data[target]
    
    split_idx = int(len(model_data) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Training XGBoost Challenger for {node_name} on {len(X_train)} chronological hours...")
    
    model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    
    print("\n--- XGBOOST CHALLENGER PERFORMANCE ---")
    print(f"Mean Absolute Error: ${mae:.2f} per MWh")
    print(f"Root Mean Squared Error: ${rmse:.2f} per MWh")

if __name__ == "__main__":
    train_xgboost_challenger()