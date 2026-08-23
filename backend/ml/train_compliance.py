import os
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

def generate_synthetic_compliance_data(n_samples=5000):
    categories = {
        "CLEAN": [
            "All terms standard as per company policy and Companies Act 2013.",
            "Monthly invoice for software services rendered with GST at 18%.",
            "Approved travel expenses with valid receipts and PAN details.",
            "Standard employee salary deposit reflecting TDS deduction.",
            "Office supplies procurement from approved domestic vendor.",
            "Routine maintenance contract renewal adhering to MCA guidelines.",
            "Tax forms filed and completed according to income tax rules."
        ],
        "AML_PMLA_VIOLATION": [
            "Payment routed to unverified offshore account without tax clearance or RBI approval.",
            "Funds transferred to shell company without standard PMLA source verification.",
            "Payments shall be routed via non-disclosed shell companies in Mauritius without standard PMLA source verification.",
            "Beneficial owner information withheld or obscured violating KYC norms.",
            "Payment from third party with no apparent business relationship."
        ],
        "SOX_COMPLIANCE_BREACH": [
            "Unapproved transaction terms bypassing standard SOX controls.",
            "Financial statement modified by an unauthorized user.",
            "Audit logs disabled during off-hours data migration.",
            "Lack of segregation of duties in payment approval process.",
            "Material omission in quarterly earnings draft."
        ],
        "GST_EVASION_SUSPICION": [
            "Vendor paid in cash to avoid tax reporting.",
            "Invoice disguised as consultancy fee without deliverables or GSTIN.",
            "Off-the-books transaction with unrecorded liabilities.",
            "Fake GST invoice claiming input tax credit.",
            "Income routed through non-taxable entity to evade taxes."
        ],
        "UNAUTHORIZED_OFFSHORE_ROUTING": [
            "Funds sent to Cayman Islands account avoiding FEMA compliance.",
            "Unregistered foreign remittance via hawala channels.",
            "Transfer to unapproved foreign subsidiary without RBI clearance.",
            "Offshore routing of profits without declaring under transfer pricing norms.",
            "Round tripping of funds through tax havens."
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

if __name__ == "__main__":
    print("Training Compliance Model (Indian Context)...")
    X, y = generate_synthetic_compliance_data(5000)
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
