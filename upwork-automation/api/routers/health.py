"""
Health monitoring and error recovery API endpoints
"""
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.health_monitoring_service import health_monitoring_service
from shared.error_handling import error_recovery_manager
from shared.circuit_breaker import circuit_breaker_registry
from shared.utils import setup_logging

logger = setup_logging("health-api")

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    details: Dict[str, Any]


class ServiceHealthResponse(BaseModel):
    """Service health response model"""
    name: str
    status: str
    last_check: Optional[datetime]
    consecutive_failures: int
    success_rate: float
    response_time_ms: float
    error_message: Optional[str]


class SystemHealthSummaryResponse(BaseModel):
    """System health summary response model"""
    overall_status: str
    total_services: int
    healthy_services: int
    degraded_services: int
    unhealthy_services: int
    health_percentage: float
    last_updated: datetime


class ErrorStatisticsResponse(BaseModel):
    """Error statistics response model"""
    total_errors: int
    recent_errors_1h: int
    error_rate_1h: float
    categories: Dict[str, int]
    severities: Dict[str, int]
    services: Dict[str, int]
    most_common_category: Optional[str]
    most_affected_service: Optional[str]


class CircuitBreakerStatsResponse(BaseModel):
    """Circuit breaker statistics response model"""
    name: str
    state: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    consecutive_failures: int
    consecutive_successes: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    state_changes: int


@router.get("/", response_model=HealthResponse)
async def get_overall_health():
    """Get overall system health status"""
    try:
        summary = health_monitoring_service.get_system_health_summary()
        
        return HealthResponse(
            status=summary["overall_status"],
            timestamp=datetime.utcnow(),
            details=summary
        )
    except Exception as e:
        logger.error(f"Error getting overall health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/summary", response_model=SystemHealthSummaryResponse)
async def get_health_summary():
    """Get system health summary"""
    try:
        summary = health_monitoring_service.get_system_health_summary()
        
        return SystemHealthSummaryResponse(
            overall_status=summary["overall_status"],
            total_services=summary["total_services"],
            healthy_services=summary["healthy_services"],
            degraded_services=summary["degraded_services"],
            unhealthy_services=summary["unhealthy_services"],
            health_percentage=summary["health_percentage"],
            last_updated=datetime.fromisoformat(summary["last_updated"])
        )
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health summary")


@router.get("/services", response_model=Dict[str, ServiceHealthResponse])
async def get_all_services_health():
    """Get health status for all services"""
    try:
        services_health = health_monitoring_service.get_service_status()
        
        response = {}
        for name, health_data in services_health.items():
            response[name] = ServiceHealthResponse(
                name=name,
                status=health_data["status"],
                last_check=datetime.fromisoformat(health_data["last_check"]) if health_data["last_check"] else None,
                consecutive_failures=health_data["consecutive_failures"],
                success_rate=health_data["success_rate"],
                response_time_ms=health_data["response_time_ms"],
                error_message=health_data["error_message"]
            )
        
        return response
    except Exception as e:
        logger.error(f"Error getting services health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get services health")


@router.get("/services/{service_name}", response_model=ServiceHealthResponse)
async def get_service_health(service_name: str):
    """Get health status for a specific service"""
    try:
        health_data = health_monitoring_service.get_service_status(service_name)
        
        if "error" in health_data:
            raise HTTPException(status_code=404, detail=health_data["error"])
        
        return ServiceHealthResponse(
            name=health_data["name"],
            status=health_data["status"],
            last_check=datetime.fromisoformat(health_data["last_check"]) if health_data["last_check"] else None,
            consecutive_failures=health_data["consecutive_failures"],
            success_rate=health_data["success_rate"],
            response_time_ms=health_data["response_time_ms"],
            error_message=health_data["error_message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service health for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service health")


@router.get("/errors/statistics", response_model=ErrorStatisticsResponse)
async def get_error_statistics():
    """Get error statistics and patterns"""
    try:
        stats = error_recovery_manager.get_error_statistics()
        
        return ErrorStatisticsResponse(
            total_errors=stats["total_errors"],
            recent_errors_1h=stats.get("recent_errors_1h", 0),
            error_rate_1h=stats.get("error_rate_1h", 0.0),
            categories=stats.get("categories", {}),
            severities=stats.get("severities", {}),
            services=stats.get("services", {}),
            most_common_category=stats.get("most_common_category"),
            most_affected_service=stats.get("most_affected_service")
        )
    except Exception as e:
        logger.error(f"Error getting error statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error statistics")


@router.get("/circuit-breakers", response_model=Dict[str, CircuitBreakerStatsResponse])
async def get_circuit_breaker_stats():
    """Get circuit breaker statistics for all services"""
    try:
        all_stats = await circuit_breaker_registry.get_all_stats()
        
        response = {}
        for name, stats in all_stats.items():
            response[name] = CircuitBreakerStatsResponse(
                name=stats["name"],
                state=stats["state"],
                total_requests=stats["total_requests"],
                successful_requests=stats["successful_requests"],
                failed_requests=stats["failed_requests"],
                success_rate=stats["success_rate"],
                consecutive_failures=stats["consecutive_failures"],
                consecutive_successes=stats["consecutive_successes"],
                last_failure_time=datetime.fromisoformat(stats["last_failure_time"]) if stats["last_failure_time"] else None,
                last_success_time=datetime.fromisoformat(stats["last_success_time"]) if stats["last_success_time"] else None,
                state_changes=stats["state_changes"]
            )
        
        return response
    except Exception as e:
        logger.error(f"Error getting circuit breaker stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker statistics")


@router.get("/circuit-breakers/{service_name}", response_model=CircuitBreakerStatsResponse)
async def get_circuit_breaker_stats_for_service(service_name: str):
    """Get circuit breaker statistics for a specific service"""
    try:
        breaker = await circuit_breaker_registry.get_breaker(service_name)
        stats = breaker.get_stats()
        
        return CircuitBreakerStatsResponse(
            name=stats["name"],
            state=stats["state"],
            total_requests=stats["total_requests"],
            successful_requests=stats["successful_requests"],
            failed_requests=stats["failed_requests"],
            success_rate=stats["success_rate"],
            consecutive_failures=stats["consecutive_failures"],
            consecutive_successes=stats["consecutive_successes"],
            last_failure_time=datetime.fromisoformat(stats["last_failure_time"]) if stats["last_failure_time"] else None,
            last_success_time=datetime.fromisoformat(stats["last_success_time"]) if stats["last_success_time"] else None,
            state_changes=stats["state_changes"]
        )
    except Exception as e:
        logger.error(f"Error getting circuit breaker stats for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker statistics")


@router.post("/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(service_name: str):
    """Manually reset a circuit breaker"""
    try:
        breaker = await circuit_breaker_registry.get_breaker(service_name)
        await breaker.reset()
        
        return {"message": f"Circuit breaker for {service_name} has been reset"}
    except Exception as e:
        logger.error(f"Error resetting circuit breaker for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers():
    """Reset all circuit breakers"""
    try:
        await circuit_breaker_registry.reset_all()
        
        return {"message": "All circuit breakers have been reset"}
    except Exception as e:
        logger.error(f"Error resetting all circuit breakers: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breakers")


@router.post("/monitoring/start")
async def start_health_monitoring():
    """Start health monitoring for all services"""
    try:
        await health_monitoring_service.start_monitoring()
        
        return {"message": "Health monitoring started"}
    except Exception as e:
        logger.error(f"Error starting health monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to start health monitoring")


@router.post("/monitoring/stop")
async def stop_health_monitoring():
    """Stop health monitoring"""
    try:
        await health_monitoring_service.stop_monitoring()
        
        return {"message": "Health monitoring stopped"}
    except Exception as e:
        logger.error(f"Error stopping health monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop health monitoring")


@router.get("/monitoring/status")
async def get_monitoring_status():
    """Get health monitoring status"""
    try:
        return {
            "is_running": health_monitoring_service.is_running,
            "monitored_services": list(health_monitoring_service.health_checks.keys()),
            "active_tasks": len(health_monitoring_service.monitoring_tasks)
        }
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring status")