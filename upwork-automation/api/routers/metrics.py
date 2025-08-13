"""
Metrics API router - handles performance metrics and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from database.connection import get_db
from shared.models import DashboardMetrics
from shared.utils import setup_logging
from services.metrics_service import metrics_service

logger = setup_logging("metrics-router")
router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard metrics
    
    Returns comprehensive dashboard metrics including:
    - Total jobs discovered
    - Total applications submitted
    - Applications submitted today
    - Success rate (last 30 days)
    - Average response time
    - Top performing keywords
    - Recent applications
    """
    try:
        return await metrics_service.get_dashboard_metrics(db)
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )


@router.get("/performance")
async def get_performance_metrics(
    time_period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for specified time period
    
    - **time_period**: Aggregation period (daily, weekly, monthly)
    - **days**: Number of days to look back (1-365)
    
    Returns time-series performance data including:
    - Application success rates over time
    - Response rates and timing
    - Job discovery effectiveness
    - Conversion funnel metrics
    """
    try:
        return await metrics_service.get_performance_metrics(
            db=db,
            time_period=time_period,
            days=days
        )
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/funnel")
async def get_application_funnel_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get application funnel conversion metrics
    
    Returns conversion rates through the application pipeline:
    - Jobs discovered → Jobs filtered
    - Jobs filtered → Applications submitted
    - Applications submitted → Client responses
    - Client responses → Interviews scheduled
    - Interviews scheduled → Hired
    """
    try:
        return await metrics_service.get_application_funnel_metrics(db)
    except Exception as e:
        logger.error(f"Error getting funnel metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve funnel metrics"
        )


@router.post("/record")
async def record_performance_metric(
    metric_type: str,
    metric_value: float,
    time_period: str = "daily",
    metadata: Dict[str, Any] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Record a performance metric
    
    - **metric_type**: Type of metric (e.g., 'application_success', 'response_rate')
    - **metric_value**: Numeric value of the metric
    - **time_period**: Time period for aggregation (daily, weekly, monthly)
    - **metadata**: Additional metadata for the metric
    """
    try:
        await metrics_service.record_performance_metric(
            db=db,
            metric_type=metric_type,
            metric_value=metric_value,
            time_period=time_period,
            metadata=metadata or {}
        )
        
        return {
            "message": "Metric recorded successfully",
            "metric_type": metric_type,
            "metric_value": metric_value
        }
        
    except Exception as e:
        logger.error(f"Error recording metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record metric"
        )


@router.get("/summary")
async def get_metrics_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Get metrics summary for the specified number of days
    
    - **days**: Number of days to summarize (1-90)
    
    Returns a summary of key metrics including:
    - Total activity counts
    - Success rates and trends
    - Performance indicators
    """
    try:
        # This would implement a comprehensive metrics summary
        # For now, return basic structure
        return {
            "period_days": days,
            "summary": {
                "jobs_discovered": 0,
                "applications_submitted": 0,
                "success_rate": 0.0,
                "avg_response_time_hours": None
            },
            "trends": {
                "jobs_trend": "stable",
                "applications_trend": "stable", 
                "success_trend": "stable"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics summary"
        )