import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';
import { SLAStatus } from '../types';

interface SLACountdownProps {
  deadline: string;
  isResolved?: boolean;
  slaStatus?: SLAStatus;
}

export const SLACountdown: React.FC<SLACountdownProps> = ({ deadline, isResolved, slaStatus }) => {
  const [timeLeft, setTimeLeft] = useState<{
    totalSeconds: number;
    hours: number;
    minutes: number;
    seconds: number;
    isBreached: boolean;
  }>({ totalSeconds: 0, hours: 0, minutes: 0, seconds: 0, isBreached: false });

  useEffect(() => {
    if (isResolved) return;

    const calculate = () => {
      const now = new Date().getTime();
      const target = new Date(deadline).getTime();
      const diff = Math.floor((target - now) / 1000);

      const isBreached = diff <= 0;
      const absDiff = Math.abs(diff);
      const hours = Math.floor(absDiff / 3600);
      const minutes = Math.floor((absDiff % 3600) / 60);
      const seconds = absDiff % 60;

      setTimeLeft({ totalSeconds: diff, hours, minutes, seconds, isBreached });
    };

    calculate();
    const timer = setInterval(calculate, 1000);
    return () => clearInterval(timer);
  }, [deadline, isResolved]);

  if (isResolved) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20">
        Resolved
      </span>
    );
  }

  const { hours, minutes, seconds, isBreached } = timeLeft;
  const formatted = `${hours > 0 ? `${hours}h ` : ''}${minutes}m ${seconds}s`;

  if (isBreached || slaStatus === 'BREACHED') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-500/20 dark:text-rose-400 dark:border-rose-500/30 animate-pulse">
        <AlertTriangle className="w-3.5 h-3.5" />
        -{formatted} OVERDUE
      </span>
    );
  }

  const isWarning = minutes <= 15 && hours === 0;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium border ${
        isWarning
          ? 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30'
          : 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
      }`}
    >
      <Clock className="w-3.5 h-3.5 opacity-70" />
      {formatted}
    </span>
  );
};
