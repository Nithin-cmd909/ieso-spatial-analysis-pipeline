import sqlite3
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

def train_walk_forward_classifier():
    print("Connecting to database...")
    conn = sqlite3.connect('ieso_nodal_data.db')
    df = pd.read_sql_query("SELECT * FROM model_features ORDER BY Date, Hour", conn)

    features = [
        'Hour', 'Energy_Price', 'Loss_Price', 'Congestion_Price',
        'temp_c', 'rel_humidity', 'wind_spd_kmh', 'Node_Outage_Flag',
        'Price_t_1', 'Spatial_Lag_t_1',
        'Provincial_Demand_MW', 'Demand_Delta_MW'
    ]
    
    df['Spread_Direction'] = (df['True_Price_Spread'] > 0).astype(int)
    df = df.dropna(subset=features + ['Spread_Direction'])

    # 2. Walk-Forward Setup (14-Day Rolling Window)
    unique_dates = df['Date'].drop_duplicates().sort_values().tolist()
    window_size = 14
    
    if len(unique_dates) <= window_size:
        print("Not enough days for walk-forward validation.")
        return

    print(f"Starting Walk-Forward Validation across {len(unique_dates) - window_size} trading days...")
    
    all_predictions = []
    feature_importances = []

    # 3. Rolling Training Loop
    for i in range(window_size, len(unique_dates)):
        train_dates = unique_dates[i - window_size : i]
        test_date = unique_dates[i]
        
        train_mask = df['Date'].isin(train_dates)
        test_mask = df['Date'] == test_date
        
        X_train, y_train = df.loc[train_mask, features], df.loc[train_mask, 'Spread_Direction']
        X_test, y_test = df.loc[test_mask, features], df.loc[test_mask, 'Spread_Direction']
        
        # Train XGBoost for this specific window
        clf = XGBClassifier(
            n_estimators=200,
            learning_rate=0.03,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=(1 - y_train.mean()) / y_train.mean(),
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )
        
        clf.fit(X_train, y_train)
        
        # Predict the next unseen day
        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)[:, 1]
        
        # Store results
        test_results = df.loc[test_mask, ['Date', 'Hour', 'Node', 'True_Price_Spread', 'Spread_Direction']].copy()
        test_results['Predicted_Direction'] = preds
        test_results['Long_Spread_Probability'] = probs
        all_predictions.append(test_results)
        
        feature_importances.append(clf.feature_importances_)
        
        print(f"Trained up to {train_dates[-1]} -> Evaluated on {test_date} (Acc: {accuracy_score(y_test, preds):.2%})")

    # 4. Aggregate Walk-Forward Results
    final_preds_df = pd.concat(all_predictions, ignore_index=True)
    overall_acc = accuracy_score(final_preds_df['Spread_Direction'], final_preds_df['Predicted_Direction'])
    overall_auc = roc_auc_score(final_preds_df['Spread_Direction'], final_preds_df['Long_Spread_Probability'])

    print("\n--- Walk-Forward Validation Complete ---")
    print(f"Aggregated Rolling Accuracy : {overall_acc:.2%}")
    print(f"Aggregated Rolling AUC-ROC  : {overall_auc:.4f}")

    # Calculate average feature importance across all rolling windows
    avg_importances = np.mean(feature_importances, axis=0)
    importance_df = pd.DataFrame({
        'Feature': features,
        'Importance': avg_importances
    }).sort_values('Importance', ascending=False)
    
    print("\n--- Average Feature Importance ---")
    print(importance_df.to_string(index=False))

    # 5. Save to SQLite for the Dashboard
    final_preds_df.to_sql('model_directional_predictions', conn, if_exists='replace', index=False)
    print("\nRolling predictions saved to `ieso_nodal_data.db`.")
    conn.close()

if __name__ == "__main__":
    train_walk_forward_classifier()