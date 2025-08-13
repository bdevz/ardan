"""
Enhanced error recovery and resilience system
"""
import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
import traceback

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_registry

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    EXTERNAL_SERVICE = "external_service"
    BROWSER_AUTOMATION = "browser_automation"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    exception: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    service_name: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = field(default="")
    
    def __post_init__(self):
        if not self.stack_trace:
            self.stack_trace = traceback.format_exc()


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()


class ErrorClassifier:
    """Classifies errors into categories and determines severity"""
    
    # Exception mappings to categories
    CATEGORY_MAPPINGS = {
        # Network errors
        (ConnectionError, TimeoutError, OSError): ErrorCategory.NETWORK,
        
        # Authentication errors
        (PermissionError,): ErrorCategory.AUTHENTICATION,
        
        # Validation errors
        (ValueError, TypeError, KeyError): ErrorCategory.VALIDATION,
        
        # Database errors
        (Exception,): ErrorCategory.DATABASE,  # Will be refined based on exception message
    }
    
    # Severity mappings
    SEVERITY_MAPPINGS = {
        ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
        ErrorCategory.AUTHENTICATION: ErrorSeverity.HIGH,
        ErrorCategory.RATE_LIMIT: ErrorSeverity.MEDIUM,
        ErrorCategory.VALIDATION: ErrorSeverity.LOW,
        ErrorCategory.EXTERNAL_SERVICE: ErrorSeverity.MEDIUM,
        ErrorCategory.BROWSER_AUTOMATION: ErrorSeverity.MEDIUM,
        ErrorCategory.DATABASE: ErrorSeverity.HIGH,
        ErrorCategory.CONFIGURATION: ErrorSeverity.HIGH,
        ErrorCategory.UNKNOWN: ErrorSeverity.LOW,
    }
    
    @classmethod
    def classify_error(cls, exception: Exception, context: Dict[str, Any] = None) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error into category and severity"""
        context = context or {}
        
        # Check exception type mappings
        for exception_types, category in cls.CATEGORY_MAPPINGS.items():
            if isinstance(exception, exception_types):
                severity = cls.SEVERITY_MAPPINGS.get(category, ErrorSeverity.LOW)
                return category, severity
        
        # Check error message for specific patterns
        error_message = str(exception).lower()
        
        if any(keyword in error_message for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM
        
        if any(keyword in error_message for keyword in ['unauthorized', 'forbidden', '401', '403']):
            return ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH
        
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network']):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        if any(keyword in error_message for keyword in ['browser', 'selenium', 'stagehand', 'browserbase']):
            return ErrorCategory.BROWSER_AUTOMATION, ErrorSeverity.MEDIUM
        
        # Check context for service-specific classification
        service_name = context.get('service_name', '').lower()
        if 'google' in service_name or 'slack' in service_name or 'n8n' in service_name:
            return ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.MEDIUM
        
        return ErrorCategory.UNKNOWN, ErrorSeverity.LOW


class ExponentialBackoffWithJitter:
    """Exponential backoff with jitter implementation"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if attempt <= 0:
            return 0
        
        # Calculate exponential delay
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** (attempt - 1)),
            self.config.max_delay
        )
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)
        
        return delay


class ErrorRecoveryManager:
    """Manages error recovery strategies and resilience patterns"""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self.max_history_size = 1000
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies for different error categories"""
        self.recovery_strategies[ErrorCategory.NETWORK] = self._handle_network_error
        self.recovery_strategies[ErrorCategory.RATE_LIMIT] = self._handle_rate_limit_error
        self.recovery_strategies[ErrorCategory.AUTHENTICATION] = self._handle_auth_error
        self.recovery_strategies[ErrorCategory.EXTERNAL_SERVICE] = self._handle_external_service_error
        self.recovery_strategies[ErrorCategory.BROWSER_AUTOMATION] = self._handle_browser_error
    
    async def handle_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle error with appropriate recovery strategy"""
        # Record error in history
        self._record_error(error_info)
        
        # Log error details
        logger.error(
            f"Error in {error_info.service_name}.{error_info.operation}: "
            f"{error_info.category.value} - {error_info.severity.value} - {error_info.exception}"
        )
        
        # Apply recovery strategy
        recovery_strategy = self.recovery_strategies.get(error_info.category)
        if recovery_strategy:
            try:
                recovery_result = await recovery_strategy(error_info)
                logger.info(f"Applied recovery strategy for {error_info.category.value}: {recovery_result}")
                return recovery_result
            except Exception as e:
                logger.error(f"Recovery strategy failed: {e}")
        
        return {"recovered": False, "action": "no_strategy"}
    
    def _record_error(self, error_info: ErrorInfo):
        """Record error in history with size limit"""
        self.error_history.append(error_info)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    async def _handle_network_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle network-related errors"""
        return {
            "recovered": False,
            "action": "retry_with_backoff",
            "delay": 5.0,
            "message": "Network error detected, will retry with exponential backoff"
        }
    
    async def _handle_rate_limit_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle rate limiting errors"""
        # Extract rate limit info from error message if available
        delay = 60.0  # Default 1 minute delay
        
        error_message = str(error_info.exception).lower()
        if 'retry-after' in error_message:
            # Try to extract retry-after value
            import re
            match = re.search(r'retry-after[:\s]+(\d+)', error_message)
            if match:
                delay = float(match.group(1))
        
        return {
            "recovered": False,
            "action": "wait_and_retry",
            "delay": delay,
            "message": f"Rate limit exceeded, waiting {delay} seconds"
        }
    
    async def _handle_auth_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle authentication errors"""
        return {
            "recovered": False,
            "action": "refresh_credentials",
            "message": "Authentication error, credentials may need refresh"
        }
    
    async def _handle_external_service_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle external service errors"""
        return {
            "recovered": False,
            "action": "circuit_breaker",
            "message": "External service error, circuit breaker will handle"
        }
    
    async def _handle_browser_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """Handle browser automation errors"""
        return {
            "recovered": False,
            "action": "reset_session",
            "message": "Browser automation error, session may need reset"
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and patterns"""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Calculate statistics
        total_errors = len(self.error_history)
        recent_errors = [e for e in self.error_history if e.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        # Group by category
        category_counts = {}
        severity_counts = {}
        service_counts = {}
        
        for error in self.error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            service_counts[error.service_name] = service_counts.get(error.service_name, 0) + 1
        
        return {
            "total_errors": total_errors,
            "recent_errors_1h": len(recent_errors),
            "error_rate_1h": len(recent_errors) / 60,  # errors per minute
            "categories": category_counts,
            "severities": severity_counts,
            "services": service_counts,
            "most_common_category": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
            "most_affected_service": max(service_counts.items(), key=lambda x: x[1])[0] if service_counts else None
        }


class ResilientServiceWrapper:
    """Wrapper for services to add resilience patterns"""
    
    def __init__(
        self,
        service_name: str,
        retry_config: RetryConfig = None,
        circuit_breaker_config: CircuitBreakerConfig = None,
        error_recovery_manager: ErrorRecoveryManager = None
    ):
        self.service_name = service_name
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.error_recovery_manager = error_recovery_manager or ErrorRecoveryManager()
        self.backoff_calculator = ExponentialBackoffWithJitter(self.retry_config)
        
        # Get or create circuit breaker
        self.circuit_breaker = None
        self._circuit_breaker_task = None
    
    async def _get_circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker instance"""
        if not self.circuit_breaker:
            self.circuit_breaker = await circuit_breaker_registry.get_breaker(
                self.service_name, 
                self.circuit_breaker_config
            )
        return self.circuit_breaker
    
    async def execute_with_resilience(
        self,
        operation: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with full resilience patterns"""
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Execute with circuit breaker protection
                circuit_breaker = await self._get_circuit_breaker()
                result = await circuit_breaker.call(func, *args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    logger.info(f"Operation {operation} succeeded after {attempt} retries")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Classify error
                category, severity = ErrorClassifier.classify_error(
                    e, 
                    {"service_name": self.service_name, "operation": operation}
                )
                
                # Create error info
                error_info = ErrorInfo(
                    exception=e,
                    category=category,
                    severity=severity,
                    service_name=self.service_name,
                    operation=operation,
                    retry_count=attempt,
                    context={"args": str(args), "kwargs": str(kwargs)}
                )
                
                # Check if error is retryable
                if not self._is_retryable(e):
                    logger.error(f"Non-retryable error in {operation}: {e}")
                    await self.error_recovery_manager.handle_error(error_info)
                    raise
                
                # Check if we should retry
                if attempt >= self.retry_config.max_retries:
                    logger.error(f"Max retries exceeded for {operation}: {e}")
                    await self.error_recovery_manager.handle_error(error_info)
                    break
                
                # Handle error and get recovery strategy
                recovery_result = await self.error_recovery_manager.handle_error(error_info)
                
                # Calculate delay
                delay = self.backoff_calculator.calculate_delay(attempt + 1)
                
                # Apply recovery-specific delay if provided
                if recovery_result.get("delay"):
                    delay = max(delay, recovery_result["delay"])
                
                logger.warning(
                    f"Attempt {attempt + 1} failed for {operation}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        # Check non-retryable exceptions first
        if isinstance(exception, self.retry_config.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        return isinstance(exception, self.retry_config.retryable_exceptions)


class ServiceHealthMonitor:
    """Monitors service health and provides degradation strategies"""
    
    def __init__(self):
        self.service_health: Dict[str, Dict[str, Any]] = {}
        self.health_check_interval = 60  # seconds
        self.degradation_strategies: Dict[str, Callable] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
    
    def register_service(
        self,
        service_name: str,
        health_check_func: Callable,
        degradation_strategy: Callable = None
    ):
        """Register a service for health monitoring"""
        self.service_health[service_name] = {
            "status": "unknown",
            "last_check": None,
            "consecutive_failures": 0,
            "health_check_func": health_check_func
        }
        
        if degradation_strategy:
            self.degradation_strategies[service_name] = degradation_strategy
        
        # Start monitoring task
        self._monitoring_tasks[service_name] = asyncio.create_task(
            self._monitor_service_health(service_name)
        )
    
    async def _monitor_service_health(self, service_name: str):
        """Monitor health of a specific service"""
        while True:
            try:
                health_info = self.service_health[service_name]
                health_check_func = health_info["health_check_func"]
                
                # Perform health check
                is_healthy = await health_check_func()
                
                if is_healthy:
                    health_info["status"] = "healthy"
                    health_info["consecutive_failures"] = 0
                else:
                    health_info["status"] = "unhealthy"
                    health_info["consecutive_failures"] += 1
                
                health_info["last_check"] = datetime.utcnow()
                
                # Check if degradation is needed
                if health_info["consecutive_failures"] >= 3:
                    await self._apply_degradation(service_name)
                
                logger.debug(f"Health check for {service_name}: {health_info['status']}")
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                self.service_health[service_name]["status"] = "error"
                self.service_health[service_name]["consecutive_failures"] += 1
            
            await asyncio.sleep(self.health_check_interval)
    
    async def _apply_degradation(self, service_name: str):
        """Apply degradation strategy for unhealthy service"""
        degradation_strategy = self.degradation_strategies.get(service_name)
        if degradation_strategy:
            try:
                await degradation_strategy(service_name)
                logger.warning(f"Applied degradation strategy for {service_name}")
            except Exception as e:
                logger.error(f"Degradation strategy failed for {service_name}: {e}")
    
    def get_service_health(self, service_name: str = None) -> Dict[str, Any]:
        """Get health status for service(s)"""
        if service_name:
            return self.service_health.get(service_name, {"status": "not_registered"})
        
        return {
            name: {
                "status": info["status"],
                "last_check": info["last_check"].isoformat() if info["last_check"] else None,
                "consecutive_failures": info["consecutive_failures"]
            }
            for name, info in self.service_health.items()
        }
    
    async def shutdown(self):
        """Shutdown health monitoring"""
        for task in self._monitoring_tasks.values():
            task.cancel()
        
        await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)


# Global instances
error_recovery_manager = ErrorRecoveryManager()
service_health_monitor = ServiceHealthMonitor()


def resilient_service(
    service_name: str,
    retry_config: RetryConfig = None,
    circuit_breaker_config: CircuitBreakerConfig = None
):
    """Decorator to make service methods resilient"""
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._resilience_wrapper = ResilientServiceWrapper(
                service_name=service_name,
                retry_config=retry_config,
                circuit_breaker_config=circuit_breaker_config,
                error_recovery_manager=error_recovery_manager
            )
        
        cls.__init__ = new_init
        
        # Wrap all async methods
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if (callable(attr) and 
                not attr_name.startswith('_') and 
                asyncio.iscoroutinefunction(attr)):
                
                setattr(cls, attr_name, _wrap_method(attr, attr_name))
        
        return cls
    return decorator


def _wrap_method(method, method_name):
    """Wrap method with resilience patterns"""
    async def wrapper(self, *args, **kwargs):
        # Create a bound method that includes self
        async def bound_method():
            return await method(self, *args, **kwargs)
        
        return await self._resilience_wrapper.execute_with_resilience(
            method_name,
            bound_method
        )
    return wrapper