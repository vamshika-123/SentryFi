import re
import pdfplumber
import pytesseract
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

# ── Currency detection ────────────────────────────────────────────────────────
_CURRENCY_SYMBOLS = {'₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP'}
_SYMBOL_MAP = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£'}

def _detect_currency(text: str):
    """
    Returns ISO currency code detected in the invoice text, or None if detection fails.
    Priority: explicit ISO code / Rs -> currency symbol -> None (caller must handle).
    Returning None means the backend will signal to the frontend that the user
    should be asked to pick a currency manually.
    """
    # 1. Look for explicit 3-letter ISO codes (standalone, e.g. "EUR", "[GBP]", "USD")
    iso_match = re.search(r'\b(EUR|GBP|USD|INR|CHF|AUD|CAD|JPY|CNY|SGD|AED)\b', text, re.IGNORECASE)
    if iso_match:
        return iso_match.group(1).upper()
    if re.search(r'\bRs\.?\b', text, re.IGNORECASE):
        return 'INR'
    # 2. Look for unambiguous currency symbols near numbers
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            return code
    # 3. Cannot confidently detect — return None so the caller can ask the user
    return None

def _currency_display(code) -> str:
    """Return display symbol for ISO code, or code itself if unrecognised. None -> ''."""
    if code is None:
        return ''
    return _SYMBOL_MAP.get(code, code)

# ── Currency-aware number extraction ─────────────────────────────────────────
# Matches any known currency prefix (symbol or ISO code) optionally before a number
_CCY_PREFIX = r'(?:₹|Rs\.?|INR|EUR|GBP|USD|\$|€|£|CHF|AUD|CAD)?\s*'
_AMOUNT = r'([\d,]+\.?\d{0,2})'   # e.g. 402.9 or 2,712.95 or 1000

def _parse_amount(text_fragment: str) -> float:
    """Strip commas and cast to float; return 0.0 on failure."""
    try:
        return float(text_fragment.replace(',', '').strip())
    except (ValueError, AttributeError):
        return 0.0



# Currencies that use Indian GST slab logic when user-selected
_INR_CURRENCIES = {'INR'}


def parse_invoice_text(text: str, currency_hint: str = None) -> dict:
    """
    Parse invoice text and extract ML features.

    currency_hint: optional ISO code supplied by the user when auto-detection failed.
      When provided it overrides _detect_currency() AND adjusts is_gst_invoice logic:
        INR  -> apply Indian GST slab deviation check
        other -> treat as generic tax (neutral effective_tax_rate, no slab check)

    Model feature columns (must stay fixed — 5 keys):
        subtotal, gst_rate_deviation, item_sum_delta, round_number_bias,
        tds_deduction_mismatch

    Display-only fields (NOT fed to model):
        tax_amount, line_item_delta, tax_percentage_variance,
        currency, currency_user_selected, additional_charges,
        additional_charges_label, tax_not_stated, effective_tax_rate, is_gst_invoice
    """
    # Currency: user hint takes precedence over auto-detection
    if currency_hint:
        currency = currency_hint.strip().upper()
        currency_user_selected = True
    else:
        currency = _detect_currency(text)   # may be None
        currency_user_selected = False

    # ── BUG 11: Subtotal — summary-line match first, then line-item fallback ──
    subtotal = 0.0
    subtotal_match = re.search(
        r'(?:subtotal|sub-total|total before tax)[\s:]+' + _CCY_PREFIX + _AMOUNT,
        text, re.IGNORECASE
    )
    if subtotal_match:
        subtotal = _parse_amount(subtotal_match.group(1))

    # ── BUG 14: Tax — distinguish GST-labelled vs. generic ───────────────────
    tax_amount = 0.0
    # is_gst_invoice: True when tax lines are explicitly labelled GST/CGST/SGST/IGST
    # OR when the user-supplied currency hint is INR (implying Indian context)
    is_gst_invoice = False
    gst_hint_from_currency = (currency in _INR_CURRENCIES)

    # Try CGST/SGST/IGST components first
    gst_component_pattern = re.compile(
        r'\b(CGST|SGST|IGST)\b(?:\s*[\(@]?\s*[\d.]+\s*%(?:\s*\))?)?.{0,40}?' + _CCY_PREFIX + _AMOUNT,
        re.IGNORECASE
    )
    gst_matches = gst_component_pattern.findall(text)
    if gst_matches:
        tax_amount = sum(_parse_amount(m[1]) for m in gst_matches)
        is_gst_invoice = True
    else:
        # Check for bare "GST" label
        gst_bare = re.search(
            r'\bGST\b(?:\s*[\(@]?\s*[\d.]+\s*%(?:\s*\))?)?.{0,30}?' + _CCY_PREFIX + _AMOUNT,
            text, re.IGNORECASE
        )
        if gst_bare:
            tax_amount = _parse_amount(gst_bare.group(1))
            is_gst_invoice = True
        else:
            # Generic tax/VAT/Sales Tax line
            tax_fallback = re.search(
                r'\b(?:sales\s*tax|vat|tax)\b(?:\s*[\(@]?\s*[\d.]+\s*%(?:\s*\))?)?.{0,30}?' + _CCY_PREFIX + _AMOUNT,
                text, re.IGNORECASE
            )
            if tax_fallback:
                tax_amount = _parse_amount(tax_fallback.group(1))
                # If user explicitly selected INR, even a generic "Tax" label is
                # likely Indian GST — apply slab check.
                is_gst_invoice = gst_hint_from_currency

    # ── Grand Total ───────────────────────────────────────────────────────────
    total = 0.0
    total_match = re.search(
        r'\b(?:grand total|amount due|total due|total payable)\b.{0,40}?' + _CCY_PREFIX + _AMOUNT,
        text, re.IGNORECASE
    )
    if not total_match:
        total_match = re.search(
            r'(?<!\w)Total[\s:]+' + _CCY_PREFIX + _AMOUNT,
            text, re.IGNORECASE
        )
    if total_match:
        total = _parse_amount(total_match.group(1))

    # ── BUG 11: Line-item table fallback ─────────────────────────────────────
    # Trigger when summary-line parse didn't find a subtotal/total.
    tax_not_stated = False
    line_item_computed_subtotal = None

    if subtotal == 0.0 and total == 0.0:
        # Scan lines for rows ending with a currency amount (but skip obvious header lines)
        line_amounts = []
        header_keywords = re.compile(
            r'\b(?:description|qty|quantity|unit|price|amount|item|date|invoice|no\.?|#)\b',
            re.IGNORECASE
        )
        for line in text.splitlines():
            line = line.strip()
            if not line or header_keywords.search(line):
                continue
            # A "data row" ends with an optional currency prefix + number
            row_match = re.search(
                _CCY_PREFIX + r'([\d,]+\.?\d{0,2})\s*$',
                line
            )
            if row_match:
                amount = _parse_amount(row_match.group(1))
                if amount > 0:
                    line_amounts.append(amount)

        if line_amounts:
            # Use the largest single value as the total if recognisable,
            # otherwise sum all detected row amounts as the computed subtotal
            if len(line_amounts) >= 2:
                # Heuristic: if one value equals ~sum of the others it's a total row
                sorted_amounts = sorted(line_amounts)
                candidate_total = sorted_amounts[-1]
                candidate_subtotal_sum = sum(sorted_amounts[:-1])
                if abs(candidate_total - candidate_subtotal_sum) < (candidate_total * 0.05):
                    # Last line is likely the total, rest are line-item rows
                    subtotal = candidate_subtotal_sum
                    total = candidate_total
                else:
                    subtotal = sum(line_amounts)
            else:
                subtotal = line_amounts[0]

            line_item_computed_subtotal = subtotal
            tax_not_stated = True  # no summary section = no explicit tax breakdown

    # ── True extraction failure — both strategies returned nothing ─────────────
    extraction_failed = (subtotal == 0.0 and total == 0.0)
    if extraction_failed:
        return {
            "subtotal": 0.0,
            "gst_rate_deviation": 0.0,
            "item_sum_delta": 0.0,
            "round_number_bias": 0,
            "tds_deduction_mismatch": 0.0,
            "extraction_failed": True,
            # Display-only
            "currency": currency,
            "currency_user_selected": currency_user_selected,
            "tax_not_stated": True,
        }

    # ── BUG 13 / BUG 17: Additional charges (shipping, discounts, …) ─────────
    # Process LINE BY LINE so a line like "Shipping & Handling: 50.00" is counted
    # ONCE, not once per matching keyword.  Per-keyword independent searches
    # caused double/triple counting on combined-label lines.
    additional_charges = 0.0
    additional_charges_label = ""

    _ADDITIVE_KW = r'(?:shipping|handling|delivery|service\s+charge|postage|freight)'
    _SUBTRACTIVE_KW = r'(?:discount|rebate|credit)'
    _CHARGE_LINE_RE = re.compile(
        r'(?P<type>' + _ADDITIVE_KW + r'|' + _SUBTRACTIVE_KW + r').*?' +
        _CCY_PREFIX + r'(?P<amount>[\d,]+\.?\d{0,2})\s*$',
        re.IGNORECASE
    )
    _ADDITIVE_RE = re.compile(_ADDITIVE_KW, re.IGNORECASE)

    seen_lines = set()   # dedup: skip lines we've already captured an amount from

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped in seen_lines:
            continue
        m = _CHARGE_LINE_RE.search(stripped)
        if not m:
            continue
        val = _parse_amount(m.group('amount'))
        if val <= 0:
            continue
        seen_lines.add(stripped)
        # Determine first keyword found in the line to name the label
        first_kw = m.group('type').strip()
        sym = _currency_display(currency)
        if _ADDITIVE_RE.match(first_kw):
            additional_charges += val
            label = f"{first_kw.title()}: {sym}{val:.2f}"
        else:
            additional_charges -= val
            label = f"{first_kw.title()}: -{sym}{val:.2f}"
        additional_charges_label = (additional_charges_label + "; " + label).lstrip("; ")

    # ── Line-item delta (BUG 13 fix: include additional charges) ─────────────
    line_item_delta = 0.0
    if subtotal > 0 and total > 0:
        expected_total = subtotal + tax_amount + additional_charges
        line_item_delta = abs(total - expected_total)
    # If no explicit total found (line-item-table path), delta stays 0
    if total == 0.0:
        line_item_delta = 0.0

    # ── BUG 14: Tax rate logic ────────────────────────────────────────────────
    tax_to_subtotal_ratio = tax_amount / subtotal if subtotal > 0 else 0.0
    STANDARD_GST_RATES = [0.05, 0.12, 0.18, 0.28]

    gst_rate_deviation = 0.0
    effective_tax_rate = round(tax_to_subtotal_ratio * 100, 4)  # plain percentage, always computed

    if is_gst_invoice and subtotal > 0 and tax_amount > 0:
        # Compare against nearest valid Indian GST slab
        gst_rate_deviation = min(abs(tax_to_subtotal_ratio - r) for r in STANDARD_GST_RATES)
    else:
        # Generic / non-GST invoice — deviation is meaningless; keep at 0
        gst_rate_deviation = 0.0

    # ── TDS Mismatch ──────────────────────────────────────────────────────────
    tds_deduction_mismatch = 0.0
    tds_amount_stated = None

    tds_amount_match = re.search(
        r'\b(?:TDS|tax deducted at source|194C?|194J|194H|194I)\b.{0,60}?' + _CCY_PREFIX + _AMOUNT,
        text, re.IGNORECASE | re.DOTALL
    )
    if tds_amount_match:
        tds_amount_stated = _parse_amount(tds_amount_match.group(1))

    tds_rate = 0.10
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
        "line_item_delta": round(line_item_delta, 2),
        "tax_percentage_variance": round(gst_rate_deviation * 100, 4),
        # BUG 12: currency
        "currency": currency,
        "currency_user_selected": currency_user_selected,
        # BUG 13: additional charges breakdown
        "additional_charges": round(additional_charges, 2),
        "additional_charges_label": additional_charges_label,
        # BUG 11: no summary section flag
        "tax_not_stated": tax_not_stated,
        # BUG 14: neutral tax rate and GST context flag
        "effective_tax_rate": effective_tax_rate,
        "is_gst_invoice": is_gst_invoice,
    }


def process_invoice_file(file_bytes: bytes, filename: str, currency_hint: str = None) -> dict:
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
    return parse_invoice_text(text, currency_hint=currency_hint)
