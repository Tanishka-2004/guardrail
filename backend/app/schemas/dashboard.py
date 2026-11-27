from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DashboardMetricsResponse(BaseModel):
    total_active_alerts: int
    critical_alerts: int
    high_risk_alerts: int
    sla_breaches: int
    sla_warnings: int
    avg_resolution_time_minutes: float
    alerts_processed_today: int
    active_analysts: int
    queue_throughput_per_minute: float
    circuit_breaker_state: str
    dlq_pending_count: int

class QueueSummaryResponse(BaseModel):
    by_status: Dict[str, int]
    by_risk_level: Dict[str, int]
    by_priority: Dict[str, int]
    volume_over_time: List[Dict[str, Any]]
    sla_compliance_rate_percent: float

class SLASummaryResponse(BaseModel):
    healthy: int
    warning: int
    breached: int
    average_time_remaining_minutes: float
    breach_rate_percent: float
    breaches_by_priority: Dict[str, int]

class AnalystWorkloadResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    team: str
    active_claims: int
    workload_limit: int
    resolved_today: int
    avg_resolution_time_minutes: float
    sla_compliance_rate_percent: float

class DependencyHealth(BaseModel):
    name: str
    status: str  # UP, DOWN, DEGRADED
    latency_ms: Optional[float] = None
    details: Optional[str] = None

class SystemHealthResponse(BaseModel):
    status: str  # HEALTHY, DEGRADED, CRITICAL
    timestamp: str
    version: str
    dependencies: List[DependencyHealth]
    circuit_breaker: Dict[str, Any]
    active_websocket_connections: int
