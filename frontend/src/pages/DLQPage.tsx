import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { DeadLetterEvent } from '../types';
import { RefreshCw, X } from 'lucide-react';

export const DLQPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedEvent, setSelectedEvent] = useState<DeadLetterEvent | null>(null);

  const { data: dlqEvents, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dlqEvents'],
    queryFn: () => api.listDLQ(),
    refetchInterval: 10000,
    retry: 1,
  });

  const replayMutation = useMutation({
    mutationFn: (eventId: string) => api.replayDLQ(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlqEvents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  const replayAllMutation = useMutation({
    mutationFn: () => api.replayAllDLQ(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dlqEvents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  const pendingEvents = dlqEvents?.filter((e: DeadLetterEvent) => e.replay_status === 'PENDING') || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Dead Letter Queue (DLQ) Management</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Poison message isolation, schema validation failure inspection, and operator replay controls
          </p>
        </div>

        <button
          onClick={() => replayAllMutation.mutate()}
          disabled={replayAllMutation.isPending || pendingEvents.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-xs font-semibold text-white transition-colors shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${replayAllMutation.isPending ? 'animate-spin' : ''}`} />
          <span>Replay Pending ({pendingEvents.length})</span>
        </button>
      </div>

      {/* DLQ Events Table */}
      <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-surface-border bg-surface-subtle text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              <th className="py-2.5 px-3">Event ID</th>
              <th className="py-2.5 px-3">Topic / Partition</th>
              <th className="py-2.5 px-3">Failure Reason</th>
              <th className="py-2.5 px-3">Retries</th>
              <th className="py-2.5 px-3">DLQ Status</th>
              <th className="py-2.5 px-3">Timestamp</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border text-xs">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-400 font-mono">
                  <div className="flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
                    <span>Loading dead letter queue...</span>
                  </div>
                </td>
              </tr>
            ) : isError ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-rose-500 font-mono">
                  <div className="space-y-2">
                    <div>Failed to load Dead Letter Queue: {(error as any)?.message || 'Unauthorized or network error'}</div>
                    <button
                      onClick={() => refetch()}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                </td>
              </tr>
            ) : dlqEvents?.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-slate-400 font-mono">
                  Dead Letter Queue is clear. No poison events detected.
                </td>
              </tr>
            ) : (
              dlqEvents?.map((event: DeadLetterEvent) => {
                const isPending = event.replay_status === 'PENDING';
                const isSuccess = event.replay_status === 'SUCCEEDED' || event.replay_status === 'REPLAYED';
                const isQuarantine = event.replay_status === 'FAILED_VALIDATION';
                return (
                  <tr key={event.id} className="hover:bg-blue-50/40 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-3 font-mono font-bold text-blue-600 dark:text-blue-400">
                      {event.original_event_id}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-500 dark:text-slate-400">
                      {event.topic}:{event.partition}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-rose-600 dark:text-rose-400">{event.error_type}</div>
                      <div className="text-[11px] text-slate-600 dark:text-slate-400 truncate max-w-xs">{event.error_message}</div>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-700 dark:text-slate-300">{event.retry_count}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border ${
                          isSuccess
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30'
                            : isPending
                            ? 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30'
                            : isQuarantine
                            ? 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30'
                            : 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/30'
                        }`}
                      >
                        {event.replay_status}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-500 dark:text-slate-400 text-[11px]">
                      {new Date(event.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedEvent(event)}
                          className="px-2.5 py-1 rounded bg-surface-subtle hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs border border-surface-border shadow-sm"
                        >
                          Inspect
                        </button>
                        {isPending && (
                          <button
                            onClick={() => replayMutation.mutate(event.original_event_id)}
                            disabled={replayMutation.isPending}
                            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-1 shadow-sm"
                          >
                            <RefreshCw className="w-3 h-3" />
                            Replay
                          </button>
                        )}
                        {isQuarantine && (
                          <span className="text-[10px] text-slate-500 font-mono italic px-1">
                            Quarantined
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Payload Inspection Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="bg-surface border border-surface-border rounded-xl p-6 w-full max-w-2xl space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Dead Letter Event Forensics</h3>
                <span className="text-xs font-mono text-blue-600 dark:text-blue-400">{selectedEvent.original_event_id}</span>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 dark:text-slate-400 block mb-1 font-mono">ERROR MESSAGE</span>
                <p className="p-2.5 bg-rose-50 dark:bg-rose-950/20 rounded border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 font-mono">
                  {selectedEvent.error_message}
                </p>
              </div>

              <div>
                <span className="text-slate-500 dark:text-slate-400 block mb-1 font-mono">ORIGINAL TRANSACTION PAYLOAD</span>
                <pre className="p-3 bg-surface-subtle rounded border border-surface-border text-slate-800 dark:text-slate-200 font-mono text-[11px] overflow-x-auto max-h-60">
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
