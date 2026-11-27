import json
import logging
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_started: bool = False
        self._in_memory_queue: list = []  # Fallback buffer if Kafka unavailable in dev/test

    async def start(self):
        if self._is_started:
            return
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                enable_idempotence=True,
                max_request_size=1048576,
                request_timeout_ms=5000,
            )
            await self._producer.start()
            self._is_started = True
            logger.info(f"Kafka producer successfully connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.warning(f"Could not connect to Kafka broker ({e}). Fallback in-memory buffer active.")
            self._producer = None
            self._is_started = False

    async def stop(self):
        if self._producer and self._is_started:
            await self._producer.stop()
            self._is_started = False
            logger.info("Kafka producer stopped.")

    async def publish(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Publishes message to Kafka topic.
        If broker is offline, buffers in memory and logs degraded state.
        """
        if self._producer and self._is_started:
            try:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()] if headers else None
                await self._producer.send_and_wait(
                    topic=topic,
                    value=value,
                    key=key,
                    headers=kafka_headers
                )
                return True
            except Exception as e:
                logger.error(f"Error publishing to Kafka topic '{topic}': {e}. Buffering in memory.")
        
        # Buffer fallback
        self._in_memory_queue.append({
            "topic": topic,
            "key": key,
            "value": value,
            "headers": headers
        })
        return True

    def get_in_memory_queue(self):
        return self._in_memory_queue

    def clear_in_memory_queue(self):
        self._in_memory_queue.clear()

kafka_producer = KafkaProducerService()
