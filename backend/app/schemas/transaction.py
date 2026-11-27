from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TransactionEventIngest(BaseModel):
    event_id: Optional[str] = Field(None, description="Optional unique idempotency key. Generated if omitted.")
    transaction_id: str = Field(..., description="Unique transaction reference ID")
    customer_id: str = Field(..., description="Customer ID")
    merchant_id: str = Field(..., description="Merchant ID")
    merchant_category: Optional[str] = Field("retail", description="MCC / Merchant category")
    transaction_amount: float = Field(..., gt=0, description="Transaction monetary amount")
    currency: str = Field("USD", min_length=3, max_length=3, description="ISO currency code")
    transaction_type: str = Field("PURCHASE", description="PURCHASE, TRANSFER, WITHDRAWAL, etc.")
    transaction_timestamp: Optional[datetime] = Field(None, description="Transaction timestamp in UTC")
    location: Optional[str] = Field(None, description="Transaction location / IP country")
    ip_address: Optional[str] = Field(None, description="Originating IP address")
    device_id: Optional[str] = Field(None, description="Originating device fingerprint")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional arbitrary telemetry")

class IngestionResponse(BaseModel):
    status: str = "ACCEPTED"
    event_id: str
    correlation_id: str
    topic: str
    received_at: datetime
    message: str = "Event accepted for asynchronous fraud processing"
