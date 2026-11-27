import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Analyst(Base):
    __tablename__ = "analysts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="ANALYST")
    team = Column(String(100), nullable=False, default="Tier 1 Fraud Operations")
    is_active = Column(Boolean, default=True, nullable=False)
    workload_limit = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    assigned_alerts = relationship("FraudAlert", back_populates="assigned_analyst")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "team": self.team,
            "is_active": self.is_active,
            "workload_limit": self.workload_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
