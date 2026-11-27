import React from 'react';
import { useAuthStore } from '../stores/authStore';
import { useWSStore } from '../stores/wsStore';
import { useThemeStore } from '../stores/themeStore';
import { Shield, LogOut, Sun, Moon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { isConnected } = useWSStore();
  const { theme, toggleTheme } = useThemeStore();

  return (
    <header className="h-14 border-b border-surface-border bg-surface px-6 flex items-center justify-between sticky top-0 z-30 transition-colors shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-500/30 px-2.5 py-1 rounded-lg">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <span className="font-bold text-sm tracking-wide text-slate-900 dark:text-white font-mono">GUARDRAIL</span>
          <span className="text-[10px] text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/60 px-1.5 py-0.5 rounded font-semibold uppercase">
            Triage Console
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Dark Mode Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode (White & Blue)'}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors bg-surface-subtle hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border-surface-border"
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-3.5 h-3.5 text-blue-600" />
              <span className="font-sans font-semibold">Dark Mode</span>
            </>
          ) : (
            <>
              <Sun className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-sans font-semibold">Light Mode</span>
            </>
          )}
        </button>

        {/* Live WebSocket Connection Pill */}
        <div
          className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${
            isConnected
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30'
              : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30'
          }`}
          title={isConnected ? 'Real-time WebSocket feed active' : 'WebSocket disconnected - reconnecting...'}
        >
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
          <span>{isConnected ? 'LIVE FEED' : 'DISCONNECTED'}</span>
        </div>

        {/* User Info & Actions */}
        {user && (
          <div className="flex items-center gap-3 pl-3 border-l border-surface-border">
            <div className="flex flex-col text-right">
              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">{user.name}</span>
              <span className="text-[10px] font-mono text-blue-600 dark:text-blue-400 uppercase tracking-wider font-semibold">
                {user.role}
              </span>
            </div>
            <button
              onClick={logout}
              title="Logout"
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
