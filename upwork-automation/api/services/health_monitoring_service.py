"""
Service health monitoring and alerting system
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import aiohttp
import json

from shared.utils import setup_logging
from shared.error_handling import ServiceHealthMonitor, error_recovery_manager
from .notification_service import SlackNotificationService

logger = setup_logging("health_monitoring", "INFO")


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    name: str
    check_function: Callable
    interval_seconds: int = 60
    timeout_seconds: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    critical: bool = False
    degradation_strategy: Optional[Callable] = None


@dataclass
class ServiceStatus:
    """Service status information"""
    name: str
    status: str  # healthy, degraded, unhealthy, unknown
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    success_rate: float = 0.0
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitoringService:
    """
    Comprehensive service health monitoring with automatic alerting
    """
    
    def __init__(self):
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.health_checks: Dict[str, HealthCheckConfig] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.notification_service = SlackNotificationService()
        self.is_running = False
        
        # Register default health checks
        self._register_default_health_checks()
    
    def _register_default_health_checks(self):
        """Register default health checks for core services"""
        
        # Database health check
        self.register_health_check(HealthCheckConfig(
            name="database",
            check_function=self._check_database_health,
            interval_seconds=30,
            failure_threshold=2,
            critical=True,
            degradation_strategy=self._degrade_database_operations
        ))
        
        # Redis health check
        self.register_health_check(HealthCheckConfig(
            name="redis",
            check_function=self._check_redis_health,
            interval_seconds=30,
            failure_threshold=2,
            critical=True,
            degradation_strategy=self._degrade_queue_operations
        ))
        
        # Browserbase health check
        self.register_health_check(HealthCheckConfig(
            name="browserbase",
            check_function=self._check_browserbase_health,
            interval_seconds=60,
            failure_threshold=3,
            critical=False,
            degradation_strategy=self._degrade_browser_operations
        ))
        
        # Google Services health check
        self.register_health_check(HealthCheckConfig(
            name="google_services",
            check_function=self._check_google_services_health,
            interval_seconds=120,
            failure_threshold=3,
            critical=False,
            degradation_strategy=self._degrade_google_operations
        ))
        
        # Slack health check
        self.register_health_check(HealthCheckConfig(
            name="slack",
            check_function=self._check_slack_health,
            interval_seconds=300,
            failure_threshold=5,
            critical=False
        ))
        
        # n8n health check
        self.register_health_check(HealthCheckConfig(
            name="n8n",
            check_function=self._check_n8n_health,
            interval_seconds=120,
            failure_threshold=3,
            critical=False,
            degradation_strategy=self._degrade_workflow_operations
        ))
    
    def register_health_check(self, config: HealthCheckConfig):
        """Register a new health check"""
        self.health_checks[config.name] = config
        self.service_statuses[config.name] = ServiceStatus(
            name=config.name,
            status="unknown"
        )
        
        logger.info(f"Registered health check for {config.name}")
    
    async def start_monitoring(self):
        """Start health monitoring for all registered services"""
        if self.is_running:
            logger.warning("Health monitoring is already running")
            return
        
        self.is_running = True
        logger.info("Starting health monitoring for all services")
        
        # Start monitoring tasks for each service
        for service_name, config in self.health_checks.items():
            task = asyncio.create_task(self._monitor_service(service_name, config))
            self.monitoring_tasks[service_name] = task
        
        # Start alerting task
        self.monitoring_tasks["alerting"] = asyncio.create_task(self._alerting_loop())
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping health monitoring")
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        self.monitoring_tasks.clear()
    
    async def _monitor_service(self, service_name: str, config: HealthCheckConfig):
        """Monitor a specific service"""
        logger.info(f"Starting health monitoring for {service_name}")
        
        while self.is_running:
            try:
                await self._perform_health_check(service_name, config)
                await asyncio.sleep(config.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring for {service_name}: {e}")
                await asyncio.sleep(config.interval_seconds)
    
    async def _perform_health_check(self, service_name: str, config: HealthCheckConfig):
        """Perform health check for a service"""
        status = self.service_statuses[service_name]
        start_time = datetime.utcnow()
        
        try:
            # Perform health check with timeout
            is_healthy = await asyncio.wait_for(
                config.check_function(),
                timeout=config.timeout_seconds
            )
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update status
            status.last_check = datetime.utcnow()
            status.total_checks += 1
            status.response_time_ms = response_time
            status.error_message = None
            
            if is_healthy:
                status.last_success = datetime.utcnow()
                status.consecutive_successes += 1
                status.consecutive_failures = 0
                
                # Determine status based on consecutive successes
                if status.status == "unhealthy" and status.consecutive_successes >= config.recovery_threshold:
                    await self._handle_service_recovery(service_name, status)
                elif status.status in ["unknown", "degraded"]:
                    status.status = "healthy"
            else:
                status.last_failure = datetime.utcnow()
                status.consecutive_failures += 1
                status.consecutive_successes = 0
                
                # Determine status based on consecutive failures
                if status.consecutive_failures >= config.failure_threshold:
                    await self._handle_service_failure(service_name, status, config)
                elif status.status == "healthy":
                    status.status = "degraded"
            
            # Update success rate
            successful_checks = status.total_checks - status.consecutive_failures
            status.success_rate = successful_checks / status.total_checks if status.total_checks > 0 else 0.0
            
            logger.debug(f"Health check for {service_name}: {status.status} ({response_time:.2f}ms)")
            
        except asyncio.TimeoutError:
            await self._handle_health_check_timeout(service_name, status, config)
        except Exception as e:
            await self._handle_health_check_error(service_name, status, config, e)
    
    async def _handle_service_failure(self, service_name: str, status: ServiceStatus, config: HealthCheckConfig):
        """Handle service failure"""
        old_status = status.status
        status.status = "unhealthy"
        status.error_message = f"Service failed {status.consecutive_failures} consecutive health checks"
        
        logger.error(f"Service {service_name} is now unhealthy after {status.consecutive_failures} failures")
        
        # Apply degradation strategy if available
        if config.degradation_strategy:
            try:
                await config.degradation_strategy(service_name)
                logger.info(f"Applied degradation strategy for {service_name}")
            except Exception as e:
                logger.error(f"Failed to apply degradation strategy for {service_name}: {e}")
        
        # Send alert if status changed
        if old_status != "unhealthy":
            await self._send_service_alert(service_name, status, "failure")
    
    async def _handle_service_recovery(self, service_name: str, status: ServiceStatus):
        """Handle service recovery"""
        old_status = status.status
        status.status = "healthy"
        status.error_message = None
        
        logger.info(f"Service {service_name} has recovered after {status.consecutive_successes} successful checks")
        
        # Send recovery alert if status changed from unhealthy
        if old_status == "unhealthy":
            await self._send_service_alert(service_name, status, "recovery")
    
    async def _handle_health_check_timeout(self, service_name: str, status: ServiceStatus, config: HealthCheckConfig):
        """Handle health check timeout"""
        status.last_check = datetime.utcnow()
        status.last_failure = datetime.utcnow()
        status.total_checks += 1
        status.consecutive_failures += 1
        status.consecutive_successes = 0
        status.error_message = f"Health check timed out after {config.timeout_seconds} seconds"
        
        if status.consecutive_failures >= config.failure_threshold:
            await self._handle_service_failure(service_name, status, config)
        
        logger.warning(f"Health check timeout for {service_name}")
    
    async def _handle_health_check_error(self, service_name: str, status: ServiceStatus, config: HealthCheckConfig, error: Exception):
        """Handle health check error"""
        status.last_check = datetime.utcnow()
        status.last_failure = datetime.utcnow()
        status.total_checks += 1
        status.consecutive_failures += 1
        status.consecutive_successes = 0
        status.error_message = str(error)
        
        if status.consecutive_failures >= config.failure_threshold:
            await self._handle_service_failure(service_name, status, config)
        
        logger.error(f"Health check error for {service_name}: {error}")
    
    async def _alerting_loop(self):
        """Main alerting loop for critical issues"""
        while self.is_running:
            try:
                await self._check_critical_services()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alerting loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_critical_services(self):
        """Check critical services and send alerts if needed"""
        critical_failures = []
        
        for service_name, config in self.health_checks.items():
            if config.critical:
                status = self.service_statuses[service_name]
                if status.status == "unhealthy":
                    critical_failures.append((service_name, status))
        
        if critical_failures:
            await self._send_critical_alert(critical_failures)
    
    async def _send_service_alert(self, service_name: str, status: ServiceStatus, alert_type: str):
        """Send service-specific alert"""
        try:
            if alert_type == "failure":
                message = f"🚨 Service Alert: {service_name} is unhealthy"
                color = "danger"
            else:  # recovery
                message = f"✅ Service Recovery: {service_name} is healthy again"
                color = "good"
            
            await self.notification_service.send_message(
                channel="#upwork-automation-alerts",
                message=message,
                attachments=[{
                    "color": color,
                    "fields": [
                        {"title": "Service", "value": service_name, "short": True},
                        {"title": "Status", "value": status.status, "short": True},
                        {"title": "Consecutive Failures", "value": str(status.consecutive_failures), "short": True},
                        {"title": "Success Rate", "value": f"{status.success_rate:.1%}", "short": True},
                        {"title": "Last Check", "value": status.last_check.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                        {"title": "Response Time", "value": f"{status.response_time_ms:.2f}ms", "short": True}
                    ]
                }]
            )
        except Exception as e:
            logger.error(f"Failed to send service alert for {service_name}: {e}")
    
    async def _send_critical_alert(self, critical_failures: List[tuple]):
        """Send critical system alert"""
        try:
            service_names = [name for name, _ in critical_failures]
            message = f"🔥 CRITICAL: {len(critical_failures)} critical services are down: {', '.join(service_names)}"
            
            fields = []
            for service_name, status in critical_failures:
                fields.extend([
                    {"title": f"{service_name} Status", "value": status.status, "short": True},
                    {"title": f"{service_name} Error", "value": status.error_message or "Unknown", "short": True}
                ])
            
            await self.notification_service.send_message(
                channel="#upwork-automation-alerts",
                message=message,
                attachments=[{
                    "color": "danger",
                    "fields": fields
                }]
            )
        except Exception as e:
            logger.error(f"Failed to send critical alert: {e}")
    
    # Health check implementations
    async def _check_database_health(self) -> bool:
        """Check database connectivity and performance"""
        try:
            from database.connection import get_database_connection
            
            async with get_database_connection() as conn:
                # Simple query to test connectivity
                result = await conn.execute("SELECT 1")
                return result is not None
        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            return False
    
    async def _check_redis_health(self) -> bool:
        """Check Redis connectivity"""
        try:
            import redis.asyncio as redis
            from shared.config import get_redis_url
            
            redis_client = redis.from_url(get_redis_url())
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            return False
    
    async def _check_browserbase_health(self) -> bool:
        """Check Browserbase API connectivity"""
        try:
            from browser_automation.browserbase_client import BrowserbaseClient
            
            client = BrowserbaseClient()
            # Try to list sessions (lightweight operation)
            sessions = await client.list_sessions()
            return isinstance(sessions, list)
        except Exception as e:
            logger.debug(f"Browserbase health check failed: {e}")
            return False
    
    async def _check_google_services_health(self) -> bool:
        """Check Google Services connectivity"""
        try:
            from services.google_services import GoogleServicesManager
            
            google_manager = GoogleServicesManager()
            # Try to access Google Drive (lightweight operation)
            drive_service = await google_manager.get_drive_service()
            return drive_service is not None
        except Exception as e:
            logger.debug(f"Google Services health check failed: {e}")
            return False
    
    async def _check_slack_health(self) -> bool:
        """Check Slack API connectivity"""
        try:
            # Try to get bot info (lightweight operation)
            response = await self.notification_service._make_api_call("auth.test")
            return response.get("ok", False)
        except Exception as e:
            logger.debug(f"Slack health check failed: {e}")
            return False
    
    async def _check_n8n_health(self) -> bool:
        """Check n8n connectivity"""
        try:
            from services.n8n_service import N8NService
            
            n8n_service = N8NService()
            # Try to get workflows (lightweight operation)
            workflows = await n8n_service.get_workflows()
            return isinstance(workflows, list)
        except Exception as e:
            logger.debug(f"n8n health check failed: {e}")
            return False
    
    # Degradation strategies
    async def _degrade_database_operations(self, service_name: str):
        """Degrade database operations"""
        logger.warning("Degrading database operations - switching to read-only mode")
        # Implementation would set a global flag to disable writes
    
    async def _degrade_queue_operations(self, service_name: str):
        """Degrade queue operations"""
        logger.warning("Degrading queue operations - switching to synchronous processing")
        # Implementation would disable queue-based processing
    
    async def _degrade_browser_operations(self, service_name: str):
        """Degrade browser operations"""
        logger.warning("Degrading browser operations - reducing concurrent sessions")
        # Implementation would reduce browser session pool size
    
    async def _degrade_google_operations(self, service_name: str):
        """Degrade Google services operations"""
        logger.warning("Degrading Google operations - disabling non-essential features")
        # Implementation would disable Google Docs/Drive integrations
    
    async def _degrade_workflow_operations(self, service_name: str):
        """Degrade n8n workflow operations"""
        logger.warning("Degrading workflow operations - switching to direct API calls")
        # Implementation would bypass n8n workflows
    
    # API methods
    def get_service_status(self, service_name: str = None) -> Dict[str, Any]:
        """Get service status information"""
        if service_name:
            status = self.service_statuses.get(service_name)
            if not status:
                return {"error": f"Service {service_name} not found"}
            
            return {
                "name": status.name,
                "status": status.status,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "last_failure": status.last_failure.isoformat() if status.last_failure else None,
                "consecutive_failures": status.consecutive_failures,
                "consecutive_successes": status.consecutive_successes,
                "total_checks": status.total_checks,
                "success_rate": status.success_rate,
                "response_time_ms": status.response_time_ms,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
        
        # Return all services
        return {
            name: {
                "status": status.status,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "consecutive_failures": status.consecutive_failures,
                "success_rate": status.success_rate,
                "response_time_ms": status.response_time_ms,
                "error_message": status.error_message
            }
            for name, status in self.service_statuses.items()
        }
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        total_services = len(self.service_statuses)
        healthy_services = sum(1 for s in self.service_statuses.values() if s.status == "healthy")
        degraded_services = sum(1 for s in self.service_statuses.values() if s.status == "degraded")
        unhealthy_services = sum(1 for s in self.service_statuses.values() if s.status == "unhealthy")
        
        # Determine overall system status
        if unhealthy_services > 0:
            overall_status = "unhealthy"
        elif degraded_services > 0:
            overall_status = "degraded"
        elif healthy_services == total_services:
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        return {
            "overall_status": overall_status,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "degraded_services": degraded_services,
            "unhealthy_services": unhealthy_services,
            "health_percentage": (healthy_services / total_services * 100) if total_services > 0 else 0,
            "last_updated": datetime.utcnow().isoformat()
        }


# Global instance
health_monitoring_service = HealthMonitoringService()