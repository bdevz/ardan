"""
Circuit breaker pattern implementation for external service calls
"""
import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    def __init__(self, message: str, stats: CircuitBreakerStats):
        super().__init__(message)
        self.stats = stats


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external service calls
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        """
        async with self._lock:
            # Check if we should allow the call
            if not self._should_allow_request():
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}",
                    self.stats
                )
            
            # Record request attempt
            self.stats.total_requests += 1
        
        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_function(func, *args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Record success
            await self._record_success()
            return result
            
        except asyncio.TimeoutError as e:
            await self._record_failure(e)
            raise
        except self.config.expected_exception as e:
            await self._record_failure(e)
            raise
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.warning(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function, handling both sync and async"""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self._should_attempt_reset():
                self._transition_to_half_open()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.stats.last_failure_time:
            return True
        
        time_since_failure = datetime.utcnow() - self.stats.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    async def _record_success(self):
        """Record successful request"""
        async with self._lock:
            self.stats.successful_requests += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = datetime.utcnow()
            
            # Check if we should close the circuit
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()
    
    async def _record_failure(self, exception: Exception):
        """Record failed request"""
        async with self._lock:
            self.stats.failed_requests += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = datetime.utcnow()
            
            logger.warning(f"Circuit breaker '{self.name}' recorded failure: {exception}")
            
            # Check if we should open the circuit
            if (self.state == CircuitState.CLOSED and 
                self.stats.consecutive_failures >= self.config.failure_threshold):
                self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state goes back to open
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit breaker to open state"""
        self.state = CircuitState.OPEN
        self.stats.state_changes += 1
        logger.warning(f"Circuit breaker '{self.name}' opened after {self.stats.consecutive_failures} failures")
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.stats.state_changes += 1
        self.stats.consecutive_successes = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to half-open")
    
    def _transition_to_closed(self):
        """Transition circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.stats.state_changes += 1
        logger.info(f"Circuit breaker '{self.name}' closed after {self.stats.consecutive_successes} successes")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": (
                self.stats.successful_requests / self.stats.total_requests 
                if self.stats.total_requests > 0 else 0
            ),
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            "last_success_time": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            "state_changes": self.stats.state_changes
        }
    
    async def reset(self):
        """Manually reset circuit breaker to closed state"""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.stats.consecutive_failures = 0
            self.stats.consecutive_successes = 0
            self.stats.state_changes += 1
            logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create circuit breaker"""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        async with self._lock:
            return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator for applying circuit breaker to functions"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            breaker = await circuit_breaker_registry.get_breaker(name, config)
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator