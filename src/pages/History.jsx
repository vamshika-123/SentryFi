import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getRecentScans, deleteScanRecord } from '../services/firestoreService';
import { Search, Filter, Trash2, Download, FileText, Globe, Shield } from 'lucide-react';
import clsx from 'clsx';
import { VERDICT_LABELS, getVerdictColor } from '../utils/verdictLabels';

export default function History() {
  const { currentUser } = useAuth();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [selectedScan, setSelectedScan] = useState(null); // For modal

  useEffect(() => {
    fetchScans();
  }, [currentUser]);

  const fetchScans = async () => {
    if (!currentUser) return;
    try {
      setLoading(true);
      // Fetch up to 100 for history view
      const data = await getRecentScans(currentUser.uid, 100);
      setScans(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (scan) => {
    if (!window.confirm('Are you sure you want to delete this scan record?')) return;
    
    try {
      await deleteScanRecord(scan.id);
      setScans(scans.filter(s => s.id !== scan.id));
      setSelectedScan(null);
    } catch (error) {
      console.error(error);
      alert('Failed to delete scan record.');
    }
  };

  const filteredScans = scans.filter(scan => {
    const matchesSearch = scan.targetName?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || scan.type === filterType;
    return matchesSearch && matchesType;
  });

  const getTypeIcon = (type) => {
    if (type === 'phishing') return <Globe className="w-4 h-4" />;
    if (type === 'invoice') return <FileText className="w-4 h-4" />;
    return <Shield className="w-4 h-4" />;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-1">Scan History &amp; Audit Trail</h2>
          <p className="text-text-secondary text-sm">Review all past scans, download reports, and manage evidence.</p>
        </div>
        
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text"
              placeholder="Search target..."
              className="input-field pl-9 w-56 text-sm"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <select 
            className="input-field cursor-pointer text-sm"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="all">All Types</option>
            <option value="phishing">Phishing</option>
            <option value="invoice">Invoice</option>
            <option value="compliance">Compliance</option>
          </select>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredScans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-surface-alt border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Date/Time</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Type</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Target</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Risk Score</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Verdict</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-secondary uppercase tracking-wide text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredScans.map((scan) => (
                  <tr 
                    key={scan.id} 
                    className="hover:bg-surface-alt transition-colors cursor-pointer"
                    onClick={() => setSelectedScan(scan)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-secondary">
                      {scan.createdAt?.toDate ? scan.createdAt.toDate().toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 capitalize text-sm text-text-primary">
                        {getTypeIcon(scan.type)}
                        <span>{scan.type}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 truncate max-w-xs text-sm text-text-primary" title={scan.targetName}>
                      {scan.targetName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-text-primary">
                      {scan.riskScore?.toFixed(1) || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={clsx("px-3 py-1 text-xs font-semibold rounded-full border", getVerdictColor(scan.verdict))}>
                        {VERDICT_LABELS[scan.verdict] || scan.verdict}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDelete(scan); }}
                        className="p-2 text-text-secondary hover:text-danger hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete Record"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-text-secondary">
            <Filter className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p className="text-base">No scans found matching your criteria.</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedScan && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in"
          onClick={() => setSelectedScan(null)}
        >
          <div
            className="bg-surface border border-border rounded-2xl shadow-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-6">
              <h3 className="text-xl font-bold capitalize text-text-primary">{selectedScan.type} Scan Details</h3>
              <button onClick={() => setSelectedScan(null)} className="text-text-secondary hover:text-text-primary transition-colors">✕</button>
            </div>
            
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface-alt p-4 rounded-lg border border-border">
                  <p className="text-xs text-text-secondary mb-1 uppercase tracking-wide font-semibold">Verdict</p>
                  <p className={clsx("text-base font-bold", getVerdictColor(selectedScan.verdict).split(' ')[0])}>
                    {VERDICT_LABELS[selectedScan.verdict] || selectedScan.verdict}
                  </p>
                </div>
                <div className="bg-surface-alt p-4 rounded-lg border border-border">
                  <p className="text-xs text-text-secondary mb-1 uppercase tracking-wide font-semibold">Risk Score / Confidence</p>
                  <p className="text-base font-bold text-text-primary">
                    {selectedScan.riskScore?.toFixed(1) || 'N/A'} <span className="text-sm font-normal text-text-secondary">/ {selectedScan.confidence?.toFixed(1)}%</span>
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs text-text-secondary mb-2 uppercase tracking-wide font-semibold">Target Analyzed</p>
                <div className="bg-surface-alt p-3 rounded-lg border border-border font-mono text-sm break-all flex justify-between items-center">
                  <span className="text-text-primary">{selectedScan.targetName}</span>
                  {selectedScan.fileUrl && (
                    <a href={selectedScan.fileUrl} target="_blank" rel="noreferrer" className="text-primary hover:text-primary-hover flex items-center gap-1 shrink-0 ml-4 bg-blue-50 px-3 py-1 rounded-md text-xs font-semibold border border-blue-100">
                      <Download className="w-4 h-4" /> Download Original
                    </a>
                  )}
                </div>
              </div>

              {selectedScan.flaggedReasons && selectedScan.flaggedReasons.length > 0 && (
                <div>
                  <p className="text-xs text-text-secondary mb-2 uppercase tracking-wide font-semibold">Detected Anomalies</p>
                  <ul className="space-y-2">
                    {selectedScan.flaggedReasons.map((reason, idx) => (
                      <li key={idx} className="bg-red-50 border border-red-100 p-3 rounded-lg text-text-primary text-sm flex gap-2">
                        <span className="text-danger">•</span> {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end pt-4 border-t border-border">
                <button onClick={() => handleDelete(selectedScan)} className="btn-primary bg-danger hover:bg-red-700 flex items-center gap-2">
                  <Trash2 className="w-4 h-4" /> Delete Record
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
