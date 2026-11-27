export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'NEW' | 'CLAIMED' | 'UNDER_REVIEW' | 'ESCALATED' | 'RESOLVED' | 'REOPENED';
export type Priority = 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW';
export type SLAStatus = 'HEALTHY' | 'WARNING' | 'BREACHED';
export type UserRole = 'ANALYST' | 'SENIOR_ANALYST' | 'SUPERVISOR' | 'ADMIN';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  team: string;
  is_active: boolean;
  workload_limit: number;
  created_at?: string;
}

export interface FraudAlert {
  id: string;
  event_id: string;
  transaction_id: string;
  customer_id: string;
  merchant_id: string;
  transaction_amount: number;
  currency: string;
  transaction_type: string;
  transaction_timestamp: string;
  fraud_score: number;
  risk_level: RiskLevel;
  fraud_reason: string;
  status: AlertStatus;
  priority: Priority;
  sla_deadline: string;
  sla_duration_minutes: number;
  sla_time_remaining_seconds?: number;
  sla_percent_consumed?: number;
  sla_status?: SLAStatus;
  assigned_analyst_id?: string;
  claimed_by?: string;
  claimed_at?: string;
  claim_expires_at?: string;
  is_claim_expired?: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  resolution_reason?: string;
  notes?: string;
  replay_count: number;
  source_event_metadata: Record<string, any>;
}

export interface AlertListResponse {
  items: FraudAlert[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface AuditLog {
  id: string;
  alert_id: string;
  actor_id?: string;
  actor_name?: string;
  action: string;
  previous_state: Record<string, any>;
  new_state: Record<string, any>;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface DeadLetterEvent {
  id: string;
  original_event_id: string;
  topic: string;
  partition: number;
  offset: number;
  payload: Record<string, any>;
  error_type: string;
  error_message: string;
  retry_count: number;
  replay_status: string;
  created_at: string;
  replayed_at?: string;
}

export interface DashboardMetrics {
  total_active_alerts: number;
  critical_alerts: number;
  high_risk_alerts: number;
  sla_breaches: number;
  sla_warnings: number;
  avg_resolution_time_minutes: number;
  alerts_processed_today: number;
  active_analysts: number;
  queue_throughput_per_minute: number;
  circuit_breaker_state: string;
  dlq_pending_count: number;
}

export interface QueueSummary {
  by_status: Record<string, number>;
  by_risk_level: Record<string, number>;
  by_priority: Record<string, number>;
  volume_over_time: Array<{ hour: string; count: number }>;
  sla_compliance_rate_percent: number;
}

export interface SLASummary {
  healthy: number;
  warning: number;
  breached: number;
  average_time_remaining_minutes: number;
  breach_rate_percent: number;
  breaches_by_priority: Record<string, number>;
}

export interface AnalystWorkload {
  id: string;
  name: string;
  email: string;
  role: string;
  team: string;
  active_claims: number;
  workload_limit: number;
  resolved_today: number;
  total_resolved: number;
  avg_resolution_time_minutes: number;
  sla_compliance_rate_percent: number;
}

export interface DependencyHealth {
  name: string;
  status: string;
  latency_ms?: number;
  details?: string;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  version: string;
  dependencies: DependencyHealth[];
  circuit_breaker: Record<string, any>;
  active_websocket_connections: number;
}
