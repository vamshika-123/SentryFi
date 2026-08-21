import os
import joblib
import pandas as pd
import numpy as np
import urllib.request
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

def generate_synthetic_compliance_data(n_samples=5000):
    categories = {
        "CLEAN": [
            "All terms standard as per company policy.",
            "Monthly invoice for software services rendered.",
            "Approved travel expenses with valid receipts.",
            "Standard employee salary deposit.",
            "Office supplies procurement from approved vendor.",
            "Routine maintenance contract renewal.",
            "Tax forms filed and completed according to state laws."
        ],
        "AML_RED_FLAG": [
            "Payment routed to unverified offshore account without tax clearance.",
            "Funds transferred to shell company in Cayman Islands.",
            "Multiple rapid transactions just below reporting thresholds.",
            "Beneficial owner information withheld or obscured.",
            "Payment from third party with no apparent business relationship."
        ],
        "SOX_VIOLATION": [
            "Unapproved transaction terms bypassing standard SOX controls.",
            "Financial statement modified by an unauthorized user.",
            "Audit logs disabled during off-hours data migration.",
            "Lack of segregation of duties in payment approval process.",
            "Material omission in quarterly earnings draft."
        ],
        "TAX_EVASION_SUSPICION": [
            "Vendor paid in cash to avoid tax reporting.",
            "Invoice disguised as consultancy fee without deliverables.",
            "Off-the-books transaction with unrecorded liabilities.",
            "Capital gains manipulated via backdated contracts.",
            "Income routed through non-taxable entity."
        ],
        "UNAUTHORIZED_PAYMENT_TERMS": [
            "Net 90 terms overridden to immediate payout by sales head.",
            "Contract signed without legal department review.",
            "Bonus disbursed without HR approval.",
            "Invoice paid twice to the same supplier.",
            "Payment terms altered post-signature."
        ]
    }
    
    X = []
    y = []
    
    # Generate balanced dataset
    samples_per_class = n_samples // len(categories)
    for label, texts in categories.items():
        for _ in range(samples_per_class):
            # Pick a template and add some random noise/words to make it unique
            text = np.random.choice(texts)
            if np.random.rand() > 0.5:
                text += " Reviewed on " + str(np.random.randint(2020, 2025)) + "."
            X.append(text)
            y.append(label)
            
    return X, y

def load_compliance_data():
    try:
        url = "https://raw.githubusercontent.com/dssg/cuad/master/data/train.csv"
        print("Attempting to download real legal compliance dataset...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5)
        
        # A tiny heuristic to try and parse real dataset if it works
        df = pd.read_csv(io.StringIO(response.read().decode('utf-8')))
        X = df.iloc[:, 0].tolist()
        y = ["CLEAN"] * len(X) # Dummy since real datasets are complex
        print(f"Successfully loaded {len(X)} records from remote dataset.")
        return X, y
    except Exception as e:
        print(f"Failed to download remote dataset ({str(e)}). Falling back to extensive synthetic data.")
        return generate_synthetic_compliance_data(5000)

if __name__ == "__main__":
    print("Training Compliance Model...")
    X, y = load_compliance_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
        ('clf', LogisticRegression(class_weight='balanced', random_state=42, max_iter=1000))
    ])
    
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    print(f"Training Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    
    print("\n--- Classification Report ---")
    print(classification_report(y_test, y_pred))
    
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'compliance_model.joblib'))
    joblib.dump(pipeline, model_path)
    print(f"Saved compliance model to {model_path}")
