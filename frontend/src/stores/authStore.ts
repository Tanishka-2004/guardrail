import { create } from 'zustand';
import { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  initAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('guardrail_token'),
  isAuthenticated: !!localStorage.getItem('guardrail_token'),

  setAuth: (user, token) => {
    localStorage.setItem('guardrail_token', token);
    localStorage.setItem('guardrail_user', JSON.stringify(user));
    set({ user, token, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('guardrail_token');
    localStorage.removeItem('guardrail_user');
    set({ user: null, token: null, isAuthenticated: false });
  },

  initAuth: () => {
    const token = localStorage.getItem('guardrail_token');
    const userStr = localStorage.getItem('guardrail_user');
    if (token && userStr) {
      try {
        // Inspect token expiration if JWT
        const parts = token.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          if (payload.exp && payload.exp * 1000 < Date.now()) {
            // Expired token
            localStorage.removeItem('guardrail_token');
            localStorage.removeItem('guardrail_user');
            set({ user: null, token: null, isAuthenticated: false });
            return;
          }
        }
        const user = JSON.parse(userStr);
        set({ user, token, isAuthenticated: true });
      } catch {
        localStorage.removeItem('guardrail_token');
        localStorage.removeItem('guardrail_user');
        set({ user: null, token: null, isAuthenticated: false });
      }
    } else {
      set({ user: null, token: null, isAuthenticated: false });
    }
  },
}));
