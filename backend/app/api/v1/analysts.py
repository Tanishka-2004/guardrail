from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.repositories.analyst_repo import AnalystRepository
from app.schemas.auth import UserResponse
from app.schemas.dashboard import AnalystWorkloadResponse

router = APIRouter(prefix="/analysts", tags=["Analysts"])

@router.get("", response_model=List[UserResponse])
async def list_analysts(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    repo = AnalystRepository(db)
    analysts = await repo.list_analysts()
    return analysts

@router.get("/{analyst_id}/workload", response_model=AnalystWorkloadResponse)
async def get_analyst_workload(analyst_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    repo = AnalystRepository(db)
    metrics = await repo.get_analyst_workload_metrics(analyst_id)
    if not metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyst not found")
    return metrics
