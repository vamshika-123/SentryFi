import os
import sys

# Ensure backend can be imported from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def print_result(name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {name}")
    if details and not passed:
        print(f"       -> {details}")

def verify():
    print("--- Starting SentryFi Backend Verification ---")
    
    # 1. Models should load automatically via lifespan event on client creation
    # Test Health Endpoint
    try:
        response = client.get("/api/v1/health")
        if response.status_code == 200:
            print_result("Health Check GET /api/v1/health", True)
        else:
            print_result("Health Check GET /api/v1/health", False, f"Status Code: {response.status_code}")
    except Exception as e:
        print_result("Health Check GET /api/v1/health", False, str(e))
        
    # 2. Test Phishing Endpoint
    try:
        response = client.post("/api/v1/scan/phishing", json={"url": "https://secure-bank-login-update.top"})
        if response.status_code == 200:
            data = response.json()
            if "riskScore" in data and len(data.get("flaggedReasons", [])) > 0:
                print_result("Phishing Scan POST /api/v1/scan/phishing", True)
            else:
                print_result("Phishing Scan POST /api/v1/scan/phishing", False, "Missing riskScore or flaggedReasons")
        else:
            print_result("Phishing Scan POST /api/v1/scan/phishing", False, f"Status Code: {response.status_code} - {response.text}")
    except Exception as e:
        print_result("Phishing Scan POST /api/v1/scan/phishing", False, str(e))
        
    # 3. Test Invoice Endpoint (mock file payload)
    try:
        # Create a dummy text file to act as the invoice payload for test
        file_content = b"Subtotal: $500\nTax: $50\nTotal: $550\n"
        files = {"file": ("test_invoice.txt", file_content, "text/plain")}
        response = client.post("/api/v1/scan/invoice", files=files)
        
        if response.status_code == 200:
            data = response.json()
            if "extractedFields" in data and "riskScore" in data:
                print_result("Invoice Scan POST /api/v1/scan/invoice", True)
            else:
                print_result("Invoice Scan POST /api/v1/scan/invoice", False, "Missing expected fields in response")
        else:
            print_result("Invoice Scan POST /api/v1/scan/invoice", False, f"Status Code: {response.status_code} - {response.text}")
    except Exception as e:
        print_result("Invoice Scan POST /api/v1/scan/invoice", False, str(e))
        
    # 4. Test Compliance Endpoint
    try:
        response = client.post(
            "/api/v1/scan/compliance",
            json={"text": "Funds transferred to offshore shell entity without audit signoff."}
        )
        if response.status_code == 200:
            data = response.json()
            if "documentRiskScore" in data and data.get("verdict") in ["CLEAN", "FLAGGED"]:
                print_result("Compliance Scan POST /api/v1/scan/compliance", True)
            else:
                print_result("Compliance Scan POST /api/v1/scan/compliance", False, "Missing expected fields in response")
        else:
            print_result("Compliance Scan POST /api/v1/scan/compliance", False, f"Status Code: {response.status_code} - {response.text}")
    except Exception as e:
        print_result("Compliance Scan POST /api/v1/scan/compliance", False, str(e))

    print("--- Verification Complete ---")

if __name__ == "__main__":
    # TestClient implicitly triggers FastAPI lifespan events (model loading) inside a 'with' context
    with client:
        verify()
