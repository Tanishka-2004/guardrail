import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class AlertAuditLog(Base):
    __tablename__ = "alert_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("fraud_alerts.id", ondelete="CASCADE"), index=True, nullable=False)
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(100), nullable=True)
    action = Column(String(50), index=True, nullable=False)
    previous_state = Column(JSON, default=dict, nullable=False)
    new_state = Column(JSON, default=dict, nullable=False)
    metadata_info = Column("metadata", JSON, default=dict, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    alert = relationship("FraudAlert", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_alert_timestamp", "alert_id", "timestamp"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "action": self.action,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "metadata": self.metadata_info,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
