import asyncio
import time
from typing import Callable, Any, Optional, Dict
from app.domain.enums import CircuitState
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Raised when request is rejected because circuit breaker is in OPEN state."""
    pass

class CircuitBreaker:
    """
    Standard 3-state Circuit Breaker pattern implementation:
    - CLOSED: Normal operation. All calls pass through. If consecutive failures >= threshold, transitions to OPEN.
    - OPEN: Calls immediately fail-fast with CircuitBreakerOpenException. After recovery_timeout, transitions to HALF_OPEN.
    - HALF_OPEN: Allows limited probe requests (half_open_max_requests). If all succeed, transitions back to CLOSED. If any fails, transitions back to OPEN.
    """
    def __init__(
        self,
        name: str = "FraudScoringService",
        failure_threshold: int = settings.SCORING_FAILURE_THRESHOLD,
        recovery_timeout: float = settings.SCORING_RECOVERY_TIMEOUT_SECONDS,
        half_open_max_requests: int = settings.SCORING_HALF_OPEN_MAX_REQUESTS,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._consecutive_success_count: int = 0
        self._last_state_change: float = time.time()
        self._last_failure_time: Optional[float] = None
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

        # Telemetry metrics
        self.total_calls: int = 0
        self.successful_calls: int = 0
        self.failed_calls: int = 0
        self.rejected_calls: int = 0
        self.state_transitions: int = 0

    @property
    def state(self) -> CircuitState:
        # Check if OPEN has timed out to naturally move to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_state_change >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._consecutive_success_count = 0
                self._last_state_change = time.time()
                self.state_transitions += 1
                logger.info(f"[{self.name}] Circuit Breaker transitioned from OPEN to HALF_OPEN")
        return self._state

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                self.rejected_calls += 1
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN. Fast failing request."
                )

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_requests:
                    self.rejected_calls += 1
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is HALF_OPEN and reached probe limit."
                    )
                self._half_open_calls += 1

            self.total_calls += 1

        # Execute call outside lock so we do not serialize all async work
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self):
        async with self._lock:
            self.successful_calls += 1
            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_success_count += 1
                if self._consecutive_success_count >= self.half_open_max_requests:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._last_state_change = time.time()
                    self.state_transitions += 1
                    logger.info(f"[{self.name}] Circuit Breaker recovered and transitioned to CLOSED")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self, exception: Exception):
        async with self._lock:
            self.failed_calls += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN throws circuit back to OPEN
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
                self.state_transitions += 1
                logger.warning(f"[{self.name}] Probe failed in HALF_OPEN: {exception}. Returned to OPEN.")
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_state_change = time.time()
                    self.state_transitions += 1
                    logger.error(
                        f"[{self.name}] Failure threshold ({self.failure_threshold}) reached. Circuit transitioned to OPEN."
                    )

    def force_state(self, state: CircuitState):
        """Allows manual testing or administrative overrides."""
        self._state = state
        self._last_state_change = time.time()
        self.state_transitions += 1

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "consecutive_success_count": self._consecutive_success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_state_change": self._last_state_change,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "state_transitions": self.state_transitions,
        }

# Global singleton circuit breaker instance for scoring dependency
scoring_circuit_breaker = CircuitBreaker()
