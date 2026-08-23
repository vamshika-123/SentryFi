import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getRecentScans, deleteScanRecord } from '../services/firestoreService';
import { Search, Filter, Trash2, ExternalLink, Download, FileText, Globe, Shield } from 'lucide-react';
import clsx from 'clsx';

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

  const getVerdictColor = (verdict) => {
    if (verdict === 'CLEAN') return 'text-success bg-success/10 border-success/30';
    if (['HIGH_RISK', 'FRAUD', 'FLAGGED'].includes(verdict)) return 'text-danger bg-danger/10 border-danger/30';
    return 'text-warning bg-warning/10 border-warning/30';
  };

  const getTypeIcon = (type) => {
    if (type === 'phishing') return <Globe className="w-4 h-4" />;
    if (type === 'invoice') return <FileText className="w-4 h-4" />;
    return <Shield className="w-4 h-4" />;
  };

  return (
    <div className="space-y-6 animate-fade-in relative">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold mb-2">Scan History & Audit Trail</h2>
          <p className="text-slate-400">Review all past scans, download reports, and manage evidence.</p>
        </div>
        
        <div className="flex gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              type="text"
              placeholder="Search target..."
              className="input-field pl-9 w-64"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <select 
            className="input-field cursor-pointer"
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
              <thead className="bg-slate-800/50 border-b border-slate-700">
                <tr>
                  <th className="px-6 py-4 font-semibold text-slate-300">Date/Time</th>
                  <th className="px-6 py-4 font-semibold text-slate-300">Type</th>
                  <th className="px-6 py-4 font-semibold text-slate-300">Target</th>
                  <th className="px-6 py-4 font-semibold text-slate-300">Risk Score</th>
                  <th className="px-6 py-4 font-semibold text-slate-300">Verdict</th>
                  <th className="px-6 py-4 font-semibold text-slate-300 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {filteredScans.map((scan) => (
                  <tr 
                    key={scan.id} 
                    className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedScan(scan)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400">
                      {scan.createdAt?.toDate ? scan.createdAt.toDate().toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 capitalize text-slate-300">
                        {getTypeIcon(scan.type)}
                        <span>{scan.type}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 truncate max-w-xs text-slate-300" title={scan.targetName}>
                      {scan.targetName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-slate-300">
                      {scan.riskScore?.toFixed(1) || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={clsx("px-3 py-1 text-xs font-semibold rounded-full border", getVerdictColor(scan.verdict))}>
                        {scan.verdict}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDelete(scan); }}
                        className="p-2 text-slate-500 hover:text-danger hover:bg-danger/10 rounded-lg transition-colors"
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
          <div className="p-12 text-center text-slate-500">
            <Filter className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p className="text-lg">No scans found matching your criteria.</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in" onClick={() => setSelectedScan(null)}>
          <div className="glass-panel p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-6">
              <h3 className="text-2xl font-bold capitalize">{selectedScan.type} Scan Details</h3>
              <button onClick={() => setSelectedScan(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                  <p className="text-sm text-slate-400 mb-1">Verdict</p>
                  <p className={clsx("text-lg font-bold", getVerdictColor(selectedScan.verdict).split(' ')[0])}>
                    {selectedScan.verdict}
                  </p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                  <p className="text-sm text-slate-400 mb-1">Risk Score / Confidence</p>
                  <p className="text-lg font-bold text-slate-200">
                    {selectedScan.riskScore?.toFixed(1) || 'N/A'} <span className="text-sm font-normal text-slate-500">/ {selectedScan.confidence?.toFixed(1)}%</span>
                  </p>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-400 mb-2">Target Analyzed</p>
                <div className="bg-slate-900 p-3 rounded-lg border border-slate-700 font-mono text-sm break-all flex justify-between items-center">
                  <span>{selectedScan.targetName}</span>
                  {selectedScan.fileUrl && (
                    <a href={selectedScan.fileUrl} target="_blank" rel="noreferrer" className="text-primary hover:text-blue-400 flex items-center gap-1 shrink-0 ml-4 bg-primary/10 px-3 py-1 rounded-md">
                      <Download className="w-4 h-4" /> Download Original
                    </a>
                  )}
                </div>
              </div>

              {selectedScan.flaggedReasons && selectedScan.flaggedReasons.length > 0 && (
                <div>
                  <p className="text-sm text-slate-400 mb-2">Detected Anomalies / Flagged Reasons</p>
                  <ul className="space-y-2">
                    {selectedScan.flaggedReasons.map((reason, idx) => (
                      <li key={idx} className="bg-danger/5 border border-danger/20 p-3 rounded-lg text-slate-300 text-sm flex gap-2">
                        <span className="text-danger">•</span> {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end pt-4 border-t border-slate-700">
                <button onClick={() => handleDelete(selectedScan)} className="btn-primary bg-danger hover:bg-red-600 flex items-center gap-2">
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
