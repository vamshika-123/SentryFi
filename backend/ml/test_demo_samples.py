import os
from fastapi.testclient import TestClient
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.main import app

DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../demo_samples'))

def test_invoice(client, filename, expected_verdict_contains):
    filepath = os.path.join(DEMO_DIR, filename)
    print(f"\n--- Testing Invoice: {filename} ---")
    
    with open(filepath, 'rb') as f:
        response = client.post(
            "/api/v1/scan/invoice", 
            files={"file": (filename, f, "application/pdf")}
        )
        
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return False
        
    data = response.json()
    verdict = data.get("verdict", "")
    risk_score = data.get("riskScore", 0)
    
    print(f"Verdict: {verdict}")
    print(f"Risk Score: {risk_score}")
    print(f"Extracted Fields: {data.get('extractedFields')}")
    print(f"Flagged Explanations: {data.get('flaggedExplanations')}")
    
    if expected_verdict_contains in verdict or (expected_verdict_contains == 'HIGH_RISK' and verdict == 'SUSPICIOUS'):
        print("PASS")
        return True
    else:
        print(f"FAIL (Expected {expected_verdict_contains})")
        return False

def test_compliance(client, filename, expected_verdict_contains):
    filepath = os.path.join(DEMO_DIR, filename)
    print(f"\n--- Testing Compliance: {filename} ---")
    
    with open(filepath, 'rb') as f:
        response = client.post(
            "/api/v1/scan/compliance", 
            files={"file": (filename, f, "application/pdf")},
            headers={"Content-Type": "multipart/form-data; boundary=---BOUNDARY"} # TestClient handles it, but let's just omit explicit headers for files
        )
        # Actually TestClient automatically sets correct content-type for files if omitted
        
    # Re-do request correctly
    with open(filepath, 'rb') as f:
        response = client.post(
            "/api/v1/scan/compliance", 
            files={"file": (filename, f, "application/pdf")}
        )
        
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return False
        
    data = response.json()
    verdict = data.get("verdict", "")
    risk_score = data.get("documentRiskScore", 0)
    
    print(f"Verdict: {verdict}")
    print(f"Risk Score: {risk_score}")
    
    if data.get('flaggedClauses'):
        print("Flagged Clauses:")
        for fc in data['flaggedClauses']:
            print(f"  - {fc.get('riskTag')}: {fc.get('clause')[:50]}... (Conf: {fc.get('confidence')})")
            
    if expected_verdict_contains in verdict or (expected_verdict_contains == 'HIGH_RISK' and verdict == 'FLAGGED'):
        print("PASS")
        return True
    else:
        print(f"FAIL (Expected {expected_verdict_contains})")
        return False

if __name__ == "__main__":
    if not os.path.exists(DEMO_DIR):
        print(f"Error: {DEMO_DIR} not found. Run generate_demo_pdfs.py first.")
        exit(1)
        
    all_passed = True
    
    with TestClient(app) as client:
        # 1. Test Clean Invoice
        if not test_invoice(client, "invoice_clean_inr.pdf", "CLEAN"):
            all_passed = False
            
        # 2. Test Fraud Invoice
        if not test_invoice(client, "invoice_fraud_tampered_inr.pdf", "HIGH_RISK"): # Maps to SUSPICIOUS
            all_passed = False
            
        # 3. Test Clean Compliance
        if not test_compliance(client, "compliance_clean.pdf", "CLEAN"):
            all_passed = False
            
        # 4. Test Violation Compliance
        if not test_compliance(client, "compliance_violation_aml.pdf", "HIGH_RISK"): # Maps to FLAGGED
            all_passed = False
            
        if all_passed:
            print("\nALL TESTS PASSED!")
        else:
            print("\nSOME TESTS FAILED.")
