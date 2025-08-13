"""
System API router - handles system configuration and status
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from shared.models import SystemStatusResponse, SystemConfig
from shared.utils import setup_logging
from services.system_service import system_service

logger = setup_logging("system-router")
router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """
    Get current system status
    
    Returns comprehensive system status including:
    - Automation enabled/disabled state
    - Number of jobs in queue
    - Applications submitted today
    - Daily application limit
    - Success rate (last 30 days)
    - Last application timestamp
    """
    try:
        return await system_service.get_system_status(db)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )


@router.get("/config", response_model=SystemConfig)
async def get_system_config(db: AsyncSession = Depends(get_db)):
    """
    Get system configuration
    
    Returns current system configuration including:
    - Application limits and rates
    - Filtering criteria
    - Keywords for inclusion/exclusion
    - Automation settings
    - Notification preferences
    """
    try:
        return await system_service.get_system_config(db)
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system configuration"
        )


@router.put("/config", response_model=SystemConfig)
async def update_system_config(
    config: SystemConfig,
    db: AsyncSession = Depends(get_db)
):
    """
    Update system configuration
    
    Updates system configuration with new values:
    - **daily_application_limit**: Maximum applications per day
    - **min_hourly_rate**: Minimum acceptable hourly rate
    - **target_hourly_rate**: Target hourly rate for bidding
    - **min_client_rating**: Minimum client rating filter
    - **min_hire_rate**: Minimum client hire rate filter
    - **keywords_include**: Keywords to include in searches
    - **keywords_exclude**: Keywords to exclude from searches
    - **automation_enabled**: Enable/disable automation
    - **notification_channels**: Notification channel preferences
    - **profile_name**: Profile name for applications
    """
    try:
        return await system_service.update_system_config(db, config)
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system configuration"
        )


@router.get("/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive system health check
    
    Returns detailed health status for all system components:
    - Database connectivity and performance
    - Task queue status and stuck tasks
    - Browser automation service status
    - External service connectivity (Browserbase, OpenAI, Google, Slack)
    """
    try:
        return await system_service.get_system_health(db)
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            "status": "unhealthy",
            "error": "Health check failed",
            "details": str(e)
        }


@router.post("/automation/enable")
async def enable_automation(db: AsyncSession = Depends(get_db)):
    """
    Enable automation system
    
    Enables the automated job discovery and application system.
    """
    try:
        config = await system_service.get_system_config(db)
        config.automation_enabled = True
        await system_service.update_system_config(db, config)
        
        return {"message": "Automation enabled successfully"}
    except Exception as e:
        logger.error(f"Error enabling automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable automation"
        )


@router.post("/automation/disable")
async def disable_automation(db: AsyncSession = Depends(get_db)):
    """
    Disable automation system
    
    Disables the automated job discovery and application system.
    All running processes will be stopped gracefully.
    """
    try:
        config = await system_service.get_system_config(db)
        config.automation_enabled = False
        await system_service.update_system_config(db, config)
        
        return {"message": "Automation disabled successfully"}
    except Exception as e:
        logger.error(f"Error disabling automation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable automation"
        )