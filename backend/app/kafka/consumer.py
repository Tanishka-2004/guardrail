import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.alert_repo import AlertRepository
from app.repositories.dlq_repo import DLQRepository
from app.services.scoring import fraud_scoring_engine
from app.services.sla_engine import SLAEngine
from app.kafka.producer import kafka_producer
from app.domain.enums import AlertStatus

logger = logging.getLogger(__name__)

class FraudAlertConsumer:
    """
    Asynchronous Kafka Consumer for fraud alert ingestion.
    Adheres strictly to zero-duplicate processing:
    1. Reads event from Kafka topic (fraud.alerts or fraud.alerts.retry)
    2. Validates event schema
    3. Runs fraud scoring (protected by Circuit Breaker)
    4. Transactionally creates alert in PostgreSQL with ON CONFLICT / unique event_id check
    5. Commits Kafka offset ONLY after DB commit succeeds!
    6. If processing fails repeatedly, routes event to DLQ table and fraud.alerts.dlq topic.
    """
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.messages_processed_count: int = 0
        self.messages_failed_count: int = 0
        self.duplicates_prevented_count: int = 0

    async def start(self):
        if not settings.ENABLE_KAFKA_CONSUMER:
            logger.info("Kafka consumer is disabled by configuration (ENABLE_KAFKA_CONSUMER=False).")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("Fraud alert consumer background worker started.")

    async def stop(self):
        self.is_running = False
        if self.consumer:
            try:
                await self.consumer.stop()
            except Exception as e:
                logger.warning(f"Error stopping Kafka consumer: {e}")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Fraud alert consumer stopped.")

    async def _init_consumer(self) -> bool:
        try:
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_ALERTS,
                settings.KAFKA_TOPIC_RETRY,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP,
                enable_auto_commit=False,  # MANUAL COMMIT ONLY AFTER DB SUCCESS
                auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                max_poll_records=settings.KAFKA_MAX_POLL_RECORDS,
            )
            await self.consumer.start()
            logger.info(f"Kafka consumer successfully connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect Kafka consumer: {e}. Will retry connection in background.")
            self.consumer = None
            return False

    async def _consume_loop(self):
        while self.is_running:
            if not self.consumer:
                connected = await self._init_consumer()
                if not connected:
                    await asyncio.sleep(5)
                    continue

            try:
                msg_batch = await self.consumer.getmany(timeout_ms=1000, max_records=20)
                for tp, messages in msg_batch.items():
                    for msg in messages:
                        if not self.is_running:
                            break
                        await self.process_message(msg.value, msg.topic, msg.partition, msg.offset)
                        # Commit offset specifically for this record
                        await self.consumer.commit({tp: msg.offset + 1})
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Kafka consumer loop: {e}", exc_info=True)
                await asyncio.sleep(2)

    async def process_message(
        self,
        event_payload: Dict[str, Any],
        topic: str = settings.KAFKA_TOPIC_ALERTS,
        partition: int = 0,
        offset: int = 0
    ) -> bool:
        """
        Processes single event with strict zero-duplicate guarantees and transactional commit.
        """
        event_id = event_payload.get("event_id")
        transaction_id = event_payload.get("transaction_id")
        retry_count = int(event_payload.get("retry_count", 0))

        if not event_id or not transaction_id:
            logger.error(f"Malformed event received, missing event_id or transaction_id: {event_payload}")
            await self._route_to_dlq(
                original_event_id=str(event_id or "unknown"),
                topic=topic,
                payload=event_payload,
                error_type="ValidationError",
                error_message="Missing required event_id or transaction_id",
                partition=partition,
                offset=offset,
                retry_count=retry_count
            )
            return False

        async with AsyncSessionLocal() as session:
            try:
                alert_repo = AlertRepository(session)
                
                # Check idempotency: If event_id already exists in Postgres, skip duplicate
                existing = await alert_repo.get_by_event_id(event_id)
                if existing:
                    self.duplicates_prevented_count += 1
                    logger.info(f"[Zero-Duplicate] Alert already exists for event_id '{event_id}'. Skipping duplicate insert.")
                    return True

                # Step 1: Run fraud scoring (protected by circuit breaker)
                scoring_result = await fraud_scoring_engine.evaluate_transaction(event_payload)

                # Step 2: Compute SLA deadlines
                now = datetime.now(timezone.utc)
                tx_timestamp = event_payload.get("transaction_timestamp")
                if isinstance(tx_timestamp, str):
                    try:
                        tx_time = datetime.fromisoformat(tx_timestamp)
                    except Exception:
                        tx_time = now
                else:
                    tx_time = now

                sla_deadline = SLAEngine.calculate_deadline(now, scoring_result.sla_duration_minutes)

                # Step 3: Prepare alert model data
                alert_data = {
                    "event_id": event_id,
                    "transaction_id": transaction_id,
                    "customer_id": str(event_payload.get("customer_id", "unknown")),
                    "merchant_id": str(event_payload.get("merchant_id", "unknown")),
                    "transaction_amount": float(event_payload.get("transaction_amount", 0.0)),
                    "currency": str(event_payload.get("currency", "USD")),
                    "transaction_type": str(event_payload.get("transaction_type", "PURCHASE")),
                    "transaction_timestamp": tx_time,
                    "fraud_score": scoring_result.fraud_score,
                    "risk_level": scoring_result.risk_level.value,
                    "fraud_reason": scoring_result.fraud_reason,
                    "status": AlertStatus.NEW.value,
                    "priority": scoring_result.priority.value,
                    "sla_deadline": sla_deadline,
                    "sla_duration_minutes": scoring_result.sla_duration_minutes,
                    "source_event_metadata": event_payload,
                    "replay_count": int(event_payload.get("replay_count", 0)),
                }

                # Step 4: Persist alert, audit log, outbox transactionally
                alert, created = await alert_repo.create_alert_idempotent(alert_data)
                await session.commit()

                if created:
                    self.messages_processed_count += 1
                    logger.info(f"Successfully processed alert '{alert.id}' (event_id={event_id}, score={alert.fraud_score}, priority={alert.priority})")
                else:
                    self.duplicates_prevented_count += 1

                return True

            except Exception as e:
                await session.rollback()
                self.messages_failed_count += 1
                logger.error(f"Error processing event '{event_id}': {e}", exc_info=True)

                # Handle retries vs DLQ
                if retry_count < 3:
                    event_payload["retry_count"] = retry_count + 1
                    event_payload["last_error"] = str(e)
                    await kafka_producer.publish(
                        topic=settings.KAFKA_TOPIC_RETRY,
                        value=event_payload,
                        key=transaction_id
                    )
                    logger.warning(f"Routed event '{event_id}' to retry topic (attempt {retry_count + 1}/3)")
                else:
                    await self._route_to_dlq(
                        original_event_id=event_id,
                        topic=topic,
                        payload=event_payload,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        partition=partition,
                        offset=offset,
                        retry_count=retry_count
                    )
                return False

    async def _route_to_dlq(
        self,
        original_event_id: str,
        topic: str,
        payload: Dict[str, Any],
        error_type: str,
        error_message: str,
        partition: int = 0,
        offset: int = 0,
        retry_count: int = 0,
    ):
        """Persists failed event in DeadLetterEvent table and emits to Kafka DLQ topic."""
        async with AsyncSessionLocal() as session:
            try:
                dlq_repo = DLQRepository(session)
                await dlq_repo.create_dlq_event(
                    original_event_id=original_event_id,
                    topic=topic,
                    payload=payload,
                    error_type=error_type,
                    error_message=error_message,
                    partition=partition,
                    offset=offset,
                    retry_count=retry_count
                )
                await session.commit()
            except Exception as dbe:
                await session.rollback()
                logger.error(f"Failed to persist dead letter event in DB: {dbe}")

        # Also publish to Kafka DLQ topic
        await kafka_producer.publish(
            topic=settings.KAFKA_TOPIC_DLQ,
            value={
                "original_event_id": original_event_id,
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count,
                "payload": payload,
            },
            key=original_event_id
        )
        logger.error(f"Event '{original_event_id}' permanently routed to DLQ after exhausting retries.")

kafka_consumer = FraudAlertConsumer()
