"""
Applications API router - handles application submission and tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from shared.models import Application, ApplicationSubmissionRequest
from shared.utils import setup_logging
from services.application_service import application_service

logger = setup_logging("applications-router")
router = APIRouter()


@router.post("/submit", response_model=Application)
async def submit_application(
    request: ApplicationSubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit application for a job
    
    Creates and optionally submits an application for a job using an existing proposal.
    
    - **job_id**: UUID of the job to apply for
    - **proposal_id**: UUID of the proposal to use for the application
    - **confirm_submission**: Whether to immediately submit the application (default: False)
    
    If confirm_submission is False, the application is created in PENDING status.
    If confirm_submission is True, the application is submitted immediately.
    """
    try:
        return await application_service.submit_application(db=db, request=request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error submitting application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application"
        )


@router.get("/{application_id}", response_model=Application)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific application details
    
    Retrieves detailed information for a specific application by ID.
    
    - **application_id**: UUID of the application to retrieve
    """
    try:
        application = await application_service.get_application(
            db=db, 
            application_id=application_id
        )
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        return application
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application"
        )


@router.get("/", response_model=List[Application])
async def list_applications(
    status: Optional[str] = Query(None, description="Filter by application status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of applications to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    List applications
    
    Retrieves a list of applications with optional filtering.
    
    - **status**: Filter by application status (pending, submitted, viewed, interview, hired, declined)
    - **limit**: Maximum number of applications to return (1-200)
    
    Returns applications ordered by submission date (most recent first).
    """
    try:
        return await application_service.list_applications(
            db=db,
            status=status,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve applications"
        )


@router.put("/{application_id}/status")
async def update_application_status(
    application_id: UUID,
    status: str,
    client_response: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update application status
    
    Updates the status of an application and optionally records client response.
    
    - **application_id**: UUID of the application to update
    - **status**: New status (pending, submitted, viewed, interview, hired, declined)
    - **client_response**: Optional client response text
    
    When status is set to 'interview', the interview_scheduled flag is automatically set.
    When status is set to 'hired', the hired flag and hire_date are automatically set.
    """
    try:
        success = await application_service.update_application_status(
            db=db,
            application_id=application_id,
            status=status,
            client_response=client_response
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        return {
            "message": f"Application {application_id} status updated to {status}",
            "status": status
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating application status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application status"
        )


@router.get("/{application_id}/timeline")
async def get_application_timeline(
    application_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get application timeline
    
    Retrieves the timeline of events for a specific application.
    
    - **application_id**: UUID of the application
    
    Returns a chronological list of events including status changes,
    client responses, interview scheduling, and other milestones.
    """
    try:
        # This would implement a comprehensive timeline
        # For now, return basic structure
        return {
            "application_id": application_id,
            "timeline": [
                {
                    "event": "application_created",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "description": "Application created"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting application timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application timeline"
        )


@router.post("/batch-submit")
async def batch_submit_applications(
    application_ids: List[UUID],
    max_concurrent: int = Query(2, ge=1, le=5, description="Maximum concurrent submissions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit multiple applications using browser automation
    
    Processes multiple pending applications using automated browser submission.
    Uses rate limiting and human-like timing to maintain account safety.
    
    - **application_ids**: List of application UUIDs to submit
    - **max_concurrent**: Maximum number of concurrent browser sessions (1-5)
    
    Returns detailed results for each submission attempt including success status,
    execution time, and any error messages.
    """
    try:
        if not application_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one application ID is required"
            )
        
        result = await application_service.batch_submit_applications(
            db=db,
            application_ids=application_ids,
            max_concurrent=max_concurrent
        )
        
        if result["success"]:
            return {
                "message": f"Batch submission completed: {result['successful_submissions']}/{result['total_processed']} successful",
                "results": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute batch submission"
        )


@router.get("/submission-queue")
async def get_submission_queue(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get applications queued for submission
    
    Returns pending applications ordered by priority score, including job details,
    proposal quality, and submission readiness indicators.
    
    - **limit**: Maximum number of queue items to return (1-200)
    
    Priority scoring considers proposal quality, job pay rate, client rating,
    and job match score to optimize submission order.
    """
    try:
        queue_items = await application_service.get_submission_queue(db=db, limit=limit)
        
        return {
            "queue_size": len(queue_items),
            "items": queue_items,
            "next_submission_ready": len(queue_items) > 0,
            "estimated_submission_time": len(queue_items) * 5  # Rough estimate in minutes
        }
        
    except Exception as e:
        logger.error(f"Error getting submission queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submission queue"
        )


@router.get("/submission-stats")
async def get_submission_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get application submission statistics
    
    Returns comprehensive statistics about application submissions including:
    - Status distribution (pending, submitted, viewed, etc.)
    - Daily submission counts and limits
    - Browser automation status and rate limits
    - Queue size and processing estimates
    """
    try:
        stats = await application_service.get_submission_stats(db)
        
        return {
            "statistics": stats,
            "recommendations": _generate_submission_recommendations(stats)
        }
        
    except Exception as e:
        logger.error(f"Error getting submission statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve submission statistics"
        )


@router.post("/{application_id}/submit-now")
async def submit_application_immediately(
    application_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a specific application immediately using browser automation
    
    Bypasses the normal queue and submits the application immediately.
    Use with caution as it may impact rate limiting.
    
    - **application_id**: UUID of the application to submit immediately
    """
    try:
        # Get the application
        application = await application_service.get_application(db, application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application status '{application.status}' is not eligible for submission"
            )
        
        # Submit using batch submission with single item
        result = await application_service.batch_submit_applications(
            db=db,
            application_ids=[application_id],
            max_concurrent=1
        )
        
        if result["success"] and result["successful_submissions"] > 0:
            return {
                "message": "Application submitted successfully",
                "application_id": application_id,
                "execution_time": result["results"][0]["execution_time"]
            }
        else:
            error_msg = result["results"][0]["error_message"] if result["results"] else "Unknown error"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Submission failed: {error_msg}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting application immediately: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit application"
        )


def _generate_submission_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on submission statistics"""
    recommendations = []
    
    browser_stats = stats.get("browser_automation", {})
    queue_size = stats.get("queue_size", 0)
    submissions_today = stats.get("submissions_today", 0)
    
    # Rate limiting recommendations
    if browser_stats.get("rate_limit_status") == "limited":
        recommendations.append("Rate limit reached - submissions are paused until limits reset")
    
    # Queue management recommendations
    if queue_size > 20:
        recommendations.append(f"Large submission queue ({queue_size} items) - consider batch processing")
    elif queue_size == 0:
        recommendations.append("No applications in submission queue - run job discovery to find new opportunities")
    
    # Daily volume recommendations
    daily_limit = browser_stats.get("daily_limit", 30)
    if submissions_today >= daily_limit * 0.8:
        recommendations.append(f"Approaching daily limit ({submissions_today}/{daily_limit}) - plan remaining submissions carefully")
    elif submissions_today < daily_limit * 0.3:
        recommendations.append("Low daily submission volume - consider increasing automation frequency")
    
    return recommendations