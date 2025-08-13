"""
Safety and Compliance API Router

Provides endpoints for monitoring and controlling safety systems including:
- Rate limiting status and configuration
- Platform monitoring and response analysis
- Stealth operation controls
- Compliance monitoring and policy management
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from api.services.safety_service import safety_service, SafetyLevel, RateLimitConfig
from api.services.stealth_service import stealth_service, StealthLevel
from api.services.compliance_service import compliance_service, PolicyViolationType
from shared.utils import setup_logging

logger = setup_logging("safety-router")

router = APIRouter(prefix="/api/safety", tags=["safety"])


# Request/Response Models
class RateLimitStatusResponse(BaseModel):
    """Rate limit status response"""
    allowed: bool
    reason: str
    applications_today: int
    applications_this_hour: int
    daily_limit: int
    hourly_limit: int
    time_until_next_allowed: Optional[int] = None
    current_safety_level: str
    emergency_stop_active: bool


class SafetyMetricsResponse(BaseModel):
    """Safety metrics response"""
    applications_today: int
    applications_this_hour: int
    success_rate_24h: float
    success_rate_7d: float
    consecutive_failures: int
    last_application_time: Optional[datetime]
    current_safety_level: str
    compliance_status: str
    platform_warnings: List[str]


class PlatformResponseRequest(BaseModel):
    """Platform response analysis request"""
    status_code: int
    content: str
    response_time: float
    content_length: int
    headers: Dict[str, str] = Field(default_factory=dict)


class PlatformResponseAnalysis(BaseModel):
    """Platform response analysis result"""
    has_captcha: bool
    has_rate_limit_warning: bool
    has_unusual_content: bool
    error_indicators: List[str]
    risk_level: str
    should_pause: bool
    recommended_action: str


class StealthConfigRequest(BaseModel):
    """Stealth configuration request"""
    session_id: str
    stealth_level: Optional[str] = "standard"
    page_context: Dict[str, Any] = Field(default_factory=dict)


class StealthConfigResponse(BaseModel):
    """Stealth configuration response"""
    session_id: str
    fingerprint: Dict[str, Any]
    headers: Dict[str, str]
    proxy: Optional[Dict[str, str]]
    stealth_level: str


class ComplianceStatusResponse(BaseModel):
    """Compliance status response"""
    current_risk_level: str
    compliance_score: float
    violations_today: int
    total_violations: int
    last_violation_time: Optional[datetime]
    recent_violations: List[Dict[str, Any]]
    policy_adaptations: int
    emergency_stops_triggered: int


class PolicyUpdateRequest(BaseModel):
    """Policy update request"""
    max_applications_per_day: Optional[int] = None
    max_applications_per_hour: Optional[int] = None
    min_success_rate_threshold: Optional[float] = None
    captcha_pause_duration: Optional[int] = None
    rate_limit_pause_duration: Optional[int] = None
    auto_adapt_policies: Optional[bool] = None


class EmergencyControlRequest(BaseModel):
    """Emergency control request"""
    action: str  # "stop" or "resume"
    reason: str


# Rate Limiting Endpoints
@router.get("/rate-limits/status", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(db: AsyncSession = Depends(get_db)):
    """Get current rate limiting status"""
    try:
        allowed, reason = await safety_service.check_rate_limits(db)
        
        # Get current metrics
        await safety_service._update_safety_metrics(db)
        metrics = safety_service.safety_metrics
        config = safety_service.rate_limit_config
        
        # Calculate time until next allowed application
        time_until_next = None
        if not allowed and metrics.last_application_time:
            from datetime import timedelta
            next_allowed = metrics.last_application_time + timedelta(
                seconds=config.min_time_between_applications
            )
            remaining = next_allowed - datetime.utcnow()
            if remaining.total_seconds() > 0:
                time_until_next = int(remaining.total_seconds())
        
        return RateLimitStatusResponse(
            allowed=allowed,
            reason=reason,
            applications_today=metrics.applications_today,
            applications_this_hour=metrics.applications_this_hour,
            daily_limit=config.max_daily_applications,
            hourly_limit=config.max_hourly_applications,
            time_until_next_allowed=time_until_next,
            current_safety_level=metrics.current_safety_level.value,
            emergency_stop_active=safety_service.emergency_stop_active
        )
        
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting rate limit status: {e}"
        )


@router.get("/metrics", response_model=SafetyMetricsResponse)
async def get_safety_metrics(db: AsyncSession = Depends(get_db)):
    """Get comprehensive safety metrics"""
    try:
        status_data = await safety_service.get_safety_status(db)
        metrics = status_data["safety_metrics"]
        
        return SafetyMetricsResponse(
            applications_today=metrics["applications_today"],
            applications_this_hour=metrics["applications_this_hour"],
            success_rate_24h=metrics["success_rate_24h"],
            success_rate_7d=metrics["success_rate_7d"],
            consecutive_failures=metrics["consecutive_failures"],
            last_application_time=metrics.get("last_application_time"),
            current_safety_level=metrics["current_safety_level"],
            compliance_status=metrics["compliance_status"],
            platform_warnings=metrics["platform_warnings"]
        )
        
    except Exception as e:
        logger.error(f"Error getting safety metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting safety metrics: {e}"
        )


@router.post("/scaling/update")
async def update_gradual_scaling(db: AsyncSession = Depends(get_db)):
    """Update gradual scaling configuration based on performance"""
    try:
        config = await safety_service.implement_gradual_scaling(db)
        
        return {
            "success": True,
            "message": "Gradual scaling updated successfully",
            "config": {
                "max_daily_applications": config.max_daily_applications,
                "max_hourly_applications": config.max_hourly_applications,
                "min_time_between_applications": config.min_time_between_applications,
                "scaling_factor": config.scaling_factor
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating gradual scaling: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating gradual scaling: {e}"
        )


# Platform Monitoring Endpoints
@router.post("/platform/analyze", response_model=PlatformResponseAnalysis)
async def analyze_platform_response(
    request: PlatformResponseRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze platform response for safety and compliance issues"""
    try:
        response_data = {
            "status_code": request.status_code,
            "content": request.content,
            "response_time": request.response_time,
            "content_length": request.content_length,
            "headers": request.headers
        }
        
        # Analyze with safety service
        platform_response = await safety_service.analyze_platform_response(response_data)
        
        # Monitor with compliance service
        continue_allowed, violations = await compliance_service.monitor_platform_response(
            response_data, db
        )
        
        # Determine risk level and recommended action
        risk_level = "low"
        recommended_action = "continue"
        
        if platform_response.has_captcha:
            risk_level = "high"
            recommended_action = "pause_temporarily"
        elif platform_response.has_rate_limit_warning:
            risk_level = "high"
            recommended_action = "pause_temporarily"
        elif platform_response.has_unusual_content:
            risk_level = "medium"
            recommended_action = "slow_down"
        elif len(violations) > 0:
            risk_level = "medium"
            recommended_action = "monitor_closely"
        
        return PlatformResponseAnalysis(
            has_captcha=platform_response.has_captcha,
            has_rate_limit_warning=platform_response.has_rate_limit_warning,
            has_unusual_content=platform_response.has_unusual_content,
            error_indicators=platform_response.error_indicators,
            risk_level=risk_level,
            should_pause=not continue_allowed,
            recommended_action=recommended_action
        )
        
    except Exception as e:
        logger.error(f"Error analyzing platform response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing platform response: {e}"
        )


# Stealth Operation Endpoints
@router.post("/stealth/configure", response_model=StealthConfigResponse)
async def configure_stealth_measures(request: StealthConfigRequest):
    """Configure stealth measures for browser session"""
    try:
        # Set stealth level
        if request.stealth_level:
            level_map = {
                "minimal": StealthLevel.MINIMAL,
                "standard": StealthLevel.STANDARD,
                "maximum": StealthLevel.MAXIMUM
            }
            stealth_level = level_map.get(request.stealth_level, StealthLevel.STANDARD)
            stealth_service.set_stealth_level(stealth_level)
        
        # Generate fingerprint
        fingerprint = await stealth_service.generate_browser_fingerprint(request.session_id)
        
        # Apply stealth measures
        stealth_config = await stealth_service.apply_stealth_measures(
            request.session_id, request.page_context
        )
        
        return StealthConfigResponse(
            session_id=request.session_id,
            fingerprint=stealth_config.get("fingerprint", {}),
            headers=stealth_config.get("headers", {}),
            proxy=stealth_config.get("proxy"),
            stealth_level=stealth_config.get("stealth_level", "standard")
        )
        
    except Exception as e:
        logger.error(f"Error configuring stealth measures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error configuring stealth measures: {e}"
        )


@router.post("/stealth/rotate/{session_id}")
async def rotate_stealth_fingerprint(session_id: str):
    """Rotate stealth fingerprint for session"""
    try:
        fingerprint = await stealth_service.rotate_fingerprint(session_id)
        
        return {
            "success": True,
            "message": f"Fingerprint rotated for session {session_id}",
            "new_fingerprint": {
                "user_agent": fingerprint.user_agent,
                "viewport": fingerprint.viewport,
                "timezone": fingerprint.timezone,
                "locale": fingerprint.locale
            }
        }
        
    except Exception as e:
        logger.error(f"Error rotating stealth fingerprint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rotating stealth fingerprint: {e}"
        )


@router.post("/stealth/detect-anti-bot")
async def detect_anti_bot_measures(
    page_content: str,
    response_headers: Dict[str, str] = None
):
    """Detect anti-bot measures on page"""
    try:
        if response_headers is None:
            response_headers = {}
        
        detection = await stealth_service.detect_anti_bot_measures(
            page_content, response_headers
        )
        
        return {
            "success": True,
            "detection_results": detection
        }
        
    except Exception as e:
        logger.error(f"Error detecting anti-bot measures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting anti-bot measures: {e}"
        )


# Compliance Monitoring Endpoints
@router.get("/compliance/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(db: AsyncSession = Depends(get_db)):
    """Get comprehensive compliance status"""
    try:
        status_data = await compliance_service.get_compliance_status(db)
        
        return ComplianceStatusResponse(
            current_risk_level=status_data["risk_assessment"]["current_level"],
            compliance_score=status_data["risk_assessment"]["compliance_score"],
            violations_today=status_data["risk_assessment"]["violations_today"],
            total_violations=status_data["metrics"]["total_violations"],
            last_violation_time=datetime.fromisoformat(
                status_data["risk_assessment"]["last_violation"]
            ) if status_data["risk_assessment"]["last_violation"] else None,
            recent_violations=status_data["recent_violations"],
            policy_adaptations=status_data["metrics"]["policy_adaptations"],
            emergency_stops_triggered=status_data["metrics"]["emergency_stops_triggered"]
        )
        
    except Exception as e:
        logger.error(f"Error getting compliance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting compliance status: {e}"
        )


@router.post("/compliance/policy/update")
async def update_compliance_policy(request: PolicyUpdateRequest):
    """Update compliance policy configuration"""
    try:
        # Convert request to dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No policy updates provided"
            )
        
        compliance_service.update_policy(updates)
        
        return {
            "success": True,
            "message": "Compliance policy updated successfully",
            "updated_fields": list(updates.keys())
        }
        
    except Exception as e:
        logger.error(f"Error updating compliance policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating compliance policy: {e}"
        )


@router.post("/compliance/violations/reset")
async def reset_compliance_violations(violation_type: Optional[str] = None):
    """Reset compliance violations"""
    try:
        if violation_type:
            # Convert string to enum
            violation_type_enum = None
            for vt in PolicyViolationType:
                if vt.value == violation_type:
                    violation_type_enum = vt
                    break
            
            if not violation_type_enum:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid violation type: {violation_type}"
                )
            
            await compliance_service.reset_violations(violation_type_enum)
            message = f"Reset violations of type: {violation_type}"
        else:
            await compliance_service.reset_violations()
            message = "Reset all violations"
        
        return {
            "success": True,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error resetting compliance violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting compliance violations: {e}"
        )


# Emergency Controls
@router.post("/emergency/control")
async def emergency_control(request: EmergencyControlRequest):
    """Emergency stop or resume automation"""
    try:
        if request.action == "stop":
            await safety_service.trigger_emergency_stop(request.reason)
            message = f"Emergency stop triggered: {request.reason}"
        elif request.action == "resume":
            await safety_service.release_emergency_stop(request.reason)
            message = f"Emergency stop released: {request.reason}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'stop' or 'resume'"
            )
        
        return {
            "success": True,
            "message": message,
            "emergency_stop_active": safety_service.emergency_stop_active
        }
        
    except Exception as e:
        logger.error(f"Error in emergency control: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in emergency control: {e}"
        )


@router.get("/emergency/status")
async def get_emergency_status():
    """Get emergency stop status"""
    try:
        return {
            "emergency_stop_active": safety_service.emergency_stop_active,
            "current_safety_level": safety_service.safety_metrics.current_safety_level.value,
            "compliance_status": safety_service.safety_metrics.compliance_status.value
        }
        
    except Exception as e:
        logger.error(f"Error getting emergency status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting emergency status: {e}"
        )