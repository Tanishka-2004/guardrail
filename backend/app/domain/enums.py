"""Domain enums and data definitions."""
import enum

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    CLAIMED = "CLAIMED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"

class Priority(str, enum.Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"

class SLAStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    BREACHED = "BREACHED"

class UserRole(str, enum.Enum):
    ANALYST = "ANALYST"
    SENIOR_ANALYST = "SENIOR_ANALYST"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"

class CircuitState(str, enum.Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class DLQReplayStatus(str, enum.Enum):
    PENDING = "PENDING"
    REPLAYED = "REPLAYED"
    FAILED = "FAILED"

class AuditAction(str, enum.Enum):
    INGESTED = "INGESTED"
    CLAIMED = "CLAIMED"
    RELEASED = "RELEASED"
    RENEWED = "RENEWED"
    REASSIGNED = "REASSIGNED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"
    NOTE_ADDED = "NOTE_ADDED"
