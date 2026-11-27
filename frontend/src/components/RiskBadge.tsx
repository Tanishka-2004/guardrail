import React from 'react';
import { RiskLevel, Priority } from '../types';
import { ShieldAlert, ShieldCheck, AlertCircle, AlertOctagon } from 'lucide-react';

export const RiskBadge: React.FC<{ level: RiskLevel; score?: number }> = ({ level, score }) => {
  const configs = {
    CRITICAL: {
      bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/15 dark:border-rose-500/30 dark:text-rose-400 font-semibold',
      icon: AlertOctagon,
      label: 'Critical',
    },
    HIGH: {
      bg: 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/15 dark:border-orange-500/30 dark:text-orange-400 font-semibold',
      icon: ShieldAlert,
      label: 'High',
    },
    MEDIUM: {
      bg: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/15 dark:border-amber-500/30 dark:text-amber-300 font-medium',
      icon: AlertCircle,
      label: 'Medium',
    },
    LOW: {
      bg: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-cyan-500/15 dark:border-cyan-500/30 dark:text-cyan-300 font-medium',
      icon: ShieldCheck,
      label: 'Low',
    },
  };

  const c = configs[level] || configs.LOW;
  const Icon = c.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${c.bg}`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{c.label}</span>
      {score !== undefined && (
        <span className="font-mono text-[11px] opacity-80 border-l border-current/20 pl-1">
          {score.toFixed(0)}
        </span>
      )}
    </span>
  );
};

export const PriorityBadge: React.FC<{ priority: Priority }> = ({ priority }) => {
  const styles: Record<Priority, string> = {
    P1_CRITICAL: 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/70 dark:border-rose-600/50 dark:text-rose-300 font-bold',
    P2_HIGH: 'bg-orange-50 text-orange-700 border-orange-300 dark:bg-orange-950/60 dark:border-orange-600/50 dark:text-orange-300 font-semibold',
    P3_MEDIUM: 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/50 dark:border-amber-600/40 dark:text-amber-300 font-medium',
    P4_LOW: 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-400',
  };

  const labels: Record<Priority, string> = {
    P1_CRITICAL: 'P1 CRITICAL',
    P2_HIGH: 'P2 HIGH',
    P3_MEDIUM: 'P3 MEDIUM',
    P4_LOW: 'P4 LOW',
  };

  return (
    <span className={`inline-block px-1.5 py-0.5 text-[10px] font-mono tracking-wider rounded border ${styles[priority] || styles.P4_LOW}`}>
      {labels[priority] || priority}
    </span>
  );
};
