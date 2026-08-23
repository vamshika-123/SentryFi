import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import pandas as pd

from backend.core.model_loader import registry
from backend.services.ocr_service import process_invoice_file

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models on startup
    registry.load_models()
    yield
    # Clean up on shutdown if needed

app = FastAPI(title="SentryFi API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PhishingRequest(BaseModel):
    url: str

class PhishingResponse(BaseModel):
    url: str
    riskScore: float
    verdict: str
    confidence: float
    flaggedReasons: List[str]
    scannedAt: str

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/scan/phishing", response_model=PhishingResponse)
async def scan_phishing(request: PhishingRequest):
    if not registry.phishing_model:
        raise HTTPException(status_code=503, detail="Phishing model not loaded")
        
    url = request.url
    
    # Predict
    try:
        pred = registry.phishing_model.predict([url])[0]
        probs = registry.phishing_model.predict_proba([url])[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    is_phishing = bool(pred)
    confidence = float(max(probs))
    risk_score = confidence * 100 if is_phishing else (1 - confidence) * 100
    
    verdict = "HIGH_RISK" if is_phishing else "CLEAN"
    
    # Generate some flagged reasons based on simple heuristic for the response
    reasons = []
    if is_phishing:
        if ".top" in url or ".xyz" in url or ".ru" in url or ".tk" in url:
            reasons.append("Suspicious TLD detected")
        if "login" in url.lower() or "secure" in url.lower():
            reasons.append("Contains financial/auth keywords")
        if not reasons:
            reasons.append("Structural anomalies detected by ML model")
            
    return PhishingResponse(
        url=url,
        riskScore=round(risk_score, 2),
        verdict=verdict,
        confidence=round(confidence, 4),
        flaggedReasons=reasons,
        scannedAt=datetime.now(timezone.utc).isoformat()
    )

@app.post("/api/v1/scan/invoice")
async def scan_invoice(file: UploadFile = File(...)):
    if not registry.invoice_model:
        raise HTTPException(status_code=503, detail="Invoice model not loaded")
        
    content = await file.read()
    
    # Process OCR and extract features
    features_dict = process_invoice_file(content, file.filename)
    
    # Prepare dataframe for prediction
    df = pd.DataFrame([features_dict])
    
    # Predict
    try:
        pred = registry.invoice_model.predict(df)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    is_anomaly = pred == -1
    
    # Rule-based override for perfectly clean invoices
    if (features_dict.get("gst_rate_deviation", 0) < 0.01 and 
        features_dict.get("item_sum_delta", 0) < 1.0 and 
        features_dict.get("round_number_bias", 0) == 0):
        is_anomaly = False
    
    verdict = "SUSPICIOUS" if is_anomaly else "CLEAN"
    risk_score = 90.0 if is_anomaly else 10.0
    
    explanations = []
    if is_anomaly:
        if features_dict.get("item_sum_delta", 0) > 0:
            explanations.append("Line items do not sum to total")
        if features_dict.get("gst_rate_deviation", 0) > 0.05:
            explanations.append("Unusual GST rate variance (expected standard slabs)")
            
    return {
        "extractedFields": features_dict,
        "riskScore": risk_score,
        "verdict": verdict,
        "flaggedExplanations": explanations
    }

class ComplianceRequest(BaseModel):
    text: Optional[str] = None

@app.post("/api/v1/scan/compliance")
async def scan_compliance(request: Request):
    if not registry.compliance_model:
        raise HTTPException(status_code=503, detail="Compliance model not loaded")
        
    text = ""
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        payload = await request.json()
        text = payload.get("text", "")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and hasattr(file, "read"):
            content = await file.read()
            if file.filename.lower().endswith('.pdf'):
                import pdfplumber
                import io
                try:
                    with pdfplumber.open(io.BytesIO(content)) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                except Exception as e:
                    pass
            else:
                text = content.decode('utf-8', errors='ignore')
                
    if not text.strip():
        raise HTTPException(status_code=400, detail="Must provide either text payload or file")
        
    # Split text into clauses (naive split by newline or sentences)
    import re
    clauses = [c.strip() for c in re.split(r'\n|\.', text) if len(c.strip()) > 10]
    
    if not clauses:
        clauses = ["Dummy text to prevent empty batch error."]
        
    try:
        preds = registry.compliance_model.predict(clauses)
        probs = registry.compliance_model.predict_proba(clauses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    flagged_clauses = []
    overall_risk = 0.0
    
    for i, clause in enumerate(clauses):
        pred_class = preds[i]
        confidence = float(max(probs[i])) * 100
        
        if pred_class != "CLEAN":
            flagged_clauses.append({
                "clause": clause,
                "riskTag": pred_class,
                "confidence": round(confidence, 2)
            })
            overall_risk = max(overall_risk, confidence)
            
    verdict = "FLAGGED" if flagged_clauses else "CLEAN"
    
    return {
        "documentRiskScore": round(overall_risk, 2) if flagged_clauses else 5.0,
        "verdict": verdict,
        "flaggedClauses": flagged_clauses
    }

# Trigger reload

# Trigger reload 2
