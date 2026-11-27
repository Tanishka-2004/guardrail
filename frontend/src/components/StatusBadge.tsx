import React from 'react';
import { AlertStatus } from '../types';

export const StatusBadge: React.FC<{ status: AlertStatus; claimedBy?: string | null }> = ({
  status,
  claimedBy,
}) => {
  const configs: Record<AlertStatus, { bg: string; dot: string; label: string }> = {
    NEW: {
      bg: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20',
      dot: 'bg-blue-500',
      label: 'New Unclaimed',
    },
    CLAIMED: {
      bg: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30',
      dot: 'bg-indigo-500',
      label: claimedBy ? `Claimed (${claimedBy})` : 'Claimed',
    },
    UNDER_REVIEW: {
      bg: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-500/15 dark:text-purple-300 dark:border-purple-500/30',
      dot: 'bg-purple-500',
      label: 'Under Review',
    },
    ESCALATED: {
      bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/15 dark:text-rose-400 dark:border-rose-500/30',
      dot: 'bg-rose-500 animate-ping',
      label: 'Escalated',
    },
    RESOLVED: {
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20',
      dot: 'bg-emerald-500',
      label: 'Resolved',
    },
    REOPENED: {
      bg: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30',
      dot: 'bg-amber-500',
      label: 'Reopened',
    },
  };

  const c = configs[status] || configs.NEW;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${c.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      <span className="truncate max-w-[150px]">{c.label}</span>
    </span>
  );
};
