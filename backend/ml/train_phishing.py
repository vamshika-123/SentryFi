import os
import re
import math
import joblib
import pandas as pd
import numpy as np
import tldextract
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import accuracy_score, classification_report

# Ensure models directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'models'), exist_ok=True)

class URLFeatureExtractor(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.financial_keywords = ['login', 'secure', 'bank', 'verify', 'kyc', 'wallet', 'paypal', 'crypto']
        self.suspicious_tlds = ['xyz', 'top', 'ru', 'tk']
        
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

def create_synthetic_data():
    legit_urls = [
        "https://www.google.com",
        "https://chase.com/login",
        "https://www.paypal.com/myaccount",
        "https://wellsfargo.com",
        "http://news.ycombinator.com",
        "https://github.com",
        "https://apple.com/iphone"
    ]
    phishing_urls = [
        "https://paypal-security-update-login.top",
        "http://secure-login-chase.com.ru",
        "http://192.168.1.1/wallet-verify",
        "https://kyc-update.xyz/login@bank",
        "http://crypto-secure-wallet.tk",
        "https://myaccount-update-verify.com"
    ]
    
    X = legit_urls + phishing_urls
    y = [0] * len(legit_urls) + [1] * len(phishing_urls)
    return X, y

if __name__ == "__main__":
    print("Training Phishing Model...")
    X, y = create_synthetic_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    pipeline = Pipeline([
        ('features', URLFeatureExtractor()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'phishing_model.joblib')
    joblib.dump(pipeline, model_path)
    print(f"Saved phishing model to {model_path}")
