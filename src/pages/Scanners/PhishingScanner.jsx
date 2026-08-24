import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import apiClient from '../../services/apiClient';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  AlertTriangle,
  CheckCircle2,
  Info,
  Link as LinkIcon,
  Loader2,
} from 'lucide-react';
import clsx from 'clsx';
import {
  PHISHING_TIER_LABELS,
  getPhishingTierConfig,
} from '../../utils/verdictLabels';

// --------------------------------------------------------------------------
// Per-tier icon component
// --------------------------------------------------------------------------
function TierIcon({ tier, className }) {
  if (tier === 'SAFE')          return <ShieldCheck    className={className} />;
  if (tier === 'MODERATE_RISK') return <ShieldQuestion className={className} />;
  return                               <ShieldAlert    className={className} />;
}

// Per-reason row icon
function ReasonIcon({ tier, className }) {
  if (tier === 'SAFE')          return <CheckCircle2 className={className} />;
  if (tier === 'MODERATE_RISK') return <Info         className={className} />;
  return                               <AlertTriangle className={className} />;
}

// --------------------------------------------------------------------------
// Risk score gauge — simple arc-style progress ring
// --------------------------------------------------------------------------
function RiskGauge({ score, tier }) {
  const pct   = Math.min(100, Math.max(0, score));
  const color =
    tier === 'SAFE'          ? '#22c55e' :
    tier === 'MODERATE_RISK' ? '#f59e0b' :
                               '#ef4444';
  // SVG circle arc: circumference of r=15.9 ≈ 99.9 → we use 100 for simplicity
  const dash = (pct / 100) * 100;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="3"
            strokeDasharray={`${dash} 100`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.6s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color }}>{Math.round(pct)}</span>
        </div>
      </div>
      <span className="text-xs text-text-secondary">Risk Score</span>
    </div>
  );
}

// --------------------------------------------------------------------------
// Main component
// --------------------------------------------------------------------------
export default function PhishingScanner() {
  const { currentUser } = useAuth();
  const [url,     setUrl]     = useState('');
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState('');

  // ---- helpers ----
  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch (err) {
      console.error('Failed to read clipboard contents: ', err);
    }
  };

  const normalizeUrl = (raw) => {
    const trimmed = raw.trim();
    if (!trimmed) return '';
    if (/^https?:\/\//i.test(trimmed)) return trimmed;
    return 'https://' + trimmed;
  };

  const isValidUrl = (str) => {
    try {
      const u = new URL(str);
      return u.hostname.includes('.');
    } catch {
      return false;
    }
  };

  // ---- scan ----
  const handleScan = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    const normalized = normalizeUrl(url);
    if (!isValidUrl(normalized)) {
      setError('Please enter a valid URL, e.g. "example.com" or "https://example.com/path".');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await apiClient.post('/v1/scan/phishing', { url: normalized });
      const data = response.data;
      setResult(data);

      await createScanRecord({
        userId:         currentUser.uid,
        userEmail:      currentUser.email,
        type:           'phishing',
        targetName:     normalized,
        riskScore:      data.riskScore,
        verdict:        data.riskTier ?? data.verdict,
        confidence:     data.confidence,
        flaggedReasons: data.flaggedReasons || [],
      });
    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
    }
  };

  // ---- derived display values ----
  const tier      = result?.riskTier ?? (result?.verdict === 'CLEAN' ? 'SAFE' : 'VERY_RISKY');
  const tierCfg   = getPhishingTierConfig(tier);
  const tierLabel = PHISHING_TIER_LABELS[tier] ?? tier;

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">

      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">Phishing URL Scanner</h2>
        <p className="text-text-secondary text-sm">
          Analyze any link for suspicious patterns — get a plain-English explanation of what we found.
        </p>
      </div>

      {/* Input card */}
      <div className="glass-panel p-6">
        <form onSubmit={handleScan} className="flex gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <LinkIcon className="h-4 w-4 text-slate-400" />
            </div>
            <input
              id="phishing-url-input"
              type="text"
              inputMode="url"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck="false"
              placeholder="example.com or https://example.com/path"
              className="input-field w-full pl-10 pr-20 py-3 text-sm"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setError(''); }}
            />
            <button
              type="button"
              onClick={handlePaste}
              className="absolute inset-y-2 right-2 px-3 text-xs font-semibold bg-surface-alt hover:bg-border text-text-secondary rounded-md transition-colors border border-border"
            >
              PASTE
            </button>
          </div>
          <button
            id="phishing-scan-btn"
            type="submit"
            disabled={loading || !url}
            className="btn-primary flex items-center gap-2 px-6 py-3 text-sm"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Scan URL'}
          </button>
        </form>
        {error && <p className="text-danger mt-3 text-sm">{error}</p>}
      </div>

      {/* Result card */}
      {result && (
        <div
          id="phishing-result-panel"
          className={clsx(
            'glass-panel p-0 animate-slide-up overflow-hidden border-l-4',
            tierCfg.borderColor,
          )}
        >
          {/* Top strip — tier badge + gauge */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-border">
            <div className="flex items-center gap-4">
              <div className={clsx('p-3 rounded-xl flex-shrink-0', tierCfg.iconCls)}>
                <TierIcon tier={tier} className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-text-primary">
                  {tierCfg.headlineText}
                </h3>
                <span
                  id="phishing-tier-badge"
                  className={clsx(
                    'inline-block mt-1 px-3 py-0.5 rounded-full text-xs font-bold border',
                    tierCfg.badgeCls,
                  )}
                >
                  {tierLabel}
                </span>
              </div>
            </div>

            <RiskGauge score={result.riskScore} tier={tier} />
          </div>

          {/* Scanned URL */}
          <div className="px-8 pt-5">
            <p className="text-text-secondary break-all bg-surface-alt px-4 py-3 rounded-lg border border-border font-mono text-xs">
              {result.url}
            </p>
          </div>

          {/* Reasons — ALWAYS shown for every tier */}
          <div className="px-8 py-6">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
              {tier === 'SAFE' ? 'Why this link looks safe' : 'What we found'}
            </h4>

            {result.flaggedReasons?.length > 0 ? (
              <ul className="space-y-2">
                {result.flaggedReasons.map((reason, idx) => (
                  <li
                    key={idx}
                    className={clsx(
                      'flex items-start gap-3 px-4 py-3 rounded-lg border text-sm text-text-primary',
                      tierCfg.reasonRowCls,
                    )}
                  >
                    <ReasonIcon
                      tier={tier}
                      className={clsx('w-4 h-4 mt-0.5 flex-shrink-0', tierCfg.reasonIconCls)}
                    />
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-text-secondary text-sm italic">
                No additional detail available.
              </p>
            )}
          </div>

          {/* Footer metadata */}
          <div className="px-8 pb-5 flex items-center justify-between text-xs text-text-secondary border-t border-border pt-4">
            <span>Model confidence: <strong>{(result.confidence * 100).toFixed(1)}%</strong></span>
            <span>Scanned at {new Date(result.scannedAt).toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

