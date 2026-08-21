import os
import sys
import joblib
import json
import pandas as pd

# Ensure we can import URLFeatureExtractor if needed by joblib
sys.path.append(os.path.dirname(__file__))
try:
    from train_phishing_model import URLFeatureExtractor
except ImportError:
    pass

def load_models():
    base_dir = os.path.dirname(__file__)
    phishing_path = os.path.join(base_dir, 'models', 'phishing_model.joblib')
    invoice_path = os.path.join(base_dir, 'models', 'invoice_model.joblib')
    compliance_path = os.path.join(base_dir, 'models', 'compliance_model.joblib')
    
    phishing_model = joblib.load(phishing_path)
    invoice_model = joblib.load(invoice_path)
    compliance_model = joblib.load(compliance_path)
    
    return phishing_model, invoice_model, compliance_model

def run_tests():
    phishing_model, invoice_model, compliance_model = load_models()
    
    results = {}
    
    # 1. Phishing Test
    urls = [
        "https://paypal-security-update-login.top",
        "https://chase.com"
    ]
    phishing_preds = phishing_model.predict(urls)
    phishing_probs = phishing_model.predict_proba(urls)
    
    results['phishing'] = []
    for i, url in enumerate(urls):
        is_phishing = bool(phishing_preds[i])
        confidence = float(max(phishing_probs[i])) * 100
        risk_score = confidence if is_phishing else (100 - confidence)
        
        results['phishing'].append({
            'url': url,
            'is_phishing': is_phishing,
            'risk_score': round(risk_score, 2),
            'confidence': round(confidence, 2)
        })
        
        # Assertions
        if "paypal" in url:
            assert is_phishing, f"Expected {url} to be phishing"
        else:
            assert not is_phishing, f"Expected {url} to be clean"
            
    # 2. Invoice Test
    invoice_data = pd.DataFrame([{
        'subtotal': 50000.0,
        'tax_amount': 0.0,
        'tax_percentage_variance': 15.0,
        'line_item_delta': 1000.0, # Anomaly!
        'round_number_bias': 1,
        'historical_vendor_variance': 10.0
    }])
    
    invoice_pred = invoice_model.predict(invoice_data)[0]
    # IsolationForest returns -1 for anomalies, 1 for normal
    is_anomaly = invoice_pred == -1
    
    results['invoice'] = {
        'is_anomaly': bool(is_anomaly),
        'risk_score': 95.0 if is_anomaly else 5.0 # Dummy score for IF
    }
    assert is_anomaly, "Expected invoice to be an anomaly"
    
    # 3. Compliance Test
    clauses = [
        "payment routed to unverified offshore account without tax clearance",
        "Approved travel expenses with valid receipts."
    ]
    compliance_preds = compliance_model.predict(clauses)
    compliance_probs = compliance_model.predict_proba(clauses)
    
    results['compliance'] = []
    for i, clause in enumerate(clauses):
        pred_class = compliance_preds[i]
        confidence = float(max(compliance_probs[i])) * 100
        
        results['compliance'].append({
            'clause': clause,
            'predicted_category': pred_class,
            'confidence': round(confidence, 2)
        })
        
        if "offshore" in clause:
            assert pred_class == "AML_RED_FLAG", f"Expected AML_RED_FLAG, got {pred_class}"
        else:
            assert pred_class == "CLEAN", f"Expected CLEAN, got {pred_class}"
            
    print(json.dumps(results, indent=2))
    print("\n[SUCCESS] All assertions passed perfectly!")

if __name__ == "__main__":
    run_tests()
