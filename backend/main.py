import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
async def scan_invoice(
    file: UploadFile = File(...),
    currency_override: Optional[str] = Form(default=None),
):
    if not registry.invoice_model:
        raise HTTPException(status_code=503, detail="Invoice model not loaded")

    content = await file.read()

    # Process OCR, extract features, and apply currency hint in one pass.
    # currency_override (when supplied) overrides auto-detection AND re-runs
    # the GST/generic-tax framing logic (BUG 12c + BUG 14).
    features_dict = process_invoice_file(
        content, file.filename,
        currency_hint=currency_override or None
    )

    # BUG 4 / BUG 11: if OCR completely failed (no amounts found at all), return manual review.
    # Partial success (tax_not_stated but subtotal extracted) is NOT a failure — let the model run.
    if features_dict.get("extraction_failed"):
        return {
            "extractedFields": features_dict,
            "riskScore": 50.0,
            "verdict": "NEEDS_MANUAL_REVIEW",
            "flaggedExplanations": ["Automated text extraction failed — document could not be parsed. Please review manually."]
        }

    MODEL_FEATURE_KEYS = ['subtotal', 'gst_rate_deviation', 'item_sum_delta', 'round_number_bias', 'tds_deduction_mismatch']
    df = pd.DataFrame([{k: features_dict[k] for k in MODEL_FEATURE_KEYS}])

    # Predict (binary label and calibrated risk score)
    try:
        pred = registry.invoice_model.predict(df)[0]
        # BUG 19: IsolationForest decision_function returns positive for inliers/normal
        # and negative for outliers/anomalies (threshold = 0.0).
        raw_dec = float(registry.invoice_model.decision_function(df)[0])
        
        normal_max = registry.invoice_score_range.get("normal_max", 0.25)
        anom_max = registry.invoice_score_range.get("anom_max", 0.17)
        
        if raw_dec >= 0:
            # Inlier/Normal: map [0, normal_max] -> [50, 0] (clean invoices score < 50)
            ratio = min(1.0, raw_dec / max(1e-5, normal_max))
            risk_score = round(max(0.0, 50.0 * (1.0 - ratio)), 1)
        else:
            # Outlier/Anomaly: map [0, -anom_max] -> [50, 100] (anomalous invoices score > 50)
            ratio = min(1.0, abs(raw_dec) / max(1e-5, anom_max))
            risk_score = round(min(100.0, 50.0 + 50.0 * ratio), 1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    is_anomaly = pred == -1

    # Rule-based override: if all anomaly signals are near-zero, trust clean verdict.
    if (features_dict.get("gst_rate_deviation", 1) < 0.01 and
        features_dict.get("item_sum_delta", 1) < 1.0 and
        features_dict.get("round_number_bias", 1) == 0 and
        features_dict.get("tds_deduction_mismatch", 1) < 1.0):
        if is_anomaly:
            logger.warning(
                f"Rule override changed prediction from SUSPICIOUS to CLEAN for "
                f"'{file.filename}' with features: {features_dict}"
            )
        is_anomaly = False
        # Ensure clean rule-overridden invoices reflect a safe low risk score
        risk_score = min(risk_score, 25.0)

    verdict = "SUSPICIOUS" if is_anomaly else "CLEAN"

    explanations = []

    # BUG 11: warn when tax section wasn't found (not an anomaly, just informational)
    if features_dict.get("tax_not_stated"):
        explanations.append("No tax/GST breakdown found on this invoice — subtotal computed from line items.")

    if is_anomaly:
        if features_dict.get("item_sum_delta", 0) > 0:
            # BUG 13: only flag as mismatch when there are no legitimate additional charges accounting for the gap
            if features_dict.get("additional_charges_label"):
                explanations.append(
                    f"Amount difference accounted for by: {features_dict['additional_charges_label']}"
                )
            else:
                explanations.append("Line items do not sum to stated total — possible discrepancy.")
        # BUG 14: only surface GST deviation for invoices that are explicitly GST-labelled
        if features_dict.get("is_gst_invoice") and features_dict.get("gst_rate_deviation", 0) > 0.05:
            explanations.append("Unusual GST rate variance (expected standard slabs: 5%, 12%, 18%, 28%)")
        if features_dict.get("tds_deduction_mismatch", 0) > 100:
            explanations.append("TDS deduction amount significantly differs from expected")

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
    low_confidence_flags = []  # Bug 10: below-threshold predictions, visible but not counted
    overall_risk = 0.0
    CONFIDENCE_THRESHOLD = 65.0  # Bug 10: minimum confidence to treat a clause as a real violation
    
    for i, clause in enumerate(clauses):
        pred_class = preds[i]
        confidence = float(max(probs[i])) * 100
        
        if pred_class != "CLEAN":
            if confidence >= CONFIDENCE_THRESHOLD:
                flagged_clauses.append({
                    "clause": clause,
                    "riskTag": pred_class,
                    "confidence": round(confidence, 2)
                })
                overall_risk = max(overall_risk, confidence)
            else:
                # Low-confidence prediction — surface separately, don't affect verdict/score
                low_confidence_flags.append({
                    "clause": clause,
                    "riskTag": pred_class,
                    "confidence": round(confidence, 2)
                })
            
    verdict = "FLAGGED" if flagged_clauses else "CLEAN"
    
    return {
        "documentRiskScore": round(overall_risk, 2) if flagged_clauses else 5.0,
        "verdict": verdict,
        "flaggedClauses": flagged_clauses,
        "lowConfidenceFlags": low_confidence_flags
    }

# End of SentryFi API — Bugs 8/9/10 applied
