import io
import sys
from fastapi.testclient import TestClient
from backend.main import app

def print_row(endpoint, payload_preview, verdict, status):
    print(f"{endpoint:<30} | {payload_preview[:43]:<45} | {str(verdict):<30} | {status:<10}")

def run_integration_tests():
    print(f"{'Endpoint Tested':<30} | {'Input Payload':<45} | {'Risk Score / Output Verdict':<30} | {'Status':<10}")
    print("-" * 125)
    
    all_passed = True
    
    try:
        with TestClient(app) as client:
            # 1. Health Check
            resp = client.get("/api/v1/health")
            passed = resp.status_code == 200 and resp.json().get("status") == "ok"
            verdict = "HEALTHY" if resp.status_code == 200 else str(resp.status_code)
            print_row("GET /api/v1/health", "None", verdict, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # 2. Phishing Scanner
            # Case A: Malicious URL
            malicious_url = "https://secure-login-chase-update.top/auth"
            resp = client.post("/api/v1/scan/phishing", json={"url": malicious_url})
            data = resp.json()
            passed = (resp.status_code == 200 and 
                      data.get("verdict") in ["HIGH_RISK", "SUSPICIOUS"] and 
                      data.get("riskScore", 0) >= 60 and 
                      len(data.get("flaggedReasons", [])) > 0)
            verdict_str = f"{data.get('riskScore', 'N/A')} / {data.get('verdict', 'ERR')}"
            print_row("POST /api/v1/scan/phishing", malicious_url, verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # Case B: Clean URL
            clean_url = "https://www.google.com"
            resp = client.post("/api/v1/scan/phishing", json={"url": clean_url})
            data = resp.json()
            passed = (resp.status_code == 200 and 
                      data.get("verdict") == "CLEAN" and 
                      data.get("riskScore", 100) < 30)
            verdict_str = f"{data.get('riskScore', 'N/A')} / {data.get('verdict', 'ERR')}"
            print_row("POST /api/v1/scan/phishing", clean_url, verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # 3. Invoice Anomaly & OCR Test
            # Subtotal + Tax = 51000, but Total = 60000 (math mismatch). Huge values for IF anomaly
            invoice_content = b"Subtotal: $50000.00\nTax: $1000.00\nTotal: $60000.00"
            files = {"file": ("mock_invoice.txt", invoice_content, "text/plain")}
            resp = client.post("/api/v1/scan/invoice", files=files)
            data = resp.json()
            passed = (resp.status_code == 200 and 
                      data.get("verdict") in ["SUSPICIOUS", "FRAUD", "FLAGGED"] and 
                      len(data.get("flaggedExplanations", [])) > 0)
            verdict_str = f"{data.get('riskScore', 'N/A')} / {data.get('verdict', 'ERR')}"
            print_row("POST /api/v1/scan/invoice", "Mock PDF bytes with mismatch", verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # 4. Compliance Scanner Test
            # Case A: Violation Text
            violation_text = "All vendor commissions exceeding $50,000 shall be routed through undisclosed offshore accounts without standard AML clearance."
            resp = client.post("/api/v1/scan/compliance", json={"text": violation_text})
            data = resp.json()
            # Check if any flagged clause is AML_RED_FLAG
            is_aml = any(c.get("riskTag") == "AML_RED_FLAG" for c in data.get("flaggedClauses", []))
            passed = (resp.status_code == 200 and 
                      data.get("verdict") in ["FLAGGED", "SUSPICIOUS"] and 
                      is_aml)
            verdict_str = f"{data.get('documentRiskScore', 'N/A')} / {data.get('verdict', 'ERR')}"
            print_row("POST /api/v1/scan/compliance", violation_text, verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # Case B: Standard Text
            standard_text = "Approved travel expenses with valid receipts."
            resp = client.post("/api/v1/scan/compliance", json={"text": standard_text})
            data = resp.json()
            passed = resp.status_code == 200 and data.get("verdict") == "CLEAN"
            verdict_str = f"{data.get('documentRiskScore', 'N/A')} / {data.get('verdict', 'ERR')}"
            print_row("POST /api/v1/scan/compliance", standard_text, verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed
            
            # 5. Error Handling Test
            # Empty payload for compliance should yield 400
            resp = client.post("/api/v1/scan/compliance", json={"text": ""})
            passed_400 = resp.status_code == 400
            
            # Invalid payload for phishing (missing url) should yield 422
            resp = client.post("/api/v1/scan/phishing", json={})
            passed_422 = resp.status_code == 422
            
            passed = passed_400 and passed_422
            verdict_str = f"400: {passed_400}, 422: {passed_422}"
            print_row("POST Multiple Endpoints", "Empty/Invalid Payloads", verdict_str, "PASS" if passed else "FAIL")
            all_passed = all_passed and passed

    except Exception as e:
        print(f"\n[ERROR] Test suite crashed: {e}")
        all_passed = False
        
    print("-" * 125)
    
    if all_passed:
        print("\n[SUCCESS] All Integration Tests Passed Successfully!")
        sys.exit(0)
    else:
        print("\n[FAILED] Some Integration Tests Failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_integration_tests()
