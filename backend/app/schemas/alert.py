from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class FraudAlertResponse(BaseModel):
    id: str
    event_id: str
    transaction_id: str
    customer_id: str
    merchant_id: str
    transaction_amount: float
    currency: str
    transaction_type: str
    transaction_timestamp: datetime
    fraud_score: float
    risk_level: str
    fraud_reason: str
    status: str
    priority: str
    sla_deadline: datetime
    sla_duration_minutes: int
    sla_time_remaining_seconds: Optional[int] = None
    sla_percent_consumed: Optional[float] = None
    sla_status: Optional[str] = "HEALTHY"
    assigned_analyst_id: Optional[str] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[datetime] = None
    claim_expires_at: Optional[datetime] = None
    is_claim_expired: bool = False
    version: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None
    notes: Optional[str] = None
    replay_count: int
    source_event_metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class AlertListResponse(BaseModel):
    items: List[FraudAlertResponse]
    total: int
    page: int
    limit: int
    pages: int

class AlertClaimRequest(BaseModel):
    lease_duration_seconds: Optional[int] = Field(None, ge=60, le=3600, description="Custom lease timeout in seconds")

class AlertReassignRequest(BaseModel):
    target_analyst_id: str = Field(..., description="ID of the analyst to assign this alert to")
    reason: Optional[str] = Field(None, description="Reason for reassigning")

class AlertResolveRequest(BaseModel):
    resolution_reason: str = Field(..., min_length=3, max_length=255, description="CONFIRMED_FRAUD, FALSE_POSITIVE, USER_ERROR, etc.")
    notes: Optional[str] = Field(None, description="Detailed closing investigation notes")

class AlertReopenRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Reason for reopening alert")

class AlertNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, description="Investigation note content")
