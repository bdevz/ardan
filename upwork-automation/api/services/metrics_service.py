"""
Metrics service - business logic for performance metrics and analytics
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    JobModel, ApplicationModel, ProposalModel, 
    PerformanceMetricModel, SystemConfigModel
)
from shared.models import DashboardMetrics, Application
from shared.utils import setup_logging
from .websocket_service import websocket_service

logger = setup_logging("metrics-service")


class MetricsService:
    """Service for metrics and analytics operations"""
    
    async def get_dashboard_metrics(self, db: AsyncSession) -> DashboardMetrics:
        """Get dashboard metrics"""
        try:
            # Total jobs discovered
            jobs_query = select(func.count()).select_from(JobModel)
            jobs_result = await db.execute(jobs_query)
            total_jobs_discovered = jobs_result.scalar() or 0
            
            # Total applications submitted
            apps_query = select(func.count()).select_from(ApplicationModel)
            apps_result = await db.execute(apps_query)
            total_applications_submitted = apps_result.scalar() or 0
            
            # Applications today
            today = datetime.utcnow().date()
            today_apps_query = select(func.count()).where(
                func.date(ApplicationModel.submitted_at) == today
            )
            today_apps_result = await db.execute(today_apps_query)
            applications_today = today_apps_result.scalar() or 0
            
            # Success rate (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            total_recent_query = select(func.count()).where(
                ApplicationModel.submitted_at >= thirty_days_ago
            )
            total_recent_result = await db.execute(total_recent_query)
            total_recent = total_recent_result.scalar() or 0
            
            successful_recent_query = select(func.count()).where(
                ApplicationModel.submitted_at >= thirty_days_ago,
                ApplicationModel.status.in_(["interview", "hired"])
            )
            successful_recent_result = await db.execute(successful_recent_query)
            successful_recent = successful_recent_result.scalar() or 0
            
            success_rate = Decimal(str(successful_recent / total_recent * 100)) if total_recent > 0 else Decimal("0")
            
            # Average response time (placeholder - would need to track response times)
            average_response_time = None
            
            # Top keywords (from successful applications)
            top_keywords = await self._get_top_keywords(db)
            
            # Recent applications
            recent_applications = await self._get_recent_applications(db, limit=10)
            
            metrics = DashboardMetrics(
                total_jobs_discovered=total_jobs_discovered,
                total_applications_submitted=total_applications_submitted,
                applications_today=applications_today,
                success_rate=success_rate,
                average_response_time=average_response_time,
                top_keywords=top_keywords,
                recent_applications=recent_applications
            )
            
            # Broadcast system metrics via WebSocket
            await websocket_service.broadcast_system_metrics({
                "applications_today": applications_today,
                "success_rate": float(success_rate) / 100,  # Convert to decimal
                "avg_response_time": float(average_response_time),
                "active_sessions": 0,  # Would need to get from browser service
                "system_health": "healthy" if float(success_rate) > 50 else "warning",
                "cpu_usage": 0,  # Would need to get from system monitoring
                "memory_usage": 0  # Would need to get from system monitoring
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            raise
    
    async def get_performance_metrics(
        self, 
        db: AsyncSession, 
        time_period: str = "daily",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for specified time period"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            metrics = {
                "time_period": time_period,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "metrics": []
            }
            
            if time_period == "daily":
                metrics["metrics"] = await self._get_daily_metrics(db, start_date, end_date)
            elif time_period == "weekly":
                metrics["metrics"] = await self._get_weekly_metrics(db, start_date, end_date)
            elif time_period == "monthly":
                metrics["metrics"] = await self._get_monthly_metrics(db, start_date, end_date)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            raise
    
    async def record_performance_metric(
        self,
        db: AsyncSession,
        metric_type: str,
        metric_value: float,
        time_period: str = "daily",
        metadata: Dict[str, Any] = None
    ):
        """Record a performance metric"""
        try:
            metric = PerformanceMetricModel(
                metric_type=metric_type,
                metric_value=Decimal(str(metric_value)),
                time_period=time_period,
                date_recorded=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            db.add(metric)
            await db.commit()
            
            logger.info(f"Recorded metric: {metric_type} = {metric_value}")
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
            await db.rollback()
            raise
    
    async def get_application_funnel_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get application funnel conversion metrics"""
        try:
            # Jobs discovered
            jobs_discovered = await db.execute(select(func.count()).select_from(JobModel))
            discovered_count = jobs_discovered.scalar() or 0
            
            # Jobs filtered (passed basic criteria)
            jobs_filtered = await db.execute(
                select(func.count()).where(JobModel.status.in_(["filtered", "queued", "applied"]))
            )
            filtered_count = jobs_filtered.scalar() or 0
            
            # Applications submitted
            apps_submitted = await db.execute(select(func.count()).select_from(ApplicationModel))
            submitted_count = apps_submitted.scalar() or 0
            
            # Responses received
            responses_received = await db.execute(
                select(func.count()).where(ApplicationModel.client_response.isnot(None))
            )
            responses_count = responses_received.scalar() or 0
            
            # Interviews scheduled
            interviews_scheduled = await db.execute(
                select(func.count()).where(ApplicationModel.interview_scheduled == True)
            )
            interviews_count = interviews_scheduled.scalar() or 0
            
            # Hired
            hired = await db.execute(
                select(func.count()).where(ApplicationModel.hired == True)
            )
            hired_count = hired.scalar() or 0
            
            # Calculate conversion rates
            filter_rate = (filtered_count / discovered_count * 100) if discovered_count > 0 else 0
            application_rate = (submitted_count / filtered_count * 100) if filtered_count > 0 else 0
            response_rate = (responses_count / submitted_count * 100) if submitted_count > 0 else 0
            interview_rate = (interviews_count / responses_count * 100) if responses_count > 0 else 0
            hire_rate = (hired_count / interviews_count * 100) if interviews_count > 0 else 0
            
            return {
                "funnel_stages": {
                    "discovered": discovered_count,
                    "filtered": filtered_count,
                    "applied": submitted_count,
                    "responses": responses_count,
                    "interviews": interviews_count,
                    "hired": hired_count
                },
                "conversion_rates": {
                    "filter_rate": round(filter_rate, 2),
                    "application_rate": round(application_rate, 2),
                    "response_rate": round(response_rate, 2),
                    "interview_rate": round(interview_rate, 2),
                    "hire_rate": round(hire_rate, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting funnel metrics: {e}")
            raise
    
    async def _get_top_keywords(self, db: AsyncSession, limit: int = 10) -> List[str]:
        """Get top performing keywords from successful applications"""
        try:
            # This is a simplified version - in reality, we'd analyze job titles/descriptions
            # from successful applications to identify top keywords
            
            # For now, return some common Salesforce keywords
            return [
                "Salesforce",
                "Agentforce", 
                "Einstein AI",
                "Apex",
                "Lightning",
                "CRM",
                "Automation",
                "Integration"
            ][:limit]
            
        except Exception as e:
            logger.error(f"Error getting top keywords: {e}")
            return []
    
    async def _get_recent_applications(self, db: AsyncSession, limit: int = 10) -> List[Application]:
        """Get recent applications"""
        try:
            query = (
                select(ApplicationModel)
                .order_by(desc(ApplicationModel.submitted_at))
                .limit(limit)
            )
            
            result = await db.execute(query)
            app_models = result.scalars().all()
            
            applications = []
            for app_model in app_models:
                applications.append(Application(
                    id=app_model.id,
                    job_id=app_model.job_id,
                    proposal_id=app_model.proposal_id,
                    upwork_application_id=app_model.upwork_application_id,
                    submitted_at=app_model.submitted_at,
                    status=app_model.status,
                    client_response=app_model.client_response,
                    client_response_date=app_model.client_response_date,
                    interview_scheduled=app_model.interview_scheduled,
                    interview_date=app_model.interview_date,
                    hired=app_model.hired,
                    hire_date=app_model.hire_date,
                    session_recording_url=app_model.session_recording_url,
                    created_at=app_model.created_at,
                    updated_at=app_model.updated_at
                ))
            
            return applications
            
        except Exception as e:
            logger.error(f"Error getting recent applications: {e}")
            return []
    
    async def _get_daily_metrics(self, db: AsyncSession, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get daily performance metrics"""
        # This would implement daily aggregation of metrics
        # For now, return placeholder data
        return []
    
    async def _get_weekly_metrics(self, db: AsyncSession, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get weekly performance metrics"""
        # This would implement weekly aggregation of metrics
        # For now, return placeholder data
        return []
    
    async def _get_monthly_metrics(self, db: AsyncSession, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get monthly performance metrics"""
        # This would implement monthly aggregation of metrics
        # For now, return placeholder data
        return []


# Global service instance
metrics_service = MetricsService()