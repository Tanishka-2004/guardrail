import { create } from 'zustand';

export type Theme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  initTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  // Default to 'light' (White & Blue as requested)
  theme: ((typeof window !== 'undefined' && localStorage.getItem('guardrail_theme')) as Theme) || 'light',

  toggleTheme: () => {
    const nextTheme: Theme = get().theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('guardrail_theme', nextTheme);
    if (nextTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme: nextTheme });
  },

  setTheme: (theme: Theme) => {
    localStorage.setItem('guardrail_theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme });
  },

  initTheme: () => {
    const saved = (localStorage.getItem('guardrail_theme') as Theme) || 'light';
    if (saved === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme: saved });
  },
}));
