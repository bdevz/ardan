"""
Jobs API router - handles job discovery, filtering, and management
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from shared.models import Job, JobListResponse, JobSearchParams
from shared.utils import setup_logging
from services.job_service import job_service

logger = setup_logging("jobs-router")
router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    min_rate: Optional[float] = Query(None, ge=0, description="Minimum hourly rate"),
    max_rate: Optional[float] = Query(None, ge=0, description="Maximum hourly rate"),
    db: AsyncSession = Depends(get_db)
):
    """
    List jobs with filtering and pagination
    
    - **page**: Page number (starts from 1)
    - **per_page**: Number of items per page (1-100)
    - **status**: Filter by job status (discovered, filtered, queued, applied, rejected, archived)
    - **min_rate**: Minimum hourly rate filter
    - **max_rate**: Maximum hourly rate filter
    """
    try:
        return await job_service.list_jobs(
            db=db,
            page=page,
            per_page=per_page,
            status=status,
            min_rate=min_rate,
            max_rate=max_rate
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific job details by ID
    
    - **job_id**: UUID of the job to retrieve
    """
    try:
        job = await job_service.get_job(db=db, job_id=job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job"
        )


@router.post("/search")
async def search_jobs(
    search_params: JobSearchParams,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger job search with specified parameters
    
    This endpoint initiates an automated job search using the configured browser automation.
    It will discover new jobs, filter them based on criteria, and save them to the database.
    
    - **keywords**: List of keywords to search for
    - **min_hourly_rate**: Minimum hourly rate filter
    - **max_hourly_rate**: Maximum hourly rate filter
    - **min_client_rating**: Minimum client rating filter
    - **job_type**: Job type filter (fixed or hourly)
    - **location**: Location filter
    - **payment_verified_only**: Only include payment verified clients
    """
    try:
        result = await job_service.search_jobs(db=db, search_params=search_params)
        
        if result["success"]:
            return {
                "message": "Job search completed successfully",
                "results": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job search failed: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute job search"
        )


@router.put("/{job_id}/status")
async def update_job_status(
    job_id: UUID,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Update job status
    
    - **job_id**: UUID of the job to update
    - **status**: New status (discovered, filtered, queued, applied, rejected, archived)
    """
    try:
        success = await job_service.update_job_status(
            db=db,
            job_id=job_id,
            status=status
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return {"message": f"Job {job_id} status updated to {status}"}
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job status"
        )


@router.get("/{job_id}/stats")
async def get_job_stats(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get job statistics including proposals and applications
    
    - **job_id**: UUID of the job
    """
    try:
        # This would be implemented to get job-specific stats
        # For now, return basic structure
        return {
            "job_id": job_id,
            "proposals_count": 0,
            "applications_count": 0,
            "last_activity": None
        }
    except Exception as e:
        logger.error(f"Error getting job stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job statistics"
        )