import os
import re
import math
import logging
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

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
    verdict: str          # legacy field kept for backward-compat (CLEAN / HIGH_RISK)
    riskTier: str         # SAFE | MODERATE_RISK | VERY_RISKY
    confidence: float
    flaggedReasons: List[str]
    scannedAt: str

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


def _phishing_reasons(url: str, risk_score: float, risk_tier: str) -> List[str]:
    """
    Generate specific, plain-language reasons for a phishing scan result.
    Runs for ALL tiers — never returns an empty list.
    Reason tone scales with tier: urgent for VERY_RISKY, cautious for
    MODERATE_RISK, reassuring for SAFE.
    """
    import re
    import math

    reasons: List[str] = []

    url_lower = url.lower()

    # --- Parse URL components (best-effort; fall back gracefully) ---
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if '://' in url else 'https://' + url)
        scheme   = parsed.scheme.lower()
        hostname = parsed.hostname or ''
        path     = parsed.path
        full     = url
    except Exception:
        scheme = 'https' if url_lower.startswith('https') else 'http'
        hostname = url_lower.split('/')[2] if '/' in url_lower else url_lower
        path = ''
        full = url

    # 1. No HTTPS
    if scheme == 'http':
        reasons.append(
            "This link doesn't use a secure (HTTPS) connection, which legitimate "
            "login pages almost always require."
        )

    # 2. Raw IP address instead of a domain name
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ip_pattern.match(hostname):
        reasons.append(
            "This link points to a raw numeric address instead of a real website "
            "name — a common trick used in phishing attacks."
        )

    # 3. '@' symbol in URL (hides true destination)
    if '@' in full:
        reasons.append(
            "This link contains an '@' symbol, which can be used to disguise the "
            "real destination and trick you into visiting a different site."
        )

    # 4. Suspicious uncommon domain ending
    SUSPICIOUS_TLDS = {
        '.top', '.xyz', '.ru', '.tk', '.info', '.click', '.gq', '.ml',
        '.cf', '.ga', '.pw', '.stream', '.win', '.loan', '.review',
    }
    tld_hit = next((t for t in SUSPICIOUS_TLDS if hostname.endswith(t)), None)
    if tld_hit:
        reasons.append(
            f"This uses an uncommon domain ending ({tld_hit}) that is frequently "
            f"associated with scam links and disposable websites."
        )

    # 5. Financial / auth keywords in domain (not in well-known brand list)
    KNOWN_BRANDS = {
        'google', 'microsoft', 'apple', 'amazon', 'paypal', 'chase', 'wellsfargo',
        'bankofamerica', 'citibank', 'hsbc', 'barclays', 'santander', 'sbi',
        'hdfc', 'icici', 'axis', 'kotak', 'ubs', 'linkedin', 'facebook',
        'twitter', 'instagram', 'netflix', 'spotify', 'adobe', 'dropbox',
    }
    AUTH_KEYWORDS = {
        'login', 'secure', 'verify', 'account', 'update', 'wallet', 'bank',
        'signin', 'password', 'credential', 'auth', 'confirm', 'validate',
    }
    domain_parts = hostname.replace('-', '.').split('.')
    domain_root  = domain_parts[0] if domain_parts else ''
    is_known_brand = any(brand in hostname for brand in KNOWN_BRANDS)
    matched_kw = next(
        (kw for kw in AUTH_KEYWORDS if kw in url_lower and not is_known_brand), None
    )
    if matched_kw and not is_known_brand:
        reasons.append(
            f"This link uses words like '{matched_kw}' to look official, but the "
            f"domain itself isn't a recognized site — a classic phishing pattern."
        )

    # 6. High subdomain count / random-looking characters (entropy heuristic)
    subdomains = hostname.split('.')
    if len(subdomains) > 4:
        reasons.append(
            "This web address has an unusually large number of dot-separated parts, "
            "which is typical of randomly generated phishing links."
        )
    else:
        # Estimate character entropy of the leftmost label
        label = subdomains[0] if subdomains else ''
        if len(label) >= 8:
            from collections import Counter
            counts = Counter(label)
            ent = -sum((c / len(label)) * math.log2(c / len(label)) for c in counts.values())
            if ent > 3.5:  # high randomness threshold
                reasons.append(
                    "This web address looks randomly generated rather than a real "
                    "business name — a sign it may be a throwaway phishing domain."
                )

    # 7. Excessive length or hyphen stuffing
    if len(hostname) > 40:
        reasons.append(
            "This web address is unusually long and complex, which is a common "
            "trick used to disguise a fake site as a real one."
        )
    elif hostname.count('-') >= 3:
        reasons.append(
            "This domain contains many hyphens, which is often used to pad a "
            "fake domain name so it looks more like a real website."
        )

    # 8. Lookalike characters / homograph clues (simple heuristic)
    LOOKALIKE = {'0': 'o', '1': 'l', '3': 'e', '5': 's', '@': 'a'}
    for fake, real in LOOKALIKE.items():
        if fake in hostname and real in hostname:
            reasons.append(
                "This link mixes numbers and letters in a way designed to impersonate "
                "a well-known website — look closely before clicking."
            )
            break

    # --- Tone adjustment for tier ---
    if risk_tier == 'VERY_RISKY' and reasons:
        # Prepend an urgent summary
        reasons.insert(
            0,
            "⚠️ Multiple serious warning signs detected — do NOT enter any personal "
            "information on this page.",
        )
    elif risk_tier == 'MODERATE_RISK' and reasons:
        reasons.append(
            "Worth double-checking this link before entering any personal information "
            "or clicking any buttons on the page."
        )

    # --- Positive verdict for clean URLs ---
    if not reasons:
        reasons.append(
            "No suspicious patterns detected — this looks like a standard, "
            "well-formed web address with no obvious red flags."
        )

    return reasons


@app.post("/api/v1/scan/phishing", response_model=PhishingResponse)
async def scan_phishing(request: PhishingRequest):
    if not registry.phishing_model:
        raise HTTPException(status_code=503, detail="Phishing model not loaded")

    url = request.url

    # --- Model inference ---
    try:
        probs = registry.phishing_model.predict_proba([url])[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # probs[1] is the probability of the phishing (positive) class
    phishing_prob = float(probs[1])   # 0.0 – 1.0
    confidence    = float(max(probs))

    # --- Heuristic Signal Analysis ---
    SUSPICIOUS_TLDS_S = {'.top','.xyz','.ru','.tk','.info','.click',
                          '.gq','.ml','.cf','.ga','.pw','.stream',
                          '.win','.loan','.review'}
    KNOWN_BRANDS_S = {'google','microsoft','apple','amazon','paypal',
                       'chase','wellsfargo','bankofamerica','citibank',
                       'hsbc','barclays','santander','sbi','hdfc',
                       'icici','axis','kotak','ubs','linkedin',
                       'facebook','twitter','instagram','netflix',
                       'spotify','adobe','dropbox'}
    AUTH_KEYWORDS_S = {'login','secure','verify','account','update',
                        'wallet','bank','signin','password','credential',
                        'auth','confirm','validate'}

    try:
        p = urlparse(url if '://' in url else 'https://' + url)
        sch = p.scheme.lower()
        h = p.hostname or ''
    except Exception:
        sch = 'http' if url.lower().startswith('http://') else 'https'
        h = ''

    n_signals = 0
    if sch == 'http':
        n_signals += 1
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', h):
        n_signals += 1
    if '@' in url:
        n_signals += 1
    if any(h.endswith(t) for t in SUSPICIOUS_TLDS_S):
        n_signals += 1
    is_brand = any(b in h for b in KNOWN_BRANDS_S)
    if not is_brand and any(kw in url.lower() for kw in AUTH_KEYWORDS_S):
        n_signals += 1
    parts = h.split('.')
    if len(parts) > 4:
        n_signals += 1
    else:
        lbl = parts[0] if parts else ''
        if len(lbl) >= 8:
            c = Counter(lbl)
            ent = -sum((v/len(lbl))*math.log2(v/len(lbl)) for v in c.values())
            if ent > 3.5:
                n_signals += 1
    if len(h) > 40:
        n_signals += 1
    elif h.count('-') >= 3:
        n_signals += 1

    # Escalation signals
    has_raw_ip = bool(re.match(r'^(\d{1,3}\.){3}\d{1,3}$', h))
    has_at = '@' in url

    # --- Three-tier Classification ---
    if n_signals == 0 or phishing_prob < 0.30:
        risk_tier = "SAFE"
        verdict   = "CLEAN"
    elif (has_raw_ip or has_at) or (n_signals >= 4 and phishing_prob >= 0.70):
        risk_tier = "VERY_RISKY"
        verdict   = "HIGH_RISK"
    else:
        # 1-3 signals without a hard escalator
        risk_tier = "MODERATE_RISK"
        verdict   = "HIGH_RISK"

    # --- Continuous Risk Score (0-100) ---
    if risk_tier == "SAFE":
        # Calibrated ML score is well-calibrated (0–28%)
        risk_score = round(phishing_prob * 100, 1)
    elif risk_tier == "MODERATE_RISK":
        # 1-3 signals: map to 30-65%
        base = {1: 30.0, 2: 40.0, 3: 53.0}.get(n_signals, 30.0)
        spread = {1: 9.0, 2: 12.0, 3: 12.0}.get(n_signals, 9.0)
        t = max(0.0, min(1.0, (phishing_prob - 0.30) / 0.70))
        risk_score = round(base + t * spread, 1)
    else:
        # VERY_RISKY: map to 70-100%
        severe = int(has_raw_ip) + int(has_at) + int(any(h.endswith(t) for t in SUSPICIOUS_TLDS_S))
        base = [70.0, 80.0, 88.0, 94.0][min(severe, 3)]
        spread = [9.0, 7.0, 5.0, 6.0][min(severe, 3)]
        t = max(0.0, min(1.0, phishing_prob))
        risk_score = round(min(100.0, base + t * spread), 1)

    reasons = _phishing_reasons(url, risk_score, risk_tier)

    return PhishingResponse(
        url=url,
        riskScore=risk_score,
        verdict=verdict,
        riskTier=risk_tier,
        confidence=round(confidence, 4),
        flaggedReasons=reasons,
        scannedAt=datetime.now(timezone.utc).isoformat(),
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
