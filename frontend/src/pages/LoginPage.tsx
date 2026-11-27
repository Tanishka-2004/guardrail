import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useThemeStore } from '../stores/themeStore';
import { api } from '../services/api';
import { Shield, Lock, Mail, AlertCircle, ArrowRight, Sun, Moon } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { theme, toggleTheme } = useThemeStore();

  const [email, setEmail] = useState('analyst@guardrail.io');
  const [password, setPassword] = useState('Password123!');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await api.login(email, password);
      setAuth(res.user, res.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const setDemoUser = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('Password123!');
    setError(null);
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background p-4 select-none relative">
      {/* Theme Toggle Button */}
      <div className="absolute top-6 right-6">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-border bg-surface text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 text-xs font-medium shadow-sm transition-colors"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? (
            <>
              <Moon className="w-4 h-4 text-slate-600" />
              <span>Dark Mode</span>
            </>
          ) : (
            <>
              <Sun className="w-4 h-4 text-amber-400" />
              <span>Light Mode</span>
            </>
          )}
        </button>
      </div>

      <div className="w-full max-w-md bg-surface border border-surface-border rounded-2xl p-8 shadow-xl dark:shadow-2xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 shadow-sm">
            <Shield className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black font-mono tracking-wider text-slate-900 dark:text-white">GUARDRAIL</h1>
          <p className="text-xs text-slate-600 dark:text-slate-400">Fraud Alert Triage Console & Distributed Stream Engine</p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded-lg flex items-center gap-2 text-rose-700 dark:text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Work Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@guardrail.io"
                className="w-full bg-surface-subtle border border-surface-border rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-surface-subtle border border-surface-border rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors shadow-md shadow-blue-500/20"
          >
            <span>{isLoading ? 'Authenticating...' : 'Sign In to Console'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Demo Sandbox Quick-Fill */}
        <div className="pt-4 border-t border-surface-border space-y-2.5">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
            <span className="uppercase tracking-wider font-semibold">Demo Sandbox Profiles</span>
            <span className="text-[10px] text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/50 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800 font-semibold">One-Click Fill</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setDemoUser('analyst@guardrail.io')}
              className="p-2.5 rounded-lg bg-surface-subtle hover:bg-blue-50 dark:hover:bg-slate-800 border border-surface-border text-slate-800 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-left transition-colors"
            >
              <div className="font-semibold">Fraud Analyst</div>
              <div className="text-[10px] text-slate-500 font-mono">analyst@guardrail.io</div>
            </button>

            <button
              type="button"
              onClick={() => setDemoUser('senior@guardrail.io')}
              className="p-2.5 rounded-lg bg-surface-subtle hover:bg-blue-50 dark:hover:bg-slate-800 border border-surface-border text-slate-800 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-left transition-colors"
            >
              <div className="font-semibold">Senior Analyst</div>
              <div className="text-[10px] text-slate-500 font-mono">senior@guardrail.io</div>
            </button>

            <button
              type="button"
              onClick={() => setDemoUser('supervisor@guardrail.io')}
              className="p-2.5 rounded-lg bg-surface-subtle hover:bg-blue-50 dark:hover:bg-slate-800 border border-surface-border text-slate-800 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-left transition-colors"
            >
              <div className="font-semibold">Fraud Supervisor</div>
              <div className="text-[10px] text-slate-500 font-mono">supervisor@guardrail.io</div>
            </button>

            <button
              type="button"
              onClick={() => setDemoUser('admin@guardrail.io')}
              className="p-2.5 rounded-lg bg-surface-subtle hover:bg-blue-50 dark:hover:bg-slate-800 border border-surface-border text-slate-800 dark:text-slate-200 hover:text-blue-600 dark:hover:text-blue-400 text-left transition-colors"
            >
              <div className="font-semibold">Administrator</div>
              <div className="text-[10px] text-slate-500 font-mono">admin@guardrail.io</div>
            </button>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 text-center font-mono pt-1">
            Production builds enforce SAML 2.0 / OIDC enterprise single sign-on.
          </p>
        </div>
      </div>
    </div>
  );
};
