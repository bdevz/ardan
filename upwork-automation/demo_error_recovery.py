#!/usr/bin/env python3
"""
Demonstration of the enhanced error recovery and resilience system
"""
import asyncio
import logging
from datetime import datetime
from shared.error_handling import (
    ResilientServiceWrapper, RetryConfig, ErrorRecoveryManager,
    resilient_service, ErrorClassifier, ErrorCategory, ErrorSeverity
)
from shared.circuit_breaker import CircuitBreakerConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UnreliableService:
    """Simulates an unreliable external service"""
    
    def __init__(self):
        self.call_count = 0
        self.failure_rate = 0.7  # 70% failure rate initially
    
    async def unreliable_operation(self):
        """Operation that fails most of the time initially"""
        self.call_count += 1
        
        # Gradually improve success rate
        current_failure_rate = max(0.1, self.failure_rate - (self.call_count * 0.1))
        
        import random
        if random.random() < current_failure_rate:
            if self.call_count % 3 == 0:
                raise ConnectionError("Network connection failed")
            elif self.call_count % 3 == 1:
                raise TimeoutError("Request timed out")
            else:
                raise Exception("Service temporarily unavailable")
        
        return f"Success on attempt {self.call_count}"


@resilient_service(
    "demo_service",
    retry_config=RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=10.0,
        jitter=True
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5,
        timeout=10.0
    )
)
class ResilientDemoService:
    """Demo service with resilience patterns applied"""
    
    def __init__(self):
        self.unreliable_service = UnreliableService()
    
    async def process_data(self, data: str):
        """Process data using unreliable service"""
        result = await self.unreliable_service.unreliable_operation()
        return f"Processed '{data}': {result}"


async def demonstrate_error_classification():
    """Demonstrate error classification"""
    print("\n=== Error Classification Demo ===")
    
    test_errors = [
        ConnectionError("Network connection failed"),
        TimeoutError("Request timed out"),
        PermissionError("Access denied"),
        Exception("Rate limit exceeded"),
        Exception("Stagehand timeout"),
        ValueError("Invalid input")
    ]
    
    for error in test_errors:
        category, severity = ErrorClassifier.classify_error(error)
        print(f"{type(error).__name__}: {error} -> {category.value} ({severity.value})")


async def demonstrate_resilient_wrapper():
    """Demonstrate resilient service wrapper"""
    print("\n=== Resilient Service Wrapper Demo ===")
    
    wrapper = ResilientServiceWrapper(
        service_name="demo_wrapper",
        retry_config=RetryConfig(max_retries=3, base_delay=0.5),
        circuit_breaker_config=CircuitBreakerConfig(failure_threshold=2)
    )
    
    unreliable_service = UnreliableService()
    
    for i in range(5):
        try:
            result = await wrapper.execute_with_resilience(
                "unreliable_operation",
                unreliable_service.unreliable_operation
            )
            print(f"Call {i+1}: {result}")
        except Exception as e:
            print(f"Call {i+1}: Failed with {type(e).__name__}: {e}")
        
        await asyncio.sleep(1)


async def demonstrate_resilient_service_decorator():
    """Demonstrate resilient service decorator"""
    print("\n=== Resilient Service Decorator Demo ===")
    
    service = ResilientDemoService()
    
    test_data = ["data1", "data2", "data3", "data4", "data5"]
    
    for data in test_data:
        try:
            result = await service.process_data(data)
            print(f"✅ {result}")
        except Exception as e:
            print(f"❌ Failed to process '{data}': {type(e).__name__}: {e}")
        
        await asyncio.sleep(1)


async def demonstrate_circuit_breaker_recovery():
    """Demonstrate circuit breaker recovery"""
    print("\n=== Circuit Breaker Recovery Demo ===")
    
    from shared.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=3)
    breaker = CircuitBreaker("recovery_demo", config)
    
    failure_count = 0
    
    async def sometimes_failing_service():
        nonlocal failure_count
        failure_count += 1
        
        # Fail first 4 times, then succeed
        if failure_count <= 4:
            raise ConnectionError(f"Failure {failure_count}")
        return f"Success after {failure_count} attempts"
    
    for i in range(10):
        try:
            result = await breaker.call(sometimes_failing_service)
            print(f"Attempt {i+1}: {result} (State: {breaker.state.value})")
        except Exception as e:
            print(f"Attempt {i+1}: {type(e).__name__}: {e} (State: {breaker.state.value})")
        
        # Show circuit breaker stats
        stats = breaker.get_stats()
        print(f"  Stats: {stats['successful_requests']}/{stats['total_requests']} success rate: {stats['success_rate']:.1%}")
        
        await asyncio.sleep(1)


async def demonstrate_error_recovery_manager():
    """Demonstrate error recovery manager"""
    print("\n=== Error Recovery Manager Demo ===")
    
    from shared.error_handling import ErrorInfo, error_recovery_manager
    
    test_errors = [
        ErrorInfo(
            exception=ConnectionError("Network failed"),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            service_name="demo_service",
            operation="network_call"
        ),
        ErrorInfo(
            exception=Exception("Rate limit exceeded, retry-after: 30"),
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            service_name="demo_service",
            operation="api_call"
        ),
        ErrorInfo(
            exception=PermissionError("Access denied"),
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            service_name="demo_service",
            operation="auth_call"
        )
    ]
    
    for error_info in test_errors:
        recovery_result = await error_recovery_manager.handle_error(error_info)
        print(f"Error: {error_info.exception}")
        print(f"Recovery: {recovery_result}")
        print()
    
    # Show error statistics
    stats = error_recovery_manager.get_error_statistics()
    print("Error Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


async def main():
    """Run all demonstrations"""
    print("🚀 Enhanced Error Recovery and Resilience System Demo")
    print("=" * 60)
    
    try:
        await demonstrate_error_classification()
        await demonstrate_resilient_wrapper()
        await demonstrate_resilient_service_decorator()
        await demonstrate_circuit_breaker_recovery()
        await demonstrate_error_recovery_manager()
        
        print("\n✅ All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())