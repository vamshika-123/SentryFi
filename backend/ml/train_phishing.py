import os
import re
import math
import joblib
import pandas as pd
import numpy as np
import tldextract
import urllib.request
import io
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Ensure models directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

class URLFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.financial_keywords = ['login', 'secure', 'bank', 'verify', 'kyc', 'wallet', 'paypal', 'crypto']
        self.suspicious_tlds = ['xyz', 'top', 'ru', 'tk', 'cc', 'info', 'biz']
        
    def fit(self, X, y=None):
        return self
        
    def _shannon_entropy(self, string):
        if not string:
            return 0.0
        prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(list(string))]
        entropy = - sum([p * math.log(p) / math.log(2.0) for p in prob])
        return entropy

    def transform(self, X):
        features = []
        for url in X:
            url_str = str(url).lower()
            ext = tldextract.extract(url_str)
            
            # Basic structural features
            url_length = len(url_str)
            dot_count = url_str.count('.')
            hyphen_count = url_str.count('-')
            at_count = url_str.count('@')
            
            # Presence of IP address
            has_ip = 1 if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', url_str) else 0
            
            # Suspicious TLD
            has_suspicious_tld = 1 if ext.suffix in self.suspicious_tlds else 0
            
            # Shannon entropy
            entropy = self._shannon_entropy(url_str)
            
            # Financial keywords count
            keyword_count = sum(1 for kw in self.financial_keywords if kw in url_str)
            
            features.append([
                url_length, dot_count, hyphen_count, at_count, 
                has_ip, has_suspicious_tld, entropy, keyword_count
            ])
            
        return np.array(features)

def generate_fallback_phishing_data(n_samples=5000):
    """Generate extensive synthetic data if download fails."""
    legit_domains = ["google.com", "chase.com/login", "paypal.com/myaccount",
                     "wellsfargo.com", "news.ycombinator.com", "github.com",
                     "apple.com/iphone", "microsoft.com", "netflix.com",
                     "amazon.com", "en.wikipedia.org", "bankofamerica.com",
                     "citi.com", "linkedin.com", "twitter.com"]
                     
    phishing_templates = ["paypal-security-update-login.{}", "secure-login-chase.com.{}",
                          "192.168.1.1/wallet-verify", "kyc-update.{}/login@bank",
                          "crypto-secure-wallet.{}", "myaccount-update-verify.com",
                          "54.123.43.122/secure/login", "verify-apple-id.{}/login",
                          "amazon-security-alert.{}", "netflix-billing-update.{}"]
                          
    suspicious_tlds = ['xyz', 'top', 'ru', 'tk', 'cc']
    
    X = []
    y = []
    
    # Generate legit
    for _ in range(n_samples // 2):
        domain = np.random.choice(legit_domains)
        prefix = np.random.choice(["https://www.", "https://", "http://www."])
        X.append(f"{prefix}{domain}")
        y.append(0)
        
    # Generate phishing
    for _ in range(n_samples // 2):
        template = np.random.choice(phishing_templates)
        tld = np.random.choice(suspicious_tlds)
        url = template.format(tld)
        if not url.startswith("http") and not url[0].isdigit():
            prefix = np.random.choice(["https://", "http://"])
            url = f"{prefix}{url}"
        elif url[0].isdigit():
            url = f"http://{url}"
        X.append(url)
        y.append(1)
        
    return X, y

def load_data():
    X = []
    y = []
    # Try fetching real public dataset (using HuggingFace dataset or github open datasets)
    # Using a known stable URL for a phishing dataset sample if possible.
    try:
        # Since standard github raw URLs can 404, we'll try a common one, if it fails we immediately fallback.
        url = "https://raw.githubusercontent.com/datasets/phishing-urls/master/data/phishing-urls.csv"
        print("Attempting to download real phishing dataset...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5)
        df = pd.read_csv(io.StringIO(response.read().decode('utf-8')))
        
        url_col = 'url' if 'url' in df.columns else df.columns[0]
        label_col = 'class' if 'class' in df.columns else df.columns[-1]
        
        X = df[url_col].tolist()
        y = [1 if str(val) == '1' or str(val).lower() == 'bad' else 0 for val in df[label_col].tolist()]
        print(f"Successfully loaded {len(X)} records from remote dataset.")
        
    except Exception as e:
        print(f"Failed to download remote dataset ({str(e)}). Falling back to extensive synthetic data.")
        X, y = generate_fallback_phishing_data(10000)

    return X, y

if __name__ == "__main__":
    print("Training Phishing Model...")
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    pipeline = Pipeline([
        ('features', URLFeatureExtractor()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10))
    ])
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    
    print("--- Phishing Model Metrics ---")
    print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
    print(f"Precision: {precision_score(y_test, y_pred, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(y_test, y_pred, zero_division=0):.4f}")
    print(f"F1-Score:  {f1_score(y_test, y_pred, zero_division=0):.4f}")
    
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'phishing_model.joblib'))
    joblib.dump(pipeline, model_path)
    print(f"Saved phishing model to {model_path}")
