import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

os.makedirs(os.path.join(os.path.dirname(__file__), 'models'), exist_ok=True)

def create_compliance_data():
    clauses = [
        "All terms standard as per company policy.",
        "Monthly invoice for software services rendered.",
        "Approved travel expenses with valid receipts.",
        "Payment routed to unverified offshore account without tax clearance.",
        "Funds transferred to shell company in Cayman Islands.",
        "Unapproved transaction terms bypassing standard SOX controls.",
        "Vendor paid in cash to avoid tax reporting.",
        "The financial statement was modified by an unauthorized user."
    ]
    
    labels = [
        "CLEAN",
        "CLEAN",
        "CLEAN",
        "AML_RED_FLAG",
        "AML_RED_FLAG",
        "SOX_VIOLATION",
        "TAX_EVASION_SUSPICION",
        "UNAUTHORIZED_PAYMENT_TERMS"
    ]
    return clauses, labels

if __name__ == "__main__":
    print("Training Compliance Model...")
    X, y = create_compliance_data()
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
        ('clf', LogisticRegression(class_weight='balanced', random_state=42))
    ])
    
    pipeline.fit(X, y)
    
    y_pred = pipeline.predict(X)
    print(f"Training Accuracy: {accuracy_score(y, y_pred):.2f}")
    
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'compliance_model.joblib')
    joblib.dump(pipeline, model_path)
    print(f"Saved compliance model to {model_path}")
