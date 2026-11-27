import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from app.core.database import Base

class AlertOutbox(Base):
    __tablename__ = "alert_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    aggregate_id = Column(String(128), index=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    retry_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_outbox_unprocessed", "published_at", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "retry_count": self.retry_count,
        }
