from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analysts import router as analysts_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.dlq import router as dlq_router
from app.api.v1.system import router as system_router
from app.api.v1.ws import router as ws_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(analysts_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(dlq_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(ws_router)
