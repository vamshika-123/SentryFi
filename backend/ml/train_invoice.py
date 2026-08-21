import os
import joblib
import pandas as pd
import numpy as np
import urllib.request
import io
from sklearn.ensemble import IsolationForest

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

def generate_synthetic_invoice_data(n_samples=10000):
    """Generate highly realistic synthetic invoice distribution data."""
    # Normal invoices (approx 95%)
    n_normal = int(n_samples * 0.95)
    normal_data = {
        'tax_to_subtotal_ratio': np.random.normal(0.1, 0.02, n_normal), # typically 10% tax
        'line_item_sum_delta': np.random.exponential(scale=1.0, size=n_normal), # items mostly sum correctly with minor rounding
        'round_amount_score': np.random.binomial(1, 0.05, n_normal), # 5% naturally round
        'amount_z_score': np.random.normal(0, 1, n_normal) # standard distribution
    }
    
    # Anomalous invoices (approx 5%)
    n_anomaly = n_samples - n_normal
    anomaly_data = {
        'tax_to_subtotal_ratio': np.random.uniform(0.0, 0.4, n_anomaly), # erratic tax ratios
        'line_item_sum_delta': np.random.uniform(10, 5000, n_anomaly), # large discrepancies in sums
        'round_amount_score': np.random.binomial(1, 0.7, n_anomaly), # fraudsters love round numbers
        'amount_z_score': np.random.uniform(3, 15, n_anomaly) # highly unusual amounts
    }
    
    df_normal = pd.DataFrame(normal_data)
    df_anomaly = pd.DataFrame(anomaly_data)
    
    df_train = pd.concat([df_normal, df_anomaly])
    df_train = df_train.sample(frac=1, random_state=42).reset_index(drop=True)
    return df_train

def load_invoice_data():
    try:
        url = "https://raw.githubusercontent.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection/master/creditcard.csv"
        print("Attempting to download real financial anomaly dataset...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1000000'})
        response = urllib.request.urlopen(req, timeout=5)
        
        lines = response.read().decode('utf-8').split('\n')[:-1]
        df_raw = pd.read_csv(io.StringIO('\n'.join(lines)))
        
        amounts = df_raw['Amount'].values
        mean_amt = np.mean(amounts)
        std_amt = np.std(amounts) + 1e-6
        
        df = pd.DataFrame({
            'tax_to_subtotal_ratio': np.random.normal(0.1, 0.02, len(amounts)),
            'line_item_sum_delta': np.where(df_raw['Class'] == 1 if 'Class' in df_raw.columns else np.random.rand(len(amounts)) > 0.95, 
                                            np.abs(np.random.normal(500, 200, len(amounts))), 0.0),
            'round_amount_score': np.where(amounts % 100 == 0, 1, 0),
            'amount_z_score': (amounts - mean_amt) / std_amt
        })
        
        if 'Class' in df_raw.columns:
            anomalies = df_raw['Class'] == 1
            df.loc[anomalies, 'tax_to_subtotal_ratio'] = np.random.uniform(0.0, 0.05, sum(anomalies))
            df.loc[anomalies, 'round_amount_score'] = 1
            
        print(f"Successfully synthesized invoice features from real financial distribution ({len(df)} records).")
        return df

    except Exception as e:
        print(f"Failed to download remote dataset ({str(e)}). Falling back to generative synthetic data.")
        return generate_synthetic_invoice_data(10000)

if __name__ == "__main__":
    print("Training Invoice Anomaly Model...")
    X_train = load_invoice_data()
    
    # We use IsolationForest for unsupervised anomaly detection.
    # The contamination=0.10 calibrates the decision threshold (top 10% most anomalous).
    model = IsolationForest(n_estimators=100, contamination=0.10, random_state=42)
    model.fit(X_train)
    
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'invoice_model.joblib'))
    joblib.dump(model, model_path)
    print(f"Saved invoice anomaly model to {model_path}")
