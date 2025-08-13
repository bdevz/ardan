"""
System service - business logic for system configuration and status
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SystemConfigModel, JobModel, ApplicationModel, TaskQueueModel
from shared.models import SystemStatusResponse, SystemConfig
from shared.utils import setup_logging

logger = setup_logging("system-service")


class SystemService:
    """Service for system-related operations"""
    
    async def get_system_status(self, db: AsyncSession) -> SystemStatusResponse:
        """Get current system status"""
        try:
            # Get system config
            config = await self.get_system_config(db)
            
            # Count jobs in queue (discovered but not applied)
            jobs_query = select(func.count()).where(
                JobModel.status.in_(["discovered", "filtered", "queued"])
            )
            jobs_result = await db.execute(jobs_query)
            jobs_in_queue = jobs_result.scalar() or 0
            
            # Count applications today
            today = datetime.utcnow().date()
            apps_query = select(func.count()).where(
                func.date(ApplicationModel.submitted_at) == today
            )
            apps_result = await db.execute(apps_query)
            applications_today = apps_result.scalar() or 0
            
            # Get success rate (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            total_apps_query = select(func.count()).where(
                ApplicationModel.submitted_at >= thirty_days_ago
            )
            total_apps_result = await db.execute(total_apps_query)
            total_apps = total_apps_result.scalar() or 0
            
            successful_apps_query = select(func.count()).where(
                ApplicationModel.submitted_at >= thirty_days_ago,
                ApplicationModel.status.in_(["interview", "hired"])
            )
            successful_apps_result = await db.execute(successful_apps_query)
            successful_apps = successful_apps_result.scalar() or 0
            
            success_rate = (successful_apps / total_apps * 100) if total_apps > 0 else None
            
            # Get last application time
            last_app_query = select(ApplicationModel.submitted_at).order_by(
                ApplicationModel.submitted_at.desc()
            ).limit(1)
            last_app_result = await db.execute(last_app_query)
            last_application = last_app_result.scalar_one_or_none()
            
            return SystemStatusResponse(
                automation_enabled=config.automation_enabled,
                jobs_in_queue=jobs_in_queue,
                applications_today=applications_today,
                daily_limit=config.daily_application_limit,
                success_rate=success_rate,
                last_application=last_application
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise
    
    async def get_system_config(self, db: AsyncSession) -> SystemConfig:
        """Get system configuration"""
        try:
            query = select(SystemConfigModel).order_by(SystemConfigModel.created_at.desc()).limit(1)
            result = await db.execute(query)
            config_model = result.scalar_one_or_none()
            
            if config_model:
                return SystemConfig(
                    daily_application_limit=config_model.daily_application_limit,
                    min_hourly_rate=config_model.min_hourly_rate,
                    target_hourly_rate=config_model.target_hourly_rate,
                    min_client_rating=config_model.min_client_rating,
                    min_hire_rate=config_model.min_hire_rate,
                    keywords_include=config_model.keywords_include or [],
                    keywords_exclude=config_model.keywords_exclude or [],
                    automation_enabled=config_model.automation_enabled,
                    notification_channels=config_model.notification_channels or [],
                    profile_name=config_model.profile_name
                )
            else:
                # Return default config if none exists
                return SystemConfig()
                
        except Exception as e:
            logger.error(f"Error getting system config: {e}")
            raise
    
    async def update_system_config(self, db: AsyncSession, config: SystemConfig) -> SystemConfig:
        """Update system configuration"""
        try:
            # Create new config record (we keep history)
            config_model = SystemConfigModel(
                daily_application_limit=config.daily_application_limit,
                min_hourly_rate=config.min_hourly_rate,
                target_hourly_rate=config.target_hourly_rate,
                min_client_rating=config.min_client_rating,
                min_hire_rate=config.min_hire_rate,
                keywords_include=config.keywords_include,
                keywords_exclude=config.keywords_exclude,
                automation_enabled=config.automation_enabled,
                notification_channels=config.notification_channels,
                profile_name=config.profile_name
            )
            
            db.add(config_model)
            await db.commit()
            
            logger.info("System configuration updated")
            return config
            
        except Exception as e:
            logger.error(f"Error updating system config: {e}")
            await db.rollback()
            raise
    
    async def get_system_health(self, db: AsyncSession) -> dict:
        """Get comprehensive system health status"""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            # Database health
            try:
                await db.execute(select(1))
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "response_time_ms": 0  # Could measure actual response time
                }
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "unhealthy"
            
            # Task queue health (check for stuck tasks)
            try:
                stuck_tasks_query = select(func.count()).where(
                    TaskQueueModel.status == "processing",
                    TaskQueueModel.started_at < datetime.utcnow() - timedelta(hours=1)
                )
                stuck_result = await db.execute(stuck_tasks_query)
                stuck_tasks = stuck_result.scalar() or 0
                
                health_status["components"]["task_queue"] = {
                    "status": "healthy" if stuck_tasks == 0 else "degraded",
                    "stuck_tasks": stuck_tasks
                }
                
                if stuck_tasks > 0:
                    health_status["status"] = "degraded"
                    
            except Exception as e:
                health_status["components"]["task_queue"] = {
                    "status": "unknown",
                    "error": str(e)
                }
            
            # Browser automation health (placeholder)
            health_status["components"]["browser_automation"] = {
                "status": "unknown",
                "message": "Health check not implemented"
            }
            
            # External services health (placeholder)
            health_status["components"]["external_services"] = {
                "browserbase": "unknown",
                "openai": "unknown",
                "google_services": "unknown",
                "slack": "unknown"
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global service instance
system_service = SystemService()