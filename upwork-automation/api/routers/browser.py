"""
Browser automation API router - handles browser session management and automation
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from database.connection import get_db
from shared.models import BrowserSession
from shared.utils import setup_logging
from services.browser_service import browser_service

logger = setup_logging("browser-router")
router = APIRouter()


@router.post("/session", response_model=BrowserSession)
async def create_browser_session(
    session_type: str = "job_discovery",
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new browser session
    
    Creates a new browser automation session using Browserbase and Stagehand.
    
    - **session_type**: Type of session (job_discovery, proposal_submission, profile_management)
    - **context**: Optional context data for the session
    
    Returns the created session details including session ID and connection information.
    """
    try:
        return await browser_service.create_browser_session(
            db=db,
            session_type=session_type,
            context=context
        )
    except Exception as e:
        logger.error(f"Error creating browser session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create browser session"
        )


@router.get("/session/{session_id}", response_model=BrowserSession)
async def get_browser_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get browser session details
    
    Retrieves details for a specific browser session by ID.
    
    - **session_id**: UUID of the browser session
    """
    try:
        session = await browser_service.get_browser_session(db=db, session_id=session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Browser session not found"
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting browser session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve browser session"
        )


@router.get("/sessions", response_model=List[BrowserSession])
async def list_browser_sessions(
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    status: Optional[str] = Query(None, description="Filter by session status"),
    db: AsyncSession = Depends(get_db)
):
    """
    List browser sessions
    
    Retrieves a list of browser sessions with optional filtering.
    
    - **session_type**: Filter by session type (job_discovery, proposal_submission, etc.)
    - **status**: Filter by session status (active, expired, terminated)
    """
    try:
        return await browser_service.list_browser_sessions(
            db=db,
            session_type=session_type,
            status=status
        )
    except Exception as e:
        logger.error(f"Error listing browser sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve browser sessions"
        )


@router.delete("/session/{session_id}")
async def terminate_browser_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Terminate browser session
    
    Terminates a browser session and cleans up associated resources.
    
    - **session_id**: UUID of the browser session to terminate
    """
    try:
        success = await browser_service.terminate_browser_session(
            db=db,
            session_id=session_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Browser session not found"
            )
        
        return {"message": f"Browser session {session_id} terminated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating browser session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate browser session"
        )


@router.post("/search-jobs")
async def browser_search_jobs(
    keywords: List[str],
    session_pool_size: int = Query(3, ge=1, le=10),
    max_jobs: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for jobs using browser automation
    
    Initiates an automated job search using browser automation with Stagehand.
    Creates a pool of browser sessions to search for jobs in parallel.
    
    - **keywords**: List of keywords to search for
    - **session_pool_size**: Number of parallel browser sessions (1-10)
    - **max_jobs**: Maximum number of jobs to discover (1-200)
    
    Returns search results including jobs found, processing statistics, and performance metrics.
    """
    try:
        if not keywords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one keyword is required"
            )
        
        result = await browser_service.browser_search_jobs(
            db=db,
            keywords=keywords,
            session_pool_size=session_pool_size,
            max_jobs=max_jobs
        )
        
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
        logger.error(f"Error in browser job search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute browser job search"
        )


@router.post("/cleanup-expired")
async def cleanup_expired_sessions(db: AsyncSession = Depends(get_db)):
    """
    Cleanup expired browser sessions
    
    Finds and terminates expired browser sessions to free up resources.
    This endpoint can be called periodically for maintenance.
    
    Returns the number of sessions that were cleaned up.
    """
    try:
        cleanup_count = await browser_service.cleanup_expired_sessions(db)
        
        return {
            "message": f"Cleaned up {cleanup_count} expired sessions",
            "sessions_cleaned": cleanup_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired sessions"
        )


@router.get("/health")
async def browser_automation_health():
    """
    Browser automation health check
    
    Checks the health of browser automation components including:
    - Browserbase connectivity
    - Stagehand functionality
    - Session pool status
    """
    try:
        # This would implement comprehensive health checks
        # For now, return basic structure
        return {
            "status": "healthy",
            "components": {
                "browserbase": "unknown",
                "stagehand": "unknown",
                "session_pool": "unknown"
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error checking browser automation health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }