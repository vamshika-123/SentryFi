import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

def generate_synthetic_invoice_data(n_samples=10000):
    """Generate highly realistic synthetic invoice distribution data for INR context."""
    # Normal invoices (approx 95%)
    n_normal = int(n_samples * 0.95)
    normal_data = {
        'subtotal': np.random.uniform(1000, 5000000, n_normal),
        'gst_rate_deviation': np.random.normal(0.01, 0.005, n_normal), # minor rounding deviations
        'item_sum_delta': np.random.exponential(scale=1.0, size=n_normal), # minor math rounding
        'round_number_bias': np.random.binomial(1, 0.05, n_normal), # 5% naturally round
        'tds_deduction_mismatch': np.random.uniform(0.0, 5.0, n_normal)
    }
    
    # Anomalous invoices (approx 5%)
    n_anomaly = n_samples - n_normal
    anomaly_data = {
        'subtotal': np.random.uniform(500000, 50000000, n_anomaly), # larger amounts often targeted
        'gst_rate_deviation': np.random.uniform(0.10, 0.40, n_anomaly), # erratic GST ratios
        'item_sum_delta': np.random.uniform(100, 50000, n_anomaly), # large discrepancies in sums
        'round_number_bias': np.random.binomial(1, 0.7, n_anomaly), # fraudsters love round numbers
        'tds_deduction_mismatch': np.random.uniform(500.0, 10000.0, n_anomaly) # high TDS mismatch
    }
    
    df_normal = pd.DataFrame(normal_data)
    df_anomaly = pd.DataFrame(anomaly_data)
    
    df_train = pd.concat([df_normal, df_anomaly])
    df_train = df_train.sample(frac=1, random_state=42).reset_index(drop=True)
    return df_train

if __name__ == "__main__":
    print("Training Invoice Anomaly Model (INR Context)...")
    X_train = generate_synthetic_invoice_data(10000)
    
    # We use IsolationForest for unsupervised anomaly detection.
    # The contamination=0.10 calibrates the decision threshold (top 10% most anomalous).
    model = IsolationForest(n_estimators=100, contamination=0.10, random_state=42)
    model.fit(X_train)
    
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'invoice_model.joblib'))
    joblib.dump(model, model_path)
    print(f"Saved invoice anomaly model to {model_path}")

