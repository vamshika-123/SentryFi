import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import apiClient from '../../services/apiClient';
import {
  UploadCloud, FileText, CheckCircle, AlertTriangle,
  Loader2, FileWarning, Info, ChevronDown
} from 'lucide-react';
import clsx from 'clsx';

// ── Currency helpers ──────────────────────────────────────────────────────────
const CURRENCY_SYMBOLS = { INR: '₹', USD: '$', EUR: '€', GBP: '£', AUD: 'A$', CAD: 'C$', SGD: 'S$', CHF: 'CHF ', AED: 'AED ' };

// The three supported currencies for manual selection
const COMMON_CURRENCIES = [
  { code: 'INR', label: 'INR — Indian Rupee (₹)' },
  { code: 'USD', label: 'USD — US Dollar ($)' },
  { code: 'EUR', label: 'EUR — Euro (€)' },
];

/**
 * Returns a formatted amount string with the correct currency prefix.
 * - Known ISO code   → symbol prefix, e.g. "€2,553.91"
 * - Unknown ISO code → "CODE 2,553.91", e.g. "JPY 2553.91"
 * - null / undefined → raw number with note, e.g. "2553.91 (currency not detected)"
 */
function formatAmount(amount, currency) {
  const num = (amount ?? 0).toFixed(2);
  if (!currency) return `${num} (currency not detected)`;
  const sym = CURRENCY_SYMBOLS[currency];
  return sym ? `${sym}${num}` : `${currency} ${num}`;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function InvoiceScanner() {
  const { currentUser } = useAuth();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // Currency picker state (BUG 12b/12c)
  const [pickerSelection, setPickerSelection] = useState('');   // selected ISO code
  const [applyingCurrency, setApplyingCurrency] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError('');
      setPickerSelection('');
    }
  };

  // ── Main scan (initial upload) ────────────────────────────────────────────
  const handleScan = async (currencyOverride = null) => {
    if (!file) return;

    if (currencyOverride) {
      setApplyingCurrency(true);
    } else {
      setLoading(true);
      setError('');
      setResult(null);
      setUploadProgress(0);
    }

    try {
      setStatusMsg(currencyOverride ? 'Applying currency...' : 'Extracting OCR & detecting anomalies...');

      const formData = new FormData();
      formData.append('file', file);
      if (currencyOverride) {
        formData.append('currency_override', currencyOverride);
      }

      const response = await apiClient.post('/v1/scan/invoice', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (!currencyOverride) {
            const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(pct);
          }
        }
      });

      const data = response.data;
      setResult(data);
      setPickerSelection('');   // close picker (currencyUndetected becomes false once currency is set)

      // Persist to Firestore (only on the initial scan, not currency-override re-runs)
      if (!currencyOverride) {
        setStatusMsg('Saving audit trail...');
        await createScanRecord({
          userId: currentUser.uid,
          userEmail: currentUser.email,
          type: 'invoice',
          targetName: file.name,
          fileUrl: null,
          filePath: null,
          riskScore: data.riskScore,
          verdict: data.verdict,
          confidence: 100,
          flaggedReasons: data.flaggedExplanations || [],
          // Persist whichever currency ended up being used (BUG 12b, point d)
          detectedCurrency: data.extractedFields?.currency ?? null,
        });
      }

    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
      setApplyingCurrency(false);
      setStatusMsg('');
    }
  };

  // ── Currency picker submission ───────────────────────────────────────────────
  const handleCurrencyApply = () => {
    if (!pickerSelection) return;
    handleScan(pickerSelection);
  };

  const isClean = result?.verdict === 'CLEAN';
  const ef = result?.extractedFields;
  const currency = ef?.currency ?? null;           // null  = not detected
  const currencyUndetected = currency === null && result !== null && !result.extractedFields?.extraction_failed;

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">Invoice Fraud Scanner</h2>
        <p className="text-text-secondary text-sm">
          Upload vendor invoices or receipts to detect line-item discrepancies and tax anomalies.
        </p>
      </div>

      {/* Upload panel */}
      <div className="glass-panel p-8">
        {!file ? (
          <div
            className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:bg-surface-alt hover:border-primary transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <UploadCloud className="w-14 h-14 text-slate-400 mx-auto mb-4" />
            <p className="text-base font-medium text-text-primary mb-1">Click or drag document to upload</p>
            <p className="text-sm text-text-secondary">Supports PDF, PNG, JPG (Max 10MB)</p>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,image/png,image/jpeg"
              className="hidden"
            />
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="flex items-center gap-4 bg-surface-alt p-4 rounded-lg border border-border w-full mb-6">
              <FileText className="w-10 h-10 text-primary" />
              <div className="flex-1 truncate">
                <p className="font-medium text-text-primary truncate">{file.name}</p>
                <p className="text-xs text-text-secondary">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
              <button
                onClick={() => { setFile(null); setResult(null); setError(''); setPickerSelection(''); }}
                disabled={loading || applyingCurrency}
                className="text-text-secondary hover:text-danger p-2 transition-colors"
              >
                ✕
              </button>
            </div>

            {loading && (
              <div className="w-full mb-6">
                <div className="flex justify-between text-xs text-text-secondary mb-1">
                  <span>{statusMsg}</span>
                  <span>{Math.round(uploadProgress)}%</span>
                </div>
                <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-primary h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <button
              onClick={() => handleScan()}
              disabled={loading || applyingCurrency}
              className="btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Run Anomaly Detection'}
            </button>
          </div>
        )}

        {error && <p className="text-danger mt-4 text-center text-sm">{error}</p>}
      </div>

      {/* Results panel */}
      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up",
          isClean ? 'border-l-4 border-l-success' : 'border-l-4 border-l-danger'
        )}>
          <div className="grid md:grid-cols-2 gap-8">
            {/* Left: verdict + flags */}
            <div>
              <div className="flex items-center gap-4 mb-5">
                <div className={clsx("p-3 rounded-xl", isClean ? 'bg-green-50 text-success' : 'bg-red-50 text-danger')}>
                  {isClean ? <CheckCircle className="w-8 h-8" /> : <FileWarning className="w-8 h-8" />}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-text-primary">{isClean ? 'Invoice Clear' : 'Anomalies Detected'}</h3>
                  {/* BUG 18: numeric risk score */}
                  <p className="text-text-secondary text-sm">
                    Risk Score: 
                    <span className={clsx(
                      'font-bold',
                      result.riskScore >= 70 ? 'text-danger'
                      : result.riskScore >= 40 ? 'text-warning'
                      : 'text-success'
                    )}>
                      {result.riskScore.toFixed(1)}
                    </span>
                    <span className="text-text-secondary font-normal"> / 100</span>
                  </p>
                </div>
              </div>

              {/* BUG 11: no-tax notice */}
              {ef?.tax_not_stated && (
                <div className="mb-4 flex items-start gap-2 bg-amber-50 border border-amber-200 p-3 rounded-lg text-sm text-amber-800">
                  <Info className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>No tax/GST breakdown found — subtotal computed from line items.</span>
                </div>
              )}

              {/* Flagged explanations */}
              {result.flaggedExplanations?.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Findings</h4>
                  <ul className="space-y-2">
                    {result.flaggedExplanations.map((reason, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-danger bg-red-50 p-3 rounded-md border border-red-100">
                        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                        <span className="text-sm font-medium">{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ── BUG 12b: Currency picker ─────────────────────────────── */}
              {currencyUndetected && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                  <div className="flex items-start gap-2 mb-3">
                    <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                    <p className="text-sm text-text-primary font-medium">
                      Currency not detected on this invoice — select one to apply correct formatting:
                    </p>
                  </div>

                  <div className="flex flex-col gap-2">
                    {/* Dropdown */}
                    <div className="relative">
                      <select
                        className="input-field w-full pr-8 text-sm appearance-none"
                        value={pickerSelection}
                        onChange={(e) => setPickerSelection(e.target.value)}
                      >
                        <option value="" disabled>Select currency…</option>
                        {COMMON_CURRENCIES.map(c => (
                          <option key={c.code} value={c.code}>{c.label}</option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>

                    <button
                      onClick={handleCurrencyApply}
                      disabled={applyingCurrency || !pickerSelection}
                      className="btn-primary py-2 text-sm flex items-center justify-center gap-2"
                    >
                      {applyingCurrency
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Applying…</>
                        : 'Apply Currency'}
                    </button>
                  </div>
                </div>
              )}

              {/* Show which currency was applied (manual selection badge) */}
              {ef?.currency_user_selected && currency && (
                <div className="mt-3 flex items-center gap-2 text-xs text-text-secondary">
                  <span className="inline-block px-2 py-0.5 bg-surface-alt border border-border rounded font-mono text-primary">{currency}</span>
                  <span>applied manually — amounts shown in {CURRENCY_SYMBOLS[currency] ?? currency}</span>
                </div>
              )}
            </div>

            {/* Right: extracted fields */}
            <div className="bg-surface-alt rounded-xl p-6 border border-border">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4 border-b border-border pb-2 flex items-center gap-2">
                Extracted Invoice Fields
                {currency && !currencyUndetected && (
                  <span className="ml-auto normal-case font-mono text-primary">[{currency}]</span>
                )}
                {currencyUndetected && (
                  <span className="ml-auto normal-case font-mono text-warning text-xs">[currency not detected]</span>
                )}
              </h4>

              <div className="space-y-3 font-mono text-sm">
                {/* Subtotal */}
                <div className="flex justify-between">
                  <span className="text-text-secondary">Subtotal:</span>
                  <span className="text-text-primary font-medium">{formatAmount(ef?.subtotal, currency)}</span>
                </div>

                {/* Tax — label adapts to GST vs generic (BUG 14) */}
                <div className="flex justify-between">
                  <span className="text-text-secondary">{ef?.is_gst_invoice ? 'GST Amount:' : 'Tax Amount:'}</span>
                  <span className="text-text-primary font-medium">
                    {ef?.tax_not_stated ? '—' : formatAmount(ef?.tax_amount, currency)}
                  </span>
                </div>

                {/* Additional charges (BUG 13) */}
                {ef?.additional_charges !== 0 && ef?.additional_charges_label && (
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Additional Charges:</span>
                    <span className="text-text-primary font-medium text-xs leading-tight text-right max-w-[55%]">
                      {ef.additional_charges_label}
                    </span>
                  </div>
                )}

                {/* Amount mismatch (BUG 13) */}
                <div className="flex justify-between border-t border-border pt-2 mt-2">
                  <span className="text-text-secondary">Amount Mismatch:</span>
                  <span className={clsx("font-bold", (ef?.line_item_delta ?? 0) > 0 ? "text-danger" : "text-success")}>
                    {(ef?.line_item_delta ?? 0) === 0 ? 'None' : formatAmount(ef?.line_item_delta, currency)}
                  </span>
                </div>

                {/* Tax rate row (BUG 14) */}
                <div className="flex justify-between">
                  <span className="text-text-secondary">
                    {ef?.is_gst_invoice ? 'GST Rate Difference:' : 'Effective Tax Rate:'}
                  </span>
                  <span className="text-text-primary font-medium">
                    {ef?.is_gst_invoice
                      ? `${(ef?.tax_percentage_variance ?? 0).toFixed(2)}%`
                      : ef?.tax_not_stated
                        ? '—'
                        : `${(ef?.effective_tax_rate ?? 0).toFixed(2)}%`}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
