"""
Core tests for enhanced error recovery and resilience system
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import random

from shared.error_handling import (
    ErrorClassifier, ErrorCategory, ErrorSeverity, ErrorInfo,
    ExponentialBackoffWithJitter, RetryConfig, ErrorRecoveryManager,
    ResilientServiceWrapper
)
from shared.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState


class TestErrorClassifier:
    """Test error classification functionality"""
    
    def test_classify_network_errors(self):
        """Test classification of network errors"""
        errors = [
            ConnectionError("Connection failed"),
            TimeoutError("Request timed out"),
            OSError("Network unreachable")
        ]
        
        for error in errors:
            category, severity = ErrorClassifier.classify_error(error)
            assert category == ErrorCategory.NETWORK
            assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_authentication_errors(self):
        """Test classification of authentication errors"""
        errors = [
            PermissionError("Access denied"),
            Exception("401 Unauthorized"),
            Exception("403 Forbidden")
        ]
        
        for error in errors:
            category, severity = ErrorClassifier.classify_error(error)
            assert category == ErrorCategory.AUTHENTICATION
            assert severity == ErrorSeverity.HIGH
    
    def test_classify_rate_limit_errors(self):
        """Test classification of rate limit errors"""
        errors = [
            Exception("Rate limit exceeded"),
            Exception("Too many requests"),
            Exception("HTTP 429")
        ]
        
        for error in errors:
            category, severity = ErrorClassifier.classify_error(error)
            assert category == ErrorCategory.RATE_LIMIT
            assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_browser_automation_errors(self):
        """Test classification of browser automation errors"""
        errors = [
            Exception("Stagehand timeout"),
            Exception("Browserbase session failed"),
            Exception("Selenium error")
        ]
        
        for error in errors:
            category, severity = ErrorClassifier.classify_error(error)
            assert category == ErrorCategory.BROWSER_AUTOMATION
            assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_with_context(self):
        """Test error classification with context"""
        error = Exception("Service unavailable")
        context = {"service_name": "google_docs"}
        
        category, severity = ErrorClassifier.classify_error(error, context)
        assert category == ErrorCategory.EXTERNAL_SERVICE
        assert severity == ErrorSeverity.MEDIUM


class TestExponentialBackoffWithJitter:
    """Test exponential backoff with jitter"""
    
    def test_basic_exponential_backoff(self):
        """Test basic exponential backoff calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        backoff = ExponentialBackoffWithJitter(config)
        
        assert backoff.calculate_delay(0) == 0
        assert backoff.calculate_delay(1) == 1.0
        assert backoff.calculate_delay(2) == 2.0
        assert backoff.calculate_delay(3) == 4.0
        assert backoff.calculate_delay(4) == 8.0
    
    def test_max_delay_limit(self):
        """Test maximum delay limit"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        backoff = ExponentialBackoffWithJitter(config)
        
        assert backoff.calculate_delay(10) == 5.0  # Should be capped at max_delay
    
    def test_jitter_application(self):
        """Test jitter application"""
        config = RetryConfig(base_delay=10.0, exponential_base=2.0, jitter=True, jitter_range=0.1)
        backoff = ExponentialBackoffWithJitter(config)
        
        # Run multiple times to test jitter randomness
        delays = [backoff.calculate_delay(1) for _ in range(100)]
        
        # All delays should be around 10.0 with jitter
        assert all(9.0 <= delay <= 11.0 for delay in delays)
        
        # Should have some variation due to jitter
        assert len(set(delays)) > 1


class TestErrorRecoveryManager:
    """Test error recovery manager"""
    
    @pytest.fixture
    def recovery_manager(self):
        return ErrorRecoveryManager()
    
    @pytest.mark.asyncio
    async def test_handle_network_error(self, recovery_manager):
        """Test handling of network errors"""
        error_info = ErrorInfo(
            exception=ConnectionError("Network failed"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            service_name="test_service",
            operation="test_operation"
        )
        
        result = await recovery_manager.handle_error(error_info)
        
        assert result["action"] == "retry_with_backoff"
        assert "delay" in result
        assert not result["recovered"]
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, recovery_manager):
        """Test handling of rate limit errors"""
        error_info = ErrorInfo(
            exception=Exception("Rate limit exceeded, retry-after: 120"),
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            service_name="test_service",
            operation="test_operation"
        )
        
        result = await recovery_manager.handle_error(error_info)
        
        assert result["action"] == "wait_and_retry"
        assert result["delay"] == 120.0
    
    @pytest.mark.asyncio
    async def test_handle_authentication_error(self, recovery_manager):
        """Test handling of authentication errors"""
        error_info = ErrorInfo(
            exception=PermissionError("Access denied"),
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            service_name="test_service",
            operation="test_operation"
        )
        
        result = await recovery_manager.handle_error(error_info)
        
        assert result["action"] == "refresh_credentials"
        assert not result["recovered"]
    
    def test_error_statistics(self, recovery_manager):
        """Test error statistics collection"""
        # Add some test errors
        for i in range(5):
            error_info = ErrorInfo(
                exception=ConnectionError(f"Error {i}"),
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                service_name="test_service",
                operation="test_operation"
            )
            recovery_manager._record_error(error_info)
        
        stats = recovery_manager.get_error_statistics()
        
        assert stats["total_errors"] == 5
        assert stats["categories"]["network"] == 5
        assert stats["most_common_category"] == "network"
        assert stats["most_affected_service"] == "test_service"


class TestResilientServiceWrapper:
    """Test resilient service wrapper"""
    
    @pytest.fixture
    def wrapper(self):
        import uuid
        unique_name = f"test_service_{uuid.uuid4().hex[:8]}"
        return ResilientServiceWrapper(
            service_name=unique_name,
            retry_config=RetryConfig(max_retries=3, base_delay=0.1),
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5)  # Higher threshold for tests
        )
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, wrapper):
        """Test successful function execution"""
        async def success_func():
            return "success"
        
        result = await wrapper.execute_with_resilience("test_op", success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, wrapper):
        """Test retry mechanism on failures"""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        result = await wrapper.execute_with_resilience("test_op", failing_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, wrapper):
        """Test behavior when max retries are exceeded"""
        async def always_failing_func():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            await wrapper.execute_with_resilience("test_op", always_failing_func)
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self, wrapper):
        """Test handling of non-retryable errors"""
        wrapper.retry_config.non_retryable_exceptions = (ValueError,)
        
        async def validation_error_func():
            raise ValueError("Invalid input")
        
        with pytest.raises(ValueError):
            await wrapper.execute_with_resilience("test_op", validation_error_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, wrapper):
        """Test integration with circuit breaker"""
        async def failing_func():
            raise ConnectionError("Service down")
        
        # Trigger circuit breaker opening
        for _ in range(3):
            try:
                await wrapper.execute_with_resilience("test_op", failing_func)
            except ConnectionError:
                pass
        
        # Circuit breaker should now be open
        circuit_breaker = await wrapper._get_circuit_breaker()
        assert circuit_breaker.state == CircuitState.OPEN


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with error recovery"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_recovery(self):
        """Test circuit breaker working with error recovery"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        breaker = CircuitBreaker("test_service", config)
        
        async def failing_service():
            raise ConnectionError("Service down")
        
        # Trigger failures to open circuit
        for _ in range(3):
            try:
                await breaker.call(failing_service)
            except ConnectionError:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Circuit should allow one request (half-open)
        try:
            await breaker.call(failing_service)
        except ConnectionError:
            pass
        
        assert breaker.state == CircuitState.OPEN  # Should go back to open after failure


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple resilience patterns"""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_handling(self):
        """Test handling of cascading failures across services"""
        failure_count = 0
        
        async def cascading_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 5:
                raise Exception(f"Cascading failure {failure_count}")
            return "recovered"
        
        wrapper = ResilientServiceWrapper(
            "cascading_service",
            retry_config=RetryConfig(max_retries=10, base_delay=0.01)
        )
        
        result = await wrapper.execute_with_resilience("cascade_test", cascading_service)
        assert result == "recovered"
        assert failure_count == 6
    
    @pytest.mark.asyncio
    async def test_mixed_error_types_handling(self):
        """Test handling of mixed error types in sequence"""
        call_sequence = [
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            PermissionError("Auth error"),
            ValueError("Validation error"),
            "success"
        ]
        call_index = 0
        
        async def mixed_errors_service():
            nonlocal call_index
            if call_index < len(call_sequence) - 1:
                error = call_sequence[call_index]
                call_index += 1
                raise error
            return call_sequence[call_index]
        
        wrapper = ResilientServiceWrapper(
            "mixed_service",
            retry_config=RetryConfig(
                max_retries=10,
                base_delay=0.01,
                non_retryable_exceptions=(ValueError,)
            )
        )
        
        # Should fail on ValueError (non-retryable)
        with pytest.raises(ValueError):
            await wrapper.execute_with_resilience("mixed_test", mixed_errors_service)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])