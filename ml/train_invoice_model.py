import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

os.makedirs(os.path.join(os.path.dirname(__file__), 'models'), exist_ok=True)

def create_invoice_data():
    # Normal invoices
    normal_data = {
        'subtotal': [100.0, 500.0, 1000.0, 250.0, 1500.0],
        'tax_amount': [10.0, 50.0, 100.0, 25.0, 150.0], # 10% tax
        'tax_percentage_variance': [0.0, 0.0, 0.0, 0.0, 0.0],
        'line_item_delta': [0.0, 0.0, 0.0, 0.0, 0.0], # Items sum to subtotal
        'round_number_bias': [0, 0, 0, 0, 0],
        'historical_vendor_variance': [0.1, 0.05, 0.2, 0.1, 0.0]
    }
    
    # Fraudulent/Anomalous invoices
    anomaly_data = {
        'subtotal': [9999.0, 100.0, 50000.0],
        'tax_amount': [0.0, 25.0, 10000.0], 
        'tax_percentage_variance': [10.0, 15.0, 10.0],
        'line_item_delta': [500.0, 10.0, 1000.0], # Discrepancy
        'round_number_bias': [1, 0, 1], # Ending in round numbers strangely
        'historical_vendor_variance': [5.0, 2.5, 10.0]
    }
    
    df_normal = pd.DataFrame(normal_data)
    df_anomaly = pd.DataFrame(anomaly_data)
    
    # Isolation forest uses just features, we can train on mostly normal data
    # and a few anomalies if contamination is set
    df_train = pd.concat([df_normal, df_normal, df_normal, df_anomaly])
    return df_train

if __name__ == "__main__":
    print("Training Invoice Model...")
    X_train = create_invoice_data()
    
    model = IsolationForest(contamination=0.15, random_state=42)
    model.fit(X_train)
    
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'invoice_model.joblib')
    joblib.dump(model, model_path)
    print(f"Saved invoice model to {model_path}")
