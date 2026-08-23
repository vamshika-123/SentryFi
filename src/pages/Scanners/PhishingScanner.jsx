import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import apiClient from '../../services/apiClient';
import { ShieldCheck, ShieldAlert, AlertTriangle, Link as LinkIcon, Loader2 } from 'lucide-react';
import clsx from 'clsx';

export default function PhishingScanner() {
  const { currentUser } = useAuth();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

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
      return u.hostname.includes('.'); // must have at least one dot in the host
    } catch {
      return false;
    }
  };

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
      
      // Save to history
      await createScanRecord({
        userId: currentUser.uid,
        userEmail: currentUser.email,
        type: 'phishing',
        targetName: normalized,
        riskScore: data.riskScore,
        verdict: data.verdict,
        confidence: data.confidence,
        flaggedReasons: data.flaggedReasons || []
      });
    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
    }
  };

  const isClean = result?.verdict === 'CLEAN';

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">Phishing URL Scanner</h2>
        <p className="text-text-secondary text-sm">Analyze links for structural anomalies, suspicious TLDs, and malicious intent.</p>
      </div>

      <div className="glass-panel p-6">
        <form onSubmit={handleScan} className="flex gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <LinkIcon className="h-4 w-4 text-slate-400" />
            </div>
            <input
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
            type="submit" 
            disabled={loading || !url}
            className="btn-primary flex items-center gap-2 px-6 py-3 text-sm"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Scan URL'}
          </button>
        </form>
        {error && <p className="text-danger mt-3 text-sm">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up",
          isClean ? 'border-l-4 border-l-success' : 'border-l-4 border-l-danger'
        )}>
          <div className="flex items-start gap-6">
            <div className={clsx(
              "p-4 rounded-xl flex-shrink-0",
              isClean ? 'bg-green-50 text-success' : 'bg-red-50 text-danger'
            )}>
              {isClean ? <ShieldCheck className="w-10 h-10" /> : <ShieldAlert className="w-10 h-10" />}
            </div>
            
            <div className="flex-1">
              <div className="flex items-center gap-4 mb-2">
                <h3 className="text-xl font-bold text-text-primary">{isClean ? 'Safe to Proceed' : 'Risk Detected'}</h3>
                <span className={clsx(
                  "px-3 py-1 rounded-full text-xs font-bold border",
                  isClean ? 'bg-green-50 border-green-200 text-success' : 'bg-red-50 border-red-200 text-danger'
                )}>
                  Risk Score: {result.riskScore.toFixed(1)} / 100
                </span>
              </div>
              
              <p className="text-text-secondary break-all mb-6 bg-surface-alt p-3 rounded-lg border border-border font-mono text-xs">
                {result.url}
              </p>

              {result.flaggedReasons?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Threat Analysis Breakdown</h4>
                  <ul className="space-y-2">
                    {result.flaggedReasons.map((reason, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-text-primary bg-amber-50 p-2.5 rounded-md border border-amber-100 text-sm">
                        <AlertTriangle className="w-4 h-4 text-warning mt-0.5 flex-shrink-0" />
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
