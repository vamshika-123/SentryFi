from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    # Since lifespan models might be loaded, we use the TestClient context manager
    # which triggers startup/shutdown events
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_phishing_scan_clean():
    with TestClient(app) as client:
        response = client.post("/api/v1/scan/phishing", json={"url": "https://chase.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "CLEAN"

def test_phishing_scan_high_risk():
    with TestClient(app) as client:
        response = client.post("/api/v1/scan/phishing", json={"url": "https://paypal-security-update-login.top"})
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "HIGH_RISK"
        assert "riskScore" in data

def test_invoice_scan():
    with TestClient(app) as client:
        # Create a dummy image or pdf to upload
        file_content = b"Subtotal: $50000.00\nTax: $0.00\nTotal: $60000.00"
        files = {"file": ("dummy.txt", file_content, "text/plain")}
        
        response = client.post("/api/v1/scan/invoice", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert "extractedFields" in data

def test_compliance_scan_text():
    with TestClient(app) as client:
        payload = {
            "text": "The payment was routed to an unverified offshore account without tax clearance."
        }
        response = client.post("/api/v1/scan/compliance", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "FLAGGED"
        assert len(data["flaggedClauses"]) > 0
        assert "riskTag" in data["flaggedClauses"][0]
