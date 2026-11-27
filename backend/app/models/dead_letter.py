import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, Index
from app.core.database import Base

class DeadLetterEvent(Base):
    __tablename__ = "dead_letter_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_event_id = Column(String(128), index=True, nullable=False)
    topic = Column(String(100), nullable=False)
    partition = Column(Integer, default=0, nullable=False)
    offset = Column(Integer, default=0, nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    error_type = Column(String(100), nullable=False)
    error_message = Column(String(1000), nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    replay_status = Column(String(30), default="PENDING", index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    replayed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_dlq_status_created", "replay_status", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "original_event_id": self.original_event_id,
            "topic": self.topic,
            "partition": self.partition,
            "offset": self.offset,
            "payload": self.payload,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "replay_status": self.replay_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "replayed_at": self.replayed_at.isoformat() if self.replayed_at else None,
        }
