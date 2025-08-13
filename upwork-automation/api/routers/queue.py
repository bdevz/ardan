"""
Task Queue API endpoints
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from services.task_queue_service import task_queue_service
from services.task_scheduler import task_scheduler
from services.queue_metrics_service import queue_metrics_service
from shared.models import TaskQueue

router = APIRouter(prefix="/api/queue", tags=["queue"])


# Request/Response models
class EnqueueTaskRequest(BaseModel):
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 0
    scheduled_at: Optional[datetime] = None
    max_retries: int = 3


class EnqueueTaskResponse(BaseModel):
    task_id: UUID
    message: str


class TaskStatusResponse(BaseModel):
    task: Optional[TaskQueue]
    message: str


class QueueStatsResponse(BaseModel):
    queues: Dict[str, int]
    scheduled_tasks: int
    total_pending: int
    total_processing: int
    total_completed: int
    total_failed: int


class ScheduledTaskRequest(BaseModel):
    name: str
    cron_expression: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 0
    max_retries: int = 3
    enabled: bool = True


class ScheduledTaskResponse(BaseModel):
    name: str
    cron_expression: str
    task_type: str
    priority: int
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]


@router.post("/enqueue", response_model=EnqueueTaskResponse)
async def enqueue_task(request: EnqueueTaskRequest):
    """Enqueue a new task for processing"""
    try:
        task_id = await task_queue_service.enqueue_task(
            task_type=request.task_type,
            task_data=request.task_data,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            max_retries=request.max_retries
        )
        
        return EnqueueTaskResponse(
            task_id=task_id,
            message=f"Task enqueued successfully with ID {task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: UUID):
    """Get task status by ID"""
    try:
        task = await task_queue_service.get_task_status(task_id)
        
        if not task:
            return TaskStatusResponse(
                task=None,
                message=f"Task {task_id} not found"
            )
        
        return TaskStatusResponse(
            task=task,
            message="Task found"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/task/{task_id}")
async def cancel_task(task_id: UUID):
    """Cancel a pending task"""
    try:
        success = await task_queue_service.cancel_task(task_id)
        
        if success:
            return {"message": f"Task {task_id} cancelled successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found or cannot be cancelled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """Get queue statistics"""
    try:
        stats = await task_queue_service.get_queue_stats()
        return QueueStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_tasks(days_old: int = Query(30, ge=1, le=365)):
    """Clean up old completed/failed tasks"""
    try:
        cleaned_count = await task_queue_service.cleanup_old_tasks(days_old)
        return {"message": f"Cleaned up {cleaned_count} old tasks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Scheduled tasks endpoints
@router.get("/scheduled", response_model=List[ScheduledTaskResponse])
async def get_scheduled_tasks():
    """Get all scheduled tasks"""
    try:
        tasks = task_scheduler.get_scheduled_tasks()
        return [ScheduledTaskResponse(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled", response_model=ScheduledTaskResponse)
async def add_scheduled_task(request: ScheduledTaskRequest):
    """Add a new scheduled task"""
    try:
        task_scheduler.add_scheduled_task(
            name=request.name,
            cron_expression=request.cron_expression,
            task_type=request.task_type,
            task_data=request.task_data,
            priority=request.priority,
            max_retries=request.max_retries,
            enabled=request.enabled
        )
        
        # Get the created task
        tasks = task_scheduler.get_scheduled_tasks()
        created_task = next((t for t in tasks if t["name"] == request.name), None)
        
        if not created_task:
            raise HTTPException(status_code=500, detail="Failed to create scheduled task")
        
        return ScheduledTaskResponse(**created_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled/{task_name}/enable")
async def enable_scheduled_task(task_name: str):
    """Enable a scheduled task"""
    try:
        success = task_scheduler.enable_task(task_name)
        
        if success:
            return {"message": f"Scheduled task '{task_name}' enabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Scheduled task '{task_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduled/{task_name}/disable")
async def disable_scheduled_task(task_name: str):
    """Disable a scheduled task"""
    try:
        success = task_scheduler.disable_task(task_name)
        
        if success:
            return {"message": f"Scheduled task '{task_name}' disabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Scheduled task '{task_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled/{task_name}")
async def remove_scheduled_task(task_name: str):
    """Remove a scheduled task"""
    try:
        success = task_scheduler.remove_scheduled_task(task_name)
        
        if success:
            return {"message": f"Scheduled task '{task_name}' removed"}
        else:
            raise HTTPException(status_code=404, detail=f"Scheduled task '{task_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Convenience endpoints for common task types
@router.post("/jobs/discover")
async def enqueue_job_discovery(
    keywords: List[str] = Query(...),
    session_pool_size: int = Query(3, ge=1, le=10),
    priority: int = Query(5, ge=0, le=10)
):
    """Enqueue a job discovery task"""
    try:
        task_id = await task_queue_service.enqueue_task(
            task_type="job_discovery",
            task_data={
                "search_params": {
                    "keywords": keywords,
                    "min_hourly_rate": 50,
                    "min_client_rating": 4.0,
                    "payment_verified_only": True
                },
                "session_pool_size": session_pool_size
            },
            priority=priority
        )
        
        return EnqueueTaskResponse(
            task_id=task_id,
            message=f"Job discovery task enqueued with ID {task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/generate")
async def enqueue_proposal_generation(
    job_ids: List[UUID],
    include_attachments: bool = Query(True),
    priority: int = Query(7, ge=0, le=10)
):
    """Enqueue proposal generation tasks"""
    try:
        task_id = await task_queue_service.enqueue_task(
            task_type="batch_generate_proposals",
            task_data={
                "job_ids": [str(job_id) for job_id in job_ids],
                "include_attachments": include_attachments
            },
            priority=priority
        )
        
        return EnqueueTaskResponse(
            task_id=task_id,
            message=f"Proposal generation task enqueued with ID {task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/applications/submit")
async def enqueue_application_submission(
    applications: List[Dict[str, UUID]],  # [{"job_id": UUID, "proposal_id": UUID}]
    confirm_submission: bool = Query(False),
    max_daily_limit: int = Query(30, ge=1, le=100),
    priority: int = Query(9, ge=0, le=10)
):
    """Enqueue application submission tasks"""
    try:
        # Convert UUIDs to strings for JSON serialization
        app_data = [
            {
                "job_id": str(app["job_id"]),
                "proposal_id": str(app["proposal_id"])
            }
            for app in applications
        ]
        
        task_id = await task_queue_service.enqueue_task(
            task_type="batch_submit_applications",
            task_data={
                "applications": app_data,
                "confirm_submission": confirm_submission,
                "max_daily_limit": max_daily_limit
            },
            priority=priority
        )
        
        return EnqueueTaskResponse(
            task_id=task_id,
            message=f"Application submission task enqueued with ID {task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Metrics endpoints
@router.get("/metrics/health")
async def get_queue_health_metrics():
    """Get comprehensive queue health metrics"""
    try:
        metrics = await queue_metrics_service.get_queue_health_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/task-type/{task_type}")
async def get_task_type_metrics(
    task_type: str,
    hours: int = Query(24, ge=1, le=168)  # 1 hour to 1 week
):
    """Get detailed metrics for a specific task type"""
    try:
        metrics = await queue_metrics_service.get_task_type_metrics(task_type, hours)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/performance")
async def store_performance_metric(
    metric_type: str,
    metric_value: float,
    time_period: str = "hourly",
    metadata: Optional[Dict[str, Any]] = None
):
    """Store a custom performance metric"""
    try:
        await queue_metrics_service.store_performance_metric(
            metric_type=metric_type,
            metric_value=metric_value,
            time_period=time_period,
            metadata=metadata
        )
        return {"message": f"Performance metric '{metric_type}' stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))