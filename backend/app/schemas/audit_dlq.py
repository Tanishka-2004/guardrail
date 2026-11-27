from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: str
    alert_id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    previous_state: Dict[str, Any] = {}
    new_state: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    timestamp: datetime

    class Config:
        from_attributes = True

class DeadLetterResponse(BaseModel):
    id: str
    original_event_id: str
    topic: str
    partition: int
    offset: int
    payload: Dict[str, Any]
    error_type: str
    error_message: str
    retry_count: int
    replay_status: str
    created_at: datetime
    replayed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DLQReplayResponse(BaseModel):
    event_id: str
    replay_status: str
    message: str
    replay_count: int
