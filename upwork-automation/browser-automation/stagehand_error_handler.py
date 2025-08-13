"""
Error handling and retry logic for Stagehand operations
"""
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass

from shared.utils import setup_logging, retry_async

logger = setup_logging("stagehand-error-handler")


class ErrorType(Enum):
    """Types of Stagehand operation errors"""
    NAVIGATION_FAILED = "navigation_failed"
    ELEMENT_NOT_FOUND = "element_not_found"
    EXTRACTION_FAILED = "extraction_failed"
    FORM_INTERACTION_FAILED = "form_interaction_failed"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    CAPTCHA_DETECTED = "captcha_detected"
    RATE_LIMITED = "rate_limited"
    SESSION_EXPIRED = "session_expired"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY_IMMEDIATE = "retry_immediate"
    RETRY_WITH_DELAY = "retry_with_delay"
    REFRESH_PAGE = "refresh_page"
    NAVIGATE_BACK = "navigate_back"
    RESTART_SESSION = "restart_session"
    WAIT_AND_RETRY = "wait_and_retry"
    MANUAL_INTERVENTION = "manual_intervention"
    ABORT_OPERATION = "abort_operation"


@dataclass
class ErrorContext:
    """Context information for an error"""
    error_type: ErrorType
    error_message: str
    session_id: str
    operation: str
    timestamp: datetime
    page_url: Optional[str] = None
    stack_trace: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RecoveryResult:
    """Result of an error recovery attempt"""
    success: bool
    strategy_used: RecoveryStrategy
    recovery_time: float
    error_resolved: bool
    new_error: Optional[ErrorContext] = None
    recovery_notes: Optional[str] = None


class StagehandErrorHandler:
    """Comprehensive error handling and recovery for Stagehand operations"""
    
    def __init__(self):
        self.error_history: Dict[str, List[ErrorContext]] = {}
        self.recovery_strategies: Dict[ErrorType, List[RecoveryStrategy]] = {
            ErrorType.NAVIGATION_FAILED: [
                RecoveryStrategy.RETRY_WITH_DELAY,
                RecoveryStrategy.REFRESH_PAGE,
                RecoveryStrategy.RESTART_SESSION
            ],
            ErrorType.ELEMENT_NOT_FOUND: [
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.REFRESH_PAGE,
                RecoveryStrategy.RETRY_WITH_DELAY
            ],
            ErrorType.EXTRACTION_FAILED: [
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.REFRESH_PAGE
            ],
            ErrorType.FORM_INTERACTION_FAILED: [
                RecoveryStrategy.RETRY_WITH_DELAY,
                RecoveryStrategy.REFRESH_PAGE,
                RecoveryStrategy.NAVIGATE_BACK
            ],
            ErrorType.TIMEOUT_ERROR: [
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.REFRESH_PAGE,
                RecoveryStrategy.RESTART_SESSION
            ],
            ErrorType.NETWORK_ERROR: [
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.RETRY_WITH_DELAY,
                RecoveryStrategy.RESTART_SESSION
            ],
            ErrorType.CAPTCHA_DETECTED: [
                RecoveryStrategy.MANUAL_INTERVENTION,
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.RESTART_SESSION
            ],
            ErrorType.RATE_LIMITED: [
                RecoveryStrategy.WAIT_AND_RETRY,
                RecoveryStrategy.ABORT_OPERATION
            ],
            ErrorType.SESSION_EXPIRED: [
                RecoveryStrategy.RESTART_SESSION
            ],
            ErrorType.UNKNOWN_ERROR: [
                RecoveryStrategy.RETRY_WITH_DELAY,
                RecoveryStrategy.REFRESH_PAGE,
                RecoveryStrategy.RESTART_SESSION
            ]
        }
        
        # Configuration for recovery strategies
        self.strategy_config = {
            RecoveryStrategy.RETRY_IMMEDIATE: {"max_attempts": 2},
            RecoveryStrategy.RETRY_WITH_DELAY: {"max_attempts": 3, "delay": 5.0},
            RecoveryStrategy.WAIT_AND_RETRY: {"max_attempts": 3, "wait_time": 10.0},
            RecoveryStrategy.REFRESH_PAGE: {"max_attempts": 2, "wait_after": 3.0},
            RecoveryStrategy.NAVIGATE_BACK: {"max_attempts": 1, "wait_after": 2.0},
            RecoveryStrategy.RESTART_SESSION: {"max_attempts": 1},
            RecoveryStrategy.MANUAL_INTERVENTION: {"timeout": 300},  # 5 minutes
            RecoveryStrategy.ABORT_OPERATION: {"max_attempts": 1}
        }
    
    def classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorType:
        """Classify an error based on its type and context"""
        error_message = str(error).lower()
        
        # Navigation errors
        if "navigation" in error_message or "goto" in error_message:
            return ErrorType.NAVIGATION_FAILED
        
        # Element not found errors
        if ("element" in error_message and "not found" in error_message) or \
           "selector" in error_message or "locator" in error_message:
            return ErrorType.ELEMENT_NOT_FOUND
        
        # Extraction errors
        if "extract" in error_message or "parsing" in error_message:
            return ErrorType.EXTRACTION_FAILED
        
        # Form interaction errors
        if "form" in error_message or "input" in error_message or "click" in error_message:
            return ErrorType.FORM_INTERACTION_FAILED
        
        # Timeout errors
        if "timeout" in error_message or "timed out" in error_message:
            return ErrorType.TIMEOUT_ERROR
        
        # Network errors
        if "network" in error_message or "connection" in error_message or \
           "dns" in error_message or "http" in error_message:
            return ErrorType.NETWORK_ERROR
        
        # CAPTCHA detection
        if "captcha" in error_message or "recaptcha" in error_message or \
           "verification" in error_message:
            return ErrorType.CAPTCHA_DETECTED
        
        # Rate limiting
        if "rate limit" in error_message or "too many requests" in error_message or \
           "429" in error_message:
            return ErrorType.RATE_LIMITED
        
        # Session expired
        if "session" in error_message and ("expired" in error_message or "invalid" in error_message):
            return ErrorType.SESSION_EXPIRED
        
        return ErrorType.UNKNOWN_ERROR
    
    def create_error_context(
        self,
        error: Exception,
        session_id: str,
        operation: str,
        page_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Create error context from an exception"""
        error_type = self.classify_error(error, metadata or {})
        
        return ErrorContext(
            error_type=error_type,
            error_message=str(error),
            session_id=session_id,
            operation=operation,
            timestamp=datetime.utcnow(),
            page_url=page_url,
            stack_trace=None,  # Could add traceback if needed
            retry_count=0,
            metadata=metadata
        )
    
    def record_error(self, error_context: ErrorContext):
        """Record an error in the error history"""
        session_id = error_context.session_id
        
        if session_id not in self.error_history:
            self.error_history[session_id] = []
        
        self.error_history[session_id].append(error_context)
        
        # Keep only recent errors (last 50 per session)
        if len(self.error_history[session_id]) > 50:
            self.error_history[session_id] = self.error_history[session_id][-50:]
        
        logger.warning(f"Recorded error for session {session_id}: {error_context.error_type.value}")
    
    async def handle_error(
        self,
        error_context: ErrorContext,
        stagehand_controller,
        recovery_callback: Optional[Callable] = None
    ) -> RecoveryResult:
        """Handle an error using appropriate recovery strategies"""
        start_time = datetime.utcnow()
        
        # Record the error
        self.record_error(error_context)
        
        # Get recovery strategies for this error type
        strategies = self.recovery_strategies.get(
            error_context.error_type,
            [RecoveryStrategy.RETRY_WITH_DELAY, RecoveryStrategy.ABORT_OPERATION]
        )
        
        # Try each recovery strategy
        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery strategy: {strategy.value} for error: {error_context.error_type.value}")
                
                recovery_result = await self._execute_recovery_strategy(
                    strategy,
                    error_context,
                    stagehand_controller,
                    recovery_callback
                )
                
                if recovery_result.success:
                    recovery_time = (datetime.utcnow() - start_time).total_seconds()
                    recovery_result.recovery_time = recovery_time
                    
                    logger.info(f"Recovery successful using {strategy.value} in {recovery_time:.2f}s")
                    return recovery_result
                
            except Exception as recovery_error:
                logger.error(f"Recovery strategy {strategy.value} failed: {recovery_error}")
                continue
        
        # All recovery strategies failed
        recovery_time = (datetime.utcnow() - start_time).total_seconds()
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ABORT_OPERATION,
            recovery_time=recovery_time,
            error_resolved=False,
            recovery_notes="All recovery strategies failed"
        )
    
    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        error_context: ErrorContext,
        stagehand_controller,
        recovery_callback: Optional[Callable]
    ) -> RecoveryResult:
        """Execute a specific recovery strategy"""
        config = self.strategy_config.get(strategy, {})
        
        if strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            return await self._retry_immediate(error_context, recovery_callback, config)
        
        elif strategy == RecoveryStrategy.RETRY_WITH_DELAY:
            return await self._retry_with_delay(error_context, recovery_callback, config)
        
        elif strategy == RecoveryStrategy.WAIT_AND_RETRY:
            return await self._wait_and_retry(error_context, recovery_callback, config)
        
        elif strategy == RecoveryStrategy.REFRESH_PAGE:
            return await self._refresh_page(error_context, stagehand_controller, config)
        
        elif strategy == RecoveryStrategy.NAVIGATE_BACK:
            return await self._navigate_back(error_context, stagehand_controller, config)
        
        elif strategy == RecoveryStrategy.RESTART_SESSION:
            return await self._restart_session(error_context, stagehand_controller, config)
        
        elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            return await self._manual_intervention(error_context, config)
        
        elif strategy == RecoveryStrategy.ABORT_OPERATION:
            return RecoveryResult(
                success=False,
                strategy_used=strategy,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes="Operation aborted due to unrecoverable error"
            )
        
        return RecoveryResult(
            success=False,
            strategy_used=strategy,
            recovery_time=0.0,
            error_resolved=False,
            recovery_notes="Unknown recovery strategy"
        )
    
    async def _retry_immediate(
        self,
        error_context: ErrorContext,
        recovery_callback: Optional[Callable],
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Retry the operation immediately"""
        if not recovery_callback:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_IMMEDIATE,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes="No recovery callback provided"
            )
        
        try:
            await recovery_callback()
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.RETRY_IMMEDIATE,
                recovery_time=0.0,
                error_resolved=True,
                recovery_notes="Immediate retry successful"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_IMMEDIATE,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes=f"Immediate retry failed: {str(e)}"
            )
    
    async def _retry_with_delay(
        self,
        error_context: ErrorContext,
        recovery_callback: Optional[Callable],
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Retry the operation after a delay"""
        if not recovery_callback:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_DELAY,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes="No recovery callback provided"
            )
        
        delay = config.get("delay", 5.0)
        await asyncio.sleep(delay)
        
        try:
            await recovery_callback()
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.RETRY_WITH_DELAY,
                recovery_time=delay,
                error_resolved=True,
                recovery_notes=f"Retry after {delay}s delay successful"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_DELAY,
                recovery_time=delay,
                error_resolved=False,
                recovery_notes=f"Retry after delay failed: {str(e)}"
            )
    
    async def _wait_and_retry(
        self,
        error_context: ErrorContext,
        recovery_callback: Optional[Callable],
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Wait for conditions to improve then retry"""
        wait_time = config.get("wait_time", 10.0)
        await asyncio.sleep(wait_time)
        
        if not recovery_callback:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.WAIT_AND_RETRY,
                recovery_time=wait_time,
                error_resolved=False,
                recovery_notes="No recovery callback provided"
            )
        
        try:
            await recovery_callback()
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.WAIT_AND_RETRY,
                recovery_time=wait_time,
                error_resolved=True,
                recovery_notes=f"Wait and retry after {wait_time}s successful"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.WAIT_AND_RETRY,
                recovery_time=wait_time,
                error_resolved=False,
                recovery_notes=f"Wait and retry failed: {str(e)}"
            )
    
    async def _refresh_page(
        self,
        error_context: ErrorContext,
        stagehand_controller,
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Refresh the current page"""
        try:
            stagehand = await stagehand_controller.get_stagehand(error_context.session_id)
            await stagehand.page.reload(wait_until="networkidle")
            
            wait_after = config.get("wait_after", 3.0)
            await asyncio.sleep(wait_after)
            
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.REFRESH_PAGE,
                recovery_time=wait_after,
                error_resolved=True,
                recovery_notes="Page refresh successful"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.REFRESH_PAGE,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes=f"Page refresh failed: {str(e)}"
            )
    
    async def _navigate_back(
        self,
        error_context: ErrorContext,
        stagehand_controller,
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Navigate back to the previous page"""
        try:
            stagehand = await stagehand_controller.get_stagehand(error_context.session_id)
            await stagehand.page.go_back(wait_until="networkidle")
            
            wait_after = config.get("wait_after", 2.0)
            await asyncio.sleep(wait_after)
            
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.NAVIGATE_BACK,
                recovery_time=wait_after,
                error_resolved=True,
                recovery_notes="Navigate back successful"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.NAVIGATE_BACK,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes=f"Navigate back failed: {str(e)}"
            )
    
    async def _restart_session(
        self,
        error_context: ErrorContext,
        stagehand_controller,
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Restart the browser session"""
        try:
            # Clean up current session
            await stagehand_controller.cleanup_session(error_context.session_id)
            
            # This would require integration with session manager to create new session
            # For now, just mark as requiring manual intervention
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RESTART_SESSION,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes="Session restart requires manual intervention"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RESTART_SESSION,
                recovery_time=0.0,
                error_resolved=False,
                recovery_notes=f"Session restart failed: {str(e)}"
            )
    
    async def _manual_intervention(
        self,
        error_context: ErrorContext,
        config: Dict[str, Any]
    ) -> RecoveryResult:
        """Request manual intervention"""
        timeout = config.get("timeout", 300)  # 5 minutes
        
        logger.critical(f"Manual intervention required for session {error_context.session_id}: {error_context.error_message}")
        
        # In a real implementation, this would send notifications to operators
        # For now, just wait and return failure
        await asyncio.sleep(min(timeout, 30))  # Don't actually wait the full timeout in automation
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            recovery_time=30.0,
            error_resolved=False,
            recovery_notes="Manual intervention requested but not implemented"
        )
    
    def get_error_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get error statistics for analysis"""
        if session_id:
            errors = self.error_history.get(session_id, [])
        else:
            errors = []
            for session_errors in self.error_history.values():
                errors.extend(session_errors)
        
        if not errors:
            return {"total_errors": 0}
        
        # Count errors by type
        error_counts = {}
        for error in errors:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Calculate error rate over time
        recent_errors = [e for e in errors if e.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        return {
            "total_errors": len(errors),
            "recent_errors": len(recent_errors),
            "error_types": error_counts,
            "most_common_error": max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None,
            "error_rate_per_hour": len(recent_errors)
        }
    
    def should_abort_session(self, session_id: str) -> bool:
        """Determine if a session should be aborted due to too many errors"""
        errors = self.error_history.get(session_id, [])
        
        # Check for too many recent errors
        recent_errors = [e for e in errors if e.timestamp > datetime.utcnow() - timedelta(minutes=30)]
        
        if len(recent_errors) > 10:  # More than 10 errors in 30 minutes
            return True
        
        # Check for critical error types
        critical_errors = [e for e in recent_errors if e.error_type in [
            ErrorType.CAPTCHA_DETECTED,
            ErrorType.RATE_LIMITED,
            ErrorType.SESSION_EXPIRED
        ]]
        
        if len(critical_errors) > 2:  # More than 2 critical errors
            return True
        
        return False


# Decorator for automatic error handling
def with_error_handling(error_handler: StagehandErrorHandler):
    """Decorator to automatically handle errors in Stagehand operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            session_id = kwargs.get('session_id') or (args[1] if len(args) > 1 else None)
            operation = func.__name__
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not session_id:
                    raise  # Can't handle without session_id
                
                error_context = error_handler.create_error_context(
                    e, session_id, operation
                )
                
                # Attempt recovery
                stagehand_controller = args[0] if args else None
                if stagehand_controller:
                    recovery_result = await error_handler.handle_error(
                        error_context,
                        stagehand_controller,
                        lambda: func(*args, **kwargs)
                    )
                    
                    if recovery_result.success:
                        return await func(*args, **kwargs)
                
                # If recovery failed, re-raise the original exception
                raise
        
        return wrapper
    return decorator