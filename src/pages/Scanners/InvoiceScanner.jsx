import React, { useState, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createScanRecord } from '../../services/firestoreService';
import apiClient from '../../services/apiClient';
import { UploadCloud, FileText, CheckCircle, AlertTriangle, Loader2, FileWarning } from 'lucide-react';
import clsx from 'clsx';

export default function InvoiceScanner() {
  const { currentUser } = useAuth();
  const fileInputRef = useRef(null);
  
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError('');
    }
  };

  const handleScan = async () => {
    if (!file) return;

    setLoading(true);
    setError('');
    setResult(null);
    setUploadProgress(0);

    try {
      setStatusMsg('Extracting OCR & detecting anomalies...');
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiClient.post('/v1/scan/invoice', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });
      
      const data = response.data;
      setResult(data);

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
        confidence: 100, // IF doesn't return confidence easily
        flaggedReasons: data.flaggedExplanations || []
      });

    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred during scanning.');
    } finally {
      setLoading(false);
      setStatusMsg('');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-3xl font-bold mb-2">Invoice Fraud Scanner</h2>
        <p className="text-slate-400">Upload vendor invoices or receipts to detect line-item discrepancies and tax anomalies.</p>
      </div>

      <div className="glass-panel p-8">
        {!file ? (
          <div 
            className="border-2 border-dashed border-slate-600 rounded-xl p-12 text-center hover:bg-slate-800/50 hover:border-primary transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <UploadCloud className="w-16 h-16 text-slate-400 mx-auto mb-4" />
            <p className="text-lg font-medium text-slate-200 mb-2">Click or drag document to upload</p>
            <p className="text-sm text-slate-500">Supports PDF, PNG, JPG (Max 10MB)</p>
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
            <div className="flex items-center gap-4 bg-slate-800 p-4 rounded-lg border border-slate-700 w-full mb-6">
              <FileText className="w-10 h-10 text-primary" />
              <div className="flex-1 truncate">
                <p className="font-medium text-slate-200 truncate">{file.name}</p>
                <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
              <button 
                onClick={() => setFile(null)} 
                disabled={loading}
                className="text-slate-400 hover:text-danger p-2"
              >
                ✕
              </button>
            </div>
            
            {loading && (
              <div className="w-full mb-6">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>{statusMsg}</span>
                  <span>{Math.round(uploadProgress)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div className="bg-primary h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                </div>
              </div>
            )}

            <button 
              onClick={handleScan} 
              disabled={loading}
              className="btn-primary w-full py-3 text-lg flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Run Anomaly Detection'}
            </button>
          </div>
        )}
        
        {error && <p className="text-danger mt-4 text-center">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up relative overflow-hidden",
          result.verdict === 'CLEAN' ? 'border-success/50' : 'border-danger/50'
        )}>
          {/* Background Glow */}
          <div className={clsx(
            "absolute -bottom-24 -left-24 w-64 h-64 rounded-full blur-[80px] pointer-events-none opacity-10",
            result.verdict === 'CLEAN' ? 'bg-success' : 'bg-danger'
          )}></div>

          <div className="grid md:grid-cols-2 gap-8 relative z-10">
            <div>
              <div className="flex items-center gap-4 mb-6">
                <div className={clsx(
                  "p-3 rounded-xl",
                  result.verdict === 'CLEAN' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
                )}>
                  {result.verdict === 'CLEAN' ? <CheckCircle className="w-8 h-8" /> : <FileWarning className="w-8 h-8" />}
                </div>
                <div>
                  <h3 className="text-2xl font-bold">{result.verdict === 'CLEAN' ? 'Invoice Clean' : 'Anomalies Detected'}</h3>
                  <p className="text-slate-400">Isolation Forest Verdict</p>
                </div>
              </div>

              {result.flaggedExplanations?.length > 0 && (
                <div className="mb-6">
                  <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Red Flags</h4>
                  <ul className="space-y-2">
                    {result.flaggedExplanations.map((reason, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-danger bg-danger/10 p-3 rounded-md border border-danger/20">
                        <AlertTriangle className="w-5 h-5 shrink-0" />
                        <span className="text-sm font-medium">{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="bg-slate-900 rounded-xl p-6 border border-slate-700">
              <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-700 pb-2">OCR Extracted Features</h4>
              <div className="space-y-3 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Subtotal:</span>
                  <span className="text-slate-200">₹{result.extractedFields?.subtotal?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tax Amount:</span>
                  <span className="text-slate-200">₹{result.extractedFields?.tax_amount?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between border-t border-slate-800 pt-2 mt-2">
                  <span className="text-slate-500">Line Item Delta:</span>
                  <span className={clsx(
                    "font-bold",
                    result.extractedFields?.line_item_delta > 0 ? "text-danger" : "text-success"
                  )}>
                    ₹{result.extractedFields?.line_item_delta?.toFixed(2) || '0.00'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tax Variance:</span>
                  <span className="text-slate-200">{result.extractedFields?.tax_percentage_variance?.toFixed(2) || '0'}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
