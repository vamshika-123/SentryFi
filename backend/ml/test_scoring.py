import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import json
import joblib
import pandas as pd
from backend.services.ocr_service import process_invoice_file, parse_invoice_text

model = joblib.load('backend/models/invoice_model.joblib')
with open('backend/models/invoice_score_range.json') as f:
    score_range = json.load(f)

normal_max = score_range['normal_max']
anom_max = score_range['anom_max']

def score_invoice(features_dict, filename='test'):
    MODEL_FEATURE_KEYS = ['subtotal', 'gst_rate_deviation', 'item_sum_delta', 'round_number_bias', 'tds_deduction_mismatch']
    df = pd.DataFrame([{k: features_dict[k] for k in MODEL_FEATURE_KEYS}])
    raw_dec = float(model.decision_function(df)[0])
    
    if raw_dec >= 0:
        ratio = min(1.0, raw_dec / max(1e-5, normal_max))
        risk_score = round(max(0.0, 50.0 * (1.0 - ratio)), 1)
    else:
        ratio = min(1.0, abs(raw_dec) / max(1e-5, anom_max))
        risk_score = round(min(100.0, 50.0 + 50.0 * ratio), 1)

    pred = model.predict(df)[0]
    is_anomaly = pred == -1
    if (features_dict.get('gst_rate_deviation', 1) < 0.01 and
        features_dict.get('item_sum_delta', 1) < 1.0 and
        features_dict.get('round_number_bias', 1) == 0 and
        features_dict.get('tds_deduction_mismatch', 1) < 1.0):
        is_anomaly = False
        risk_score = min(risk_score, 25.0)
        
    verdict = 'SUSPICIOUS' if is_anomaly else 'CLEAN'
    return {
        'verdict': verdict,
        'riskScore': risk_score,
        'decision_function': round(raw_dec, 4),
        'features': features_dict
    }

if __name__ == "__main__":
    print('================ TEST 1: SYNTHETIC SAMPLES ================')
    normal_synth = {'subtotal': 45000.0, 'gst_rate_deviation': 0.005, 'item_sum_delta': 0.0, 'round_number_bias': 0, 'tds_deduction_mismatch': 0.0}
    anom_synth = {'subtotal': 2500000.0, 'gst_rate_deviation': 0.30, 'item_sum_delta': 15000.0, 'round_number_bias': 1, 'tds_deduction_mismatch': 4000.0}

    res_norm = score_invoice(normal_synth)
    print(f"Normal Synthetic   -> Verdict: {res_norm['verdict']}, Risk Score: {res_norm['riskScore']}/100 (decision: {res_norm['decision_function']})")
    res_anom = score_invoice(anom_synth)
    print(f"Anomalous Synthetic-> Verdict: {res_anom['verdict']}, Risk Score: {res_anom['riskScore']}/100 (decision: {res_anom['decision_function']})")

    print('\n================ TEST 2: DEMO PDF INVOICES ================')
    demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../demo_samples'))
    for f in sorted(os.listdir(demo_dir)):
        if 'invoice' in f and f.endswith('.pdf'):
            path = os.path.join(demo_dir, f)
            with open(path, 'rb') as fp:
                feat = process_invoice_file(fp.read(), f)
                res = score_invoice(feat, f)
                print(f"{f:30} -> Verdict: {res['verdict']:10} | Risk Score: {res['riskScore']:4.1f}/100 | decision: {res['decision_function']:+0.4f}")

    print('\n================ TEST 3: REAL-WORLD INVOICES ================')
    # UK invoice: no summary section, subtotal from items
    uk_invoice_text = '''TechConsult UK Ltd
Date: 15/08/2026
Description Qty Rate Amount
Backend Architecture Review 1 2000.00 2000.00
Cloud Migration Setup 1 3500.00 3500.00
Database Optimization 1 1250.00 1250.00
'''
    uk_feat = parse_invoice_text(uk_invoice_text, currency_hint='GBP')
    res_uk = score_invoice(uk_feat)
    print(f"UK Invoice (No Summary)        -> Verdict: {res_uk['verdict']:10} | Risk Score: {res_uk['riskScore']:4.1f}/100 | [Tax Not Stated: {uk_feat.get('tax_not_stated')}]")

    # EUR standard invoice
    eur_invoice_text = '''EuroTech GmbH
Invoice EUR 94812
Subtotal: 2500.00
VAT: 475.00
Total: 2975.00
'''
    eur_feat = parse_invoice_text(eur_invoice_text, currency_hint='EUR')
    res_eur = score_invoice(eur_feat)
    print(f"EUR Standard Invoice           -> Verdict: {res_eur['verdict']:10} | Risk Score: {res_eur['riskScore']:4.1f}/100 | [Mismatch: {eur_feat.get('line_item_delta'):.2f}]")

    # EUR with shipping
    eur_shipping_text = '''Logistics EU BV
Subtotal: 5000.00
Sales Tax: 950.00
Shipping & Handling: 150.00
Total: 6100.00
'''
    eur_ship_feat = parse_invoice_text(eur_shipping_text, currency_hint='EUR')
    res_ship = score_invoice(eur_ship_feat)
    print(f"EUR Invoice w/ Shipping        -> Verdict: {res_ship['verdict']:10} | Risk Score: {res_ship['riskScore']:4.1f}/100 | [Mismatch: {eur_ship_feat.get('line_item_delta'):.2f}]")
