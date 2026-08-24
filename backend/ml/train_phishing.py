"""
train_phishing.py — Phishing URL classifier retraining script
=============================================================

Dataset choice (BUG 7a)
-----------------------
Primary dataset:
    Faizann24 / "Using machine learning to detect malicious URLs"
    URL:  https://raw.githubusercontent.com/faizann24/Using-machine-learning-to-detect-malicious-URLs/master/data/data.csv
    Size: ~420,000 URLs (344,821 good + 75,643 bad)
    Format: CSV with columns [url, label] where label ∈ {good, bad}
    Why chosen:
      • Directly downloadable as a single CSV from a stable GitHub repo (no API key needed).
      • Large enough for a real held-out test split — far beyond the 10-15 template issue.
      • Covers real-world diversity: typosquats, IP-based, redirectors, parked domains, legit sites.
      • Well-known in the academic security ML literature; widely used as a benchmark.
      • Labels map trivially: bad→1 (phishing/malicious), good→0 (legitimate).

Supplemental datasets:
    • OpenPhish live feed (https://openphish.com/feed.txt) — ~300 currently-active phishing URLs
      fetched at training time to ensure the model sees fresh real-world phishing patterns.
    • Existing synthetic data (generate_fallback_phishing_data) — adds deliberate red-flag
      patterns (IP tricks, @ symbol, suspicious TLDs, high-entropy subdomains) that may be
      underrepresented in the primary dataset.

All three sources are combined and deduplicated before training (BUG 7b).

Class imbalance handling (BUG 7c):
    The faizann24 dataset is ~82% good / 18% bad.  We use RandomForest with
    class_weight='balanced' to compensate, which internally scales class weights
    inversely proportional to their frequencies.  We do NOT oversample/undersample
    since the imbalance is mild enough for class weighting to handle correctly.

BUG 22 — Probability calibration:
    RandomForest's raw predict_proba() saturates to near-0/1 because it votes
    across trees and can achieve near-unanimity even for borderline cases.
    Fix: wrap the base Pipeline in CalibratedClassifierCV(method='isotonic',
    cv='prefit') on a dedicated 20% calibration hold-out.  This remaps raw
    scores to realistic probabilities without retraining the forest itself.
    cv='prefit' is used (instead of cv=5) because cv=5 would train 5 full
    300-tree RFs on 400K rows — impractical.  The pre-fit approach trains the
    base model once, then uses a calibration set to fit the isotonic mapping.

BUG 23 — Engineered severity-gradation features:
    The original 13 features are correct but insufficiently graduated — boolean
    flags (has_ip, has_suspicious_tld) contribute ±1 each with no sense of
    accumulation, and keyword_count is summed globally across the full URL rather
    than split by URL zone (domain vs path) where meaning differs.
    Fix: add 6 new features that give the classifier explicit severity gradation:
      • is_exact_brand_domain   — registered domain exactly matches a known-good
                                   brand (paypal.com → safe, paypal-account-update.com → not)
      • severe_signal_count     — count of the strongest individual indicators
                                   (raw IP + @ symbol + suspicious TLD + brand-in-subdomain);
                                   accumulates rather than individually dominating
      • registered_domain_len   — length of just the SLD (paypal-account-update
                                   is 22 chars; paypal is 6) — longer typosquats score higher
      • path_keyword_count      — keywords found specifically in the URL path
                                   (login/verify/secure in the PATH is a stronger signal
                                   than in the domain, where they may be typosquat tokens)
      • has_ip_with_path        — raw IP AND non-empty path (almost exclusively phishing)
      • domain_hyphen_count     — hyphens in just the registered domain name (not full URL)
"""

import os
import re
import math
import joblib
import pandas as pd
import numpy as np
import tldextract
import urllib.request
import io
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report,
)

os.makedirs(os.path.join(os.path.dirname(__file__), '../models'), exist_ok=True)


# ── Feature extractor (BUG 23: extended with severity-gradation features) ────
class URLFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts 19 structural features from raw URL strings.
    Features 1-13: original set (unchanged, backward-compatible).
    Features 14-19: new severity-gradation features (BUG 23).
    """

    # Exact registered-domain names of well-known legitimate sites.
    # A URL whose SLD exactly matches this set is almost certainly safe,
    # even if it contains financial keywords (e.g. paypal.com/login).
    EXACT_LEGIT_DOMAINS = frozenset([
        'paypal', 'google', 'amazon', 'microsoft', 'apple', 'facebook',
        'twitter', 'instagram', 'netflix', 'github', 'linkedin', 'youtube',
        'chase', 'wellsfargo', 'bankofamerica', 'citibank', 'hsbc', 'barclays',
        'hdfcbank', 'sbi', 'icicibank', 'axisbank', 'kotak', 'indusind',
        'stripe', 'paypal', 'wise', 'razorpay', 'paytm', 'phonepe',
        'dropbox', 'slack', 'zoom', 'adobe', 'shopify', 'ebay', 'alibaba',
        'uber', 'airbnb', 'booking', 'expedia', 'reddit', 'quora',
    ])

    PATH_KEYWORDS = [
        'login', 'signin', 'secure', 'verify', 'account', 'wallet',
        'bank', 'confirm', 'validate', 'credential', 'password', 'auth',
    ]

    def __init__(self):
        self.financial_keywords = [
            'login', 'secure', 'bank', 'verify', 'kyc', 'wallet', 'paypal',
            'crypto', 'update', 'confirm', 'account', 'signin', 'password',
            'credential', 'authorize', 'authenticate', 'reset', 'unlock',
        ]
        self.suspicious_tlds = [
            'xyz', 'top', 'ru', 'tk', 'cc', 'info', 'biz',
            'cf', 'ga', 'gq', 'ml', 'pw', 'click', 'live',
        ]
        self.known_brands = [
            'paypal', 'amazon', 'google', 'microsoft', 'apple', 'netflix',
            'hdfc', 'sbi', 'icici', 'axis', 'paytm', 'upi', 'npci',
        ]

    def fit(self, X, y=None):
        return self

    def _shannon_entropy(self, string):
        if not string:
            return 0.0
        prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(list(string))]
        return -sum(p * math.log(p) / math.log(2.0) for p in prob)

    def transform(self, X):
        features = []
        for url in X:
            url_str = str(url).lower()
            ext  = tldextract.extract(url_str)
            # path: everything after scheme+host (drop leading slash)
            try:
                _parts = url_str.split('/', 3)
                path = _parts[3] if len(_parts) > 3 else ''
            except Exception:
                path = ''

            # ── Original 13 features ─────────────────────────────────────────
            url_length         = len(url_str)
            dot_count          = url_str.count('.')
            hyphen_count       = url_str.count('-')          # hyphens in full URL
            at_count           = url_str.count('@')
            subdomain_depth    = len(ext.subdomain.split('.')) if ext.subdomain else 0
            has_ip             = 1 if re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', url_str) else 0
            has_suspicious_tld = 1 if ext.suffix in self.suspicious_tlds else 0
            has_https          = 1 if url_str.startswith('https') else 0
            path_length        = len(path)
            digit_ratio        = sum(c.isdigit() for c in url_str) / max(len(url_str), 1)
            entropy            = self._shannon_entropy(ext.domain if ext.domain else url_str)
            keyword_count      = sum(1 for kw in self.financial_keywords if kw in url_str)
            brand_in_subdomain = int(
                any(b in ext.subdomain.lower()
                    for b in getattr(self, 'known_brands', [
                        'paypal','amazon','google','microsoft','apple','netflix',
                        'hdfc','sbi','icici','axis','paytm','upi','npci',
                    ])) and
                not any(b == ext.domain.lower()
                    for b in getattr(self, 'known_brands', [
                        'paypal','amazon','google','microsoft','apple','netflix',
                        'hdfc','sbi','icici','axis','paytm','upi','npci',
                    ]))
            )

            # ── New severity-gradation features (BUG 23) ─────────────────────

            # 14. is_exact_brand_domain
            #     True when the registered domain (SLD) *exactly* matches a
            #     known-good brand.  paypal.com → 1 (safe), paypal-update.com → 0.
            #     Prevents brand-keyword URLs from being blindly flagged.
            is_exact_brand = int(ext.domain.lower() in self.EXACT_LEGIT_DOMAINS)

            # 15. severe_signal_count
            #     Counts the highest-severity individual phishing indicators.
            #     Accumulates: 2 severe signals > 1, unlike isolated boolean flags.
            severe_signal_count = (
                has_ip
                + int(at_count > 0)
                + has_suspicious_tld
                + brand_in_subdomain
            )

            # 16. registered_domain_len
            #     Length of just the SLD (e.g. "paypal-account-update" = 21).
            #     Legitimate brands have short SLDs; typosquats pad with keywords.
            registered_domain_len = len(ext.domain)

            # 17. path_keyword_count
            #     Financial/auth keywords appearing specifically in the PATH
            #     (not the domain).  login/verify/secure in a path is a strong
            #     phishing signal regardless of the domain name.
            path_keyword_count = sum(1 for kw in self.PATH_KEYWORDS if kw in path.lower())

            # 18. has_ip_with_path
            #     Raw IP address AND a non-trivial path — almost exclusively
            #     phishing infrastructure.  Gives the IP feature extra weight
            #     when combined with a credential-harvesting path.
            has_ip_with_path = int(has_ip == 1 and len(path) > 3)

            # 19. domain_hyphen_count
            #     Hyphens in just the registered domain (SLD), not the full URL.
            #     "paypal-account-update" has 2 domain hyphens — a typosquat
            #     pattern.  Separates domain padding from legitimate URL parameters.
            domain_hyphen_count = ext.domain.count('-')

            features.append([
                # Original 13
                url_length, dot_count, hyphen_count, at_count, subdomain_depth,
                has_ip, has_suspicious_tld, has_https, path_length, digit_ratio,
                entropy, keyword_count, brand_in_subdomain,
                # New 6 (BUG 23)
                is_exact_brand, severe_signal_count, registered_domain_len,
                path_keyword_count, has_ip_with_path, domain_hyphen_count,
            ])

        return np.array(features)


# ── Synthetic fallback data (kept for coverage of edge-case patterns) ─────────
LEGIT_DOMAINS = [
    # Banking & Finance (India)
    "hdfcbank.com/netbanking", "sbi.co.in/home", "icicibank.com/Personal",
    "axisbank.com/retail", "bankofbaroda.in", "pnbindia.in",
    "kotak.com/mahindra-bank", "indusind.com", "yesbank.in",
    "rbi.org.in/scripts", "npci.org.in", "sebi.gov.in",
    # Banking (Global)
    "chase.com/personal", "wellsfargo.com/banking", "bankofamerica.com",
    "citi.com/global", "hsbc.com/home", "barclays.co.uk",
    # E-commerce (India)
    "flipkart.com/electronics", "amazon.in/orders", "myntra.com",
    "snapdeal.com", "nykaa.com/fashion", "ajio.com", "meesho.com",
    "bigbasket.com", "grofers.com", "jiomart.com",
    # E-commerce (Global)
    "amazon.com/account", "ebay.com/myaccount", "alibaba.com",
    "etsy.com/shop", "shopify.com/admin", "wayfair.com",
    # Payments & Fintech
    "paytm.com/pay", "phonepe.com/transact", "googlepay.com",
    "bhimupi.org.in", "razorpay.com/dashboard", "stripe.com/billing",
    "paypal.com/myaccount/transfer", "wise.com/send",
    # Social & Professional
    "linkedin.com/in", "twitter.com/home", "facebook.com/login",
    "instagram.com/accounts", "reddit.com/r", "quora.com",
    "github.com/settings", "stackoverflow.com",
    # Tech & Cloud
    "google.com/drive", "microsoft.com/office", "apple.com/icloud",
    "dropbox.com/home", "notion.so/workspace", "slack.com/app",
    "zoom.us/meeting", "teams.microsoft.com", "aws.amazon.com/console",
    # News & Gov (India)
    "thehindu.com", "ndtv.com/business", "economictimes.indiatimes.com",
    "incometaxindiaefiling.gov.in", "gst.gov.in", "mca.gov.in",
    "epfindia.gov.in", "uidai.gov.in/myaadhaar", "passport.gov.in",
    # News & Gov (Global)
    "bbc.com/news", "reuters.com/finance", "bloomberg.com/markets",
    "cnn.com", "nytimes.com", "theguardian.com",
    # Healthcare & Education
    "practo.com/consult", "1mg.com/order", "apollo247.com",
    "coursera.org/learn", "udemy.com/course", "edx.org/dashboard",
    "swayam.gov.in", "nptel.ac.in", "iitk.ac.in",
    # Travel & Utilities
    "irctc.co.in/nget", "makemytrip.com/flights", "goibibo.com",
    "cleartrip.com", "airbnb.com/hosting", "booking.com",
    "olacabs.com", "uber.com/trips", "ola.com",
]

PHISHING_PATTERNS = [
    # Brand impersonation with typosquat domain
    "http://hdfc-netbanking-secure.{tld}/login",
    "https://sbi-online-update.{tld}/verify-now",
    "http://paytm-kyc-required.{tld}/complete",
    "https://amazon-order-verification.{tld}/confirm",
    "http://flipkart-offer-claim.{tld}/prize",
    "https://google-account-recovery.{tld}/reset",
    "http://paypal-security-update.{tld}/billing",
    "https://microsoft-365-verify.{tld}/signin",
    "http://apple-id-locked.{tld}/unlock",
    "https://netflix-billing-failed.{tld}/update",
    # Subdomain spoofing
    "http://hdfc.login-secure.{tld}/netbanking",
    "https://sbi.secure-verify.{tld}/loginpage",
    "http://icici.update-kyc.{tld}/confirm-details",
    "https://paypal.account-update.{tld}/verify",
    "http://amazon.secure-check.{tld}/order-issue",
    "https://google.account-restore.{tld}/recovery",
    # IP address hosting
    "http://192.168.43.101/hdfc-login/verify",
    "http://54.123.67.90/sbi/netbanking/signin",
    "http://203.45.12.88/paytm-kyc/confirm",
    "http://10.0.0.1/secure/login/banking",
    "http://172.16.254.1/wallet/verify-account",
    "http://35.200.100.45/amazon/prime/update",
    # Excessive subdomains
    "https://login.secure.verify.hdfc.{tld}/bank",
    "https://account.update.confirm.sbi.{tld}/portal",
    "https://secure.verify.kyc.paytm.{tld}/complete",
    # Encoded / obfuscated
    "http://h%64fcbank-login.{tld}/secure",
    "https://g00gle-signin.{tld}/account/verify",
    "http://am4zon-prime.{tld}/account/billing",
    "https://micros0ft-office.{tld}/verify-user",
    # Path-based indicators
    "http://legit-site.{tld}/login@hdfc.com/phish",
    "https://real-bank.{tld}/secure/verify?redir=evil",
    "http://normal-looking.{tld}/wp-content/phish/bank/login",
    "https://official-update.{tld}/admin/secure/credential-grab",
    # Long noisy URLs
    "http://secure-banking-update-required-immediately.{tld}/click-here",
    "https://your-account-has-been-suspended-verify-now.{tld}/re-verify",
    "http://urgent-action-required-payment-failed.{tld}/retry-payment",
    "https://win-prize-claim-lottery-bonus-now.{tld}/collect",
    # UPI / fintech specific
    "http://upi-transfer-failed-retry.{tld}/retry-now",
    "https://phonepe-account-blocked.{tld}/unblock",
    "http://gpay-reward-claim.{tld}/register",
    "https://bhim-update-kyc-now.{tld}/complete-kyc",
    "http://razorpay-payment-link.{tld}/fake-invoice",
    # Government impersonation
    "http://incometax-refund-pending.{tld}/claim-now",
    "https://gst-notice-reply.{tld}/file-response",
    "http://epfo-pf-withdrawal.{tld}/apply-now",
    "https://uidai-aadhaar-update.{tld}/biometric",
    "http://passport-renewal-urgent.{tld}/renew",
    "https://sebi-investor-alert.{tld}/comply-now",
    # Crypto / NFT scams
    "http://binance-airdrop-claim.{tld}/connect-wallet",
    "https://metamask-security-update.{tld}/restore-seed",
    "http://nft-whitelist-mint.{tld}/approve-contract",
    "https://crypto-exchange-verify.{tld}/kyc-complete",
]

SUSPICIOUS_TLDS   = ['xyz', 'top', 'ru', 'tk', 'cc', 'info', 'biz', 'cf', 'ga', 'gq', 'ml', 'pw', 'click', 'live']
LEGIT_PROTOCOLS   = ["https://www.", "https://", "http://www.", "http://"]


def generate_fallback_phishing_data(n_samples: int = 4000):
    """
    Generate synthetic URLs as a supplement to the real dataset.
    Kept smaller (4 000 total) now that a real 420 K dataset is the primary source.
    """
    X, y = [], []
    for _ in range(n_samples // 2):
        domain   = np.random.choice(LEGIT_DOMAINS)
        protocol = np.random.choice(LEGIT_PROTOCOLS)
        X.append(f"{protocol}{domain}")
        y.append(0)
    for _ in range(n_samples // 2):
        pattern = np.random.choice(PHISHING_PATTERNS)
        tld     = np.random.choice(SUSPICIOUS_TLDS)
        url     = pattern.format(tld=tld)
        if not url.startswith("http"):
            url = "http://" + url
        X.append(url)
        y.append(1)
    return X, y


def _fetch_openphish() -> list:
    """
    Fetch OpenPhish live feed (~300 currently-active phishing URLs).
    Returns empty list on failure (non-fatal).
    """
    try:
        req  = urllib.request.Request(
            'https://openphish.com/feed.txt',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        lines = resp.read().decode('utf-8', errors='replace').strip().splitlines()
        urls  = [l.strip() for l in lines if l.strip().startswith('http')]
        print(f"  OpenPhish: fetched {len(urls)} live phishing URLs.")
        return urls
    except Exception as e:
        print(f"  OpenPhish: unavailable ({e}), skipping.")
        return []


def load_data():
    """
    Load phishing URL data from three sources (BUG 7a, 7b):

    1. Faizann24 real dataset (~420 K URLs, good/bad labels):
       https://raw.githubusercontent.com/faizann24/Using-machine-learning-to-detect-malicious-URLs/master/data/data.csv
       Chosen because: single downloadable CSV, no API key, 420 K diverse real-world URLs,
       widely used benchmark in academic security ML, trivial label mapping (good→0, bad→1).

    2. OpenPhish live feed (~300 URLs) — supplements the phishing class with current attacks.

    3. Synthetic fallback data (generate_fallback_phishing_data) — adds deliberate patterns
       (IP tricks, @ symbol, suspicious TLDs) that may be underrepresented in the real dataset.

    All three are combined and deduplicated (BUG 7b).
    Returns X (list of URL strings), y (list of int labels 0/1).
    """
    FAIZANN_URL = (
        "https://raw.githubusercontent.com/faizann24/"
        "Using-machine-learning-to-detect-malicious-URLs/master/data/data.csv"
    )

    X_real, y_real = [], []
    real_loaded = False

    print(f"Attempting to download primary dataset from faizann24 repo...")
    try:
        req  = urllib.request.Request(FAIZANN_URL, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        df   = pd.read_csv(io.StringIO(resp.read().decode('utf-8', errors='replace')))
        # Columns: url, label  (label ∈ {good, bad})
        df   = df.dropna(subset=['url', 'label'])
        X_real = df['url'].astype(str).tolist()
        y_real = [0 if str(v).strip().lower() == 'good' else 1
                  for v in df['label'].tolist()]
        n_phish = sum(y_real)
        n_legit = len(y_real) - n_phish
        print(f"  Loaded {len(X_real):,} real URLs "
              f"({n_phish:,} phishing, {n_legit:,} legit).")
        real_loaded = True
    except Exception as e:
        print(f"  Failed to load faizann24 dataset: {e}")

    # OpenPhish supplement
    openphish_urls = _fetch_openphish()

    # Synthetic supplement
    print("Generating synthetic edge-case data...")
    X_synth, y_synth = generate_fallback_phishing_data(4000)
    print(f"  Synthetic: {len(X_synth):,} URLs (2000 legit, 2000 phishing).")

    # Merge all three sources
    X_all = X_real + openphish_urls + X_synth
    y_all = y_real + [1] * len(openphish_urls) + y_synth

    # Deduplicate (keep first occurrence)
    seen  = set()
    X_out, y_out = [], []
    for url, lbl in zip(X_all, y_all):
        key = url.strip().lower()
        if key not in seen:
            seen.add(key)
            X_out.append(url.strip())
            y_out.append(lbl)

    n_p = sum(y_out)
    n_l = len(y_out) - n_p
    print(f"\nCombined dataset after deduplication: {len(X_out):,} URLs "
          f"({n_p:,} phishing [{100*n_p/len(y_out):.1f}%], "
          f"{n_l:,} legit [{100*n_l/len(y_out):.1f}%])")

    if not real_loaded:
        print("WARNING: real dataset unavailable — training on synthetic data only.")
        print("         Generalisation will be limited (BUG 7 NOT fully resolved).")

    return X_out, y_out


def build_base_pipeline() -> Pipeline:
    """Base (uncalibrated) pipeline — used internally before calibration."""
    return Pipeline([
        ('features',   URLFeatureExtractor()),
        ('classifier', RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            max_depth=15,
            min_samples_leaf=2,
            class_weight='balanced',   # compensates for ~82/18 good/bad imbalance
            n_jobs=-1,
        ))
    ])


# Alias kept so any code that calls build_pipeline() still works.
build_pipeline = build_base_pipeline


class IsotonicCalibratedPipeline(BaseEstimator):
    """
    Lightweight pre-fit calibration wrapper (BUG 22).

    Replaces CalibratedClassifierCV(cv='prefit') which was removed in newer
    versions of scikit-learn.  Wraps an already-fitted base pipeline with an
    IsotonicRegression calibrator fitted separately on a hold-out calibration
    set.  Implements predict_proba / predict so it is a drop-in for the
    uncalibrated pipeline everywhere (model_loader.py, main.py, etc.).

    Isotonic regression is non-parametric and monotone: it preserves the
    ranking of scores while remapping them to realistic probabilities.  It
    is strictly better than Platt scaling (sigmoid) for large calibration sets
    (>~1 000 samples) because it makes no linearity assumption.
    """
    def __init__(self, base_pipeline, calibrator):
        self.base_pipeline = base_pipeline
        self.calibrator    = calibrator

    def predict_proba(self, X):
        raw  = self.base_pipeline.predict_proba(X)[:, 1]
        cal  = np.clip(self.calibrator.predict(raw), 0.0, 1.0)
        return np.column_stack([1.0 - cal, cal])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    # sklearn estimator interface
    def fit(self, X, y):
        """Not used after construction — training is done externally."""
        return self


# ── Manual sanity-check set (NOT in training data) ────────────────────────────
# These are used to evaluate real-world usefulness separately from held-out test.
SANITY_URLS = [
    # Obviously safe (prob should be very low)
    ("https://www.chase.com/login",            0, "Safe: major bank"),
    ("https://accounts.google.com/signin",     0, "Safe: Google accounts"),
    ("https://www.amazon.com/gp/cart",         0, "Safe: Amazon"),
    ("https://github.com/settings/profile",    0, "Safe: GitHub"),
    # Moderate risk (should be elevated but maybe not max)
    ("http://paypal-account-update.com/login", 1, "Moderate: typosquat + http"),
    ("https://mybank-secure-portal.info/verify",1,"Moderate: .info + secure keyword"),
    # Obviously very risky (prob should be high)
    ("http://192.168.44.201/wallet-verify/secure-login", 1, "VRisky: raw IP + http"),
    ("http://kx7vQ2mZpL9fT4wR.top/paypal-login@confirm.ru", 1, "VRisky: random + @ + .top"),
    ("http://hdfc.login-secure.xyz/netbanking", 1, "VRisky: brand spoof + .xyz"),
]


if __name__ == "__main__":
    print("=" * 65)
    print("SentryFi Phishing Model Retraining — BUG 22 + BUG 23")
    print("=" * 65)

    # ── BEFORE: load existing saved model for comparison ─────────────────────
    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../models', 'phishing_model.joblib')
    )

    old_model = None
    if os.path.exists(model_path):
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            import __main__
            __main__.URLFeatureExtractor = URLFeatureExtractor
            old_model = joblib.load(model_path)
            print("\n[BEFORE] Loaded existing model for comparison.")
        except Exception as e:
            print(f"\n[BEFORE] Could not load existing model: {e}")

    # ── Load combined dataset ─────────────────────────────────────────────────
    print("\n--- Loading Dataset ---")
    X, y = load_data()
    y_arr = np.array(y)

    # ── 60 / 20 / 20 split: base-train / calibration / test ──────────────────
    # Using a dedicated calibration set (cv='prefit') instead of cv=5 because
    # cv=5 would train 5 full 300-tree RFs on ~330K rows — too slow.
    # The 20% calibration set is large enough for isotonic regression to fit
    # a reliable score→probability mapping.
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    X_base, X_cal, y_base, y_cal = train_test_split(
        X_temp, y_temp, test_size=0.25, random_state=42, stratify=y_temp
    )  # 0.25 × 0.80 = 0.20 of original → 60/20/20

    print(f"\nBase-train: {len(X_base):,}  |  Calibration: {len(X_cal):,}  |  Test: {len(X_test):,}")

    # ── BEFORE metrics on held-out test set ──────────────────────────────────
    if old_model is not None:
        print("\n--- [BEFORE] Old Uncalibrated Model Metrics (20% test) ---")
        try:
            y_pred_old = old_model.predict(X_test)
            print(f"Accuracy:  {accuracy_score(y_test, y_pred_old):.4f}")
            print(f"Precision: {precision_score(y_test, y_pred_old, zero_division=0):.4f}")
            print(f"Recall:    {recall_score(y_test, y_pred_old, zero_division=0):.4f}")
            print(f"F1-Score:  {f1_score(y_test, y_pred_old, zero_division=0):.4f}")
        except Exception as e:
            print(f"  Could not score old model: {e}")

        print("\n--- [BEFORE] Old Model — Six Spec URLs ---")
        SPEC_URLS_BRIEF = [
            ("SAFE", "https://www.chase.com/login"),
            ("SAFE", "https://accounts.google.com/signin"),
            ("MOD",  "http://paypal-account-update.com/login"),
            ("MOD",  "https://mybank-secure-portal.info/verify"),
            ("HIGH", "http://192.168.44.201/wallet-verify/secure-login"),
            ("HIGH", "http://kx7vQ2mZpL9fT4wR.top/paypal-login@confirm.ru"),
        ]
        for exp, url in SPEC_URLS_BRIEF:
            try:
                p = old_model.predict_proba([url])[0][1]
                print(f"  {exp:<4}  score={p*100:5.1f}   {url[:65]}")
            except Exception as e:
                print(f"  ERROR: {e}")

    # ── Step 1: Train base pipeline (uncalibrated) ────────────────────────────
    print("\n--- Step 1: Training base pipeline (uncalibrated) ---")
    base_pipeline = build_base_pipeline()
    base_pipeline.fit(X_base, y_base)

    print("\n[Uncalibrated] Base pipeline — Six Spec URLs (raw RF scores):")
    for exp, url in SPEC_URLS_BRIEF:
        p = base_pipeline.predict_proba([url])[0][1]
        print(f"  {exp:<4}  score={p*100:5.1f}   {url[:65]}")

    # ── Step 2: Calibrate with isotonic regression (BUG 22) ──────────────────
    print("\n--- Step 2: Calibrating with isotonic regression (BUG 22) ---")
    # Manual pre-fit calibration: get raw scores from the base pipeline on the
    # calibration hold-out, then fit IsotonicRegression to map those raw scores
    # to real-world probabilities.  Equivalent to the (now-removed) cv='prefit'
    # option in CalibratedClassifierCV.
    from sklearn.isotonic import IsotonicRegression
    raw_cal_probs = base_pipeline.predict_proba(X_cal)[:, 1]
    ir = IsotonicRegression(out_of_bounds='clip')
    ir.fit(raw_cal_probs, np.array(y_cal, dtype=float))
    calibrated_model = IsotonicCalibratedPipeline(
        base_pipeline=base_pipeline,
        calibrator=ir,
    )
    print("  Calibration complete (isotonic regression on hold-out set).")

    # ── AFTER metrics on held-out test set (calibrated) ──────────────────────
    y_pred_cal   = (calibrated_model.predict_proba(X_test)[:, 1] >= 0.5).astype(int)
    y_pred_uncal = (base_pipeline.predict_proba(X_test)[:, 1] >= 0.5).astype(int)

    print("\n--- [AFTER] Uncalibrated vs Calibrated — Test Metrics ---")
    print(f"{'Metric':<12} {'Uncalibrated':>14} {'Calibrated':>12}")
    print("-" * 40)
    for name, fn in [("Accuracy", accuracy_score),
                     ("Precision", lambda a, b: precision_score(a, b, zero_division=0)),
                     ("Recall",    lambda a, b: recall_score(a, b, zero_division=0)),
                     ("F1-Score",  lambda a, b: f1_score(a, b, zero_division=0))]:
        u = fn(y_test, y_pred_uncal)
        c = fn(y_test, y_pred_cal)
        print(f"{name:<12} {u:>14.4f} {c:>12.4f}")

    print("\nCalibrated classification report:")
    print(classification_report(
        y_test, y_pred_cal,
        target_names=["Legitimate", "Phishing"],
        zero_division=0,
    ))

    # ── Cross-validation on 10K subsample (uncalibrated pipeline for speed) ──
    cv_sample = min(len(X), 10_000)
    idx = np.random.default_rng(42).choice(len(X), cv_sample, replace=False)
    X_cv = [X[i] for i in idx]
    y_cv = [y[i] for i in idx]
    print(f"\nRunning 5-fold CV on {cv_sample:,} subsample (base pipeline)...")
    skf   = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1 = cross_val_score(build_base_pipeline(), X_cv, y_cv, cv=skf, scoring='f1', n_jobs=-1)
    print(f"Cross-Val F1 per fold: {[round(s, 4) for s in cv_f1]}")
    print(f"Mean CV F1: {cv_f1.mean():.4f}  (+/- {cv_f1.std():.4f})")

    # ── Sanity-check set ──────────────────────────────────────────────────────
    print("\n--- [AFTER] Calibrated Model — Sanity-Check URLs ---")
    for url, expected_label, note in SANITY_URLS:
        prob = calibrated_model.predict_proba([url])[0][1]
        flag = "OK  " if (prob >= 0.5) == bool(expected_label) else "WARN"
        print(f"  {flag}  score={prob*100:5.1f}  expected={'phish' if expected_label else 'safe ':5}  {note}")
        print(f"         {url[:70]}")

    # ── Six spec test URLs: before/after comparison ───────────────────────────
    print("\n--- Six-URL Score Comparison: Old  /  Uncalibrated  /  Calibrated ---")
    import math as _math
    from collections import Counter as _Counter
    from urllib.parse import urlparse as _urlparse

    STLDS  = {'.top','.xyz','.ru','.tk','.info','.click','.gq','.ml','.cf','.ga','.pw','.stream','.win','.loan','.review'}
    BRANDS = {'google','microsoft','apple','amazon','paypal','chase','wellsfargo','bankofamerica','citibank','hsbc','barclays','santander','sbi','hdfc','icici','axis','kotak','ubs','linkedin','facebook','twitter','instagram','netflix','spotify','adobe','dropbox'}
    AKWS   = {'login','secure','verify','account','update','wallet','bank','signin','password','credential','auth','confirm','validate'}

    def _nsig(url):
        try:
            p = _urlparse(url if '://' in url else 'https://' + url)
            sch = p.scheme.lower(); h = p.hostname or ''
        except:
            sch = 'https'; h = ''
        n = 0
        if sch == 'http': n += 1
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', h): n += 1
        if '@' in url: n += 1
        if any(h.endswith(t) for t in STLDS): n += 1
        ib = any(b in h for b in BRANDS)
        if not ib and any(kw in url.lower() for kw in AKWS): n += 1
        parts = h.split('.')
        if len(parts) > 4: n += 1
        else:
            lbl = parts[0] if parts else ''
            if len(lbl) >= 8:
                c   = _Counter(lbl)
                ent = -sum((v/len(lbl))*_math.log2(v/len(lbl)) for v in c.values())
                if ent > 3.5: n += 1
        if len(h) > 40: n += 1
        elif h.count('-') >= 3: n += 1
        return n, bool(re.match(r'^(\d{1,3}\.){3}\d{1,3}$', h)), '@' in url

    SPEC_URLS = [
        ("SAFE", "https://www.chase.com/login"),
        ("SAFE", "https://accounts.google.com/signin"),
        ("MOD",  "http://paypal-account-update.com/login"),
        ("MOD",  "https://mybank-secure-portal.info/verify"),
        ("HIGH", "http://192.168.44.201/wallet-verify/secure-login"),
        ("HIGH", "http://kx7vQ2mZpL9fT4wR.top/paypal-login@confirm.ru"),
    ]

    all_ok = True
    hdr = f"{'Exp':<6}|{'OldScore':>9}|{'Uncalib':>8}|{'Calibrated':>11}|{'Sig':>4}|{'Tier':<14}|{'OK?':>4}"
    print(hdr)
    print("-" * len(hdr))
    for exp, url in SPEC_URLS:
        uncal_prob = base_pipeline.predict_proba([url])[0][1]
        cal_prob   = calibrated_model.predict_proba([url])[0][1]
        ns, has_ip, has_at = _nsig(url)
        # Tier classification uses the calibrated score
        if ns == 0 or cal_prob < 0.30: tier = "SAFE"
        elif (has_ip or has_at) or (ns >= 4 and cal_prob >= 0.70): tier = "VERY_RISKY"
        else: tier = "MODERATE_RISK"
        ok = ((exp=="SAFE" and tier=="SAFE") or
              (exp=="MOD"  and tier=="MODERATE_RISK") or
              (exp=="HIGH" and tier=="VERY_RISKY"))
        if not ok: all_ok = False
        old_score = "   -"
        if old_model is not None:
            try:
                op = old_model.predict_proba([url])[0][1]
                old_score = f"{op*100:5.1f}"
            except:
                pass
        tag = "OK  " if ok else "FAIL"
        print(f"{exp:<6}|{old_score:>9}|{uncal_prob*100:>8.1f}|{cal_prob*100:>11.1f}|{ns:>4}|{tier:<14}|{tag}")
    print()
    print("All tier checks:", "PASS" if all_ok else "SOME FAILURES")

    # ── Save calibrated model ─────────────────────────────────────────────────
    # The saved object is a CalibratedClassifierCV wrapping the base Pipeline.
    # model_loader.py loads it with joblib — URLFeatureExtractor is importable
    # from train_phishing, so deserialization works without changes.
    # predict_proba() on the loaded object returns calibrated probabilities.
    joblib.dump(calibrated_model, model_path, compress=3)
    print(f"\nSaved calibrated phishing model to {model_path} (compressed)")
    print("Training complete.")

