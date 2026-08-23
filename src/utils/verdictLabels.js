export const VERDICT_LABELS = {
  CLEAN:      "Clear",
  HIGH_RISK:  "High Risk",
  FRAUD:      "Fraud Detected",
  FLAGGED:    "Flagged for Review",
  SUSPICIOUS: "Needs Review",
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
  if (verdict === 'CLEAN') {
    return 'text-success bg-green-50 border-green-200';
  }
  if (['HIGH_RISK', 'FRAUD', 'FLAGGED'].includes(verdict)) {
    return 'text-danger bg-red-50 border-red-200';
  }
  // SUSPICIOUS, unknown
  return 'text-warning bg-amber-50 border-amber-200';
};
