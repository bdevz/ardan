"""
Task Queue Service for asynchronous job processing
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

import redis.asyncio as redis
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from database.models import TaskQueueModel
from shared.models import TaskQueue
from .websocket_service import websocket_service

logger = logging.getLogger(__name__)


class TaskQueueService:
    """Redis-based task queue service for asynchronous job processing"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.task_handlers: Dict[str, callable] = {}
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Task queue service initialized")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def register_handler(self, task_type: str, handler: callable):
        """Register a task handler for a specific task type"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def enqueue_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3
    ) -> UUID:
        """Enqueue a new task for processing"""
        task_id = uuid4()
        
        # Create task record in database
        async with get_db_session() as session:
            task = TaskQueueModel(
                id=task_id,
                task_type=task_type,
                task_data=task_data,
                priority=priority,
                scheduled_at=scheduled_at or datetime.utcnow(),
                max_retries=max_retries
            )
            session.add(task)
            await session.commit()
        
        # Add to Redis queue for immediate processing if not scheduled
        if not scheduled_at or scheduled_at <= datetime.utcnow():
            await self._add_to_redis_queue(task_id, task_type, priority)
        else:
            # Add to delayed queue
            await self._schedule_task(task_id, scheduled_at)
        
        logger.info(f"Enqueued task {task_id} of type {task_type}")
        return task_id
    
    async def _add_to_redis_queue(self, task_id: UUID, task_type: str, priority: int):
        """Add task to Redis priority queue"""
        queue_name = f"queue:{task_type}"
        task_data = {
            "task_id": str(task_id),
            "task_type": task_type,
            "priority": priority,
            "enqueued_at": datetime.utcnow().isoformat()
        }
        
        # Use sorted set for priority queue (higher priority = lower score)
        await self.redis_client.zadd(queue_name, {json.dumps(task_data): -priority})
    
    async def _schedule_task(self, task_id: UUID, scheduled_at: datetime):
        """Schedule task for future execution"""
        timestamp = scheduled_at.timestamp()
        task_data = {"task_id": str(task_id)}
        await self.redis_client.zadd("scheduled_tasks", {json.dumps(task_data): timestamp})
    
    async def dequeue_task(self, task_types: List[str], timeout: int = 10) -> Optional[Dict]:
        """Dequeue next available task from specified queues"""
        queue_names = [f"queue:{task_type}" for task_type in task_types]
        
        # Check each queue for available tasks (priority order)
        for queue_name in queue_names:
            # Get highest priority task (lowest score)
            result = await self.redis_client.zpopmin(queue_name, count=1)
            if result:
                task_json, priority = result[0]
                task_data = json.loads(task_json)
                
                # Mark task as processing in database
                task_id = UUID(task_data["task_id"])
                await self._mark_task_processing(task_id)
                
                return {
                    "task_id": task_id,
                    "task_type": task_data["task_type"],
                    "priority": -int(priority)
                }
        
        return None
    
    async def _mark_task_processing(self, task_id: UUID):
        """Mark task as processing in database"""
        async with get_db_session() as session:
            await session.execute(
                update(TaskQueueModel)
                .where(TaskQueueModel.id == task_id)
                .values(
                    status="processing",
                    started_at=datetime.utcnow()
                )
            )
            await session.commit()
    
    async def complete_task(self, task_id: UUID, result: Optional[Dict] = None):
        """Mark task as completed"""
        async with get_db_session() as session:
            update_data = {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }
            if result:
                update_data["task_data"] = result
            
            await session.execute(
                update(TaskQueueModel)
                .where(TaskQueueModel.id == task_id)
                .values(**update_data)
            )
            await session.commit()
        
        logger.info(f"Task {task_id} completed successfully")
    
    async def fail_task(self, task_id: UUID, error_message: str, retry: bool = True):
        """Mark task as failed and optionally retry"""
        async with get_db_session() as session:
            # Get current task
            result = await session.execute(
                select(TaskQueueModel).where(TaskQueueModel.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            # Check if we should retry
            if retry and task.retry_count < task.max_retries:
                # Increment retry count and re-queue
                new_retry_count = task.retry_count + 1
                await session.execute(
                    update(TaskQueueModel)
                    .where(TaskQueueModel.id == task_id)
                    .values(
                        status="pending",
                        retry_count=new_retry_count,
                        error_message=error_message,
                        started_at=None
                    )
                )
                await session.commit()
                
                # Re-add to Redis queue with exponential backoff
                delay_seconds = 2 ** new_retry_count * 60  # 2, 4, 8 minutes
                scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
                await self._schedule_task(task_id, scheduled_at)
                
                logger.warning(f"Task {task_id} failed, retrying in {delay_seconds} seconds (attempt {new_retry_count})")
            else:
                # Mark as permanently failed
                await session.execute(
                    update(TaskQueueModel)
                    .where(TaskQueueModel.id == task_id)
                    .values(
                        status="failed",
                        error_message=error_message,
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                logger.error(f"Task {task_id} permanently failed: {error_message}")
    
    async def process_scheduled_tasks(self):
        """Process tasks scheduled for execution"""
        current_time = datetime.utcnow().timestamp()
        
        # Get tasks ready for execution
        ready_tasks = await self.redis_client.zrangebyscore(
            "scheduled_tasks", 0, current_time, withscores=True
        )
        
        for task_json, timestamp in ready_tasks:
            task_data = json.loads(task_json)
            task_id = UUID(task_data["task_id"])
            
            # Get task details from database
            async with get_db_session() as session:
                result = await session.execute(
                    select(TaskQueueModel).where(TaskQueueModel.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if task and task.status == "pending":
                    # Add to appropriate queue
                    await self._add_to_redis_queue(task_id, task.task_type, task.priority)
                    
                    # Remove from scheduled tasks
                    await self.redis_client.zrem("scheduled_tasks", task_json)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            "queues": {},
            "scheduled_tasks": 0,
            "total_pending": 0,
            "total_processing": 0,
            "total_completed": 0,
            "total_failed": 0
        }
        
        # Get Redis queue lengths
        queue_keys = await self.redis_client.keys("queue:*")
        for key in queue_keys:
            queue_name = key.replace("queue:", "")
            length = await self.redis_client.zcard(key)
            stats["queues"][queue_name] = length
            stats["total_pending"] += length
        
        # Get scheduled tasks count
        stats["scheduled_tasks"] = await self.redis_client.zcard("scheduled_tasks")
        
        # Get database stats
        async with get_db_session() as session:
            for status in ["processing", "completed", "failed"]:
                result = await session.execute(
                    select(TaskQueueModel).where(TaskQueueModel.status == status)
                )
                count = len(result.all())
                stats[f"total_{status}"] = count
        
        # Broadcast queue status update via WebSocket
        await websocket_service.broadcast_queue_status_update({
            "total_jobs": stats["total_pending"] + stats["total_processing"] + stats["total_completed"] + stats["total_failed"],
            "pending_jobs": stats["total_pending"],
            "processing_jobs": stats["total_processing"],
            "completed_jobs": stats["total_completed"],
            "failed_jobs": stats["total_failed"],
            "queue_health": "healthy" if stats["total_failed"] < stats["total_completed"] * 0.1 else "warning"
        })
        
        return stats
    
    async def get_task_status(self, task_id: UUID) -> Optional[TaskQueue]:
        """Get task status by ID"""
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskQueueModel).where(TaskQueueModel.id == task_id)
            )
            task_model = result.scalar_one_or_none()
            
            if task_model:
                return TaskQueue(
                    id=task_model.id,
                    task_type=task_model.task_type,
                    task_data=task_model.task_data,
                    status=task_model.status,
                    priority=task_model.priority,
                    scheduled_at=task_model.scheduled_at,
                    started_at=task_model.started_at,
                    completed_at=task_model.completed_at,
                    error_message=task_model.error_message,
                    retry_count=task_model.retry_count,
                    max_retries=task_model.max_retries,
                    created_at=task_model.created_at
                )
        
        return None
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task"""
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskQueueModel).where(
                    and_(
                        TaskQueueModel.id == task_id,
                        TaskQueueModel.status.in_(["pending", "processing"])
                    )
                )
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return False
            
            # Mark as cancelled
            await session.execute(
                update(TaskQueueModel)
                .where(TaskQueueModel.id == task_id)
                .values(
                    status="failed",
                    error_message="Task cancelled by user",
                    completed_at=datetime.utcnow()
                )
            )
            await session.commit()
            
            # Remove from Redis queues
            queue_name = f"queue:{task.task_type}"
            # This is a bit complex since we need to find the specific task in the sorted set
            # For now, we'll let it timeout naturally
            
            logger.info(f"Task {task_id} cancelled")
            return True
    
    async def cleanup_old_tasks(self, days_old: int = 30):
        """Clean up old completed/failed tasks"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskQueueModel).where(
                    and_(
                        TaskQueueModel.status.in_(["completed", "failed"]),
                        TaskQueueModel.completed_at < cutoff_date
                    )
                )
            )
            old_tasks = result.all()
            
            for task in old_tasks:
                await session.delete(task)
            
            await session.commit()
            
            logger.info(f"Cleaned up {len(old_tasks)} old tasks")
            return len(old_tasks)


# Global task queue service instance
task_queue_service = TaskQueueService()