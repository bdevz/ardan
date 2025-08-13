"""
Compliance Monitoring Service for Upwork Automation

This service monitors platform compliance and adapts policies to maintain
account safety and adherence to platform terms of service.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ApplicationModel, JobModel
from shared.utils import setup_logging
from shared.config import settings

logger = setup_logging("compliance-service")


class PolicyViolationType(Enum):
    """Types of policy violations"""
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CAPTCHA_TRIGGERED = "captcha_triggered"
    ACCOUNT_WARNING = "account_warning"
    UNUSUAL_RESPONSE = "unusual_response"
    SUCCESS_RATE_LOW = "success_rate_low"


class ComplianceAction(Enum):
    """Actions to take for compliance"""
    CONTINUE = "continue"
    SLOW_DOWN = "slow_down"
    PAUSE_TEMPORARILY = "pause_temporarily"
    EMERGENCY_STOP = "emergency_stop"
    ROTATE_SESSION = "rotate_session"
    CHANGE_STRATEGY = "change_strategy"


@dataclass
class PolicyViolation:
    """Policy violation record"""
    violation_type: PolicyViolationType
    severity: str  # low, medium, high, critical
    description: str
    detected_at: datetime
    evidence: Dict[str, Any]
    action_taken: Optional[ComplianceAction] = None
    resolved: bool = False


@dataclass
class CompliancePolicy:
    """Compliance policy configuration"""
    max_applications_per_hour: int = 5
    max_applications_per_day: int = 30
    min_success_rate_threshold: float = 0.1
    max_consecutive_failures: int = 5
    captcha_pause_duration: int = 3600  # seconds
    rate_limit_pause_duration: int = 1800  # seconds
    auto_adapt_policies: bool = True
    emergency_stop_on_critical: bool = True


@dataclass
class ComplianceMetrics:
    """Compliance monitoring metrics"""
    total_violations: int = 0
    violations_today: int = 0
    last_violation_time: Optional[datetime] = None
    current_risk_level: str = "low"  # low, medium, high, critical
    policy_adaptations: int = 0
    emergency_stops_triggered: int = 0
    average_success_rate: float = 0.0
    compliance_score: float = 1.0  # 0.0 to 1.0


class ComplianceService:
    """Comprehensive compliance monitoring and policy adaptation service"""
    
    def __init__(self):
        self.policy = CompliancePolicy()
        self.violations: List[PolicyViolation] = []
        self.metrics = ComplianceMetrics()
        self.platform_patterns: Dict[str, Any] = {}
        self.adaptive_thresholds: Dict[str, float] = {}
        
        # Load configuration
        self._load_policy_configuration()
        self._initialize_platform_patterns()
    
    def _load_policy_configuration(self):
        """Load compliance policy from settings"""
        self.policy.max_applications_per_day = settings.daily_application_limit
        self.policy.max_applications_per_hour = getattr(
            settings, 'max_hourly_applications', 5
        )
        self.policy.min_success_rate_threshold = getattr(
            settings, 'min_success_rate_threshold', 0.1
        )
    
    def _initialize_platform_patterns(self):
        """Initialize known platform response patterns"""
        self.platform_patterns = {
            "upwork_captcha_indicators": [
                r"recaptcha",
                r"verify.*human",
                r"security.*check",
                r"unusual.*activity"
            ],
            "upwork_rate_limit_indicators": [
                r"rate.*limit",
                r"too.*many.*requests",
                r"slow.*down",
                r"temporarily.*blocked"
            ],
            "upwork_account_warnings": [
                r"account.*warning",
                r"policy.*violation",
                r"terms.*service",
                r"suspended.*account"
            ],
            "upwork_success_indicators": [
                r"application.*submitted",
                r"proposal.*sent",
                r"successfully.*applied"
            ],
            "upwork_error_indicators": [
                r"error.*occurred",
                r"something.*wrong",
                r"try.*again.*later",
                r"service.*unavailable"
            ]
        }
    
    async def monitor_platform_response(
        self,
        response_data: Dict[str, Any],
        db: AsyncSession
    ) -> Tuple[bool, List[PolicyViolation]]:
        """
        Monitor platform response for compliance issues
        Returns: (continue_allowed, violations_detected)
        """
        try:
            violations_detected = []
            
            # Extract response details
            status_code = response_data.get('status_code', 200)
            content = response_data.get('content', '').lower()
            response_time = response_data.get('response_time', 0.0)
            headers = response_data.get('headers', {})
            
            # Check for CAPTCHA
            captcha_violation = await self._check_captcha_violation(content)
            if captcha_violation:
                violations_detected.append(captcha_violation)
            
            # Check for rate limiting
            rate_limit_violation = await self._check_rate_limit_violation(content, headers)
            if rate_limit_violation:
                violations_detected.append(rate_limit_violation)
            
            # Check for account warnings
            account_warning = await self._check_account_warning(content)
            if account_warning:
                violations_detected.append(account_warning)
            
            # Check for unusual responses
            unusual_response = await self._check_unusual_response(
                status_code, content, response_time
            )
            if unusual_response:
                violations_detected.append(unusual_response)
            
            # Check application success rates
            success_rate_violation = await self._check_success_rate_violation(db)
            if success_rate_violation:
                violations_detected.append(success_rate_violation)
            
            # Process violations
            for violation in violations_detected:
                await self._process_violation(violation, db)
            
            # Determine if automation should continue
            continue_allowed = await self._determine_continuation_status(violations_detected)
            
            return continue_allowed, violations_detected
            
        except Exception as e:
            logger.error(f"Error monitoring platform response: {e}")
            return False, []
    
    async def _check_captcha_violation(self, content: str) -> Optional[PolicyViolation]:
        """Check for CAPTCHA indicators"""
        for pattern in self.platform_patterns["upwork_captcha_indicators"]:
            if re.search(pattern, content, re.IGNORECASE):
                return PolicyViolation(
                    violation_type=PolicyViolationType.CAPTCHA_TRIGGERED,
                    severity="high",
                    description="CAPTCHA challenge detected on platform",
                    detected_at=datetime.utcnow(),
                    evidence={"pattern_matched": pattern, "content_snippet": content[:200]}
                )
        return None
    
    async def _check_rate_limit_violation(
        self, 
        content: str, 
        headers: Dict[str, str]
    ) -> Optional[PolicyViolation]:
        """Check for rate limiting indicators"""
        # Check content patterns
        for pattern in self.platform_patterns["upwork_rate_limit_indicators"]:
            if re.search(pattern, content, re.IGNORECASE):
                return PolicyViolation(
                    violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                    severity="high",
                    description="Rate limiting detected from platform response",
                    detected_at=datetime.utcnow(),
                    evidence={"pattern_matched": pattern, "content_snippet": content[:200]}
                )
        
        # Check headers for rate limit indicators
        rate_limit_headers = ['x-ratelimit-remaining', 'retry-after', 'x-rate-limit-reset']
        for header in rate_limit_headers:
            if header.lower() in [h.lower() for h in headers.keys()]:
                return PolicyViolation(
                    violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                    severity="medium",
                    description="Rate limit headers detected",
                    detected_at=datetime.utcnow(),
                    evidence={"header_found": header, "header_value": headers.get(header)}
                )
        
        return None
    
    async def _check_account_warning(self, content: str) -> Optional[PolicyViolation]:
        """Check for account warning indicators"""
        for pattern in self.platform_patterns["upwork_account_warnings"]:
            if re.search(pattern, content, re.IGNORECASE):
                return PolicyViolation(
                    violation_type=PolicyViolationType.ACCOUNT_WARNING,
                    severity="critical",
                    description="Account warning or policy violation detected",
                    detected_at=datetime.utcnow(),
                    evidence={"pattern_matched": pattern, "content_snippet": content[:200]}
                )
        return None
    
    async def _check_unusual_response(
        self, 
        status_code: int, 
        content: str, 
        response_time: float
    ) -> Optional[PolicyViolation]:
        """Check for unusual response patterns"""
        # Check for unusual status codes
        if status_code in [429, 503, 403]:
            return PolicyViolation(
                violation_type=PolicyViolationType.UNUSUAL_RESPONSE,
                severity="medium",
                description=f"Unusual HTTP status code: {status_code}",
                detected_at=datetime.utcnow(),
                evidence={"status_code": status_code, "response_time": response_time}
            )
        
        # Check for unusually short responses
        if len(content) < 500 and status_code == 200:
            return PolicyViolation(
                violation_type=PolicyViolationType.UNUSUAL_RESPONSE,
                severity="low",
                description="Unusually short response content",
                detected_at=datetime.utcnow(),
                evidence={"content_length": len(content), "status_code": status_code}
            )
        
        # Check for unusually slow responses
        if response_time > 30.0:
            return PolicyViolation(
                violation_type=PolicyViolationType.UNUSUAL_RESPONSE,
                severity="low",
                description="Unusually slow response time",
                detected_at=datetime.utcnow(),
                evidence={"response_time": response_time}
            )
        
        return None
    
    async def _check_success_rate_violation(self, db: AsyncSession) -> Optional[PolicyViolation]:
        """Check for low success rate violations"""
        try:
            # Calculate recent success rate
            cutoff_date = datetime.utcnow() - timedelta(days=1)
            
            # Count total applications in last 24 hours
            total_query = select(func.count(ApplicationModel.id)).where(
                ApplicationModel.submitted_at >= cutoff_date
            )
            total_result = await db.execute(total_query)
            total_applications = total_result.scalar() or 0
            
            if total_applications < 5:  # Need minimum applications to assess
                return None
            
            # Count successful applications
            success_query = select(func.count(ApplicationModel.id)).where(
                and_(
                    ApplicationModel.submitted_at >= cutoff_date,
                    (ApplicationModel.hired == True) | (ApplicationModel.interview_scheduled == True)
                )
            )
            success_result = await db.execute(success_query)
            successful_applications = success_result.scalar() or 0
            
            success_rate = successful_applications / total_applications
            
            if success_rate < self.policy.min_success_rate_threshold:
                return PolicyViolation(
                    violation_type=PolicyViolationType.SUCCESS_RATE_LOW,
                    severity="medium",
                    description=f"Success rate below threshold: {success_rate:.2%}",
                    detected_at=datetime.utcnow(),
                    evidence={
                        "success_rate": success_rate,
                        "total_applications": total_applications,
                        "successful_applications": successful_applications,
                        "threshold": self.policy.min_success_rate_threshold
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking success rate violation: {e}")
            return None
    
    async def _process_violation(self, violation: PolicyViolation, db: AsyncSession):
        """Process detected violation and determine action"""
        try:
            # Add to violations list
            self.violations.append(violation)
            
            # Update metrics
            self.metrics.total_violations += 1
            self.metrics.violations_today += 1
            self.metrics.last_violation_time = violation.detected_at
            
            # Determine action based on violation type and severity
            action = await self._determine_compliance_action(violation)
            violation.action_taken = action
            
            # Execute action
            await self._execute_compliance_action(action, violation)
            
            # Update risk level
            await self._update_risk_level()
            
            # Adapt policies if enabled
            if self.policy.auto_adapt_policies:
                await self._adapt_policies(violation)
            
            logger.warning(f"Processed violation: {violation.violation_type.value} "
                          f"(severity: {violation.severity}, action: {action.value})")
            
        except Exception as e:
            logger.error(f"Error processing violation: {e}")
    
    async def _determine_compliance_action(
        self, 
        violation: PolicyViolation
    ) -> ComplianceAction:
        """Determine appropriate action for violation"""
        
        # Critical violations trigger emergency stop
        if violation.severity == "critical":
            return ComplianceAction.EMERGENCY_STOP
        
        # High severity violations
        if violation.severity == "high":
            if violation.violation_type == PolicyViolationType.CAPTCHA_TRIGGERED:
                return ComplianceAction.PAUSE_TEMPORARILY
            elif violation.violation_type == PolicyViolationType.RATE_LIMIT_EXCEEDED:
                return ComplianceAction.PAUSE_TEMPORARILY
            else:
                return ComplianceAction.SLOW_DOWN
        
        # Medium severity violations
        if violation.severity == "medium":
            recent_violations = [v for v in self.violations[-5:] if v.severity in ["medium", "high"]]
            if len(recent_violations) >= 3:
                return ComplianceAction.PAUSE_TEMPORARILY
            else:
                return ComplianceAction.SLOW_DOWN
        
        # Low severity violations
        if violation.severity == "low":
            return ComplianceAction.CONTINUE
        
        return ComplianceAction.CONTINUE
    
    async def _execute_compliance_action(
        self, 
        action: ComplianceAction, 
        violation: PolicyViolation
    ):
        """Execute the determined compliance action"""
        try:
            if action == ComplianceAction.EMERGENCY_STOP:
                logger.critical(f"EMERGENCY STOP triggered by: {violation.description}")
                self.metrics.emergency_stops_triggered += 1
                # TODO: Trigger emergency stop in safety service
            
            elif action == ComplianceAction.PAUSE_TEMPORARILY:
                pause_duration = self._get_pause_duration(violation)
                logger.warning(f"Temporary pause triggered for {pause_duration} seconds")
                # TODO: Schedule resume after pause duration
            
            elif action == ComplianceAction.SLOW_DOWN:
                logger.info("Slowing down automation due to compliance violation")
                # TODO: Increase delays in safety service
            
            elif action == ComplianceAction.ROTATE_SESSION:
                logger.info("Rotating browser session due to compliance violation")
                # TODO: Trigger session rotation in browser service
            
            elif action == ComplianceAction.CHANGE_STRATEGY:
                logger.info("Changing automation strategy due to compliance violation")
                # TODO: Trigger strategy change in job discovery service
            
        except Exception as e:
            logger.error(f"Error executing compliance action: {e}")
    
    def _get_pause_duration(self, violation: PolicyViolation) -> int:
        """Get pause duration based on violation type"""
        if violation.violation_type == PolicyViolationType.CAPTCHA_TRIGGERED:
            return self.policy.captcha_pause_duration
        elif violation.violation_type == PolicyViolationType.RATE_LIMIT_EXCEEDED:
            return self.policy.rate_limit_pause_duration
        else:
            return 1800  # Default 30 minutes
    
    async def _update_risk_level(self):
        """Update current risk level based on recent violations"""
        try:
            # Count violations in last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_violations = [
                v for v in self.violations 
                if v.detected_at >= cutoff_time
            ]
            
            # Calculate risk score
            risk_score = 0
            for violation in recent_violations:
                if violation.severity == "critical":
                    risk_score += 4
                elif violation.severity == "high":
                    risk_score += 3
                elif violation.severity == "medium":
                    risk_score += 2
                elif violation.severity == "low":
                    risk_score += 1
            
            # Determine risk level
            if risk_score >= 10:
                self.metrics.current_risk_level = "critical"
            elif risk_score >= 6:
                self.metrics.current_risk_level = "high"
            elif risk_score >= 3:
                self.metrics.current_risk_level = "medium"
            else:
                self.metrics.current_risk_level = "low"
            
            # Update compliance score
            max_possible_score = len(recent_violations) * 4  # If all were critical
            if max_possible_score > 0:
                self.metrics.compliance_score = max(0.0, 1.0 - (risk_score / max_possible_score))
            else:
                self.metrics.compliance_score = 1.0
            
        except Exception as e:
            logger.error(f"Error updating risk level: {e}")
    
    async def _adapt_policies(self, violation: PolicyViolation):
        """Adapt policies based on violation patterns"""
        try:
            # Count similar violations in recent history
            similar_violations = [
                v for v in self.violations[-20:]  # Last 20 violations
                if v.violation_type == violation.violation_type
            ]
            
            if len(similar_violations) >= 3:
                # Adapt policy based on violation type
                if violation.violation_type == PolicyViolationType.RATE_LIMIT_EXCEEDED:
                    # Reduce application limits
                    self.policy.max_applications_per_hour = max(1, self.policy.max_applications_per_hour - 1)
                    self.policy.max_applications_per_day = max(5, self.policy.max_applications_per_day - 5)
                
                elif violation.violation_type == PolicyViolationType.SUCCESS_RATE_LOW:
                    # Increase success rate threshold
                    self.policy.min_success_rate_threshold = min(0.3, self.policy.min_success_rate_threshold + 0.05)
                
                elif violation.violation_type == PolicyViolationType.CAPTCHA_TRIGGERED:
                    # Increase pause duration
                    self.policy.captcha_pause_duration = min(7200, self.policy.captcha_pause_duration + 600)
                
                self.metrics.policy_adaptations += 1
                logger.info(f"Adapted policy due to repeated {violation.violation_type.value} violations")
            
        except Exception as e:
            logger.error(f"Error adapting policies: {e}")
    
    async def _determine_continuation_status(
        self, 
        violations: List[PolicyViolation]
    ) -> bool:
        """Determine if automation should continue based on violations"""
        
        # Check for critical violations
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            return False
        
        # Check for high severity violations
        high_violations = [v for v in violations if v.severity == "high"]
        if len(high_violations) >= 2:
            return False
        
        # Check current risk level
        if self.metrics.current_risk_level == "critical":
            return False
        
        # Check recent violation patterns
        recent_violations = [
            v for v in self.violations[-10:]
            if v.detected_at >= datetime.utcnow() - timedelta(hours=1)
        ]
        
        if len(recent_violations) >= 5:
            return False
        
        return True
    
    async def get_compliance_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive compliance status"""
        try:
            # Update metrics
            await self._update_risk_level()
            
            # Get recent violations
            recent_violations = [
                asdict(v) for v in self.violations[-10:]
            ]
            
            return {
                "metrics": asdict(self.metrics),
                "policy": asdict(self.policy),
                "recent_violations": recent_violations,
                "risk_assessment": {
                    "current_level": self.metrics.current_risk_level,
                    "compliance_score": self.metrics.compliance_score,
                    "violations_today": self.metrics.violations_today,
                    "last_violation": self.metrics.last_violation_time.isoformat() if self.metrics.last_violation_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance status: {e}")
            return {"error": str(e)}
    
    async def reset_violations(self, violation_type: Optional[PolicyViolationType] = None):
        """Reset violations (for testing or manual intervention)"""
        if violation_type:
            self.violations = [v for v in self.violations if v.violation_type != violation_type]
            logger.info(f"Reset violations of type: {violation_type.value}")
        else:
            self.violations.clear()
            self.metrics.total_violations = 0
            self.metrics.violations_today = 0
            self.metrics.last_violation_time = None
            logger.info("Reset all violations")
    
    def update_policy(self, policy_updates: Dict[str, Any]):
        """Update compliance policy configuration"""
        for key, value in policy_updates.items():
            if hasattr(self.policy, key):
                setattr(self.policy, key, value)
                logger.info(f"Updated policy {key} to {value}")


# Global service instance
compliance_service = ComplianceService()