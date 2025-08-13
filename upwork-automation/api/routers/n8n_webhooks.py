"""
n8n Webhook API router - handles webhook endpoints for n8n workflow integration
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from database.connection import get_db
from shared.utils import setup_logging
from services.job_service import job_service
from services.proposal_service import proposal_service
from services.application_submission_service import application_submission_service
from services.task_queue_service import task_queue_service

logger = setup_logging("n8n-webhooks")
router = APIRouter()


@router.post("/trigger/job-discovery")
async def trigger_job_discovery_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for triggering job discovery workflow from n8n
    
    Expected payload:
    {
        "keywords": ["Salesforce Agentforce", "Salesforce AI"],
        "session_pool_size": 3,
        "max_jobs": 20,
        "filters": {
            "min_hourly_rate": 50,
            "min_client_rating": 4.0,
            "payment_verified": true
        }
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received job discovery webhook trigger: {payload}")
        
        # Extract parameters with defaults
        keywords = payload.get("keywords", ["Salesforce Agentforce", "Salesforce AI", "Einstein"])
        session_pool_size = payload.get("session_pool_size", 3)
        max_jobs = payload.get("max_jobs", 20)
        filters = payload.get("filters", {})
        
        # Queue job discovery task
        task_data = {
            "task_type": "job_discovery",
            "keywords": keywords,
            "session_pool_size": session_pool_size,
            "max_jobs": max_jobs,
            "filters": filters,
            "triggered_by": "n8n_webhook",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_id = await task_queue_service.add_task(
            task_type="job_discovery",
            task_data=task_data,
            priority="high"
        )
        
        return {
            "success": True,
            "message": "Job discovery workflow triggered successfully",
            "task_id": task_id,
            "parameters": {
                "keywords": keywords,
                "session_pool_size": session_pool_size,
                "max_jobs": max_jobs,
                "filters": filters
            }
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Error processing job discovery webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process job discovery webhook"
        )


@router.post("/trigger/proposal-generation")
async def trigger_proposal_generation_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for triggering proposal generation workflow from n8n
    
    Expected payload:
    {
        "job_ids": ["uuid1", "uuid2"],
        "auto_create_docs": true,
        "select_attachments": true,
        "quality_threshold": 0.7
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received proposal generation webhook trigger: {payload}")
        
        # Extract parameters
        job_ids = payload.get("job_ids", [])
        auto_create_docs = payload.get("auto_create_docs", True)
        select_attachments = payload.get("select_attachments", True)
        quality_threshold = payload.get("quality_threshold", 0.7)
        
        if not job_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one job_id is required"
            )
        
        # Queue proposal generation tasks
        task_ids = []
        for job_id in job_ids:
            task_data = {
                "task_type": "proposal_generation",
                "job_id": job_id,
                "auto_create_docs": auto_create_docs,
                "select_attachments": select_attachments,
                "quality_threshold": quality_threshold,
                "triggered_by": "n8n_webhook",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            task_id = await task_queue_service.add_task(
                task_type="proposal_generation",
                task_data=task_data,
                priority="normal"
            )
            task_ids.append(task_id)
        
        return {
            "success": True,
            "message": f"Proposal generation workflow triggered for {len(job_ids)} jobs",
            "task_ids": task_ids,
            "parameters": {
                "job_ids": job_ids,
                "auto_create_docs": auto_create_docs,
                "select_attachments": select_attachments,
                "quality_threshold": quality_threshold
            }
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Error processing proposal generation webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process proposal generation webhook"
        )


@router.post("/trigger/browser-submission")
async def trigger_browser_submission_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for triggering browser submission workflow from n8n
    
    Expected payload:
    {
        "proposal_ids": ["uuid1", "uuid2"],
        "session_type": "proposal_submission",
        "stealth_mode": true,
        "retry_attempts": 3
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received browser submission webhook trigger: {payload}")
        
        # Extract parameters
        proposal_ids = payload.get("proposal_ids", [])
        session_type = payload.get("session_type", "proposal_submission")
        stealth_mode = payload.get("stealth_mode", True)
        retry_attempts = payload.get("retry_attempts", 3)
        
        if not proposal_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one proposal_id is required"
            )
        
        # Queue browser submission tasks
        task_ids = []
        for proposal_id in proposal_ids:
            task_data = {
                "task_type": "browser_submission",
                "proposal_id": proposal_id,
                "session_type": session_type,
                "stealth_mode": stealth_mode,
                "retry_attempts": retry_attempts,
                "triggered_by": "n8n_webhook",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            task_id = await task_queue_service.add_task(
                task_type="browser_submission",
                task_data=task_data,
                priority="high"
            )
            task_ids.append(task_id)
        
        return {
            "success": True,
            "message": f"Browser submission workflow triggered for {len(proposal_ids)} proposals",
            "task_ids": task_ids,
            "parameters": {
                "proposal_ids": proposal_ids,
                "session_type": session_type,
                "stealth_mode": stealth_mode,
                "retry_attempts": retry_attempts
            }
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Error processing browser submission webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process browser submission webhook"
        )


@router.post("/trigger/notification")
async def trigger_notification_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for triggering notification workflows from n8n
    
    Expected payload:
    {
        "notification_type": "job_discovered|proposal_generated|application_submitted|error_alert",
        "data": {...},
        "channels": ["slack", "email"],
        "priority": "normal|high|urgent"
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received notification webhook trigger: {payload}")
        
        # Extract parameters
        notification_type = payload.get("notification_type")
        data = payload.get("data", {})
        channels = payload.get("channels", ["slack"])
        priority = payload.get("priority", "normal")
        
        if not notification_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_type is required"
            )
        
        # Queue notification task
        task_data = {
            "task_type": "notification",
            "notification_type": notification_type,
            "data": data,
            "channels": channels,
            "priority": priority,
            "triggered_by": "n8n_webhook",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_id = await task_queue_service.add_task(
            task_type="notification",
            task_data=task_data,
            priority=priority
        )
        
        return {
            "success": True,
            "message": f"Notification workflow triggered: {notification_type}",
            "task_id": task_id,
            "parameters": {
                "notification_type": notification_type,
                "channels": channels,
                "priority": priority
            }
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Error processing notification webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process notification webhook"
        )


@router.post("/callback/job-discovery-complete")
async def job_discovery_complete_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Callback endpoint for n8n to report job discovery completion
    
    Expected payload:
    {
        "task_id": "uuid",
        "success": true,
        "jobs_discovered": 15,
        "jobs_filtered": 8,
        "next_workflow": "proposal_generation"
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received job discovery completion callback: {payload}")
        
        task_id = payload.get("task_id")
        success = payload.get("success", False)
        jobs_discovered = payload.get("jobs_discovered", 0)
        jobs_filtered = payload.get("jobs_filtered", 0)
        next_workflow = payload.get("next_workflow")
        
        # Update task status
        if task_id:
            await task_queue_service.update_task_status(
                task_id=task_id,
                status="completed" if success else "failed",
                result={
                    "jobs_discovered": jobs_discovered,
                    "jobs_filtered": jobs_filtered,
                    "next_workflow": next_workflow
                }
            )
        
        # Trigger next workflow if specified
        if success and next_workflow == "proposal_generation" and jobs_filtered > 0:
            # Get the filtered job IDs and trigger proposal generation
            # This would be implemented based on the actual job storage mechanism
            pass
        
        return {
            "success": True,
            "message": "Job discovery completion callback processed",
            "task_id": task_id,
            "next_action": next_workflow if success else None
        }
        
    except Exception as e:
        logger.error(f"Error processing job discovery completion callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process completion callback"
        )


@router.get("/status")
async def get_n8n_integration_status():
    """
    Get status of n8n integration and available webhooks
    """
    try:
        return {
            "integration_status": "active",
            "available_webhooks": {
                "job_discovery": "/api/n8n/trigger/job-discovery",
                "proposal_generation": "/api/n8n/trigger/proposal-generation", 
                "browser_submission": "/api/n8n/trigger/browser-submission",
                "notification": "/api/n8n/trigger/notification"
            },
            "callback_endpoints": {
                "job_discovery_complete": "/api/n8n/callback/job-discovery-complete"
            },
            "last_webhook_call": None,  # Would track in real implementation
            "total_webhook_calls": 0    # Would track in real implementation
        }
        
    except Exception as e:
        logger.error(f"Error getting n8n integration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integration status"
        )


@router.post("/test-webhook")
async def test_webhook_endpoint(request: Request):
    """
    Test endpoint for validating n8n webhook connectivity
    """
    try:
        payload = await request.json()
        logger.info(f"Test webhook called with payload: {payload}")
        
        return {
            "success": True,
            "message": "Webhook test successful",
            "received_payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test webhook: {e}")
        return {
            "success": False,
            "message": f"Webhook test failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/validate-deployment")
async def validate_n8n_deployment():
    """
    Validate that all n8n workflows are properly deployed and configured
    """
    try:
        from services.n8n_service import n8n_service
        
        validation_result = await n8n_service.validate_workflow_deployment()
        
        if validation_result["success"]:
            return {
                "success": True,
                "message": "Workflow deployment validation completed",
                "validation_summary": {
                    "all_workflows_valid": validation_result["all_workflows_valid"],
                    "total_workflows": validation_result["total_workflows"],
                    "active_workflows": validation_result["active_workflows"],
                    "webhook_connectivity": validation_result["webhook_connectivity"],
                    "webhook_latency_ms": validation_result["webhook_latency_ms"]
                },
                "validation_details": validation_result["validation_results"],
                "issues": {
                    "missing_workflows": validation_result.get("missing_workflows", []),
                    "inactive_workflows": validation_result.get("inactive_workflows", [])
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation failed: {validation_result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Error validating n8n deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate n8n deployment"
        )


@router.get("/workflow-history/{workflow_id}")
async def get_workflow_execution_history(
    workflow_id: str,
    limit: int = 10
):
    """
    Get execution history for a specific workflow
    """
    try:
        from services.n8n_service import n8n_service
        
        history_result = await n8n_service.get_workflow_execution_history(
            workflow_id=workflow_id,
            limit=limit
        )
        
        if history_result["success"]:
            return {
                "success": True,
                "workflow_id": workflow_id,
                "execution_history": history_result["executions"],
                "statistics": {
                    "total_executions": history_result["total_executions"],
                    "success_rate": history_result["success_rate"],
                    "avg_execution_time_ms": history_result["avg_execution_time"]
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get execution history: {history_result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Error getting workflow execution history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow execution history"
        )


@router.post("/trigger-daily-summary")
async def trigger_daily_summary_notification(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger daily summary notification workflow
    """
    try:
        from services.metrics_service import metrics_service
        
        # Get daily metrics
        daily_metrics = await metrics_service.get_daily_summary()
        
        # Queue notification task
        task_data = {
            "task_type": "notification",
            "notification_type": "daily_summary",
            "data": daily_metrics,
            "channels": ["slack", "email"],
            "priority": "normal",
            "triggered_by": "manual_api_call",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        task_id = await task_queue_service.add_task(
            task_type="notification",
            task_data=task_data,
            priority="normal"
        )
        
        return {
            "success": True,
            "message": "Daily summary notification triggered",
            "task_id": task_id,
            "summary_data": daily_metrics
        }
        
    except Exception as e:
        logger.error(f"Error triggering daily summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger daily summary notification"
        )


@router.get("/health")
async def get_workflow_health():
    """
    Get current health status of all n8n workflows
    """
    try:
        from services.workflow_health_service import workflow_health_service
        
        health_result = await workflow_health_service.perform_health_check()
        
        return {
            "success": True,
            "health_status": health_result["status"],
            "health_score": health_result["overall_health_score"],
            "timestamp": health_result["timestamp"],
            "summary": {
                "deployment_valid": health_result.get("deployment_validation", {}).get("all_workflows_valid", False),
                "webhook_connectivity": health_result.get("webhook_connectivity", False),
                "active_workflows": health_result.get("workflow_status", {}).get("active_workflows", 0),
                "total_workflows": health_result.get("workflow_status", {}).get("total_workflows", 0),
                "alert_count": len(health_result.get("alerts", []))
            },
            "alerts": health_result.get("alerts", []),
            "recommendations": health_result.get("recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow health status"
        )


@router.get("/health/history")
async def get_workflow_health_history(limit: int = 10):
    """
    Get workflow health check history
    """
    try:
        from services.workflow_health_service import workflow_health_service
        
        history = await workflow_health_service.get_health_history(limit=limit)
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow health history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow health history"
        )


@router.get("/health/trends")
async def get_workflow_health_trends(hours: int = 24):
    """
    Get workflow health trends over specified time period
    """
    try:
        from services.workflow_health_service import workflow_health_service
        
        trends_result = await workflow_health_service.get_health_trends(hours=hours)
        
        if trends_result["success"]:
            return {
                "success": True,
                "trends": trends_result["trends"],
                "time_period_hours": hours
            }
        else:
            return {
                "success": False,
                "message": trends_result.get("message", "No trend data available"),
                "error": trends_result.get("error")
            }
        
    except Exception as e:
        logger.error(f"Error getting workflow health trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow health trends"
        )