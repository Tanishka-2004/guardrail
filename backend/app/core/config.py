from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Any
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Database
    # Support PostgreSQL with fallback for in-memory or SQLite testing when local PG is not running
    DATABASE_URL: str = "postgresql+asyncpg://guardrail:guardrail_secret_pass@localhost:5432/guardrail_db"
    SYNC_DATABASE_URL: str = "postgresql://guardrail:guardrail_secret_pass@localhost:5432/guardrail_db"
    
    # Redis
    REDIS_URL: str = "redis://:guardrail_redis_pass@localhost:6379/0"
    REDIS_KEY_PREFIX: str = "guardrail:"
    CACHE_DEFAULT_TTL_SECONDS: int = 60

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9094"
    KAFKA_TOPIC_ALERTS: str = "fraud.alerts"
    KAFKA_TOPIC_RETRY: str = "fraud.alerts.retry"
    KAFKA_TOPIC_DLQ: str = "fraud.alerts.dlq"
    KAFKA_TOPIC_EVENTS: str = "fraud.alerts.events"
    KAFKA_CONSUMER_GROUP: str = "guardrail-alert-consumer-group"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_MAX_POLL_RECORDS: int = 50

    # Security & Auth
    JWT_SECRET_KEY: str = "guardrail-super-secure-production-jwt-secret-key-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            if isinstance(v, str):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
            return v
        return []

    # Claim Leases (Seconds)
    CLAIM_LEASE_DURATION_SECONDS: int = 600  # 10 minutes default
    
    # SLA Policies (in minutes)
    SLA_CRITICAL_MINUTES: int = 5
    SLA_HIGH_MINUTES: int = 15
    SLA_MEDIUM_MINUTES: int = 60
    SLA_LOW_MINUTES: int = 240
    SLA_WARNING_THRESHOLD_PERCENT: float = 75.0  # Alert when 75% consumed

    # Fraud Scoring & Circuit Breaker
    SCORING_FAILURE_THRESHOLD: int = 5
    SCORING_RECOVERY_TIMEOUT_SECONDS: float = 30.0
    SCORING_REQUEST_TIMEOUT_SECONDS: float = 3.0
    SCORING_HALF_OPEN_MAX_REQUESTS: int = 3

    # Feature Toggles
    ENABLE_KAFKA_CONSUMER: bool = True
    ENABLE_BACKGROUND_WORKERS: bool = True

    model_config = SettingsConfigDict(
        env_file=[
            ".env",
            "backend/.env",
            os.path.join(os.path.dirname(__file__), "../../.env"),
            os.path.join(os.path.dirname(__file__), "../../../.env"),
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
