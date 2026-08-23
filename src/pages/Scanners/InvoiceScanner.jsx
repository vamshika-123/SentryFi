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

  const isClean = result?.verdict === 'CLEAN';

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">Invoice Fraud Scanner</h2>
        <p className="text-text-secondary text-sm">Upload vendor invoices or receipts to detect line-item discrepancies and tax anomalies.</p>
      </div>

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
                onClick={() => setFile(null)} 
                disabled={loading}
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
                  <div className="bg-primary h-1.5 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                </div>
              </div>
            )}

            <button 
              onClick={handleScan} 
              disabled={loading}
              className="btn-primary w-full py-3 text-sm flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Run Anomaly Detection'}
            </button>
          </div>
        )}
        
        {error && <p className="text-danger mt-4 text-center text-sm">{error}</p>}
      </div>

      {result && (
        <div className={clsx(
          "glass-panel p-8 animate-slide-up",
          isClean ? 'border-l-4 border-l-success' : 'border-l-4 border-l-danger'
        )}>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <div className="flex items-center gap-4 mb-6">
                <div className={clsx(
                  "p-3 rounded-xl",
                  isClean ? 'bg-green-50 text-success' : 'bg-red-50 text-danger'
                )}>
                  {isClean ? <CheckCircle className="w-8 h-8" /> : <FileWarning className="w-8 h-8" />}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-text-primary">{isClean ? 'Invoice Clear' : 'Anomalies Detected'}</h3>
                  <p className="text-text-secondary text-sm">Fraud Risk Assessment</p>
                </div>
              </div>

              {result.flaggedExplanations?.length > 0 && (
                <div className="mb-6">
                  <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Red Flags</h4>
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
            </div>

            <div className="bg-surface-alt rounded-xl p-6 border border-border">
              <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-4 border-b border-border pb-2">
                Extracted Invoice Fields
              </h4>
              <div className="space-y-3 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Subtotal:</span>
                  <span className="text-text-primary font-medium">₹{result.extractedFields?.subtotal?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">GST Amount:</span>
                  <span className="text-text-primary font-medium">₹{result.extractedFields?.tax_amount?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between border-t border-border pt-2 mt-2">
                  <span className="text-text-secondary">Amount Mismatch:</span>
                  <span className={clsx(
                    "font-bold",
                    result.extractedFields?.line_item_delta > 0 ? "text-danger" : "text-success"
                  )}>
                    ₹{result.extractedFields?.line_item_delta?.toFixed(2) || '0.00'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">GST Rate Difference:</span>
                  <span className="text-text-primary font-medium">{result.extractedFields?.tax_percentage_variance?.toFixed(2) || '0'}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
