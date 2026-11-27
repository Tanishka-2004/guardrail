import React, { useEffect } from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Sidebar } from '../components/Sidebar';
import { useAuthStore } from '../stores/authStore';
import { useWSStore } from '../stores/wsStore';

export const AppLayout: React.FC = () => {
  const { isAuthenticated, token } = useAuthStore();
  const { setConnected, setConnecting, addEvent } = useWSStore();

  useEffect(() => {
    if (!isAuthenticated || !token) return;

    let ws: WebSocket | null = null;
    let reconnectTimer: any = null;
    let pingInterval: any = null;

    const connectWS = () => {
      setConnecting(true);
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/alerts?token=${token}`;

      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setConnected(true);
          setConnecting(false);
          // Heartbeat ping every 25 seconds
          pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 25000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event_type && data.event_type !== 'connection.established') {
              addEvent(data);
            }
          } catch {
            // Raw string message like pong
          }
        };

        ws.onclose = () => {
          setConnected(false);
          setConnecting(false);
          if (pingInterval) clearInterval(pingInterval);
          // Auto-reconnect after 3 seconds
          reconnectTimer = setTimeout(connectWS, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch {
        setConnected(false);
        setConnecting(false);
        reconnectTimer = setTimeout(connectWS, 3000);
      }
    };

    connectWS();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (pingInterval) clearInterval(pingInterval);
      if (ws) ws.close();
    };
  }, [isAuthenticated, token, setConnected, setConnecting, addEvent]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-background p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
