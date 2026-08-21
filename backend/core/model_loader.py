import os
import sys
import joblib

# Need to ensure the 'ml' directory is in the python path
# so that joblib can find `URLFeatureExtractor` which was defined in `train_phishing`.
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ML_DIR = os.path.join(BASE_DIR, 'ml')
if ML_DIR not in sys.path:
    sys.path.append(ML_DIR)

import __main__
from train_phishing import URLFeatureExtractor
__main__.URLFeatureExtractor = URLFeatureExtractor

class ModelRegistry:
    def __init__(self):
        self.phishing_model = None
        self.invoice_model = None
        self.compliance_model = None
        
    def load_models(self):
        models_dir = os.path.join(BASE_DIR, 'models')
        
        phishing_path = os.path.join(models_dir, 'phishing_model.joblib')
        invoice_path = os.path.join(models_dir, 'invoice_model.joblib')
        compliance_path = os.path.join(models_dir, 'compliance_model.joblib')
        
        if os.path.exists(phishing_path):
            self.phishing_model = joblib.load(phishing_path)
            print("Loaded phishing model.")
            
        if os.path.exists(invoice_path):
            self.invoice_model = joblib.load(invoice_path)
            print("Loaded invoice model.")
            
        if os.path.exists(compliance_path):
            self.compliance_model = joblib.load(compliance_path)
            print("Loaded compliance model.")

registry = ModelRegistry()
