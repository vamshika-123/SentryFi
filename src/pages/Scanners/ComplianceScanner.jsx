import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import apiClient from '../../services/apiClient';
import { FileText, Loader2, UploadCloud, CheckCircle, ShieldAlert, FileSearch } from 'lucide-react';
import clsx from 'clsx';
import { COMPLIANCE_CATEGORY_LABELS } from '../../utils/verdictLabels';

export default function ComplianceScanner() {
  const { currentUser } = useAuth();
  const fileInputRef = useRef(null);
  
  const [textMode, setTextMode] = useState(true);
  const [textInput, setTextInput] = useState('');
  const [file, setFile] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleScan = async (e) => {
    e?.preventDefault();
    if (textMode && !textInput.trim()) return;
    if (!textMode && !file) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      let downloadURL = null;
      let filePath = null;
      
      const config = { headers: {} };
      let payload;

      if (textMode) {
        setStatusMsg('Analyzing compliance clauses...');
        payload = { text: textInput };
        config.headers['Content-Type'] = 'application/json';
      } else {
        setStatusMsg('Running NLP extraction...');
        payload = new FormData();
        payload.append('file', file);
        config.headers['Content-Type'] = 'multipart/form-data';
      }
      
      const response = await apiClient.post('/v1/scan/compliance', payload, config);
      const data = response.data;
      setResult(data);

      setStatusMsg('Saving audit trail...');
      await createScanRecord({
        userId: currentUser.uid,
        userEmail: currentUser.email,
        type: 'compliance',
        targetName: textMode ? 'Text Snippet' : file.name,
        fileUrl: downloadURL,
        filePath: filePath,
        riskScore: data.documentRiskScore,
        verdict: data.verdict,
        confidence: data.documentRiskScore,
        flaggedReasons: data.flaggedClauses?.map(c => `${c.riskTag}: ${c.clause.substring(0,50)}...`) || []
      });

    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
      setStatusMsg('');
    }
  };

  const isClean = result?.verdict === 'CLEAN';

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">Compliance Audit Scanner</h2>
        <p className="text-text-secondary text-sm">Analyze audit reports or legal clauses for regulatory violations (SOX, AML, Tax evasion).</p>
      </div>

      <div className="glass-panel p-6">
        {/* Mode Toggle */}
        <div className="flex gap-2 mb-6 border-b border-border pb-4">
          <button 
            className={clsx(
              "px-4 py-2 text-sm font-semibold rounded-md transition-colors",
              textMode ? "bg-primary text-white" : "text-text-secondary hover:bg-surface-alt"
            )}
            onClick={() => setTextMode(true)}
          >
            Paste Text
          </button>
          <button 
            className={clsx(
              "px-4 py-2 text-sm font-semibold rounded-md transition-colors",
              !textMode ? "bg-primary text-white" : "text-text-secondary hover:bg-surface-alt"
            )}
            onClick={() => setTextMode(false)}
          >
            Upload Document
          </button>
        </div>

        {textMode ? (
          <form onSubmit={handleScan} className="space-y-4">
            <textarea
              className="input-field w-full h-48 font-mono text-sm resize-y"
              placeholder="Paste audit clause, legal text, or transaction notes here..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              required
            ></textarea>
            <button type="submit" disabled={loading || !textInput} className="btn-primary w-full py-3 flex justify-center items-center gap-2">
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {statusMsg}</> : 'Run Text Analysis'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            {!file ? (
              <div 
                className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:bg-surface-alt hover:border-primary transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadCloud className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                <p className="text-base font-medium text-text-primary">Upload Audit PDF</p>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={(e) => { if(e.target.files[0]) setFile(e.target.files[0]); setResult(null); setError(''); }} 
                  accept=".pdf" 
                  className="hidden" 
                />
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-4 bg-surface-alt p-4 rounded-lg w-full mb-4 border border-border">
                  <FileSearch className="w-8 h-8 text-primary" />
                  <p className="flex-1 text-text-primary font-medium truncate">{file.name}</p>
                  <button onClick={() => setFile(null)} disabled={loading} className="text-text-secondary hover:text-danger p-2 transition-colors">✕</button>
                </div>
                <button onClick={handleScan} disabled={loading} className="btn-primary w-full py-3 flex justify-center items-center gap-2">
                  {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {statusMsg}</> : 'Run Document Analysis'}
                </button>
              </div>
            )}
          </div>
        )}
        
        {error && <p className="text-danger mt-4 text-center text-sm">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up",
          isClean ? 'border-l-4 border-l-success' : 'border-l-4 border-l-danger'
        )}>
          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div className={clsx(
              "p-3 rounded-xl",
              isClean ? 'bg-green-50 text-success' : 'bg-red-50 text-danger'
            )}>
              {isClean ? <CheckCircle className="w-8 h-8" /> : <ShieldAlert className="w-8 h-8" />}
            </div>
            <div>
              <h3 className="text-xl font-bold text-text-primary">{isClean ? 'Document Compliant' : 'Regulatory Issues Found'}</h3>
              <p className="text-text-secondary text-sm">Overall Risk Score: {result.documentRiskScore.toFixed(1)}</p>
            </div>
          </div>

          {result.flaggedClauses?.length > 0 ? (
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider border-b border-border pb-2">Flagged Clauses</h4>
              {result.flaggedClauses.map((item, idx) => (
                <div key={idx} className="bg-surface-alt rounded-lg p-4 border border-border flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <span className="px-3 py-1 bg-red-50 text-danger text-xs font-bold rounded-full border border-red-200">
                      {COMPLIANCE_CATEGORY_LABELS[item.riskTag]?.label || item.riskTag.replace(/_/g, ' ')}
                    </span>
                    <span className="text-text-secondary text-xs font-mono">Confidence: {item.confidence.toFixed(1)}%</span>
                  </div>
                  {COMPLIANCE_CATEGORY_LABELS[item.riskTag]?.description && (
                    <p className="text-sm text-text-secondary">{COMPLIANCE_CATEGORY_LABELS[item.riskTag].description}</p>
                  )}
                  <p className="text-text-primary font-mono text-sm leading-relaxed border-l-2 border-danger pl-3">
                    &ldquo;{item.clause}&rdquo;
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 p-6 rounded-xl text-center">
              <p className="text-success font-medium text-sm">No suspicious regulatory clauses detected in the analyzed text.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
