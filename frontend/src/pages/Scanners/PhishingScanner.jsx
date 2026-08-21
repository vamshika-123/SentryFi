import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import axios from 'axios';
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

  const handleScan = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Proxy handles /api via Vite
      const response = await axios.post('/api/v1/scan/phishing', { url });
      const data = response.data;
      setResult(data);
      
      // Save to history
      await createScanRecord({
        userId: currentUser.uid,
        userEmail: currentUser.email,
        type: 'phishing',
        targetName: url,
        riskScore: data.riskScore,
        verdict: data.verdict,
        confidence: data.confidence,
        flaggedReasons: data.flaggedReasons || []
      });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold mb-2">Phishing URL Scanner</h2>
        <p className="text-slate-400">Analyze links for structural anomalies, suspicious TLDs, and malicious intent.</p>
      </div>

      <div className="glass-panel p-6">
        <form onSubmit={handleScan} className="flex gap-4">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <LinkIcon className="h-5 w-5 text-slate-500" />
            </div>
            <input
              type="url"
              required
              placeholder="https://example.com/login..."
              className="input-field w-full pl-10 pr-20 py-3 text-lg"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button
              type="button"
              onClick={handlePaste}
              className="absolute inset-y-2 right-2 px-3 text-xs font-semibold bg-slate-700 hover:bg-slate-600 rounded-md transition-colors"
            >
              PASTE
            </button>
          </div>
          <button 
            type="submit" 
            disabled={loading || !url}
            className="btn-primary flex items-center gap-2 px-8 py-3 text-lg"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Scan URL'}
          </button>
        </form>
        {error && <p className="text-danger mt-4 text-sm">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up relative overflow-hidden",
          result.verdict === 'CLEAN' ? 'border-success/50' : 'border-danger/50'
        )}>
          {/* Background Glow */}
          <div className={clsx(
            "absolute -top-24 -right-24 w-64 h-64 rounded-full blur-[80px] pointer-events-none opacity-20",
            result.verdict === 'CLEAN' ? 'bg-success' : 'bg-danger'
          )}></div>

          <div className="flex items-start gap-6 relative z-10">
            <div className={clsx(
              "p-4 rounded-2xl flex-shrink-0",
              result.verdict === 'CLEAN' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
            )}>
              {result.verdict === 'CLEAN' ? <ShieldCheck className="w-12 h-12" /> : <ShieldAlert className="w-12 h-12" />}
            </div>
            
            <div className="flex-1">
              <div className="flex items-center gap-4 mb-2">
                <h3 className="text-2xl font-bold">{result.verdict === 'CLEAN' ? 'Safe to Proceed' : 'High Risk Detected'}</h3>
                <span className={clsx(
                  "px-3 py-1 rounded-full text-sm font-bold border",
                  result.verdict === 'CLEAN' ? 'bg-success/10 border-success/30 text-success' : 'bg-danger/10 border-danger/30 text-danger'
                )}>
                  Risk Score: {result.riskScore.toFixed(1)} / 100
                </span>
              </div>
              
              <p className="text-slate-300 break-all mb-6 bg-slate-800/50 p-3 rounded-lg border border-slate-700 font-mono text-sm">
                {result.url}
              </p>

              {result.flaggedReasons?.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Threat Analysis Breakdown</h4>
                  <ul className="space-y-2">
                    {result.flaggedReasons.map((reason, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-slate-300 bg-slate-800/30 p-2 rounded-md border border-slate-700/50">
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
