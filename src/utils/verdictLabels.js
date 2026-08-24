export const VERDICT_LABELS = {
  CLEAN:          "Clear",
  HIGH_RISK:      "High Risk",
  FRAUD:          "Fraud Detected",
  FLAGGED:        "Flagged for Review",
  SUSPICIOUS:     "Needs Review",
  // Phishing three-tier labels
  SAFE:           "Safe",
  MODERATE_RISK:  "Moderate Risk",
  VERY_RISKY:     "Very Risky",
};

export const COMPLIANCE_CATEGORY_LABELS = {
  AML_PMLA_VIOLATION: {
    label: "Anti-Money Laundering Concern",
    description: "Payment pattern suggests unverified or undisclosed fund routing.",
  },
  SOX_COMPLIANCE_BREACH: {
    label: "Financial Controls Breach",
    description: "Bypasses standard approval or audit-trail controls.",
  },
  GST_EVASION_SUSPICION: {
    label: "Tax Reporting Irregularity",
    description: "Possible attempt to underreport or avoid GST.",
  },
  UNAUTHORIZED_OFFSHORE_ROUTING: {
    label: "Unauthorized Offshore Transfer",
    description: "Funds routed outside approved regulatory channels.",
  },
};

/**
 * Returns Tailwind class string for verdict badge styling.
 * Uses light-palette semantic colors (no dark-mode classes).
 */
export const getVerdictColor = (verdict) => {
  if (verdict === 'CLEAN' || verdict === 'SAFE') {
    return 'text-success bg-green-50 border-green-200';
  }
  if (verdict === 'MODERATE_RISK') {
    return 'text-warning bg-amber-50 border-amber-200';
  }
  if (['HIGH_RISK', 'FRAUD', 'FLAGGED', 'VERY_RISKY'].includes(verdict)) {
    return 'text-danger bg-red-50 border-red-200';
  }
  // SUSPICIOUS, unknown
  return 'text-warning bg-amber-50 border-amber-200';
};

// ---------------------------------------------------------------------------
// Phishing-specific three-tier helpers
// ---------------------------------------------------------------------------

/** Human-readable label for each risk tier. */
export const PHISHING_TIER_LABELS = {
  SAFE:          "Safe",
  MODERATE_RISK: "Moderate Risk",
  VERY_RISKY:    "Very Risky",
};

/**
 * Returns a config object for rendering a phishing risk tier:
 *   { borderColor, badgeCls, iconCls, panelCls, headlineText }
 */
export const getPhishingTierConfig = (riskTier) => {
  switch (riskTier) {
    case 'SAFE':
      return {
        borderColor:  'border-l-success',
        badgeCls:     'bg-green-50 border-green-200 text-success',
        iconCls:      'bg-green-50 text-success',
        reasonIconCls:'text-success',
        reasonRowCls: 'bg-green-50 border-green-100',
        headlineText: 'Safe to Proceed',
      };
    case 'MODERATE_RISK':
      return {
        borderColor:  'border-l-warning',
        badgeCls:     'bg-amber-50 border-amber-200 text-warning',
        iconCls:      'bg-amber-50 text-warning',
        reasonIconCls:'text-warning',
        reasonRowCls: 'bg-amber-50 border-amber-100',
        headlineText: 'Proceed with Caution',
      };
    case 'VERY_RISKY':
    default:
      return {
        borderColor:  'border-l-danger',
        badgeCls:     'bg-red-50 border-red-200 text-danger',
        iconCls:      'bg-red-50 text-danger',
        reasonIconCls:'text-danger',
        reasonRowCls: 'bg-red-50 border-red-100',
        headlineText: 'High Risk Detected',
      };
  }
};
