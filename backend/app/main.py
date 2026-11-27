from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.services.redis_service import redis_service
from app.kafka.producer import kafka_producer
from app.kafka.consumer import kafka_consumer
from app.websocket.manager import ws_manager
from app.workers import background_workers
from app.api.v1 import api_v1_router
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("guardrail")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing GuardRail Fraud Alert Triage Engine...")
    await redis_service.connect()
    await kafka_producer.start()
    await ws_manager.start()
    
    if settings.ENABLE_KAFKA_CONSUMER:
        await kafka_consumer.start()
        
    if settings.ENABLE_BACKGROUND_WORKERS:
        await background_workers.start_all()
        
    logger.info("GuardRail Backend successfully started.")
    yield

    # Shutdown sequence
    logger.info("Shutting down GuardRail Backend...")
    if settings.ENABLE_BACKGROUND_WORKERS:
        await background_workers.stop_all()
        
    if settings.ENABLE_KAFKA_CONSUMER:
        await kafka_consumer.stop()
        
    await ws_manager.stop()
    await kafka_producer.stop()
    await redis_service.disconnect()
    logger.info("GuardRail Backend cleanly stopped.")

app = FastAPI(
    title="GuardRail | Fraud Alert Triage Console API",
    description="Event-driven fraud-alert operations platform with Kafka ingestion, atomic claim-locking, SLA-aware triage, and real-time WebSockets.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {
        "project": "GuardRail - Fraud Alert Triage Console",
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "docs": "/docs"
    }
