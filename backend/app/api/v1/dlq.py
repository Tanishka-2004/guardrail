from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.core.database import get_db
from app.core.security import require_roles, get_current_user
from app.domain.enums import UserRole
from app.services.dlq_service import DLQService
from app.schemas.audit_dlq import DeadLetterResponse, DLQReplayResponse

router = APIRouter(prefix="/dlq", tags=["Dead Letter Queue"])

@router.get("", response_model=List[DeadLetterResponse])
async def list_dlq(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = DLQService(db)
    items, total = await service.list_dlq(replay_status=status, page=page, limit=limit)
    return items

@router.get("/{event_id}", response_model=DeadLetterResponse)
async def get_dlq_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    service = DLQService(db)
    item = await service.get_by_event_id(event_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ event not found")
    return item

@router.post("/{event_id}/replay", response_model=DLQReplayResponse)
async def replay_dlq_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN.value, UserRole.SUPERVISOR.value)),
):
    service = DLQService(db)
    success, msg, count = await service.replay_event(event_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return DLQReplayResponse(
        event_id=event_id,
        replay_status="REPLAYED",
        message=msg,
        replay_count=count,
    )

@router.post("/replay-all")
async def replay_all_dlq(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN.value, UserRole.SUPERVISOR.value)),
):
    service = DLQService(db)
    return await service.replay_all_pending(max_items=100)
