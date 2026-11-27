from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    QueueSummaryResponse,
    SLASummaryResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    service = DashboardService(db)
    return await service.get_metrics()

@router.get("/queue-summary", response_model=QueueSummaryResponse)
async def get_queue_summary(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    service = DashboardService(db)
    return await service.get_queue_summary()

@router.get("/sla-summary", response_model=SLASummaryResponse)
async def get_sla_summary(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    service = DashboardService(db)
    return await service.get_sla_summary()
