import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { FraudAlert } from '../types';
import { useAuthStore } from '../stores/authStore';
import { RiskBadge, PriorityBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { SLACountdown } from '../components/SLACountdown';
import { InvestigationDrawer } from '../components/InvestigationDrawer';
import { 
  Search, 
  RotateCw, 
  ChevronLeft, 
  ChevronRight, 
  Lock, 
  Eye
} from 'lucide-react';

export const QueuePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [activeTab, setActiveTab] = useState<'ACTIVE' | 'UNASSIGNED' | 'ESCALATED' | 'RESOLVED'>('ACTIVE');
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [search, setSearch] = useState('');
  const [selectedRisk, setSelectedRisk] = useState<string>('');
  const [sortBy, setSortBy] = useState('priority_sla');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  // Derive status from active tab
  const getStatusFilter = () => {
    if (activeTab === 'UNASSIGNED') return 'NEW';
    if (activeTab === 'ESCALATED') return 'ESCALATED';
    if (activeTab === 'RESOLVED') return 'RESOLVED';
    return ''; // For ACTIVE, we handle in query or list
  };

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['alerts', page, search, activeTab, selectedRisk, sortBy],
    queryFn: () =>
      api.listAlerts({
        page,
        limit,
        search: search || undefined,
        status: getStatusFilter() || undefined,
        risk_level: selectedRisk || undefined,
        sort_by: sortBy,
      }),
    refetchInterval: 8000,
  });

  const claimMutation = useMutation({
    mutationFn: (id: string) => api.claimAlert(id),
    onSuccess: (updatedAlert) => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setSelectedAlertId(updatedAlert.id);
    },
  });

  // Filter items in ACTIVE tab to exclude resolved alerts
  const items = (data?.items || []).filter((item: FraudAlert) => {
    if (activeTab === 'ACTIVE') {
      return item.status !== 'RESOLVED';
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Title & Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Fraud Alert Triage Queue</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time urgency prioritization, atomic claim locks, and SLA countdowns
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-100 dark:hover:bg-slate-800 border border-surface-border text-xs text-slate-700 dark:text-slate-300 transition-colors shadow-sm"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Queue View Tabs */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 text-xs">
        <button
          onClick={() => { setActiveTab('ACTIVE'); setPage(1); }}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
            activeTab === 'ACTIVE'
              ? 'bg-blue-600 text-white font-semibold shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
          }`}
        >
          All Active Alerts
        </button>
        <button
          onClick={() => { setActiveTab('UNASSIGNED'); setPage(1); }}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
            activeTab === 'UNASSIGNED'
              ? 'bg-blue-600 text-white font-semibold shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
          }`}
        >
          Unassigned (New)
        </button>
        <button
          onClick={() => { setActiveTab('ESCALATED'); setPage(1); }}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
            activeTab === 'ESCALATED'
              ? 'bg-rose-600 text-white font-semibold shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
          }`}
        >
          Escalated / Overdue
        </button>
        <button
          onClick={() => { setActiveTab('RESOLVED'); setPage(1); }}
          className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
            activeTab === 'RESOLVED'
              ? 'bg-emerald-600 text-white font-semibold shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
          }`}
        >
          Resolved Today
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 bg-surface rounded-xl border border-surface-border flex items-center gap-3 flex-wrap shadow-sm">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by customer, merchant, reason, or event ID..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-surface-subtle border border-surface-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-blue-600"
          />
        </div>

        {/* Risk Level Filter */}
        <select
          value={selectedRisk}
          onChange={(e) => {
            setSelectedRisk(e.target.value);
            setPage(1);
          }}
          className="bg-surface-subtle border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none"
        >
          <option value="">All Risk Tiers</option>
          <option value="CRITICAL">Critical (Score 85+)</option>
          <option value="HIGH">High (Score 65-84)</option>
          <option value="MEDIUM">Medium (Score 40-64)</option>
          <option value="LOW">Low (Score &lt;40)</option>
        </select>

        {/* Sorting Options */}
        <select
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value);
            setPage(1);
          }}
          className="bg-surface-subtle border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-300 focus:outline-none font-mono"
        >
          <option value="priority_sla">Sort: SLA Urgency + Score</option>
          <option value="sla_deadline">Sort: SLA Deadline</option>
          <option value="fraud_score">Sort: Highest Fraud Score</option>
          <option value="amount">Sort: Transaction Amount</option>
          <option value="created_at">Sort: Most Recent</option>
        </select>
      </div>

      {/* Main Alert Table */}
      <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-surface-border bg-surface-subtle text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              <th className="py-2.5 px-3">Priority</th>
              <th className="py-2.5 px-3 w-[36%]">Fraud Reason & Anomaly Explanation</th>
              <th className="py-2.5 px-3">Amount</th>
              <th className="py-2.5 px-3">Risk Tier</th>
              <th className="py-2.5 px-3">SLA Status</th>
              <th className="py-2.5 px-3">Owner</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border text-xs">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-400 font-mono">
                  Loading fraud alert stream...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-400 font-mono">
                  No alerts match active filter criteria.
                </td>
              </tr>
            ) : (
              items.map((alert: FraudAlert) => {
                const isOverdue = alert.status === 'ESCALATED' || alert.sla_status === 'BREACHED';
                return (
                  <tr
                    key={alert.id}
                    onClick={() => setSelectedAlertId(alert.id)}
                    className={`cursor-pointer transition-colors ${
                      isOverdue 
                        ? 'bg-rose-50/60 dark:bg-rose-950/20 hover:bg-rose-100/60 dark:hover:bg-rose-950/30' 
                        : 'hover:bg-blue-50/40 dark:hover:bg-slate-800/40'
                    }`}
                  >
                    {/* Priority */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <div className="flex flex-col gap-1 items-start">
                        <PriorityBadge priority={alert.priority} />
                        <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                          {alert.priority === 'P1_CRITICAL' 
                            ? (isOverdue ? 'Escalated' : 'Score ≥85') 
                            : alert.priority === 'P2_HIGH' ? 'Score ≥65' : 'Standard'}
                        </span>
                      </div>
                    </td>

                    {/* Fraud Reason */}
                    <td className="py-3 px-3">
                      <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                        {alert.fraud_reason}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-1 flex items-center gap-2">
                        <span className="text-blue-600 dark:text-blue-400 font-semibold">{alert.customer_id}</span>
                        <span>•</span>
                        <span className="truncate max-w-[160px]">{alert.merchant_id}</span>
                        <span>•</span>
                        <span className="text-slate-400 dark:text-slate-500">{alert.id.slice(0, 8)}</span>
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <div className="font-mono font-bold text-slate-900 dark:text-white text-sm">
                        ${alert.transaction_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                      <span className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-mono">{alert.currency} • {alert.transaction_type}</span>
                    </td>

                    {/* Risk Tier & Score */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <RiskBadge level={alert.risk_level} score={alert.fraud_score} />
                    </td>

                    {/* SLA Status & Countdown */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <SLACountdown
                        deadline={alert.sla_deadline}
                        isResolved={alert.status === 'RESOLVED'}
                        slaStatus={alert.sla_status}
                      />
                    </td>

                    {/* Status & Owner */}
                    <td className="py-3 px-3 whitespace-nowrap">
                      <StatusBadge status={alert.status} claimedBy={alert.claimed_by} />
                    </td>

                    {/* Action */}
                    <td className="py-3 px-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {!alert.claimed_by && alert.status !== 'RESOLVED' ? (
                        <button
                          onClick={() => claimMutation.mutate(alert.id)}
                          disabled={claimMutation.isPending}
                          className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs inline-flex items-center gap-1 transition-colors shadow-sm"
                        >
                          <Lock className="w-3 h-3" />
                          Claim
                        </button>
                      ) : (
                        <button
                          onClick={() => setSelectedAlertId(alert.id)}
                          className="px-2.5 py-1 rounded bg-surface-subtle hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-medium text-xs inline-flex items-center gap-1 border border-surface-border transition-colors shadow-sm"
                        >
                          <Eye className="w-3 h-3" />
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Pagination Bar */}
        <div className="p-3 bg-surface-subtle border-t border-surface-border flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
          <div>
            Showing <span className="text-slate-900 dark:text-white font-bold">{items.length}</span> alerts on page <span className="text-slate-900 dark:text-white font-bold">{page}</span> of{' '}
            <span className="text-slate-900 dark:text-white font-bold">{data?.pages || 1}</span> ({data?.total || 0} total)
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded bg-surface hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-40 border border-surface-border text-slate-700 dark:text-slate-300 shadow-sm"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => (data && page < data.pages ? p + 1 : p))}
              disabled={!data || page >= data.pages}
              className="p-1 rounded bg-surface hover:bg-slate-200 dark:hover:bg-slate-800 disabled:opacity-40 border border-surface-border text-slate-700 dark:text-slate-300 shadow-sm"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Slide-over Investigation Drawer */}
      <InvestigationDrawer alertId={selectedAlertId} onClose={() => setSelectedAlertId(null)} />
    </div>
  );
};
