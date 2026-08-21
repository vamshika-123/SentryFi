import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { subscribeToUserScans } from '../services/firestoreService';
import { Activity, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import clsx from 'clsx';

export default function Dashboard() {
  const { currentUser } = useAuth();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentUser) return;
    
    const unsubscribe = subscribeToUserScans(currentUser.uid, (data) => {
      setScans(data);
      setLoading(false);
    }, 100); // fetch up to 100 recent for stats

    return () => unsubscribe();
  }, [currentUser]);

  // KPI Calculations
  const totalScans = scans.length;
  const highRiskScans = scans.filter(s => s.verdict === 'HIGH_RISK' || s.verdict === 'FRAUD' || s.verdict === 'FLAGGED').length;
  const avgRiskScore = totalScans > 0 ? (scans.reduce((acc, s) => acc + (s.riskScore || 0), 0) / totalScans).toFixed(1) : 0;
  const cleanRatio = totalScans > 0 ? Math.round(((totalScans - highRiskScans) / totalScans) * 100) : 100;

  // Chart Data
  const typeCounts = scans.reduce((acc, scan) => {
    acc[scan.type] = (acc[scan.type] || 0) + 1;
    return acc;
  }, {});

  const chartData = [
    { name: 'Phishing', value: typeCounts['phishing'] || 0, color: '#3B82F6' },
    { name: 'Invoice', value: typeCounts['invoice'] || 0, color: '#F59E0B' },
    { name: 'Compliance', value: typeCounts['compliance'] || 0, color: '#8B5CF6' }
  ].filter(d => d.value > 0);

  const getVerdictColor = (verdict) => {
    if (verdict === 'CLEAN') return 'text-success bg-success/10 border-success/30';
    if (['HIGH_RISK', 'FRAUD', 'FLAGGED'].includes(verdict)) return 'text-danger bg-danger/10 border-danger/30';
    return 'text-warning bg-warning/10 border-warning/30';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-2xl font-bold">Dashboard Overview</h2>
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard title="Total Scans" value={totalScans} icon={Activity} color="text-primary" />
        <KpiCard title="Threats Flagged" value={highRiskScans} icon={AlertTriangle} color="text-danger" />
        <KpiCard title="Avg Risk Score" value={avgRiskScore} icon={ShieldAlert} color="text-warning" />
        <KpiCard title="Clean Ratio" value={`${cleanRatio}%`} icon={CheckCircle} color="text-success" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-1 glass-panel p-6 flex flex-col">
          <h3 className="text-lg font-semibold mb-4">Scan Distribution</h3>
          {chartData.length > 0 ? (
            <div className="flex-1 min-h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                    itemStyle={{ color: '#E2E8F0' }}
                  />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              No scan data available
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 glass-panel p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          {loading ? (
            <div className="flex justify-center items-center h-48">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : scans.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-700/50 text-slate-400 text-sm">
                    <th className="pb-3 font-medium">Type</th>
                    <th className="pb-3 font-medium">Target</th>
                    <th className="pb-3 font-medium">Score</th>
                    <th className="pb-3 font-medium">Verdict</th>
                    <th className="pb-3 font-medium text-right">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.slice(0, 5).map((scan) => (
                    <tr key={scan.id} className="border-b border-slate-700/20 last:border-0 hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 capitalize font-medium">{scan.type}</td>
                      <td className="py-3 max-w-[200px] truncate" title={scan.targetName}>{scan.targetName}</td>
                      <td className="py-3">{scan.riskScore?.toFixed(1) || 'N/A'}</td>
                      <td className="py-3">
                        <span className={clsx("px-2 py-1 text-xs font-semibold rounded-full border", getVerdictColor(scan.verdict))}>
                          {scan.verdict}
                        </span>
                      </td>
                      <td className="py-3 text-right text-sm text-slate-400">
                        {scan.createdAt?.toDate ? scan.createdAt.toDate().toLocaleString() : 'Just now'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500">
              No recent activity. Start scanning to see results.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ title, value, icon: Icon, color }) {
  return (
    <div className="glass-panel p-6 flex items-center justify-between">
      <div>
        <p className="text-slate-400 text-sm font-medium mb-1">{title}</p>
        <p className="text-3xl font-bold">{value}</p>
      </div>
      <div className={clsx("p-3 rounded-xl bg-slate-800", color)}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
}
