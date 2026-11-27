from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.services.alert_service import AlertTriageService
from app.repositories.audit_repo import AuditRepository
from app.kafka.producer import kafka_producer
from app.kafka.consumer import kafka_consumer
from app.core.config import settings
from app.domain.enums import UserRole
from app.schemas.transaction import TransactionEventIngest, IngestionResponse
from app.schemas.alert import (
    FraudAlertResponse,
    AlertListResponse,
    AlertClaimRequest,
    AlertReassignRequest,
    AlertResolveRequest,
    AlertReopenRequest,
    AlertNoteRequest,
)
from app.schemas.audit_dlq import AuditLogResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.post("/ingest", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_transaction(event: TransactionEventIngest):
    """
    Ingests transaction event into Kafka pipeline.
    Validates payload, assigns or verifies stable idempotency event_id,
    and returns immediately with correlation tracking.
    """
    event_id = event.event_id or f"evt_{uuid.uuid4().hex[:16]}"
    correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    payload = event.model_dump()
    payload["event_id"] = event_id
    payload["correlation_id"] = correlation_id
    payload["ingested_at"] = now.isoformat()
    if not payload.get("transaction_timestamp"):
        payload["transaction_timestamp"] = now.isoformat()

    # Publish to Kafka fraud.alerts topic
    published = await kafka_producer.publish(
        topic=settings.KAFKA_TOPIC_ALERTS,
        value=payload,
        key=event.transaction_id,
        headers={"correlation_id": correlation_id}
    )

    # In standalone / test mode when Kafka broker is offline, consumer can process immediately
    if not settings.ENABLE_KAFKA_CONSUMER or not kafka_consumer.is_running:
        # Run through consumer processing synchronously for demo/test mode
        try:
            await kafka_consumer.process_message(payload)
        except Exception as e:
            pass

    return IngestionResponse(
        status="ACCEPTED",
        event_id=event_id,
        correlation_id=correlation_id,
        topic=settings.KAFKA_TOPIC_ALERTS,
        received_at=now,
        message="Event accepted for asynchronous fraud processing and triage",
    )

@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_analyst_id: Optional[str] = None,
    claimed: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query("priority_sla", description="priority_sla, sla_deadline, fraud_score, created_at, amount"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    items, total = await service.list_alerts(
        status=status,
        risk_level=risk_level,
        priority=priority,
        assigned_analyst_id=assigned_analyst_id,
        claimed=claimed,
        search=search,
        sort_by=sort_by,
        page=page,
        limit=limit,
    )
    pages = (total + limit - 1) // limit if total > 0 else 1
    return AlertListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )

@router.get("/{alert_id}", response_model=FraudAlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    service = AlertTriageService(db)
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert

@router.post("/{alert_id}/claim", response_model=FraudAlertResponse)
async def claim_alert(
    alert_id: str,
    req: AlertClaimRequest = AlertClaimRequest(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    lease = req.lease_duration_seconds or settings.CLAIM_LEASE_DURATION_SECONDS
    alert, error = await service.claim_alert(
        alert_id=alert_id,
        analyst_id=current_user.id,
        analyst_name=current_user.name,
        analyst_role=current_user.role,
        lease_duration_seconds=lease,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return alert

@router.post("/{alert_id}/release", response_model=FraudAlertResponse)
async def release_claim(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    alert, error = await service.release_claim(
        alert_id=alert_id,
        analyst_id=current_user.id,
        analyst_name=current_user.name,
        analyst_role=current_user.role,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.post("/{alert_id}/renew-claim", response_model=FraudAlertResponse)
async def renew_claim(
    alert_id: str,
    req: AlertClaimRequest = AlertClaimRequest(),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    lease = req.lease_duration_seconds or settings.CLAIM_LEASE_DURATION_SECONDS
    alert, error = await service.renew_claim(
        alert_id=alert_id,
        analyst_id=current_user.id,
        lease_duration_seconds=lease,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.post("/{alert_id}/reassign", response_model=FraudAlertResponse)
async def reassign_alert(
    alert_id: str,
    req: AlertReassignRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles(UserRole.SENIOR_ANALYST.value, UserRole.SUPERVISOR.value, UserRole.ADMIN.value)),
):
    service = AlertTriageService(db)
    alert, error = await service.reassign_alert(
        alert_id=alert_id,
        target_analyst_id=req.target_analyst_id,
        actor_id=current_user.id,
        actor_name=current_user.name,
        reason=req.reason,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.post("/{alert_id}/resolve", response_model=FraudAlertResponse)
async def resolve_alert(
    alert_id: str,
    req: AlertResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    alert, error = await service.resolve_alert(
        alert_id=alert_id,
        resolution_reason=req.resolution_reason,
        notes=req.notes,
        actor_id=current_user.id,
        actor_name=current_user.name,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.post("/{alert_id}/reopen", response_model=FraudAlertResponse)
async def reopen_alert(
    alert_id: str,
    req: AlertReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles(UserRole.SUPERVISOR.value, UserRole.ADMIN.value)),
):
    service = AlertTriageService(db)
    alert, error = await service.reopen_alert(
        alert_id=alert_id,
        reason=req.reason,
        actor_id=current_user.id,
        actor_name=current_user.name,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.post("/{alert_id}/notes", response_model=FraudAlertResponse)
async def add_alert_note(
    alert_id: str,
    req: AlertNoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = AlertTriageService(db)
    alert, error = await service.add_note(
        alert_id=alert_id,
        note=req.note,
        actor_id=current_user.id,
        actor_name=current_user.name,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return alert

@router.get("/{alert_id}/audit", response_model=List[AuditLogResponse])
async def get_alert_audit_trail(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    repo = AuditRepository(db)
    logs = await repo.get_by_alert_id(alert_id)
    return [log.to_dict() for log in logs]
