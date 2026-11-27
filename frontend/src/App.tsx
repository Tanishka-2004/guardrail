import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './layouts/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { QueuePage } from './pages/QueuePage';
import { WorkloadPage } from './pages/WorkloadPage';
import { DLQPage } from './pages/DLQPage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { useThemeStore } from './stores/themeStore';
import { useAuthStore } from './stores/authStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  const initTheme = useThemeStore((state) => state.initTheme);
  const initAuth = useAuthStore((state) => state.initAuth);

  useEffect(() => {
    initTheme();
    initAuth();
  }, [initTheme, initAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="queue" element={<QueuePage />} />
            <Route path="workload" element={<WorkloadPage />} />
            <Route path="dlq" element={<DLQPage />} />
            <Route path="system" element={<SystemHealthPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
