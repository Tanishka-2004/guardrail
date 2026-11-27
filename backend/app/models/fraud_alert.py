import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Idempotency identifier - unique constraint
    event_id = Column(String(128), unique=True, index=True, nullable=False)
    
    # Transaction attributes
    transaction_id = Column(String(128), index=True, nullable=False)
    customer_id = Column(String(128), index=True, nullable=False)
    merchant_id = Column(String(128), index=True, nullable=False)
    transaction_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    transaction_type = Column(String(50), default="PURCHASE", nullable=False)
    transaction_timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    # Fraud scoring & risk
    fraud_score = Column(Float, nullable=False)  # 0.0 - 100.0
    risk_level = Column(String(30), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    fraud_reason = Column(String(500), nullable=False)

    # Workflow & SLA
    status = Column(String(30), default="NEW", index=True, nullable=False)
    priority = Column(String(30), default="P3_MEDIUM", index=True, nullable=False)
    sla_deadline = Column(DateTime(timezone=True), index=True, nullable=False)
    sla_duration_minutes = Column(Integer, default=60, nullable=False)

    # Atomic claim locking
    assigned_analyst_id = Column(String(36), ForeignKey("analysts.id", ondelete="SET NULL"), nullable=True, index=True)
    claimed_by = Column(String(255), nullable=True)  # Name / Email of analyst
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    claim_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Concurrency control & audit
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_reason = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    replay_count = Column(Integer, default=0, nullable=False)
    source_event_metadata = Column(JSON, default=dict, nullable=False)

    # Relationships
    assigned_analyst = relationship("Analyst", back_populates="assigned_alerts")
    audit_logs = relationship("AlertAuditLog", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_fraud_alerts_status_priority", "status", "priority"),
        Index("ix_fraud_alerts_sla_status", "status", "sla_deadline"),
        Index("ix_fraud_alerts_claimed_expires", "claimed_by", "claim_expires_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "merchant_id": self.merchant_id,
            "transaction_amount": self.transaction_amount,
            "currency": self.currency,
            "transaction_type": self.transaction_type,
            "transaction_timestamp": self.transaction_timestamp.isoformat() if self.transaction_timestamp else None,
            "fraud_score": self.fraud_score,
            "risk_level": self.risk_level,
            "fraud_reason": self.fraud_reason,
            "status": self.status,
            "priority": self.priority,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_duration_minutes": self.sla_duration_minutes,
            "assigned_analyst_id": self.assigned_analyst_id,
            "claimed_by": self.claimed_by,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "claim_expires_at": self.claim_expires_at.isoformat() if self.claim_expires_at else None,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_reason": self.resolution_reason,
            "notes": self.notes,
            "replay_count": self.replay_count,
            "source_event_metadata": self.source_event_metadata,
        }
