"""
Performance tracking and analytics API endpoints
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from database.connection import get_db
from services.performance_tracking_service import performance_tracking_service
from services.analytics_engine import analytics_engine
from services.learning_system import learning_system
from services.recommendation_system import recommendation_system
from services.alerting_system import alerting_system, AlertSeverity, AlertType
from shared.utils import setup_logging

logger = setup_logging("performance-api")

router = APIRouter(prefix="/api/performance", tags=["performance"])


# Request/Response Models
class PipelineTrackingRequest(BaseModel):
    application_id: UUID
    stage: str
    metadata: Optional[Dict[str, Any]] = None


class AnalyticsRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    min_sample_size: int = Field(default=20, ge=5, le=1000)


class PredictiveScoreRequest(BaseModel):
    job_data: Dict[str, Any]
    proposal_data: Dict[str, Any]


class RecommendationRequest(BaseModel):
    analysis_days: int = Field(default=60, ge=7, le=365)
    focus_areas: Optional[List[str]] = None
    max_recommendations: int = Field(default=10, ge=1, le=50)


class StrategyAdjustmentRequest(BaseModel):
    force_adjustment: bool = False


class AlertThresholdUpdate(BaseModel):
    thresholds: Dict[str, Dict[str, float]]


class AlertAcknowledgment(BaseModel):
    acknowledged_by: str = "api_user"


class AlertResolution(BaseModel):
    resolution_notes: Optional[str] = None


# Performance Tracking Endpoints
@router.post("/track/pipeline")
async def track_application_pipeline(
    request: PipelineTrackingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Track application progress through the pipeline"""
    try:
        await performance_tracking_service.track_application_pipeline(
            db, request.application_id, request.stage, request.metadata
        )
        
        return {
            "status": "tracked",
            "application_id": str(request.application_id),
            "stage": request.stage,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error tracking pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/pipeline")
async def get_pipeline_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive pipeline analytics"""
    try:
        analytics = await performance_tracking_service.get_pipeline_analytics(db, days)
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting pipeline analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/correlations")
async def get_success_correlations(
    min_applications: int = Query(default=20, ge=5, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get success correlations and patterns"""
    try:
        correlations = await performance_tracking_service.get_success_correlations(
            db, min_applications
        )
        return correlations
        
    except Exception as e:
        logger.error(f"Error getting success correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_performance_insights(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get actionable performance insights"""
    try:
        insights = await performance_tracking_service.get_performance_insights(db, days)
        return insights
        
    except Exception as e:
        logger.error(f"Error getting performance insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics Engine Endpoints
@router.post("/analytics/patterns")
async def analyze_success_patterns(
    request: AnalyticsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze success patterns and correlations"""
    try:
        patterns = await analytics_engine.analyze_success_patterns(
            db, request.min_sample_size
        )
        return patterns
        
    except Exception as e:
        logger.error(f"Error analyzing success patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/opportunities")
async def get_optimization_opportunities(
    db: AsyncSession = Depends(get_db)
):
    """Get optimization opportunities"""
    try:
        # Get current performance for analysis
        current_performance = await performance_tracking_service.get_performance_insights(db, days=7)
        
        opportunities = await analytics_engine.identify_optimization_opportunities(
            db, current_performance
        )
        return {"opportunities": opportunities}
        
    except Exception as e:
        logger.error(f"Error getting optimization opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/predict")
async def calculate_predictive_scores(
    request: PredictiveScoreRequest,
    db: AsyncSession = Depends(get_db)
):
    """Calculate predictive scores for job/proposal combinations"""
    try:
        scores = await analytics_engine.calculate_predictive_scores(
            db, request.job_data, request.proposal_data
        )
        return scores
        
    except Exception as e:
        logger.error(f"Error calculating predictive scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/trends")
async def get_performance_trends(
    days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get performance trends analysis"""
    try:
        trends = await analytics_engine.analyze_performance_trends(db, days)
        return trends
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Learning System Endpoints
@router.post("/learning/analyze-adjust")
async def analyze_and_adjust_strategies(
    request: StrategyAdjustmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze performance and adjust strategies"""
    try:
        result = await learning_system.analyze_and_adjust_strategies(
            db, request.force_adjustment
        )
        return result
        
    except Exception as e:
        logger.error(f"Error in strategy analysis and adjustment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/evaluation")
async def evaluate_adjustment_results(
    days_since_adjustment: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate results of recent strategy adjustments"""
    try:
        evaluation = await learning_system.evaluate_adjustment_results(
            db, days_since_adjustment
        )
        return evaluation
        
    except Exception as e:
        logger.error(f"Error evaluating adjustment results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/insights")
async def get_learning_insights(
    db: AsyncSession = Depends(get_db)
):
    """Get insights from the learning system"""
    try:
        insights = await learning_system.get_learning_insights(db)
        return insights
        
    except Exception as e:
        logger.error(f"Error getting learning insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/predict-strategy")
async def predict_strategy_performance(
    strategy_changes: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Predict performance impact of strategy changes"""
    try:
        prediction = await learning_system.predict_strategy_performance(
            db, strategy_changes
        )
        return prediction
        
    except Exception as e:
        logger.error(f"Error predicting strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Recommendation System Endpoints
@router.post("/recommendations/comprehensive")
async def get_comprehensive_recommendations(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive recommendations across all categories"""
    try:
        recommendations = await recommendation_system.generate_comprehensive_recommendations(
            db, request.analysis_days
        )
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating comprehensive recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/personalized")
async def get_personalized_recommendations(
    focus_areas: Optional[str] = Query(default=None, description="Comma-separated focus areas"),
    max_recommendations: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get personalized recommendations"""
    try:
        focus_list = focus_areas.split(",") if focus_areas else None
        
        recommendations = await recommendation_system.get_personalized_recommendations(
            db, focus_list, max_recommendations
        )
        return {"recommendations": recommendations}
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/optimization-plan")
async def get_profile_optimization_plan(
    target_improvement: float = Query(default=0.2, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db)
):
    """Get profile optimization plan"""
    try:
        plan = await recommendation_system.generate_profile_optimization_plan(
            db, target_improvement
        )
        return plan
        
    except Exception as e:
        logger.error(f"Error generating optimization plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/{recommendation_id}/track")
async def track_recommendation_implementation(
    recommendation_id: str,
    implementation_status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Track recommendation implementation"""
    try:
        result = await recommendation_system.track_recommendation_implementation(
            db, recommendation_id, implementation_status, notes
        )
        return result
        
    except Exception as e:
        logger.error(f"Error tracking recommendation implementation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alerting System Endpoints
@router.get("/alerts/monitor")
async def monitor_performance(
    db: AsyncSession = Depends(get_db)
):
    """Run performance monitoring and generate alerts"""
    try:
        monitoring_result = await alerting_system.monitor_performance(db)
        return monitoring_result
        
    except Exception as e:
        logger.error(f"Error in performance monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/active")
async def get_active_alerts(
    severity: Optional[AlertSeverity] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Get active alerts"""
    try:
        alerts = await alerting_system.get_active_alerts(severity)
        return {"alerts": alerts}
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    request: AlertAcknowledgment,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an alert"""
    try:
        result = await alerting_system.acknowledge_alert(alert_id, request.acknowledged_by)
        return result
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: AlertResolution,
    db: AsyncSession = Depends(get_db)
):
    """Resolve an alert"""
    try:
        result = await alerting_system.resolve_alert(alert_id, request.resolution_notes)
        return result
        
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/history")
async def get_alert_history(
    days: int = Query(default=30, ge=1, le=365),
    alert_type: Optional[AlertType] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Get alert history"""
    try:
        history = await alerting_system.get_alert_history(days, alert_type)
        return {"alerts": history}
        
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/thresholds")
async def update_alert_thresholds(
    request: AlertThresholdUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update alert thresholds"""
    try:
        result = await alerting_system.update_alert_thresholds(request.thresholds)
        return result
        
    except Exception as e:
        logger.error(f"Error updating alert thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{alert_id}/action-plan")
async def get_corrective_action_plan(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get corrective action plan for an alert"""
    try:
        action_plan = await alerting_system.generate_corrective_action_plan(db, alert_id)
        return action_plan
        
    except Exception as e:
        logger.error(f"Error generating corrective action plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard and Summary Endpoints
@router.get("/dashboard")
async def get_performance_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive performance dashboard data"""
    try:
        # Get key metrics
        pipeline_analytics = await performance_tracking_service.get_pipeline_analytics(db, days=30)
        active_alerts = await alerting_system.get_active_alerts()
        recent_recommendations = await recommendation_system.get_personalized_recommendations(
            db, max_recommendations=5
        )
        
        # Get learning system status
        learning_insights = await learning_system.get_learning_insights(db)
        
        dashboard_data = {
            "last_updated": datetime.utcnow().isoformat(),
            "pipeline_analytics": pipeline_analytics,
            "active_alerts": {
                "total": len(active_alerts),
                "critical": len([a for a in active_alerts if a["severity"] == "critical"]),
                "high": len([a for a in active_alerts if a["severity"] == "high"]),
                "alerts": active_alerts[:5]  # Top 5 alerts
            },
            "top_recommendations": recent_recommendations,
            "learning_system": {
                "total_adjustments": learning_insights.get("total_adjustments", 0),
                "recent_performance": "stable"  # Would be calculated
            },
            "system_health": {
                "monitoring_enabled": alerting_system.monitoring_enabled,
                "last_analysis": datetime.utcnow().isoformat(),
                "status": "healthy"
            }
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_performance_summary(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Get performance summary for specified period"""
    try:
        # Get key performance indicators
        pipeline_analytics = await performance_tracking_service.get_pipeline_analytics(db, days)
        conversion_rates = pipeline_analytics.get("conversion_rates", {})
        
        # Calculate summary metrics
        summary = {
            "period": {
                "days": days,
                "end_date": datetime.utcnow().isoformat()
            },
            "key_metrics": {
                "applications_submitted": pipeline_analytics.get("pipeline_metrics", {}).get("applied", 0),
                "response_rate": conversion_rates.get("application_to_response", 0),
                "interview_rate": conversion_rates.get("response_to_interview", 0),
                "hire_rate": conversion_rates.get("interview_to_hire", 0),
                "overall_success_rate": (
                    conversion_rates.get("application_to_response", 0) / 100 *
                    conversion_rates.get("response_to_interview", 0) / 100 *
                    conversion_rates.get("interview_to_hire", 0) / 100 * 100
                )
            },
            "alerts_summary": {
                "new_alerts": len(await alerting_system.get_alert_history(days)),
                "active_alerts": len(await alerting_system.get_active_alerts())
            },
            "recommendations_available": len(await recommendation_system.get_personalized_recommendations(
                db, max_recommendations=20
            ))
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))