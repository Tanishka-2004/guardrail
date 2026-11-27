import { 
  User, 
  FraudAlert, 
  AlertListResponse, 
  AuditLog, 
  DeadLetterEvent, 
  DashboardMetrics, 
  QueueSummary, 
  SLASummary, 
  AnalystWorkload, 
  SystemHealth 
} from '../types';

const API_BASE = '/api/v1';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('guardrail_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...options.headers,
    },
  });

  if (!res.ok) {
    if (res.status === 401 && endpoint !== '/auth/login') {
      localStorage.removeItem('guardrail_token');
      localStorage.removeItem('guardrail_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    let errorDetail = 'API request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = await res.text() || res.statusText;
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => request<User>('/auth/me'),

  // Alerts
  listAlerts: (params: Record<string, any> = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        searchParams.append(k, String(v));
      }
    });
    return request<AlertListResponse>(`/alerts?${searchParams.toString()}`);
  },
  getAlert: (id: string) => request<FraudAlert>(`/alerts/${id}`),
  claimAlert: (id: string, leaseDuration?: number) =>
    request<FraudAlert>(`/alerts/${id}/claim`, {
      method: 'POST',
      body: JSON.stringify({ lease_duration_seconds: leaseDuration }),
    }),
  releaseAlert: (id: string) =>
    request<FraudAlert>(`/alerts/${id}/release`, { method: 'POST' }),
  renewClaim: (id: string, leaseDuration?: number) =>
    request<FraudAlert>(`/alerts/${id}/renew-claim`, {
      method: 'POST',
      body: JSON.stringify({ lease_duration_seconds: leaseDuration }),
    }),
  reassignAlert: (id: string, targetAnalystId: string, reason?: string) =>
    request<FraudAlert>(`/alerts/${id}/reassign`, {
      method: 'POST',
      body: JSON.stringify({ target_analyst_id: targetAnalystId, reason }),
    }),
  resolveAlert: (id: string, resolutionReason: string, notes?: string) =>
    request<FraudAlert>(`/alerts/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_reason: resolutionReason, notes }),
    }),
  reopenAlert: (id: string, reason: string) =>
    request<FraudAlert>(`/alerts/${id}/reopen`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  addNote: (id: string, note: string) =>
    request<FraudAlert>(`/alerts/${id}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  getAuditTrail: (id: string) => request<AuditLog[]>(`/alerts/${id}/audit`),
  ingestTransaction: (eventData: Record<string, any>) =>
    request<{ status: string; event_id: string; correlation_id: string }>('/alerts/ingest', {
      method: 'POST',
      body: JSON.stringify(eventData),
    }),

  // Analysts
  listAnalysts: () => request<User[]>('/analysts'),
  getAnalystWorkload: (id: string) => request<AnalystWorkload>(`/analysts/${id}/workload`),

  // Dashboard
  getMetrics: () => request<DashboardMetrics>('/dashboard/metrics'),
  getQueueSummary: () => request<QueueSummary>('/dashboard/queue-summary'),
  getSLASummary: () => request<SLASummary>('/dashboard/sla-summary'),

  // DLQ
  listDLQ: (status?: string) =>
    request<DeadLetterEvent[]>(`/dlq${status ? `?status=${status}` : ''}`),
  replayDLQ: (eventId: string) =>
    request<{ event_id: string; replay_status: string; message: string }>(`/dlq/${eventId}/replay`, {
      method: 'POST',
    }),
  replayAllDLQ: () => request<{ total_found: number; replayed: number; failed: number }>('/dlq/replay-all', {
    method: 'POST',
  }),

  // System
  getSystemHealth: () => request<SystemHealth>('/system/health'),
  resetCircuitBreaker: () => request<{ status: string }>('/system/circuit-breaker/reset', { method: 'POST' }),
};
