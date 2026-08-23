import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { subscribeToUserScans } from '../services/firestoreService';
import { Activity, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import clsx from 'clsx';
import { VERDICT_LABELS, getVerdictColor } from '../utils/verdictLabels';

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

  // Chart Data — updated to use new palette
  const typeCounts = scans.reduce((acc, scan) => {
    acc[scan.type] = (acc[scan.type] || 0) + 1;
    return acc;
  }, {});

  const chartData = [
    { name: 'Phishing',   value: typeCounts['phishing']   || 0, color: '#1E40AF' }, // primary navy
    { name: 'Invoice',    value: typeCounts['invoice']     || 0, color: '#0284C7' }, // sky blue
    { name: 'Compliance', value: typeCounts['compliance']  || 0, color: '#6366F1' }  // indigo
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-2xl font-bold text-text-primary">Dashboard Overview</h2>
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard title="Total Scans"    value={totalScans}         icon={Activity}    colorClass="text-primary bg-blue-50" />
        <KpiCard title="Threats Flagged" value={highRiskScans}     icon={AlertTriangle} colorClass="text-danger bg-red-50" />
        <KpiCard title="Avg Risk Score"  value={avgRiskScore}      icon={ShieldAlert}  colorClass="text-warning bg-amber-50" />
        <KpiCard title="Clean Ratio"    value={`${cleanRatio}%`}  icon={CheckCircle}  colorClass="text-success bg-green-50" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-1 glass-panel p-6 flex flex-col">
          <h3 className="text-base font-semibold text-text-primary mb-4">Scan Distribution</h3>
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
                    contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '8px', color: '#0F172A' }}
                    itemStyle={{ color: '#0F172A' }}
                  />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-text-secondary text-sm">
              No scan data available
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 glass-panel p-6">
          <h3 className="text-base font-semibold text-text-primary mb-4">Recent Activity</h3>
          {loading ? (
            <div className="flex justify-center items-center h-48">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : scans.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border text-text-secondary text-xs uppercase tracking-wide">
                    <th className="pb-3 font-semibold">Type</th>
                    <th className="pb-3 font-semibold">Target</th>
                    <th className="pb-3 font-semibold">Score</th>
                    <th className="pb-3 font-semibold">Verdict</th>
                    <th className="pb-3 font-semibold text-right">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.slice(0, 5).map((scan) => (
                    <tr key={scan.id} className="border-b border-border last:border-0 hover:bg-surface-alt transition-colors">
                      <td className="py-3 capitalize text-sm font-medium text-text-primary">{scan.type}</td>
                      <td className="py-3 max-w-[200px] truncate text-sm text-text-secondary" title={scan.targetName}>{scan.targetName}</td>
                      <td className="py-3 text-sm text-text-primary">{scan.riskScore?.toFixed(1) || 'N/A'}</td>
                      <td className="py-3">
                        <span className={clsx("px-2 py-1 text-xs font-semibold rounded-full border", getVerdictColor(scan.verdict))}>
                          {VERDICT_LABELS[scan.verdict] || scan.verdict}
                        </span>
                      </td>
                      <td className="py-3 text-right text-xs text-text-secondary">
                        {scan.createdAt?.toDate ? scan.createdAt.toDate().toLocaleString() : 'Just now'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-text-secondary text-sm">
              No recent activity. Start scanning to see results.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ title, value, icon: Icon, colorClass }) {
  return (
    <div className="glass-panel p-6 flex items-center justify-between">
      <div>
        <p className="text-text-secondary text-sm font-medium mb-1">{title}</p>
        <p className="text-3xl font-bold text-text-primary">{value}</p>
      </div>
      <div className={clsx("p-3 rounded-xl", colorClass)}>
        <Icon className="w-6 h-6" />
      </div>
    </div>
  );
}
