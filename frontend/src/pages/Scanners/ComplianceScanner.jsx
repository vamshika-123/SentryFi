import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { uploadScanDocument } from '../../services/storageService';
import { createScanRecord } from '../../services/firestoreService';
import axios from 'axios';
import { FileText, Loader2, UploadCloud, CheckCircle, ShieldAlert, FileSearch } from 'lucide-react';
import clsx from 'clsx';

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
        setStatusMsg('Uploading document securely...');
        const uploadRes = await uploadScanDocument(file, currentUser.uid, 'compliance');
        downloadURL = uploadRes.downloadURL;
        filePath = uploadRes.filePath;
        
        setStatusMsg('Running NLP extraction...');
        payload = new FormData();
        payload.append('file', file);
        config.headers['Content-Type'] = 'multipart/form-data';
      }
      
      const response = await axios.post('/api/v1/scan/compliance', payload, config);
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
      setError(err.response?.data?.detail || err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
      setStatusMsg('');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold mb-2">Compliance Audit Scanner</h2>
        <p className="text-slate-400">Analyze audit reports or legal clauses for regulatory violations (SOX, AML, Tax evasion).</p>
      </div>

      <div className="glass-panel p-6">
        <div className="flex gap-4 mb-6 border-b border-slate-700 pb-4">
          <button 
            className={clsx("px-4 py-2 font-semibold rounded-md transition-colors", textMode ? "bg-primary text-white" : "text-slate-400 hover:bg-slate-800")}
            onClick={() => setTextMode(true)}
          >
            Paste Text
          </button>
          <button 
            className={clsx("px-4 py-2 font-semibold rounded-md transition-colors", !textMode ? "bg-primary text-white" : "text-slate-400 hover:bg-slate-800")}
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
              {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> {statusMsg}</> : 'Run Text Analysis'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            {!file ? (
              <div 
                className="border-2 border-dashed border-slate-600 rounded-xl p-12 text-center hover:bg-slate-800/50 hover:border-primary transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadCloud className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-200">Upload Audit PDF</p>
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
                <div className="flex items-center gap-4 bg-slate-800 p-4 rounded-lg w-full mb-4 border border-slate-700">
                  <FileSearch className="w-8 h-8 text-primary" />
                  <p className="flex-1 text-slate-200 font-medium truncate">{file.name}</p>
                  <button onClick={() => setFile(null)} disabled={loading} className="text-slate-400 hover:text-danger p-2">✕</button>
                </div>
                <button onClick={handleScan} disabled={loading} className="btn-primary w-full py-3 flex justify-center items-center gap-2">
                  {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> {statusMsg}</> : 'Run Document Analysis'}
                </button>
              </div>
            )}
          </div>
        )}
        
        {error && <p className="text-danger mt-4 text-center">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up relative overflow-hidden",
          result.verdict === 'CLEAN' ? 'border-success/50' : 'border-danger/50'
        )}>
          <div className="flex items-center gap-4 mb-6">
            <div className={clsx(
              "p-3 rounded-xl",
              result.verdict === 'CLEAN' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
            )}>
              {result.verdict === 'CLEAN' ? <CheckCircle className="w-8 h-8" /> : <ShieldAlert className="w-8 h-8" />}
            </div>
            <div>
              <h3 className="text-2xl font-bold">{result.verdict === 'CLEAN' ? 'Document Compliant' : 'Regulatory Violations Found'}</h3>
              <p className="text-slate-400">Overall Risk Score: {result.documentRiskScore.toFixed(1)}</p>
            </div>
          </div>

          {result.flaggedClauses?.length > 0 ? (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700 pb-2">Flagged Clauses</h4>
              {result.flaggedClauses.map((item, idx) => (
                <div key={idx} className="bg-slate-900 rounded-lg p-4 border border-slate-700 flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <span className="px-3 py-1 bg-danger/20 text-danger text-xs font-bold rounded-full border border-danger/30">
                      {item.riskTag.replace(/_/g, ' ')}
                    </span>
                    <span className="text-slate-500 text-xs font-mono">Conf: {item.confidence.toFixed(1)}%</span>
                  </div>
                  <p className="text-slate-300 font-mono text-sm leading-relaxed border-l-2 border-danger pl-3">
                    "{item.clause}"
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-success/5 border border-success/20 p-6 rounded-xl text-center">
              <p className="text-success font-medium">No suspicious regulatory clauses detected in the analyzed text.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
