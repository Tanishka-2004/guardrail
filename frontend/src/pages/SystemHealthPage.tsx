import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { SystemHealth } from '../types';
import { CheckCircle2, AlertTriangle, XCircle, Radio } from 'lucide-react';

export const SystemHealthPage: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: health, isLoading } = useQuery<SystemHealth>({
    queryKey: ['systemHealth'],
    queryFn: api.getSystemHealth,
    refetchInterval: 5000,
  });

  const resetCircuitMutation = useMutation({
    mutationFn: api.resetCircuitBreaker,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemHealth'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">System Infrastructure Health</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Real-time health verification for Kafka KRaft brokers, PostgreSQL, Redis, and Circuit Breakers
        </p>
      </div>

      {isLoading || !health ? (
        <div className="p-8 text-center text-slate-400 font-mono">Querying cluster health checks...</div>
      ) : (
        <div className="space-y-6">
          {/* Overall Health Pill */}
          <div className="p-5 bg-surface rounded-xl border border-surface-border flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <span
                className={`w-3.5 h-3.5 rounded-full ${
                  health.status === 'HEALTHY'
                    ? 'bg-emerald-500'
                    : health.status === 'DEGRADED'
                    ? 'bg-amber-500 animate-ping'
                    : 'bg-rose-500 animate-pulse'
                }`}
              />
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Cluster Status: {health.status}</h3>
                <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  Engine Version {health.version} | Timestamp: {new Date(health.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40 px-3 py-1.5 rounded-lg border border-blue-200 dark:border-blue-500/30">
              <Radio className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Active WebSockets: <strong>{health.active_websocket_connections}</strong></span>
            </div>
          </div>

          {/* Dependency Grid */}
          <div className="grid grid-cols-2 gap-4">
            {health.dependencies.map((dep) => (
              <div
                key={dep.name}
                className="p-4 bg-surface rounded-xl border border-surface-border flex items-center justify-between shadow-sm"
              >
                <div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white">{dep.name}</h4>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5 flex flex-col gap-0.5">
                    {dep.latency_ms !== null && dep.latency_ms !== undefined && (
                      <span>Latency: <strong className="text-slate-900 dark:text-slate-100">{dep.latency_ms} ms</strong></span>
                    )}
                    {dep.details && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">{dep.details}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  {dep.status === 'UP' ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      UP
                    </span>
                  ) : dep.status === 'DEGRADED' ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      DEGRADED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30">
                      <XCircle className="w-3.5 h-3.5" />
                      DOWN
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Circuit Breaker Detailed Telemetry */}
          <div className="p-5 bg-surface rounded-xl border border-surface-border space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Fraud Scoring Circuit Breaker</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  Fault tolerance governor protecting against scoring dependency degradation
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`px-3 py-1 rounded text-xs font-mono font-bold uppercase border ${
                    health.circuit_breaker.state === 'CLOSED'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30'
                      : health.circuit_breaker.state === 'HALF_OPEN'
                      ? 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30 animate-pulse'
                      : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30'
                  }`}
                >
                  STATE: {health.circuit_breaker.state}
                </span>
                <button
                  onClick={() => {
                    if (window.confirm('Confirm manual circuit breaker reset to CLOSED state?')) {
                      resetCircuitMutation.mutate();
                    }
                  }}
                  disabled={resetCircuitMutation.isPending}
                  className="px-3 py-1 bg-surface-subtle hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-medium text-slate-700 dark:text-slate-200 border border-surface-border rounded transition-colors shadow-sm"
                >
                  Force Reset (CLOSED)
                </button>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3 bg-surface-subtle rounded border border-surface-border">
                <span className="text-slate-500 dark:text-slate-400 block mb-1">TOTAL CALLS</span>
                <span className="text-slate-900 dark:text-white font-bold text-base">
                  {health.circuit_breaker.total_calls.toLocaleString()}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded border border-surface-border">
                <span className="text-slate-500 dark:text-slate-400 block mb-1">SUCCESSFUL</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-bold text-base">
                  {health.circuit_breaker.successful_calls.toLocaleString()}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded border border-surface-border">
                <span className="text-slate-500 dark:text-slate-400 block mb-1">FAILED</span>
                <span className="text-rose-600 dark:text-rose-400 font-bold text-base">
                  {health.circuit_breaker.failed_calls}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded border border-surface-border">
                <span className="text-slate-500 dark:text-slate-400 block mb-1">REJECTED (FAST FAIL)</span>
                <span className="text-amber-600 dark:text-amber-400 font-bold text-base">
                  {health.circuit_breaker.rejected_calls}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
