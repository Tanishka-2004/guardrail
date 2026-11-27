import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ListFilter, 
  Users, 
  Archive, 
  ActivitySquare, 
  Radio
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

export const Sidebar: React.FC = () => {
  const { user } = useAuthStore();

  const navItems = [
    { to: '/', label: 'Operations Dashboard', icon: LayoutDashboard },
    { to: '/queue', label: 'Live Alert Queue', icon: ListFilter },
    { to: '/workload', label: 'Analyst Workload', icon: Users },
    { to: '/dlq', label: 'Failed Events (DLQ)', icon: Archive },
    { to: '/system', label: 'System Health', icon: ActivitySquare },
  ];

  return (
    <aside className="w-64 border-r border-surface-border bg-surface flex flex-col justify-between p-3 select-none transition-colors">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-mono font-semibold tracking-wider text-slate-500 uppercase">
          Fraud Operations
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 border border-blue-200 dark:border-blue-500/30 font-semibold shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="p-3 bg-surface-subtle rounded-lg border border-surface-border">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Real-time Stream</span>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
          WebSocket connected. Processing transaction fraud alerts.
        </p>
      </div>
    </aside>
  );
};
