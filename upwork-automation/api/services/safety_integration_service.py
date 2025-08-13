"""
Safety Integration Service

This service integrates all safety components and provides a unified interface
for the automation system to interact with safety controls.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from .safety_service import safety_service, SafetyLevel
from .stealth_service import stealth_service, StealthLevel
from .compliance_service import compliance_service, ComplianceAction
from shared.utils import setup_logging

logger = setup_logging("safety-integration")


class AutomationDecision(Enum):
    """Automation decision based on safety analysis"""
    PROCEED = "proceed"
    PROCEED_WITH_DELAY = "proceed_with_delay"
    PAUSE_TEMPORARILY = "pause_temporarily"
    EMERGENCY_STOP = "emergency_stop"
    ROTATE_SESSION = "rotate_session"
    CHANGE_STRATEGY = "change_strategy"


@dataclass
class SafetyAssessment:
    """Comprehensive safety assessment result"""
    decision: AutomationDecision
    reason: str
    delay_seconds: int = 0
    confidence: float = 1.0
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class ApplicationContext:
    """Context for application attempt"""
    job_id: str
    session_id: str
    attempt_number: int = 1
    previous_failures: int = 0
    last_attempt_time: Optional[datetime] = None


class SafetyIntegrationService:
    """Unified safety integration service"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.application_history: List[Dict[str, Any]] = []
        self.last_safety_check: Optional[datetime] = None
    
    async def assess_application_safety(
        self,
        context: ApplicationContext,
        db: AsyncSession
    ) -> SafetyAssessment:
        """
        Comprehensive safety assessment before application attempt
        """
        try:
            logger.info(f"Assessing application safety for job {context.job_id}")
            
            # Step 1: Check rate limits
            rate_allowed, rate_reason = await safety_service.check_rate_limits(db)
            if not rate_allowed:
                return SafetyAssessment(
                    decision=AutomationDecision.PAUSE_TEMPORARILY,
                    reason=f"Rate limit check failed: {rate_reason}",
                    delay_seconds=await self._calculate_rate_limit_delay(rate_reason)
                )
            
            # Step 2: Check compliance status
            compliance_status = await compliance_service.get_compliance_status(db)
            risk_level = compliance_status["risk_assessment"]["current_level"]
            
            if risk_level == "critical":
                return SafetyAssessment(
                    decision=AutomationDecision.EMERGENCY_STOP,
                    reason="Critical compliance risk level detected"
                )
            elif risk_level == "high":
                return SafetyAssessment(
                    decision=AutomationDecision.PAUSE_TEMPORARILY,
                    reason="High compliance risk level - temporary pause recommended",
                    delay_seconds=1800  # 30 minutes
                )
            
            # Step 3: Check emergency stop status
            if safety_service.emergency_stop_active:
                return SafetyAssessment(
                    decision=AutomationDecision.EMERGENCY_STOP,
                    reason="Emergency stop is currently active"
                )
            
            # Step 4: Assess session health
            session_assessment = await self._assess_session_health(context.session_id)
            if session_assessment["needs_rotation"]:
                return SafetyAssessment(
                    decision=AutomationDecision.ROTATE_SESSION,
                    reason="Browser session needs rotation for safety",
                    recommendations=["Create new browser session", "Apply fresh fingerprint"]
                )
            
            # Step 5: Calculate human delay
            human_delay = await safety_service.calculate_human_delay()
            
            # Step 6: Check for strategy changes needed
            strategy_change = await self._assess_strategy_change(context, db)
            if strategy_change["needed"]:
                return SafetyAssessment(
                    decision=AutomationDecision.CHANGE_STRATEGY,
                    reason=strategy_change["reason"],
                    recommendations=strategy_change["recommendations"]
                )
            
            # Step 7: Final decision
            if risk_level == "medium":
                return SafetyAssessment(
                    decision=AutomationDecision.PROCEED_WITH_DELAY,
                    reason="Medium risk level - proceeding with increased delay",
                    delay_seconds=human_delay * 2,  # Double delay for medium risk
                    confidence=0.7,
                    recommendations=["Monitor response closely", "Be ready to pause if issues arise"]
                )
            else:
                return SafetyAssessment(
                    decision=AutomationDecision.PROCEED,
                    reason="All safety checks passed",
                    delay_seconds=human_delay,
                    confidence=0.9,
                    recommendations=["Continue normal operation"]
                )
            
        except Exception as e:
            logger.error(f"Error in safety assessment: {e}")
            return SafetyAssessment(
                decision=AutomationDecision.PAUSE_TEMPORARILY,
                reason=f"Safety assessment error: {e}",
                delay_seconds=300  # 5 minutes
            )
    
    async def prepare_safe_session(
        self,
        session_id: str,
        page_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare browser session with all safety measures
        """
        try:
            logger.info(f"Preparing safe session: {session_id}")
            
            # Step 1: Generate stealth configuration
            stealth_config = await stealth_service.apply_stealth_measures(
                session_id, page_context
            )
            
            # Step 2: Check if fingerprint rotation is needed
            session_info = self.active_sessions.get(session_id, {})
            last_rotation = session_info.get("last_fingerprint_rotation")
            
            if (not last_rotation or 
                datetime.utcnow() - last_rotation > timedelta(hours=2)):
                # Rotate fingerprint every 2 hours
                await stealth_service.rotate_fingerprint(session_id)
                stealth_config = await stealth_service.apply_stealth_measures(
                    session_id, page_context
                )
                
                # Update session info
                if session_id not in self.active_sessions:
                    self.active_sessions[session_id] = {}
                self.active_sessions[session_id]["last_fingerprint_rotation"] = datetime.utcnow()
            
            # Step 3: Add safety headers and configuration
            safety_config = {
                "stealth": stealth_config,
                "safety_level": safety_service.safety_metrics.current_safety_level.value,
                "rate_limits": {
                    "max_daily": safety_service.rate_limit_config.max_daily_applications,
                    "max_hourly": safety_service.rate_limit_config.max_hourly_applications,
                    "min_interval": safety_service.rate_limit_config.min_time_between_applications
                },
                "session_id": session_id,
                "prepared_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Safe session prepared for {session_id}")
            return safety_config
            
        except Exception as e:
            logger.error(f"Error preparing safe session: {e}")
            raise
    
    async def analyze_response_and_adapt(
        self,
        response_data: Dict[str, Any],
        session_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Analyze platform response and adapt safety measures
        """
        try:
            logger.info(f"Analyzing response for session {session_id}")
            
            # Step 1: Analyze with safety service
            platform_response = await safety_service.analyze_platform_response(response_data)
            
            # Step 2: Monitor with compliance service
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, db
            )
            
            # Step 3: Detect anti-bot measures
            anti_bot_detection = await stealth_service.detect_anti_bot_measures(
                response_data.get("content", ""),
                response_data.get("headers", {})
            )
            
            # Step 4: Update session tracking
            session_info = self.active_sessions.get(session_id, {})
            session_info.update({
                "last_response_analysis": datetime.utcnow(),
                "response_count": session_info.get("response_count", 0) + 1,
                "last_risk_level": anti_bot_detection.get("risk_level", "low")
            })
            self.active_sessions[session_id] = session_info
            
            # Step 5: Determine adaptations needed
            adaptations = []
            
            if platform_response.has_captcha:
                adaptations.append({
                    "type": "emergency_pause",
                    "reason": "CAPTCHA detected",
                    "duration": 3600  # 1 hour
                })
            
            if platform_response.has_rate_limit_warning:
                adaptations.append({
                    "type": "increase_delays",
                    "reason": "Rate limit warning detected",
                    "multiplier": 2.0
                })
            
            if anti_bot_detection.get("risk_level") == "high":
                adaptations.append({
                    "type": "rotate_fingerprint",
                    "reason": "High anti-bot risk detected",
                    "session_id": session_id
                })
            
            if len(violations) > 0:
                adaptations.append({
                    "type": "compliance_action",
                    "reason": f"Compliance violations detected: {len(violations)}",
                    "violations": [v.violation_type.value for v in violations]
                })
            
            # Step 6: Execute adaptations
            for adaptation in adaptations:
                await self._execute_adaptation(adaptation, session_id, db)
            
            analysis_result = {
                "continue_allowed": continue_allowed,
                "platform_response": {
                    "has_captcha": platform_response.has_captcha,
                    "has_rate_limit_warning": platform_response.has_rate_limit_warning,
                    "has_unusual_content": platform_response.has_unusual_content,
                    "error_indicators": platform_response.error_indicators
                },
                "anti_bot_detection": anti_bot_detection,
                "violations": [
                    {
                        "type": v.violation_type.value,
                        "severity": v.severity,
                        "description": v.description
                    } for v in violations
                ],
                "adaptations_applied": adaptations,
                "session_health": session_info
            }
            
            logger.info(f"Response analysis complete for session {session_id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing response: {e}")
            return {
                "continue_allowed": False,
                "error": str(e),
                "adaptations_applied": []
            }
    
    async def _calculate_rate_limit_delay(self, rate_reason: str) -> int:
        """Calculate appropriate delay based on rate limit reason"""
        if "daily limit" in rate_reason.lower():
            # Wait until next day
            now = datetime.utcnow()
            next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            return int((next_day - now).total_seconds())
        
        elif "hourly limit" in rate_reason.lower():
            # Wait until next hour
            now = datetime.utcnow()
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return int((next_hour - now).total_seconds())
        
        elif "must wait" in rate_reason.lower():
            # Extract wait time from reason if possible
            import re
            match = re.search(r'(\d+)', rate_reason)
            if match:
                return int(match.group(1))
            return 300  # Default 5 minutes
        
        else:
            return 600  # Default 10 minutes
    
    async def _assess_session_health(self, session_id: str) -> Dict[str, Any]:
        """Assess health of browser session"""
        session_info = self.active_sessions.get(session_id, {})
        
        # Check session age
        created_at = session_info.get("created_at", datetime.utcnow())
        age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
        
        # Check response count
        response_count = session_info.get("response_count", 0)
        
        # Check last risk level
        last_risk_level = session_info.get("last_risk_level", "low")
        
        needs_rotation = (
            age_hours > 4 or  # Session older than 4 hours
            response_count > 50 or  # Too many responses
            last_risk_level == "high"  # High risk detected
        )
        
        return {
            "session_id": session_id,
            "age_hours": age_hours,
            "response_count": response_count,
            "last_risk_level": last_risk_level,
            "needs_rotation": needs_rotation,
            "health_score": max(0.0, 1.0 - (age_hours / 8) - (response_count / 100))
        }
    
    async def _assess_strategy_change(
        self,
        context: ApplicationContext,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Assess if automation strategy needs to change"""
        try:
            # Check recent success rate
            success_rate = await safety_service._calculate_success_rate(db, days=1)
            
            # Check consecutive failures
            consecutive_failures = await safety_service._count_consecutive_failures(db)
            
            # Determine if strategy change is needed
            needs_change = False
            reason = ""
            recommendations = []
            
            if success_rate < 0.05 and context.previous_failures > 3:
                needs_change = True
                reason = "Very low success rate with multiple failures"
                recommendations = [
                    "Switch to different job search keywords",
                    "Adjust proposal template",
                    "Change application timing"
                ]
            
            elif consecutive_failures > 8:
                needs_change = True
                reason = "Too many consecutive failures"
                recommendations = [
                    "Review and update job filtering criteria",
                    "Analyze failed applications for patterns",
                    "Consider temporary pause for strategy review"
                ]
            
            return {
                "needed": needs_change,
                "reason": reason,
                "recommendations": recommendations,
                "current_success_rate": success_rate,
                "consecutive_failures": consecutive_failures
            }
            
        except Exception as e:
            logger.error(f"Error assessing strategy change: {e}")
            return {"needed": False, "reason": "", "recommendations": []}
    
    async def _execute_adaptation(
        self,
        adaptation: Dict[str, Any],
        session_id: str,
        db: AsyncSession
    ):
        """Execute safety adaptation"""
        try:
            adaptation_type = adaptation["type"]
            
            if adaptation_type == "emergency_pause":
                await safety_service.trigger_emergency_stop(adaptation["reason"])
                logger.warning(f"Emergency pause triggered: {adaptation['reason']}")
            
            elif adaptation_type == "increase_delays":
                multiplier = adaptation.get("multiplier", 1.5)
                safety_service.rate_limit_config.scaling_factor *= multiplier
                logger.info(f"Increased delays by factor {multiplier}")
            
            elif adaptation_type == "rotate_fingerprint":
                await stealth_service.rotate_fingerprint(session_id)
                logger.info(f"Rotated fingerprint for session {session_id}")
            
            elif adaptation_type == "compliance_action":
                # Compliance actions are handled by compliance service
                logger.info(f"Compliance action noted: {adaptation['reason']}")
            
        except Exception as e:
            logger.error(f"Error executing adaptation {adaptation_type}: {e}")
    
    async def get_safety_dashboard(self, db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive safety dashboard data"""
        try:
            # Get data from all safety services
            safety_status = await safety_service.get_safety_status(db)
            compliance_status = await compliance_service.get_compliance_status(db)
            
            # Session health summary
            session_health = {}
            for session_id, info in self.active_sessions.items():
                health = await self._assess_session_health(session_id)
                session_health[session_id] = health
            
            dashboard = {
                "safety_metrics": safety_status["safety_metrics"],
                "rate_limits": safety_status["rate_limit_config"],
                "compliance": {
                    "risk_level": compliance_status["risk_assessment"]["current_level"],
                    "compliance_score": compliance_status["risk_assessment"]["compliance_score"],
                    "violations_today": compliance_status["risk_assessment"]["violations_today"],
                    "recent_violations": compliance_status["recent_violations"][:5]  # Last 5
                },
                "session_health": session_health,
                "emergency_status": {
                    "emergency_stop_active": safety_service.emergency_stop_active,
                    "current_safety_level": safety_status["safety_metrics"]["current_safety_level"]
                },
                "recommendations": await self._generate_safety_recommendations(
                    safety_status, compliance_status
                ),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error getting safety dashboard: {e}")
            return {"error": str(e)}
    
    async def _generate_safety_recommendations(
        self,
        safety_status: Dict[str, Any],
        compliance_status: Dict[str, Any]
    ) -> List[str]:
        """Generate safety recommendations based on current status"""
        recommendations = []
        
        # Check safety metrics
        metrics = safety_status["safety_metrics"]
        
        if metrics["success_rate_24h"] < 0.1:
            recommendations.append("Consider pausing automation due to low success rate")
        
        if metrics["consecutive_failures"] > 5:
            recommendations.append("Review job filtering criteria - too many consecutive failures")
        
        if metrics["applications_today"] > metrics.get("daily_limit", 30) * 0.8:
            recommendations.append("Approaching daily application limit - consider slowing down")
        
        # Check compliance status
        risk_level = compliance_status["risk_assessment"]["current_level"]
        
        if risk_level == "high":
            recommendations.append("High compliance risk - consider temporary pause")
        elif risk_level == "medium":
            recommendations.append("Medium compliance risk - increase monitoring")
        
        if compliance_status["risk_assessment"]["violations_today"] > 3:
            recommendations.append("Multiple violations today - review automation strategy")
        
        # Session health recommendations
        unhealthy_sessions = sum(
            1 for info in self.active_sessions.values()
            if info.get("health_score", 1.0) < 0.5
        )
        
        if unhealthy_sessions > 0:
            recommendations.append(f"Rotate {unhealthy_sessions} unhealthy browser sessions")
        
        if not recommendations:
            recommendations.append("All safety systems operating normally")
        
        return recommendations


# Global service instance
safety_integration_service = SafetyIntegrationService()