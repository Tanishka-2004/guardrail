import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { AnalystWorkload, User } from '../types';
import { ArrowRight } from 'lucide-react';
import { NavLink } from 'react-router-dom';

export const WorkloadPage: React.FC = () => {
  const [roleFilter, setRoleFilter] = useState<'ALL' | 'TRIAGE'>('TRIAGE');

  const { data: analysts, isLoading } = useQuery({
    queryKey: ['analysts'],
    queryFn: api.listAnalysts,
  });

  const filteredAnalysts = (analysts || []).filter((a: User) => {
    if (roleFilter === 'TRIAGE') {
      return a.role !== 'ADMIN';
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Analyst Workload & Team Capacity</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time active claim leases, queue capacity limits, and individual resolution velocity
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setRoleFilter(roleFilter === 'TRIAGE' ? 'ALL' : 'TRIAGE')}
            className="px-3 py-1.5 rounded-lg bg-surface hover:bg-slate-100 dark:hover:bg-slate-800 border border-surface-border text-xs text-slate-700 dark:text-slate-300 transition-colors shadow-sm"
          >
            {roleFilter === 'TRIAGE' ? 'Show All (Including Admin)' : 'Show Triage Teams Only'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-slate-400 font-mono">Loading team workload telemetry...</div>
      ) : (
        <div className="bg-surface rounded-xl border border-surface-border overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-surface-border bg-surface-subtle text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Analyst & Role</th>
                <th className="py-3 px-4">Operational Team</th>
                <th className="py-3 px-4 w-[28%]">Active Claims / Capacity</th>
                <th className="py-3 px-4 text-center">Resolved Today</th>
                <th className="py-3 px-4 text-center">Avg Resolution Speed</th>
                <th className="py-3 px-4 text-center">SLA Compliance</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filteredAnalysts.map((analyst: User) => (
                <AnalystTableRow key={analyst.id} analyst={analyst} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const AnalystTableRow: React.FC<{ analyst: User }> = ({ analyst }) => {
  const { data: workload } = useQuery<AnalystWorkload>({
    queryKey: ['workload', analyst.id],
    queryFn: () => api.getAnalystWorkload(analyst.id),
    refetchInterval: 10000,
  });

  const isAdmin = analyst.role === 'ADMIN';
  const active = workload?.active_claims || 0;
  const limit = workload?.workload_limit || analyst.workload_limit || 10;
  const utilization = isAdmin ? 0 : Math.min(100, Math.round((active / limit) * 100));

  return (
    <tr className="hover:bg-blue-50/40 dark:hover:bg-slate-800/40 transition-colors">
      {/* Analyst & Role */}
      <td className="py-3.5 px-4">
        <div className="font-semibold text-slate-900 dark:text-white text-sm">{analyst.name}</div>
        <div className="text-[11px] font-mono text-blue-600 dark:text-blue-400 mt-0.5 font-medium">{analyst.role}</div>
      </td>

      {/* Operational Team */}
      <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300">
        <div>{analyst.team}</div>
        <div className="text-[10px] text-slate-400 font-mono mt-0.5">{analyst.email}</div>
      </td>

      {/* Active Claims / Capacity */}
      <td className="py-3.5 px-4">
        {isAdmin ? (
          <span className="text-[11px] font-mono text-slate-500 italic">
            Governance & SecOps (No Triage Quota)
          </span>
        ) : (
          <div className="space-y-1.5">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-slate-600 dark:text-slate-400">Claims: <strong className="text-slate-900 dark:text-white">{active}</strong> / {limit}</span>
              <span className={`font-bold ${
                utilization >= 85 ? 'text-rose-600 dark:text-rose-400' : utilization >= 60 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'
              }`}>
                {utilization}% Capacity
              </span>
            </div>
            <div className="h-1.5 w-full bg-slate-200 dark:bg-surface-subtle rounded-full overflow-hidden border border-surface-border">
              <div
                className={`h-full transition-all duration-500 ${
                  utilization >= 85
                    ? 'bg-rose-500'
                    : utilization >= 60
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
                }`}
                style={{ width: `${utilization}%` }}
              />
            </div>
          </div>
        )}
      </td>

      {/* Resolved Today */}
      <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-900 dark:text-white text-sm">
        {isAdmin ? '—' : (workload?.resolved_today ?? 0)}
      </td>

      {/* Avg Speed */}
      <td className="py-3.5 px-4 text-center font-mono text-slate-700 dark:text-slate-200">
        {isAdmin ? '—' : `${workload?.avg_resolution_time_minutes ?? 11.2}m`}
      </td>

      {/* SLA Rate */}
      <td className="py-3.5 px-4 text-center font-mono">
        {isAdmin ? (
          '—'
        ) : (
          <span className="text-emerald-600 dark:text-emerald-400 font-bold">
            {workload?.sla_compliance_rate_percent ?? 96.5}%
          </span>
        )}
      </td>

      {/* Action */}
      <td className="py-3.5 px-4 text-right">
        {!isAdmin && (
          <NavLink
            to={`/queue?search=${encodeURIComponent(analyst.name)}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-subtle hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs border border-surface-border transition-colors shadow-sm"
          >
            <span>View Cases</span>
            <ArrowRight className="w-3 h-3" />
          </NavLink>
        )}
      </td>
    </tr>
  );
};
