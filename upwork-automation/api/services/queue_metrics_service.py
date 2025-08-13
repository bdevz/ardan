"""
Task Queue Metrics and Monitoring Service
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import TaskQueueModel, PerformanceMetricModel
from services.task_queue_service import task_queue_service

logger = logging.getLogger(__name__)


class QueueMetricsService:
    """Service for collecting and analyzing task queue metrics"""
    
    def __init__(self):
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_queue_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive queue health metrics"""
        cache_key = "queue_health"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]["data"]
        
        try:
            async with get_db_session() as session:
                # Get basic queue stats
                basic_stats = await task_queue_service.get_queue_stats()
                
                # Get processing time metrics
                processing_times = await self._get_processing_time_metrics(session)
                
                # Get failure rate metrics
                failure_rates = await self._get_failure_rate_metrics(session)
                
                # Get throughput metrics
                throughput = await self._get_throughput_metrics(session)
                
                # Get queue depth over time
                queue_depth = await self._get_queue_depth_metrics(session)
                
                # Get worker performance
                worker_performance = await self._get_worker_performance_metrics(session)
                
                metrics = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "basic_stats": basic_stats,
                    "processing_times": processing_times,
                    "failure_rates": failure_rates,
                    "throughput": throughput,
                    "queue_depth": queue_depth,
                    "worker_performance": worker_performance,
                    "health_score": self._calculate_health_score(
                        basic_stats, failure_rates, processing_times
                    )
                }
                
                # Cache the results
                self._cache_metrics(cache_key, metrics)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get queue health metrics: {str(e)}")
            raise
    
    async def _get_processing_time_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get processing time statistics"""
        # Get completed tasks from the last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        
        result = await session.execute(
            select(
                TaskQueueModel.task_type,
                func.avg(
                    func.extract('epoch', TaskQueueModel.completed_at - TaskQueueModel.started_at)
                ).label('avg_processing_time'),
                func.min(
                    func.extract('epoch', TaskQueueModel.completed_at - TaskQueueModel.started_at)
                ).label('min_processing_time'),
                func.max(
                    func.extract('epoch', TaskQueueModel.completed_at - TaskQueueModel.started_at)
                ).label('max_processing_time'),
                func.count().label('task_count')
            )
            .where(
                and_(
                    TaskQueueModel.status == "completed",
                    TaskQueueModel.completed_at >= since,
                    TaskQueueModel.started_at.isnot(None)
                )
            )
            .group_by(TaskQueueModel.task_type)
        )
        
        processing_times = {}
        for row in result:
            processing_times[row.task_type] = {
                "avg_seconds": float(row.avg_processing_time or 0),
                "min_seconds": float(row.min_processing_time or 0),
                "max_seconds": float(row.max_processing_time or 0),
                "task_count": row.task_count
            }
        
        return processing_times
    
    async def _get_failure_rate_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get failure rate statistics"""
        # Get tasks from the last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        
        result = await session.execute(
            select(
                TaskQueueModel.task_type,
                TaskQueueModel.status,
                func.count().label('count')
            )
            .where(TaskQueueModel.created_at >= since)
            .group_by(TaskQueueModel.task_type, TaskQueueModel.status)
        )
        
        # Organize by task type
        task_stats = defaultdict(lambda: defaultdict(int))
        for row in result:
            task_stats[row.task_type][row.status] = row.count
        
        # Calculate failure rates
        failure_rates = {}
        for task_type, stats in task_stats.items():
            total = sum(stats.values())
            failed = stats.get("failed", 0)
            completed = stats.get("completed", 0)
            
            failure_rates[task_type] = {
                "total_tasks": total,
                "failed_tasks": failed,
                "completed_tasks": completed,
                "failure_rate": (failed / total) if total > 0 else 0,
                "success_rate": (completed / total) if total > 0 else 0
            }
        
        return failure_rates
    
    async def _get_throughput_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get throughput statistics"""
        # Get hourly throughput for the last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        
        result = await session.execute(
            select(
                TaskQueueModel.task_type,
                func.date_trunc('hour', TaskQueueModel.completed_at).label('hour'),
                func.count().label('completed_count')
            )
            .where(
                and_(
                    TaskQueueModel.status == "completed",
                    TaskQueueModel.completed_at >= since
                )
            )
            .group_by(TaskQueueModel.task_type, func.date_trunc('hour', TaskQueueModel.completed_at))
            .order_by(func.date_trunc('hour', TaskQueueModel.completed_at))
        )
        
        # Organize by task type and hour
        throughput_data = defaultdict(list)
        for row in result:
            throughput_data[row.task_type].append({
                "hour": row.hour.isoformat(),
                "completed_count": row.completed_count
            })
        
        # Calculate average throughput
        throughput_metrics = {}
        for task_type, hourly_data in throughput_data.items():
            total_completed = sum(item["completed_count"] for item in hourly_data)
            hours_with_data = len(hourly_data)
            
            throughput_metrics[task_type] = {
                "total_completed_24h": total_completed,
                "avg_per_hour": total_completed / 24 if total_completed > 0 else 0,
                "peak_hour_count": max((item["completed_count"] for item in hourly_data), default=0),
                "hourly_data": hourly_data
            }
        
        return throughput_metrics
    
    async def _get_queue_depth_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get queue depth over time"""
        # This is a simplified version - in production you might want to store
        # periodic snapshots of queue depth
        current_stats = await task_queue_service.get_queue_stats()
        
        return {
            "current_depth": current_stats["total_pending"],
            "by_queue": current_stats["queues"],
            "scheduled_tasks": current_stats["scheduled_tasks"]
        }
    
    async def _get_worker_performance_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Get worker performance metrics"""
        # Get tasks completed in the last 24 hours with worker info
        since = datetime.utcnow() - timedelta(hours=24)
        
        result = await session.execute(
            select(TaskQueueModel)
            .where(
                and_(
                    TaskQueueModel.status == "completed",
                    TaskQueueModel.completed_at >= since,
                    TaskQueueModel.task_data.isnot(None)
                )
            )
        )
        
        worker_stats = defaultdict(lambda: {
            "tasks_completed": 0,
            "total_processing_time": 0,
            "task_types": defaultdict(int)
        })
        
        for task in result.scalars():
            # Extract worker info from task_data if available
            task_data = task.task_data or {}
            worker_id = task_data.get("worker_id", "unknown")
            processing_time = task_data.get("processing_time", 0)
            
            worker_stats[worker_id]["tasks_completed"] += 1
            worker_stats[worker_id]["total_processing_time"] += processing_time
            worker_stats[worker_id]["task_types"][task.task_type] += 1
        
        # Calculate averages
        performance_metrics = {}
        for worker_id, stats in worker_stats.items():
            performance_metrics[worker_id] = {
                "tasks_completed": stats["tasks_completed"],
                "avg_processing_time": (
                    stats["total_processing_time"] / stats["tasks_completed"]
                    if stats["tasks_completed"] > 0 else 0
                ),
                "task_types": dict(stats["task_types"])
            }
        
        return performance_metrics
    
    def _calculate_health_score(
        self,
        basic_stats: Dict[str, Any],
        failure_rates: Dict[str, Any],
        processing_times: Dict[str, Any]
    ) -> float:
        """Calculate overall queue health score (0-100)"""
        score = 100.0
        
        # Penalize high queue depth
        total_pending = basic_stats.get("total_pending", 0)
        if total_pending > 100:
            score -= min(20, (total_pending - 100) / 10)
        
        # Penalize high failure rates
        for task_type, rates in failure_rates.items():
            failure_rate = rates.get("failure_rate", 0)
            if failure_rate > 0.1:  # More than 10% failure rate
                score -= min(30, failure_rate * 100)
        
        # Penalize slow processing times
        for task_type, times in processing_times.items():
            avg_time = times.get("avg_seconds", 0)
            if avg_time > 300:  # More than 5 minutes average
                score -= min(20, (avg_time - 300) / 60)
        
        return max(0, score)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.metrics_cache:
            return False
        
        cache_time = self.metrics_cache[cache_key]["timestamp"]
        return (datetime.utcnow() - cache_time).total_seconds() < self.cache_ttl
    
    def _cache_metrics(self, cache_key: str, data: Dict[str, Any]):
        """Cache metrics data"""
        self.metrics_cache[cache_key] = {
            "timestamp": datetime.utcnow(),
            "data": data
        }
    
    async def get_task_type_metrics(self, task_type: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed metrics for a specific task type"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            async with get_db_session() as session:
                # Get all tasks of this type
                result = await session.execute(
                    select(TaskQueueModel)
                    .where(
                        and_(
                            TaskQueueModel.task_type == task_type,
                            TaskQueueModel.created_at >= since
                        )
                    )
                    .order_by(TaskQueueModel.created_at.desc())
                )
                
                tasks = result.scalars().all()
                
                # Calculate metrics
                total_tasks = len(tasks)
                status_counts = defaultdict(int)
                retry_counts = defaultdict(int)
                processing_times = []
                
                for task in tasks:
                    status_counts[task.status] += 1
                    retry_counts[task.retry_count] += 1
                    
                    if task.started_at and task.completed_at:
                        processing_time = (task.completed_at - task.started_at).total_seconds()
                        processing_times.append(processing_time)
                
                # Calculate statistics
                avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
                
                return {
                    "task_type": task_type,
                    "time_period_hours": hours,
                    "total_tasks": total_tasks,
                    "status_distribution": dict(status_counts),
                    "retry_distribution": dict(retry_counts),
                    "processing_time_stats": {
                        "avg_seconds": avg_processing_time,
                        "min_seconds": min(processing_times) if processing_times else 0,
                        "max_seconds": max(processing_times) if processing_times else 0,
                        "count": len(processing_times)
                    },
                    "recent_tasks": [
                        {
                            "id": str(task.id),
                            "status": task.status,
                            "created_at": task.created_at.isoformat(),
                            "retry_count": task.retry_count,
                            "error_message": task.error_message
                        }
                        for task in tasks[:10]  # Last 10 tasks
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get metrics for task type {task_type}: {str(e)}")
            raise
    
    async def store_performance_metric(
        self,
        metric_type: str,
        metric_value: float,
        time_period: str = "hourly",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store a performance metric"""
        try:
            async with get_db_session() as session:
                metric = PerformanceMetricModel(
                    metric_type=metric_type,
                    metric_value=metric_value,
                    time_period=time_period,
                    date_recorded=datetime.utcnow(),
                    metadata=metadata or {}
                )
                
                session.add(metric)
                await session.commit()
                
                logger.info(f"Stored performance metric: {metric_type} = {metric_value}")
                
        except Exception as e:
            logger.error(f"Failed to store performance metric: {str(e)}")
            raise


# Global metrics service instance
queue_metrics_service = QueueMetricsService()