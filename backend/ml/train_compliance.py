import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)

# ── Template bank (Bug 6a/b fix) ─────────────────────────────────────────────
# Each category has 25+ distinct sentence templates with embedded variation.
# Phrases cover varied phrasing, amounts, entities, jurisdictions, structures.

CATEGORIES = {
    "CLEAN": [
        "All terms comply with Companies Act 2013 and applicable MCA guidelines.",
        "Invoice for professional services rendered; 18% GST applied as per GST Act.",
        "Travel reimbursement for Bengaluru client visit with valid receipts and PAN.",
        "Standard salary credited to employee account with correct TDS deduction.",
        "Office stationery purchased from GST-registered vendor; bill retained.",
        "Annual software license renewal; vendor GSTIN verified; 18% IGST levied.",
        "Maintenance contract renewed with Mumbai-based vendor per procurement policy.",
        "Tax returns filed on time; advance tax paid as per Schedule VI requirement.",
        "Board resolution passed for Rs 2 crore capital expenditure with full approval.",
        "Quarterly audit by ICAI-empanelled firm; no material discrepancy noted.",
        "Export invoice raised with LUT; zero-rated supply under IGST Act.",
        "Inter-company loan at arm's length rate per transfer pricing report.",
        "Employee provident fund contributions deposited by due date as per EPF Act.",
        "Dividend declared in compliance with Companies Act Section 123.",
        "Vendor due diligence completed; GSTIN, PAN, and bank account verified.",
        "Payment to registered MSME vendor made within 45 days per MSME Act.",
        "Share allotment to existing shareholders; rights issue notified to SEBI.",
        "Statutory registers updated; annual return filed with Registrar of Companies.",
        "Insurance premium for company assets; policy from IRDAI-registered insurer.",
        "Lease agreement reviewed by legal; stamp duty paid per state legislation.",
        "Research grant from DSIR-approved institution; tax exemption claimed under 35(2AB).",
        "Charitable trust donation; donor furnished valid 80G certificate.",
        "Factory compliance inspection passed; no violations under Factories Act.",
        "Foreign remittance approved by Authorised Dealer under FEMA; AD code noted.",
        "Royalty payment to parent company at ALP; Form 15CB obtained from CA.",
    ],
    "AML_PMLA_VIOLATION": [
        "Payment routed to unverified offshore shell entity without RBI approval.",
        "Beneficial owner identity deliberately obscured; KYC documents withheld.",
        "Layering transaction: funds split across five nominees to evade PMLA reporting.",
        "Third-party payment for client invoice with no documented business relationship.",
        "Cash payments above Rs 2 lakh to single vendor circumventing PMLA threshold.",
        "Wire transfer to Cayman Islands entity lacking standard AML source verification.",
        "Multiple rapid round-trip transactions just below Rs 10 lakh FIU reporting limit.",
        "Correspondent bank routing through sanctioned jurisdiction without compliance check.",
        "Funds received from high-risk PEP without enhanced due diligence under PMLA.",
        "Nominee account used to receive contract proceeds; ultimate beneficiary unknown.",
        "Trade-based money laundering: invoice inflated by 300% vs market value.",
        "Structuring deposits into seven accounts to avoid CTR filing obligation.",
        "Hawala network used to settle Rs 50 lakh across five individuals in three cities.",
        "Bearer instrument payment to avoid audit trail; counterparty identity unknown.",
        "Proceeds of fraud detected in suspicious account; STR not filed within 7 days.",
        "Transaction routed through IFSC-non-compliant fintech without AML controls.",
        "Shell company in Mauritius used to receive export proceeds without declaration.",
        "Loan from foreign entity without ECB registration with Reserve Bank of India.",
        "Smurfing: Rs 9.8 lakh deposited repeatedly by different individuals to avoid KYC.",
        "Virtual assets used to settle B2B invoice bypassing PMLA entity verification.",
        "Real estate transaction settled in cash without ITR-verified income source.",
        "Unexplained wealth: asset value five times declared income over three years.",
        "Payment to politically exposed person without senior management sign-off.",
        "Cross-border payment with no underlying trade document; FEMA violation suspected.",
        "AML controls overridden by branch manager for high-value non-resident account.",
    ],
    "SOX_COMPLIANCE_BREACH": [
        "Transaction posted without segregation of duties; initiator and approver same person.",
        "Financial statement manually adjusted by CFO without audit trail or journal entry.",
        "Audit logs deleted during off-hours maintenance window before year-end review.",
        "Material weakness identified: no independent review of revenue recognition policy.",
        "Unauthorized access to ERP granted to terminated employee; access not revoked.",
        "Internal control override: purchase order backdated to match approval threshold.",
        "CEO certification filed under SOX 302 despite known misstatement in Q2 report.",
        "Undisclosed related-party transaction omitted from management representation letter.",
        "IT general controls failure: password policy not enforced for financial systems.",
        "Segregation of duties bypassed: same person performs bank reconciliation and approval.",
        "Quarterly earnings draft revised without version control or CFO sign-off.",
        "Disclosure controls deficiency: material contract not reported within 4 business days.",
        "Whistleblower complaint suppressed; no independent investigation initiated.",
        "Hedge accounting designation changed retroactively to improve P&L appearance.",
        "Impairment write-down deferred to next quarter to meet analyst earnings estimate.",
        "Restricted stock units granted without compensation committee approval.",
        "Contract revenue recognized upfront despite multi-year delivery obligation.",
        "Physical access to server room not logged; SOX ITGC audit finding raised.",
        "Change management process bypassed; production system modified without testing.",
        "Financial close performed without mandatory management review checklist completion.",
        "Intercompany eliminations skipped in consolidation; group results overstated.",
        "Significant estimate changed without documentation of basis or board approval.",
        "Going-concern doubt not disclosed in audit report despite cash flow deficiency.",
        "External auditor independence compromised: audit partner provided consulting services.",
        "Subsidiary accounts not consolidated; material revenue excluded from group results.",
    ],
    "GST_EVASION_SUSPICION": [
        "Fake tax invoice raised to claim ITC without actual supply of goods or services.",
        "GSTIN quoted on invoice belongs to a cancelled or non-existent taxpayer.",
        "Goods undervalued in invoice to reduce GST liability; actual price Rs 5 lakh.",
        "Vendor in GST suspension; input tax credit claimed against this supplier invalid.",
        "Circular trading: same goods invoiced among three related entities to inflate ITC.",
        "E-way bill not generated for interstate movement of goods worth Rs 1.2 lakh.",
        "Composition dealer raised inter-state tax invoice in violation of GST rules.",
        "ITC reversed on vendor payment outstanding beyond 180 days not adjusted in return.",
        "Zero-rated export claim without LUT or bond; IGST refund fraudulently claimed.",
        "Mismatch between GSTR-1 and GSTR-3B for Rs 18 lakh; no reconciliation submitted.",
        "Exempt supplies clubbed with taxable supplies; GST wrongly collected and retained.",
        "HSN code misclassified: 12% slab declared instead of applicable 28% for luxury goods.",
        "Invoice split to avoid e-invoicing mandate applicable above Rs 5 crore turnover.",
        "Duplicate invoice numbers issued to two different buyers for same tax period.",
        "Cash sales omitted from GSTR-1; output tax liability suppressed by Rs 3.6 lakh.",
        "Reverse charge mechanism not applied on import of services from foreign vendor.",
        "Input credit availed on personal expenses disguised as business procurement.",
        "Tax collected but not deposited; customer charged GST and amount misappropriated.",
        "Sub-contractor payments without deducting TDS under Section 51 of GST Act.",
        "Return filed under wrong GST category; turnover basis incorrect for composition scheme.",
        "Advance received from customer not declared in GSTR-1 for the relevant tax period.",
        "Stock transfer treated as supply but value declared at cost, not arm's length price.",
        "Input service distributor credit wrongly allocated to ineligible recipient units.",
        "Petroleum products included in GST input claim despite being outside GST ambit.",
        "Non-genuine invoice accepted from fly-by-night operator to boost ITC balance.",
    ],
    "UNAUTHORIZED_OFFSHORE_ROUTING": [
        "Funds remitted to Cayman Islands SPV without FEMA prior approval.",
        "Unregistered foreign remittance settled through informal hawala network.",
        "Dividend repatriation routed via Singapore holding company to avoid withholding tax.",
        "Transfer pricing manipulation: services invoiced to parent at 4x market rate.",
        "Round-tripping: Indian capital sent offshore and returned as FDI to avoid tax.",
        "Profit shifted to low-tax jurisdiction via management fee not justified at ALP.",
        "Subsidiary loan to parent treated as trade advance; ECB limits violated.",
        "Overseas direct investment made without Form ODI filing with Reserve Bank.",
        "Export proceeds not repatriated within prescribed period under FEMA Section 8.",
        "Fictitious consultancy fees paid to offshore entity for non-existent services.",
        "Thin capitalisation: related-party debt-to-equity ratio exceeds OECD guidelines.",
        "Foreign exchange earned retained in overseas account beyond FEMA-permitted limit.",
        "Capital account transaction conducted outside Liberalised Remittance Scheme limit.",
        "Buyback of shares by overseas subsidiary to return funds without board approval.",
        "Controlled foreign corporation income not included in Indian parent's total income.",
        "Hybrid instrument used to avoid Indian tax while claiming deduction in UK entity.",
        "Commission paid to foreign agent exceeds 12.5% FEDAI cap without RBI waiver.",
        "Goods imported via third country to mis-declare origin and evade customs duty.",
        "Overseas bank account operated without disclosure to Income Tax authorities.",
        "Treaty shopping: structure inserted solely to claim DTAA benefit without substance.",
        "Transfer of intellectual property to Mauritius entity at nominal value; BEPS risk.",
        "Loan repayment rerouted through Cyprus to obscure true creditor identity.",
        "Branch profit remittance exceeds permissible limit without Form 15CA/CB.",
        "Digital service tax avoided by routing revenue through non-resident intermediary.",
        "Swap arrangement between two multinationals to disguise cross-border profit shift.",
    ],
}

# ── Lexical variation helpers (Bug 6b fix) ────────────────────────────────────
AMOUNTS = [
    "Rs 1.2 lakh", "Rs 45,000", "INR 3 crore", "Rs 8,75,000", "Rs 12 lakh",
    "INR 50,000", "Rs 2.5 crore", "Rs 7,20,000", "INR 4.8 lakh", "Rs 99,000",
]
ENTITIES = [
    "Reliance Industries", "Infosys Ltd", "HDFC Bank", "TCS Mumbai branch",
    "XYZ Pvt Ltd", "Sharma & Associates", "Mehta Enterprises", "Kumar Corp",
    "Global Tech India", "Sunrise Exports", "Bharat Dynamics", "Apex Solutions",
]
YEARS = list(range(2019, 2027))
QUARTERS = ["Q1 FY24", "Q2 FY25", "Q3 FY23", "Q4 FY24", "H1 FY25", "H2 FY23"]


def augment(text: str) -> str:
    """Add random lexical variation to a template sentence."""
    amount = np.random.choice(AMOUNTS)
    entity = np.random.choice(ENTITIES)
    year = np.random.choice(YEARS)
    quarter = np.random.choice(QUARTERS)
    
    # Randomly append one of several suffixes
    suffixes = [
        f" Reviewed by {entity} audit team.",
        f" Transaction dated FY {year}.",
        f" Pertaining to {quarter} reporting period.",
        f" Amount involved: {amount}.",
        f" Entity: {entity}; period under review: {quarter}.",
        "",  # sometimes no suffix
    ]
    return text + np.random.choice(suffixes)


def generate_synthetic_compliance_data(n_samples=5000):
    X, y = [], []
    samples_per_class = n_samples // len(CATEGORIES)
    for label, templates in CATEGORIES.items():
        for _ in range(samples_per_class):
            base = np.random.choice(templates)
            X.append(augment(base))
            y.append(label)
    return X, y


# ── Held-out realistic evaluation set (Bug 6d fix) ────────────────────────────
# These are hand-written and MUST NOT be used during training.
HELD_OUT = [
    ("All vendor payments processed within 30 days; GST reconciliation complete for FY 2025.", "CLEAN"),
    ("Remittance to Dubai-based shell company without AD bank approval or purpose code.", "AML_PMLA_VIOLATION"),
    ("Audit committee was bypassed; CEO approved own expense claim of Rs 8 lakh.", "SOX_COMPLIANCE_BREACH"),
    ("Supplier raised invoice with cancelled GSTIN; buyer still claimed input tax credit.", "GST_EVASION_SUSPICION"),
    ("Profits parked in Netherlands holding company via royalty payments at 40% of turnover.", "UNAUTHORIZED_OFFSHORE_ROUTING"),
    ("Employee expense report approved by finance manager per delegation of authority policy.", "CLEAN"),
    ("Loan from promoter's BVI entity at zero interest; no arm's-length documentation.", "AML_PMLA_VIOLATION"),
    ("Same accountant both prepares and authorises journal entries above Rs 5 lakh threshold.", "SOX_COMPLIANCE_BREACH"),
    ("GST return filed with inflated ITC to reduce net tax payable by Rs 14 lakh.", "GST_EVASION_SUSPICION"),
    ("Indian subsidiary paying management fees to Singapore parent far above ALP benchmark.", "UNAUTHORIZED_OFFSHORE_ROUTING"),
]


def build_pipeline() -> Pipeline:
    return Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 3), max_features=8000, sublinear_tf=True)),
        ('clf', LogisticRegression(class_weight='balanced', C=1.0, random_state=42, max_iter=2000))
    ])


if __name__ == "__main__":
    print("Training Compliance Model (Indian Context — expanded templates)...")
    X, y = generate_synthetic_compliance_data(5000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    # ── Train/test split metrics ──────────────────────────────────────────────
    y_pred = pipeline.predict(X_test)
    print(f"\nTrain/Test Split Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("\n--- Classification Report (Train/Test Split) ---")
    print(classification_report(y_test, y_pred))

    # ── Cross-validation metrics (Bug 6c fix) ────────────────────────────────
    print("Running 5-fold stratified cross-validation for honest generalisation estimate...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(build_pipeline(), X, y, cv=skf, scoring='f1_macro', n_jobs=-1)
    print(f"Cross-Val F1 (macro) per fold: {[round(s, 4) for s in cv_scores]}")
    print(f"Mean CV F1: {cv_scores.mean():.4f}  (+/- {cv_scores.std():.4f})")

    # ── Held-out realistic evaluation (Bug 6d fix) ───────────────────────────
    X_ho, y_ho = zip(*HELD_OUT)
    y_ho_pred = pipeline.predict(list(X_ho))
    ho_accuracy = accuracy_score(list(y_ho), list(y_ho_pred))
    print(f"\nHeld-Out Realistic Clause Accuracy: {ho_accuracy:.2f} ({sum(p==g for p,g in zip(y_ho_pred,y_ho))}/{len(y_ho)})")
    for clause, true_label, pred_label in zip(X_ho, y_ho, y_ho_pred):
        status = "OK" if true_label == pred_label else "WRONG"
        print(f"  [{status}] True={true_label} | Pred={pred_label} | \"{clause[:60]}...\"")

    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models', 'compliance_model.joblib'))
    joblib.dump(pipeline, model_path)
    print(f"\nSaved compliance model to {model_path}")
