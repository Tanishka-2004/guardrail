import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { FraudAlert, User } from '../types';
import { useAuthStore } from '../stores/authStore';
import { RiskBadge, PriorityBadge } from './RiskBadge';
import { StatusBadge } from './StatusBadge';
import { SLACountdown } from './SLACountdown';
import {
  X,
  Lock,
  Unlock,
  RefreshCw,
  UserCheck,
  CheckCircle2,
  RotateCcw,
  MessageSquare,
  FileText,
  AlertTriangle,
  History,
  CreditCard,
  Building,
  User as UserIcon,
} from 'lucide-react';

interface DrawerProps {
  alertId: string | null;
  onClose: () => void;
}

export const InvestigationDrawer: React.FC<DrawerProps> = ({ alertId, onClose }) => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [noteContent, setNoteContent] = useState('');
  const [resolveReason, setResolveReason] = useState('CONFIRMED_FRAUD');
  const [resolveNotes, setResolveNotes] = useState('');
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [reassignAnalystId, setReassignAnalystId] = useState('');
  const [showReassignModal, setShowReassignModal] = useState(false);

  const { data: alert, isLoading } = useQuery<FraudAlert>({
    queryKey: ['alert', alertId],
    queryFn: () => api.getAlert(alertId!),
    enabled: !!alertId,
    refetchInterval: 5000,
  });

  const { data: auditTrail } = useQuery({
    queryKey: ['audit', alertId],
    queryFn: () => api.getAuditTrail(alertId!),
    enabled: !!alertId,
  });

  const { data: analysts } = useQuery({
    queryKey: ['analysts'],
    queryFn: api.listAnalysts,
    enabled: showReassignModal,
  });

  // Action mutations
  const claimMutation = useMutation({
    mutationFn: () => api.claimAlert(alertId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const releaseMutation = useMutation({
    mutationFn: () => api.releaseAlert(alertId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const renewMutation = useMutation({
    mutationFn: () => api.renewClaim(alertId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
    },
  });

  const noteMutation = useMutation({
    mutationFn: (note: string) => api.addNote(alertId!, note),
    onSuccess: () => {
      setNoteContent('');
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['audit', alertId] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => api.resolveAlert(alertId!, resolveReason, resolveNotes),
    onSuccess: () => {
      setShowResolveModal(false);
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const reassignMutation = useMutation({
    mutationFn: () => api.reassignAlert(alertId!, reassignAnalystId),
    onSuccess: () => {
      setShowReassignModal(false);
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: () => api.reopenAlert(alertId!, 'Reopened for additional investigation evidence'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  if (!alertId) return null;

  const isOwner = alert?.assigned_analyst_id === user?.id || alert?.claimed_by === user?.name;
  const isSupervisorOrAdmin = user?.role === 'SUPERVISOR' || user?.role === 'ADMIN';

  return (
    <div className="fixed inset-y-0 right-0 w-[640px] bg-surface border-l border-surface-border shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-surface-border flex items-center justify-between bg-surface-subtle/50">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900 dark:text-white font-mono">{alert?.id.slice(0, 8)}...</h2>
            {alert && <RiskBadge level={alert.risk_level} score={alert.fraud_score} />}
            {alert && <PriorityBadge priority={alert.priority} />}
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5 block">
            Event ID: {alert?.event_id}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {isLoading || !alert ? (
        <div className="p-8 text-center text-slate-500">Loading alert details...</div>
      ) : (
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Action Bar */}
          <div className="flex items-center gap-2 flex-wrap p-3 bg-surface-subtle rounded-xl border border-surface-border">
            {!alert.claimed_by ? (
              <button
                onClick={() => claimMutation.mutate()}
                disabled={claimMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs font-semibold text-white shadow-sm transition-colors"
              >
                <Lock className="w-3.5 h-3.5" />
                Claim Alert (Lock)
              </button>
            ) : (
              <>
                {(isOwner || isSupervisorOrAdmin) && (
                  <>
                    <button
                      onClick={() => releaseMutation.mutate()}
                      disabled={releaseMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 border border-surface-border shadow-sm transition-colors"
                    >
                      <Unlock className="w-3.5 h-3.5" />
                      Release Claim
                    </button>
                    <button
                      onClick={() => renewMutation.mutate()}
                      disabled={renewMutation.isPending}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 border border-surface-border shadow-sm transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Renew Lease (10m)
                    </button>
                  </>
                )}

                {isSupervisorOrAdmin && (
                  <button
                    onClick={() => setShowReassignModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/40 text-xs font-medium text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 transition-colors"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    Reassign
                  </button>
                )}

                {alert.status !== 'RESOLVED' ? (
                  <button
                    onClick={() => setShowResolveModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white ml-auto shadow-sm transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Resolve Alert
                  </button>
                ) : (
                  isSupervisorOrAdmin && (
                    <button
                      onClick={() => reopenMutation.mutate()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-xs font-semibold text-white ml-auto shadow-sm transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reopen Alert
                    </button>
                  )
                )}
              </>
            )}
          </div>

          {/* Claim & SLA Status Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-surface rounded-xl border border-surface-border shadow-sm">
              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 block mb-1">Claim Status</span>
              <StatusBadge status={alert.status} claimedBy={alert.claimed_by} />
              {alert.claim_expires_at && (
                <span className="text-[10px] text-slate-500 block mt-1 font-mono">
                  Lease expires: {new Date(alert.claim_expires_at).toLocaleTimeString()}
                </span>
              )}
            </div>

            <div className="p-3 bg-surface rounded-xl border border-surface-border shadow-sm">
              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400 block mb-1">SLA Countdown</span>
              <SLACountdown
                deadline={alert.sla_deadline}
                isResolved={alert.status === 'RESOLVED'}
                slaStatus={alert.sla_status}
              />
              <span className="text-[10px] text-slate-500 block mt-1 font-mono">
                Target: {alert.sla_duration_minutes}m duration
              </span>
            </div>
          </div>

          {/* Fraud Reason & Anomaly Explanation */}
          <div className="p-4 bg-rose-50/60 dark:bg-rose-950/20 rounded-xl border border-rose-200 dark:border-rose-900/50 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-rose-700 dark:text-rose-400">
                <AlertTriangle className="w-4 h-4" />
                <span>FRAUD SCORING & ANOMALY BREAKDOWN</span>
              </div>
              <span className="font-mono text-xs font-bold text-rose-700 dark:text-rose-300 bg-rose-100 dark:bg-rose-900/40 px-2.5 py-0.5 rounded border border-rose-300 dark:border-rose-500/40">
                Score: {alert.fraud_score} / 100
              </span>
            </div>
            <p className="text-xs text-rose-900 dark:text-rose-200/95 leading-relaxed font-sans">{alert.fraud_reason}</p>

            {/* Granular Factor Breakdown */}
            <div className="space-y-1.5 pt-2 border-t border-rose-200 dark:border-rose-800/40">
              <span className="text-[10px] font-mono text-rose-700 dark:text-rose-300 uppercase tracking-wider block font-semibold">
                Risk Factor Contributions:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {((alert.source_event_metadata?.risk_factors as string[]) || [
                  "Velocity Burst (+35)",
                  "Geo-Distance Anomaly (+25)",
                  "Unregistered Device (+15)"
                ]).map((factor: string, idx: number) => (
                  <span
                    key={idx}
                    className="inline-flex items-center text-[11px] font-mono bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-200 border border-rose-300 dark:border-rose-800 px-2 py-0.5 rounded font-medium"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Financial Transaction Overview */}
          <div className="p-4 bg-surface rounded-xl border border-surface-border shadow-sm space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
              Transaction Metadata
            </h3>
            <div className="grid grid-cols-2 gap-y-2 text-xs">
              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                <CreditCard className="w-3.5 h-3.5" />
                <span>Amount:</span>
              </div>
              <div className="font-mono font-bold text-slate-900 dark:text-white text-right">
                ${alert.transaction_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {alert.currency}
              </div>

              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                <UserIcon className="w-3.5 h-3.5" />
                <span>Customer ID:</span>
              </div>
              <div className="font-mono text-slate-700 dark:text-slate-200 text-right">{alert.customer_id}</div>

              <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                <Building className="w-3.5 h-3.5" />
                <span>Merchant ID:</span>
              </div>
              <div className="font-mono text-slate-700 dark:text-slate-200 text-right">{alert.merchant_id}</div>

              <div className="text-slate-500 dark:text-slate-400">Transaction Type:</div>
              <div className="font-mono text-slate-700 dark:text-slate-200 text-right">{alert.transaction_type}</div>

              <div className="text-slate-500 dark:text-slate-400">Transaction Time:</div>
              <div className="font-mono text-slate-700 dark:text-slate-300 text-right text-[11px]">
                {new Date(alert.transaction_timestamp).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Notes Section */}
          <div className="p-4 bg-surface rounded-xl border border-surface-border shadow-sm space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5" />
              Investigation Notes
            </h3>

            {alert.notes ? (
              <pre className="text-xs font-mono text-slate-800 dark:text-slate-200 bg-surface-subtle p-3 rounded-lg border border-surface-border whitespace-pre-wrap">
                {alert.notes}
              </pre>
            ) : (
              <p className="text-xs text-slate-400 italic">No notes logged yet.</p>
            )}

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add investigation finding..."
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && noteContent.trim()) {
                    noteMutation.mutate(noteContent.trim());
                  }
                }}
                className="flex-1 bg-surface-subtle border border-surface-border rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={() => noteContent.trim() && noteMutation.mutate(noteContent.trim())}
                disabled={!noteContent.trim() || noteMutation.isPending}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-xs font-semibold rounded-lg text-white transition-colors"
              >
                Save
              </button>
            </div>
          </div>

          {/* Immutable Audit Trail */}
          <div className="p-4 bg-surface rounded-xl border border-surface-border shadow-sm space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5">
              <History className="w-3.5 h-3.5" />
              Audit Log Timeline
            </h3>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {auditTrail?.map((log) => (
                <div
                  key={log.id}
                  className="p-2.5 rounded-lg bg-surface-subtle border border-surface-border text-xs space-y-1"
                >
                  <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px] font-mono">
                    <span className="font-bold text-blue-600 dark:text-blue-400">{log.action}</span>
                    <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-slate-700 dark:text-slate-300">
                    By <span className="font-semibold text-slate-900 dark:text-white">{log.actor_name || 'SYSTEM'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Resolve Confirmation Modal */}
      {showResolveModal && (
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-surface border border-surface-border rounded-xl p-5 w-full max-w-md space-y-4 shadow-2xl">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Resolve Fraud Alert</h4>
            <div>
              <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Resolution Outcome</label>
              <select
                value={resolveReason}
                onChange={(e) => setResolveReason(e.target.value)}
                className="w-full bg-surface-subtle border border-surface-border rounded-lg p-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-blue-500"
              >
                <option value="CONFIRMED_FRAUD">CONFIRMED FRAUD (Block Card & Report)</option>
                <option value="FALSE_POSITIVE">FALSE POSITIVE (Verified Legitimate)</option>
                <option value="CARDHOLDER_VERIFIED">CARDHOLDER VERIFIED (SMS/Voice confirmation)</option>
                <option value="SUSPICIOUS_MONITORED">SUSPICIOUS (Added to watchlist)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Closing Notes</label>
              <textarea
                value={resolveNotes}
                onChange={(e) => setResolveNotes(e.target.value)}
                rows={3}
                placeholder="Document resolution rationale..."
                className="w-full bg-surface-subtle border border-surface-border rounded-lg p-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowResolveModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => resolveMutation.mutate()}
                disabled={resolveMutation.isPending}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white shadow-sm transition-colors"
              >
                Confirm Resolution
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reassign Modal */}
      {showReassignModal && (
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-surface border border-surface-border rounded-xl p-5 w-full max-w-md space-y-4 shadow-2xl">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Supervisor Reassignment</h4>
            <div>
              <label className="text-xs text-slate-600 dark:text-slate-400 block mb-1">Assign to Analyst</label>
              <select
                value={reassignAnalystId}
                onChange={(e) => setReassignAnalystId(e.target.value)}
                className="w-full bg-surface-subtle border border-surface-border rounded-lg p-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Select target analyst...</option>
                {analysts?.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.role} - {a.team})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowReassignModal(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => reassignMutation.mutate()}
                disabled={!reassignAnalystId || reassignMutation.isPending}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs font-semibold text-white shadow-sm transition-colors"
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
