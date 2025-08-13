"""
Workflows API router - handles automated workflow orchestration
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from shared.models import JobSearchParams
from shared.utils import setup_logging
from services.workflow_service import workflow_service

logger = setup_logging("workflows-router")
router = APIRouter()


@router.post("/discovery-to-proposal")
async def execute_discovery_to_proposal_workflow(
    search_params: Optional[JobSearchParams] = None,
    max_jobs: int = Query(20, ge=1, le=100, description="Maximum jobs to process"),
    auto_generate_proposals: bool = Query(True, description="Automatically generate proposals"),
    quality_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum quality threshold"),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute complete discovery-to-proposal workflow
    
    This endpoint orchestrates the full automation workflow:
    1. Discovers new jobs using intelligent search
    2. Filters jobs based on quality criteria
    3. Automatically generates AI-powered proposals
    4. Stores proposals in Google Docs
    5. Exports results to Google Sheets
    
    - **search_params**: Optional search parameters (uses defaults if not provided)
    - **max_jobs**: Maximum number of jobs to process (1-100)
    - **auto_generate_proposals**: Whether to automatically generate proposals
    - **quality_threshold**: Minimum quality score for proposal generation (0.0-1.0)
    
    Returns comprehensive workflow results including statistics and next steps.
    """
    try:
        result = await workflow_service.execute_discovery_to_proposal_workflow(
            db=db,
            search_params=search_params,
            max_jobs=max_jobs,
            auto_generate_proposals=auto_generate_proposals,
            quality_threshold=quality_threshold
        )
        
        if result["success"]:
            return {
                "message": "Workflow completed successfully",
                "results": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow failed: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing discovery-to-proposal workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute workflow"
        )


@router.post("/optimize-proposals")
async def execute_proposal_optimization_workflow(
    proposal_ids: List[UUID],
    auto_apply_optimizations: bool = Query(False, description="Automatically apply optimizations"),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute proposal optimization workflow
    
    Analyzes multiple proposals and provides optimization suggestions.
    Optionally applies optimizations automatically for significant improvements.
    
    - **proposal_ids**: List of proposal UUIDs to optimize
    - **auto_apply_optimizations**: Whether to automatically apply optimizations
    
    Returns optimization results with suggestions and improvement statistics.
    """
    try:
        if not proposal_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one proposal ID is required"
            )
        
        result = await workflow_service.execute_proposal_optimization_workflow(
            db=db,
            proposal_ids=proposal_ids,
            auto_apply_optimizations=auto_apply_optimizations
        )
        
        if result["success"]:
            return {
                "message": "Proposal optimization workflow completed",
                "results": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Optimization workflow failed: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing proposal optimization workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute optimization workflow"
        )


@router.get("/status")
async def get_workflow_status(db: AsyncSession = Depends(get_db)):
    """
    Get current workflow status
    
    Returns information about running workflows, recent executions,
    and system readiness for workflow execution.
    """
    try:
        # This would track active workflows in a real implementation
        # For now, return basic status information
        
        return {
            "active_workflows": 0,
            "last_discovery_workflow": None,
            "last_optimization_workflow": None,
            "system_ready": True,
            "services_status": {
                "job_discovery": "ready",
                "proposal_generation": "ready", 
                "google_services": "ready",
                "llm_service": "ready"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow status"
        )


@router.post("/schedule")
async def schedule_workflow(
    workflow_type: str = Query(..., regex="^(discovery-to-proposal|optimize-proposals)$"),
    schedule_time: str = Query(..., description="ISO format datetime for scheduling"),
    workflow_params: dict = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a workflow for future execution
    
    - **workflow_type**: Type of workflow to schedule
    - **schedule_time**: When to execute the workflow (ISO format)
    - **workflow_params**: Parameters for the workflow execution
    
    This would integrate with a task queue system for actual scheduling.
    """
    try:
        # This would integrate with a task queue like Celery or Redis Queue
        # For now, return a placeholder response
        
        return {
            "message": f"Workflow '{workflow_type}' scheduled successfully",
            "workflow_id": f"scheduled_{workflow_type}_{schedule_time}",
            "scheduled_time": schedule_time,
            "status": "scheduled"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule workflow"
        )


@router.get("/history")
async def get_workflow_history(
    limit: int = Query(10, ge=1, le=100, description="Number of workflow executions to return"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get workflow execution history
    
    - **limit**: Number of executions to return (1-100)
    - **workflow_type**: Optional filter by workflow type
    
    Returns recent workflow executions with results and performance metrics.
    """
    try:
        # This would query a workflow history table in a real implementation
        # For now, return placeholder data
        
        return {
            "workflow_executions": [],
            "total_executions": 0,
            "success_rate": 0.0,
            "average_duration": 0.0
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow history"
        )