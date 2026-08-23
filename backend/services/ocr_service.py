import re
import pdfplumber
import pytesseract
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def parse_invoice_text(text: str) -> dict:
    """
    Parse invoice text and extract ML features.
    Returns a dict with numeric features, plus an 'extraction_failed' bool.
    """
    subtotal = 0.0
    tax_amount = 0.0
    total = 0.0

    # ── Subtotal ────────────────────────────────────────────────────────────────
    subtotal_match = re.search(
        r'(?:subtotal|sub-total|total before tax)[\s:]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
        text, re.IGNORECASE
    )
    if subtotal_match:
        subtotal = float(subtotal_match.group(1).replace(',', ''))

    # ── GST Tax (Bug 3 fix) ─────────────────────────────────────────────────────
    # Strategy: try to sum CGST + SGST + IGST line items individually first.
    # Each is typically on its own line: "CGST @ 9%: ₹4,500.00" or "SGST  ₹ 1,500.00"
    # Tightly bounded pattern — number must appear within ~40 chars of the keyword.
    gst_component_pattern = re.compile(
        r'\b(CGST|SGST|IGST)\b.{0,40}?(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
        re.IGNORECASE
    )
    gst_matches = gst_component_pattern.findall(text)
    if gst_matches:
        tax_amount = sum(float(m[1].replace(',', '')) for m in gst_matches)
    else:
        # Fallback: generic tax keyword — but constrained to 30 chars after keyword
        tax_fallback = re.search(
            r'\b(?:tax|vat|gst)\b.{0,30}?(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
            text, re.IGNORECASE
        )
        if tax_fallback:
            tax_amount = float(tax_fallback.group(1).replace(',', ''))

    # ── Grand Total ─────────────────────────────────────────────────────────────
    total_match = re.search(
        r'\b(?:grand total|amount due|total due|total payable)\b.{0,40}?(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
        text, re.IGNORECASE
    )
    if not total_match:
        # Narrower match for bare "Total:" to avoid matching "Subtotal"
        total_match = re.search(
            r'(?<!\w)Total[\s:]+(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
            text, re.IGNORECASE
        )
    if total_match:
        total = float(total_match.group(1).replace(',', ''))

    # ── Extraction failed (Bug 4 fix) ───────────────────────────────────────────
    # Do NOT silently substitute fake values — flag it instead
    extraction_failed = (subtotal == 0.0 and total == 0.0)
    if extraction_failed:
        return {
            "subtotal": 0.0,
            "gst_rate_deviation": 0.0,
            "item_sum_delta": 0.0,
            "round_number_bias": 0,
            "tds_deduction_mismatch": 0.0,
            "extraction_failed": True,
        }

    # ── Line-item sum delta ─────────────────────────────────────────────────────
    line_item_delta = 0.0
    if subtotal > 0 and tax_amount > 0 and total > 0:
        line_item_delta = abs(total - (subtotal + tax_amount))

    # ── GST Rate Deviation ──────────────────────────────────────────────────────
    tax_to_subtotal_ratio = tax_amount / subtotal if subtotal > 0 else 0.0
    # Indian standard slabs: 5, 12, 18, 28 %.  Deviation = min distance to any slab.
    STANDARD_GST_RATES = [0.05, 0.12, 0.18, 0.28]
    if subtotal > 0 and tax_amount > 0:
        gst_rate_deviation = min(abs(tax_to_subtotal_ratio - r) for r in STANDARD_GST_RATES)
    else:
        gst_rate_deviation = 0.0

    # ── TDS Deduction Mismatch (Bug 2 fix) ─────────────────────────────────────
    # Look for TDS-related lines and their stated amounts.
    tds_deduction_mismatch = 0.0
    tds_amount_stated = None

    tds_amount_match = re.search(
        r'\b(?:TDS|tax deducted at source|194C?|194J|194H|194I)\b.{0,60}?(?:₹|Rs\.?|INR)?\s*([\d,]+\.\d{2})',
        text, re.IGNORECASE | re.DOTALL
    )
    if tds_amount_match:
        tds_amount_stated = float(tds_amount_match.group(1).replace(',', ''))

    # Also try to extract explicit TDS rate from text
    tds_rate = 0.10  # default 10%
    tds_rate_match = re.search(
        r'\b(?:TDS|tax deducted)\b.*?@\s*([\d.]+)\s*%',
        text, re.IGNORECASE | re.DOTALL
    )
    if tds_rate_match:
        try:
            tds_rate = float(tds_rate_match.group(1)) / 100.0
        except ValueError:
            pass

    if tds_amount_stated is not None and subtotal > 0:
        expected_tds = subtotal * tds_rate
        tds_deduction_mismatch = abs(tds_amount_stated - expected_tds)
    # If no TDS section found at all, leave mismatch as 0.0
    # (many B2C invoices legitimately have no TDS; the model handles this via other features)

    return {
        # ── Model features (these 5 keys must stay in sync with invoice_model.joblib) ──
        "subtotal": subtotal,
        "gst_rate_deviation": round(gst_rate_deviation, 6),
        "item_sum_delta": round(line_item_delta, 2),
        "round_number_bias": 1 if subtotal % 100 == 0 else 0,
        "tds_deduction_mismatch": round(tds_deduction_mismatch, 2),
        "extraction_failed": False,
        # ── Display-only keys for API response / frontend (NOT fed to model) ──
        "tax_amount": round(tax_amount, 2),
        "line_item_delta": round(line_item_delta, 2),          # alias of item_sum_delta for frontend
        "tax_percentage_variance": round(gst_rate_deviation * 100, 4),  # deviation as % for UI display
    }


def process_invoice_file(file_bytes: bytes, filename: str) -> dict:
    text = ""
    if filename.lower().endswith('.pdf'):
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"PDF extraction failed: {e}")
    elif filename.lower().endswith('.txt'):
        text = file_bytes.decode('utf-8', errors='ignore')
    else:
        # Assume image
        try:
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")

    # Do NOT inject fake fallback text here — let parse_invoice_text set extraction_failed
    return parse_invoice_text(text)
