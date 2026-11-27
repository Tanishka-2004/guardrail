import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useWSStore } from '../stores/wsStore';
import { 
  ShieldAlert, 
  Clock, 
  AlertTriangle, 
  Activity, 
  Zap,
  TrendingUp,
  Cpu
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar 
} from 'recharts';

export const DashboardPage: React.FC = () => {
  const { recentEvents } = useWSStore();

  const { data: metrics } = useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: api.getMetrics,
    refetchInterval: 10000,
  });

  const { data: queueSummary } = useQuery({
    queryKey: ['queueSummary'],
    queryFn: api.getQueueSummary,
    refetchInterval: 15000,
  });

  const { data: slaSummary } = useQuery({
    queryKey: ['slaSummary'],
    queryFn: api.getSLASummary,
    refetchInterval: 15000,
  });

  const riskData = [
    { name: 'Critical', value: queueSummary?.by_risk_level?.CRITICAL || 0, color: '#EF4444' },
    { name: 'High', value: queueSummary?.by_risk_level?.HIGH || 0, color: '#F97316' },
    { name: 'Medium', value: queueSummary?.by_risk_level?.MEDIUM || 0, color: '#F59E0B' },
    { name: 'Low', value: queueSummary?.by_risk_level?.LOW || 0, color: '#3B82F6' },
  ];

  const slaData = [
    { name: 'Healthy', value: slaSummary?.healthy || 0, fill: '#10B981' },
    { name: 'Warning (<15m)', value: slaSummary?.warning || 0, fill: '#F59E0B' },
    { name: 'Breached', value: slaSummary?.breached || 0, fill: '#EF4444' },
  ];

  const volumeData = queueSummary?.volume_over_time || [];

  return (
    <div className="space-y-6">
      {/* Top Banner & KPI Cards */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Operations Dashboard</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time fraud alert stream, SLA compliance, and cluster health
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-600 dark:text-slate-300 bg-surface px-3 py-1.5 rounded-lg border border-surface-border flex items-center gap-2 shadow-sm">
            <Cpu className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>Scoring Circuit Breaker:</span>
            <span className="font-bold text-emerald-600 dark:text-emerald-400">{metrics?.circuit_breaker_state || 'CLOSED'}</span>
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Active Alerts */}
        <div className="p-4 bg-surface rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-medium">Active Alerts</span>
            <Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
            {metrics?.total_active_alerts ?? '...'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1 font-mono">
            <span>Throughput: <strong className="text-blue-600 dark:text-blue-400">{metrics?.queue_throughput_per_minute ?? 0}/min</strong></span>
          </div>
        </div>

        {/* Critical Alerts */}
        <div className="p-4 bg-surface rounded-xl border border-rose-200 dark:border-rose-500/20 bg-rose-50/40 dark:bg-rose-950/10 shadow-sm">
          <div className="flex items-center justify-between text-rose-700 dark:text-rose-300 mb-2">
            <span className="text-xs font-medium">Critical Alerts</span>
            <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-700 dark:text-rose-400">
            {metrics?.critical_alerts ?? '...'}
          </div>
          <div className="text-[11px] text-rose-600/80 dark:text-rose-300/70 mt-1 font-mono">
            Requires immediate action
          </div>
        </div>

        {/* SLA Breaches */}
        <div className="p-4 bg-surface rounded-xl border border-amber-200 dark:border-amber-500/20 bg-amber-50/40 dark:bg-amber-950/10 shadow-sm">
          <div className="flex items-center justify-between text-amber-800 dark:text-amber-300 mb-2">
            <span className="text-xs font-medium">SLA Breaches</span>
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-800 dark:text-amber-400">
            {metrics?.sla_breaches ?? '...'}
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 font-mono">
            {metrics?.sla_warnings ?? 0} approaching warning threshold
          </div>
        </div>

        {/* Avg Resolution Speed */}
        <div className="p-4 bg-surface rounded-xl border border-surface-border shadow-sm">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2">
            <span className="text-xs font-medium">Avg Resolution Time</span>
            <Clock className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
            {metrics?.avg_resolution_time_minutes?.toFixed(1) ?? '...'}m
          </div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">
            {metrics?.alerts_processed_today ?? 0} processed today
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-3 gap-6">
        {/* Ingestion Volume Over Time */}
        <div className="col-span-2 p-5 bg-surface rounded-xl border border-surface-border space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Alert Ingestion Volume</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">Hourly Kafka streaming event intake</p>
            </div>
            <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeData}>
                <defs>
                  <linearGradient id="volumeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#F8FAFC',
                  }}
                />
                <Area type="monotone" dataKey="count" stroke="#2563EB" strokeWidth={2} fillOpacity={1} fill="url(#volumeGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Level Distribution */}
        <div className="p-5 bg-surface rounded-xl border border-surface-border space-y-4 flex flex-col justify-between shadow-sm">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Risk Distribution</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">Active queue risk severity breakdown</p>
          </div>

          <div className="h-44 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {riskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#F8FAFC',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {riskData.map((d) => (
              <div key={d.name} className="flex items-center gap-2 p-1.5 bg-surface-subtle rounded border border-surface-border">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                <span className="text-slate-600 dark:text-slate-300 font-medium">{d.name}:</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white ml-auto">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SLA Compliance & Live Feed */}
      <div className="grid grid-cols-3 gap-6">
        {/* SLA Health Chart */}
        <div className="p-5 bg-surface rounded-xl border border-surface-border space-y-4 shadow-sm">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">SLA Target Compliance</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">Alert countdown health breakdown</p>
          </div>

          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={slaData} layout="vertical">
                <XAxis type="number" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={11} tickLine={false} width={100} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#F8FAFC',
                  }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Live Real-Time Activity Feed */}
        <div className="col-span-2 p-5 bg-surface rounded-xl border border-surface-border space-y-4 flex flex-col shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                <span>Real-Time WebSocket Feed</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">Live stream of ingested, claimed & resolved fraud events</p>
            </div>
            <span className="text-xs font-mono text-slate-500">{recentEvents.length} events logged</span>
          </div>

          <div className="flex-1 max-h-56 overflow-y-auto space-y-2 pr-1">
            {recentEvents.length === 0 ? (
              <div className="h-44 flex flex-col items-center justify-center text-slate-500 text-xs italic space-y-2">
                <Zap className="w-5 h-5 text-slate-400 animate-pulse" />
                <span>Waiting for live incoming WebSocket events from Kafka cluster...</span>
              </div>
            ) : (
              recentEvents.map((evt, idx) => (
                <div
                  key={`${evt.event_id}-${idx}`}
                  className="p-2.5 rounded bg-surface-subtle border border-surface-border flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-blue-600 dark:text-blue-400 font-bold">{evt.event_type}</span>
                    <span className="text-slate-700 dark:text-slate-300 truncate max-w-xs">
                      {evt.payload?.fraud_reason || evt.payload?.notes || evt.payload?.claimed_by || 'Event processed'}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
