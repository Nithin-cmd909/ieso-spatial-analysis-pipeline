import sqlite3
import pandas as pd
from sklearn.metrics import accuracy_score

conn = sqlite3.connect('ieso_nodal_data.db')
df = pd.read_sql_query("SELECT True_Price_Spread, Predicted_Direction, Long_Spread_Probability, Spread_Direction FROM model_directional_predictions", conn)
conn.close()

# Evaluate at different confidence thresholds
for threshold in [0.50, 0.55, 0.60, 0.65]:
    # For long trades (probability > threshold) or short trades (probability < 1 - threshold)
    confident_trades = df[(df['Long_Spread_Probability'] >= threshold) | (df['Long_Spread_Probability'] <= (1 - threshold))]
    
    if len(confident_trades) > 0:
        acc = accuracy_score(confident_trades['Spread_Direction'], confident_trades['Predicted_Direction'])
        coverage = len(confident_trades) / len(df)
        print(f"Threshold {threshold*100:.0f}% -> Accuracy: {acc:.2%} (Trades {coverage:.1%} of the time)")