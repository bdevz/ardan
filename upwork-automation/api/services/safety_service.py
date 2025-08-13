"""
Safety and Compliance Service for Upwork Automation System

This service implements comprehensive safety controls including:
- Rate limiting to mimic human application patterns
- Platform monitoring for unusual responses
- Gradual scaling system for safe volume increases
- Browser fingerprinting and stealth enhancements
- Compliance monitoring and policy adaptation
"""
import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ApplicationModel, JobModel
from shared.models import Application, Job
from shared.utils import setup_logging
from shared.config import settings

logger = setup_logging("safety-service")


class SafetyLevel(Enum):
    """Safety operation levels"""
    CONSERVATIVE = "conservative"  # Minimal activity, maximum safety
    NORMAL = "normal"             # Standard operation
    AGGRESSIVE = "aggressive"     # Higher volume, reduced delays
    EMERGENCY_STOP = "emergency_stop"  # All automation paused


class ComplianceStatus(Enum):
    """Platform compliance status"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    SUSPENDED = "suspended"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    max_daily_applications: int = 30
    max_hourly_applications: int = 5
    min_time_between_applications: int = 300  # seconds
    base_delay_range: Tuple[int, int] = (60, 180)  # seconds
    scaling_factor: float = 1.0
    human_pattern_variance: float = 0.3  # 30% variance in timing


@dataclass
class SafetyMetrics:
    """Safety and compliance metrics"""
    applications_today: int = 0
    applications_this_hour: int = 0
    success_rate_24h: float = 0.0
    success_rate_7d: float = 0.0
    consecutive_failures: int = 0
    last_application_time: Optional[datetime] = None
    current_safety_level: SafetyLevel = SafetyLevel.NORMAL
    compliance_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    platform_warnings: List[str] = None
    
    def __post_init__(self):
        if self.platform_warnings is None:
            self.platform_warnings = []


@dataclass
class PlatformResponse:
    """Platform response analysis"""
    response_time: float
    status_code: int
    content_length: int
    has_captcha: bool = False
    has_rate_limit_warning: bool = False
    has_unusual_content: bool = False
    error_indicators: List[str] = None
    
    def __post_init__(self):
        if self.error_indicators is None:
            self.error_indicators = []


class SafetyService:
    """Comprehensive safety and compliance service"""
    
    def __init__(self):
        self.rate_limit_config = RateLimitConfig()
        self.safety_metrics = SafetyMetrics()
        self.platform_responses: List[PlatformResponse] = []
        self.fingerprint_rotation_schedule = {}
        self.emergency_stop_active = False
        
        # Load configuration from settings
        self._load_configuration()
    
    def _load_configuration(self):
        """Load safety configuration from settings"""
        self.rate_limit_config.max_daily_applications = settings.daily_application_limit
        self.rate_limit_config.max_hourly_applications = getattr(
            settings, 'max_hourly_applications', 5
        )
        self.rate_limit_config.min_time_between_applications = getattr(
            settings, 'min_time_between_applications', 300
        )
    
    async def check_rate_limits(self, db: AsyncSession) -> Tuple[bool, str]:
        """
        Check if current rate limits allow for new application
        Returns: (allowed, reason)
        """
        try:
            # Update current metrics
            await self._update_safety_metrics(db)
            
            # Check emergency stop
            if self.emergency_stop_active:
                return False, "Emergency stop is active"
            
            # Check daily limit
            if self.safety_metrics.applications_today >= self.rate_limit_config.max_daily_applications:
                return False, f"Daily limit reached ({self.rate_limit_config.max_daily_applications})"
            
            # Check hourly limit
            if self.safety_metrics.applications_this_hour >= self.rate_limit_config.max_hourly_applications:
                return False, f"Hourly limit reached ({self.rate_limit_config.max_hourly_applications})"
            
            # Check minimum time between applications
            if self.safety_metrics.last_application_time:
                time_since_last = datetime.utcnow() - self.safety_metrics.last_application_time
                min_interval = timedelta(seconds=self.rate_limit_config.min_time_between_applications)
                
                if time_since_last < min_interval:
                    remaining = min_interval - time_since_last
                    return False, f"Must wait {remaining.seconds} more seconds"
            
            # Check consecutive failures
            if self.safety_metrics.consecutive_failures >= 5:
                return False, "Too many consecutive failures - automatic pause"
            
            # Check success rate
            if self.safety_metrics.success_rate_24h < 0.1 and self.safety_metrics.applications_today > 5:
                return False, "Success rate too low - automatic pause"
            
            return True, "Rate limits allow application"
            
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return False, f"Error checking rate limits: {e}"
    
    async def calculate_human_delay(self) -> int:
        """
        Calculate human-like delay between actions
        Returns delay in seconds
        """
        base_min, base_max = self.rate_limit_config.base_delay_range
        
        # Apply scaling factor based on current safety level
        scaling = self.rate_limit_config.scaling_factor
        if self.safety_metrics.current_safety_level == SafetyLevel.CONSERVATIVE:
            scaling *= 1.5
        elif self.safety_metrics.current_safety_level == SafetyLevel.AGGRESSIVE:
            scaling *= 0.7
        
        # Calculate base delay
        base_delay = random.uniform(base_min * scaling, base_max * scaling)
        
        # Add human-like variance
        variance = self.rate_limit_config.human_pattern_variance
        variance_factor = random.uniform(1 - variance, 1 + variance)
        
        # Add time-of-day adjustment (slower during typical work hours)
        current_hour = datetime.utcnow().hour
        if 9 <= current_hour <= 17:  # Business hours
            time_factor = random.uniform(1.2, 1.8)
        else:
            time_factor = random.uniform(0.8, 1.2)
        
        final_delay = int(base_delay * variance_factor * time_factor)
        
        logger.info(f"Calculated human delay: {final_delay} seconds")
        return final_delay
    
    async def analyze_platform_response(
        self, 
        response_data: Dict[str, Any]
    ) -> PlatformResponse:
        """
        Analyze platform response for unusual patterns or warnings
        """
        try:
            platform_response = PlatformResponse(
                response_time=response_data.get('response_time', 0.0),
                status_code=response_data.get('status_code', 200),
                content_length=response_data.get('content_length', 0)
            )
            
            # Check for CAPTCHA indicators
            content = response_data.get('content', '').lower()
            captcha_indicators = [
                'captcha', 'recaptcha', 'verify you are human',
                'security check', 'unusual activity'
            ]
            platform_response.has_captcha = any(
                indicator in content for indicator in captcha_indicators
            )
            
            # Check for rate limiting warnings
            rate_limit_indicators = [
                'rate limit', 'too many requests', 'slow down',
                'temporarily blocked', 'suspicious activity'
            ]
            platform_response.has_rate_limit_warning = any(
                indicator in content for indicator in rate_limit_indicators
            )
            
            # Check for unusual content patterns
            if platform_response.content_length < 1000 and platform_response.status_code == 200:
                platform_response.has_unusual_content = True
                platform_response.error_indicators.append("Unusually short response")
            
            if platform_response.response_time > 10.0:
                platform_response.has_unusual_content = True
                platform_response.error_indicators.append("Unusually slow response")
            
            # Store response for pattern analysis
            self.platform_responses.append(platform_response)
            
            # Keep only last 100 responses
            if len(self.platform_responses) > 100:
                self.platform_responses = self.platform_responses[-100:]
            
            # Trigger automatic pause if needed
            await self._check_automatic_pause_triggers(platform_response)
            
            return platform_response
            
        except Exception as e:
            logger.error(f"Error analyzing platform response: {e}")
            return PlatformResponse(
                response_time=0.0,
                status_code=500,
                content_length=0,
                error_indicators=[f"Analysis error: {e}"]
            )
    
    async def _check_automatic_pause_triggers(self, response: PlatformResponse):
        """Check if response triggers automatic pause"""
        should_pause = False
        reason = ""
        
        if response.has_captcha:
            should_pause = True
            reason = "CAPTCHA detected"
        
        elif response.has_rate_limit_warning:
            should_pause = True
            reason = "Rate limit warning detected"
        
        elif len([r for r in self.platform_responses[-5:] if r.has_unusual_content]) >= 3:
            should_pause = True
            reason = "Multiple unusual responses detected"
        
        if should_pause:
            await self.trigger_emergency_stop(reason)
    
    async def implement_gradual_scaling(self, db: AsyncSession) -> RateLimitConfig:
        """
        Implement gradual scaling system for safe volume increases
        """
        try:
            # Get historical performance data
            success_rate_7d = await self._calculate_success_rate(db, days=7)
            success_rate_30d = await self._calculate_success_rate(db, days=30)
            
            # Calculate scaling factor based on performance
            base_scaling = 1.0
            
            # Increase scaling if performance is good
            if success_rate_7d > 0.3 and success_rate_30d > 0.25:
                base_scaling = min(1.5, base_scaling + 0.1)
            elif success_rate_7d > 0.2 and success_rate_30d > 0.15:
                base_scaling = min(1.2, base_scaling + 0.05)
            
            # Decrease scaling if performance is poor
            elif success_rate_7d < 0.1 or success_rate_30d < 0.1:
                base_scaling = max(0.5, base_scaling - 0.2)
            elif success_rate_7d < 0.15 or success_rate_30d < 0.15:
                base_scaling = max(0.7, base_scaling - 0.1)
            
            # Apply time-based scaling (gradual increase over time)
            days_active = await self._get_days_active(db)
            if days_active < 7:
                time_scaling = 0.5  # Very conservative for first week
            elif days_active < 30:
                time_scaling = 0.7  # Conservative for first month
            elif days_active < 90:
                time_scaling = 0.9  # Slightly conservative for first 3 months
            else:
                time_scaling = 1.0  # Full scaling after 3 months
            
            # Combine scaling factors
            final_scaling = base_scaling * time_scaling
            
            # Update rate limit configuration
            new_config = RateLimitConfig(
                max_daily_applications=int(30 * final_scaling),
                max_hourly_applications=max(1, int(5 * final_scaling)),
                min_time_between_applications=max(60, int(300 / final_scaling)),
                scaling_factor=final_scaling
            )
            
            self.rate_limit_config = new_config
            
            logger.info(f"Updated scaling: factor={final_scaling:.2f}, "
                       f"daily_limit={new_config.max_daily_applications}, "
                       f"hourly_limit={new_config.max_hourly_applications}")
            
            return new_config
            
        except Exception as e:
            logger.error(f"Error implementing gradual scaling: {e}")
            return self.rate_limit_config
    
    async def enhance_browser_fingerprinting(self) -> Dict[str, Any]:
        """
        Generate enhanced browser fingerprinting configuration
        """
        try:
            # Rotate user agents periodically
            user_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
            ]
            
            # Screen resolutions commonly used
            screen_resolutions = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1536, "height": 864}
            ]
            
            # Timezone variations
            timezones = [
                "America/New_York",
                "America/Chicago", 
                "America/Denver",
                "America/Los_Angeles",
                "America/Toronto"
            ]
            
            # Generate fingerprint configuration
            fingerprint_config = {
                "userAgent": random.choice(user_agents),
                "viewport": random.choice(screen_resolutions),
                "timezone": random.choice(timezones),
                "locale": random.choice(["en-US", "en-CA"]),
                "platform": random.choice(["MacIntel", "Win32", "Linux x86_64"]),
                "webgl": {
                    "vendor": random.choice(["Intel Inc.", "NVIDIA Corporation", "AMD"]),
                    "renderer": "Randomized WebGL Renderer"
                },
                "canvas": {
                    "noise": random.uniform(0.0001, 0.001)
                },
                "fonts": self._generate_font_list(),
                "plugins": self._generate_plugin_list(),
                "headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1"
                }
            }
            
            logger.info("Generated enhanced browser fingerprint configuration")
            return fingerprint_config
            
        except Exception as e:
            logger.error(f"Error enhancing browser fingerprinting: {e}")
            return {}
    
    def _generate_font_list(self) -> List[str]:
        """Generate realistic font list"""
        base_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Courier New",
            "Verdana", "Georgia", "Palatino", "Garamond", "Bookman"
        ]
        
        system_fonts = {
            "MacIntel": ["SF Pro Display", "Helvetica Neue", "Lucida Grande"],
            "Win32": ["Segoe UI", "Tahoma", "Microsoft Sans Serif"],
            "Linux x86_64": ["Ubuntu", "DejaVu Sans", "Liberation Sans"]
        }
        
        # Combine base fonts with system-specific fonts
        all_fonts = base_fonts.copy()
        for platform_fonts in system_fonts.values():
            all_fonts.extend(platform_fonts)
        
        # Return random subset
        return random.sample(all_fonts, random.randint(15, 25))
    
    def _generate_plugin_list(self) -> List[Dict[str, str]]:
        """Generate realistic plugin list"""
        common_plugins = [
            {"name": "Chrome PDF Plugin", "filename": "internal-pdf-viewer"},
            {"name": "Chrome PDF Viewer", "filename": "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
            {"name": "Native Client", "filename": "internal-nacl-plugin"}
        ]
        
        return random.sample(common_plugins, random.randint(2, len(common_plugins)))
    
    async def monitor_compliance_status(self, db: AsyncSession) -> ComplianceStatus:
        """
        Monitor overall compliance status and adapt policies
        """
        try:
            # Check recent application success rates
            success_rate_24h = await self._calculate_success_rate(db, days=1)
            success_rate_7d = await self._calculate_success_rate(db, days=7)
            
            # Check for warning indicators
            warning_indicators = 0
            
            if success_rate_24h < 0.1 and self.safety_metrics.applications_today > 3:
                warning_indicators += 1
                self.safety_metrics.platform_warnings.append("Low 24h success rate")
            
            if success_rate_7d < 0.15:
                warning_indicators += 1
                self.safety_metrics.platform_warnings.append("Low 7d success rate")
            
            if self.safety_metrics.consecutive_failures >= 3:
                warning_indicators += 1
                self.safety_metrics.platform_warnings.append("Multiple consecutive failures")
            
            # Check platform response patterns
            recent_responses = self.platform_responses[-10:]
            captcha_count = sum(1 for r in recent_responses if r.has_captcha)
            rate_limit_count = sum(1 for r in recent_responses if r.has_rate_limit_warning)
            
            if captcha_count >= 2:
                warning_indicators += 2
                self.safety_metrics.platform_warnings.append("Multiple CAPTCHAs detected")
            
            if rate_limit_count >= 2:
                warning_indicators += 2
                self.safety_metrics.platform_warnings.append("Multiple rate limit warnings")
            
            # Determine compliance status
            if warning_indicators == 0:
                status = ComplianceStatus.COMPLIANT
            elif warning_indicators <= 2:
                status = ComplianceStatus.WARNING
            elif warning_indicators <= 4:
                status = ComplianceStatus.VIOLATION
            else:
                status = ComplianceStatus.SUSPENDED
            
            self.safety_metrics.compliance_status = status
            
            # Adapt safety level based on compliance status
            await self._adapt_safety_level(status)
            
            logger.info(f"Compliance status: {status.value}, warnings: {warning_indicators}")
            return status
            
        except Exception as e:
            logger.error(f"Error monitoring compliance status: {e}")
            return ComplianceStatus.WARNING
    
    async def _adapt_safety_level(self, compliance_status: ComplianceStatus):
        """Adapt safety level based on compliance status"""
        if compliance_status == ComplianceStatus.COMPLIANT:
            if self.safety_metrics.current_safety_level == SafetyLevel.CONSERVATIVE:
                self.safety_metrics.current_safety_level = SafetyLevel.NORMAL
        
        elif compliance_status == ComplianceStatus.WARNING:
            if self.safety_metrics.current_safety_level == SafetyLevel.AGGRESSIVE:
                self.safety_metrics.current_safety_level = SafetyLevel.NORMAL
        
        elif compliance_status == ComplianceStatus.VIOLATION:
            self.safety_metrics.current_safety_level = SafetyLevel.CONSERVATIVE
        
        elif compliance_status == ComplianceStatus.SUSPENDED:
            await self.trigger_emergency_stop("Compliance violation detected")
    
    async def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop of all automation"""
        self.emergency_stop_active = True
        self.safety_metrics.current_safety_level = SafetyLevel.EMERGENCY_STOP
        
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        
        # TODO: Send immediate alerts via Slack/email
        # TODO: Pause all active browser sessions
        # TODO: Clear job queue
    
    async def release_emergency_stop(self, reason: str):
        """Release emergency stop and resume normal operation"""
        self.emergency_stop_active = False
        self.safety_metrics.current_safety_level = SafetyLevel.CONSERVATIVE
        self.safety_metrics.platform_warnings.clear()
        
        logger.info(f"Emergency stop released: {reason}")
    
    async def get_safety_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive safety status"""
        await self._update_safety_metrics(db)
        
        return {
            "safety_metrics": asdict(self.safety_metrics),
            "rate_limit_config": asdict(self.rate_limit_config),
            "emergency_stop_active": self.emergency_stop_active,
            "recent_platform_responses": len(self.platform_responses),
            "compliance_warnings": len(self.safety_metrics.platform_warnings)
        }
    
    async def _update_safety_metrics(self, db: AsyncSession):
        """Update current safety metrics from database"""
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            
            # Count applications today
            today_query = select(func.count(ApplicationModel.id)).where(
                ApplicationModel.submitted_at >= today_start
            )
            today_result = await db.execute(today_query)
            self.safety_metrics.applications_today = today_result.scalar() or 0
            
            # Count applications this hour
            hour_query = select(func.count(ApplicationModel.id)).where(
                ApplicationModel.submitted_at >= hour_start
            )
            hour_result = await db.execute(hour_query)
            self.safety_metrics.applications_this_hour = hour_result.scalar() or 0
            
            # Get last application time
            last_app_query = select(ApplicationModel.submitted_at).order_by(
                desc(ApplicationModel.submitted_at)
            ).limit(1)
            last_app_result = await db.execute(last_app_query)
            last_app = last_app_result.scalar_one_or_none()
            self.safety_metrics.last_application_time = last_app
            
            # Calculate success rates
            self.safety_metrics.success_rate_24h = await self._calculate_success_rate(db, days=1)
            self.safety_metrics.success_rate_7d = await self._calculate_success_rate(db, days=7)
            
            # Count consecutive failures
            self.safety_metrics.consecutive_failures = await self._count_consecutive_failures(db)
            
        except Exception as e:
            logger.error(f"Error updating safety metrics: {e}")
    
    async def _calculate_success_rate(self, db: AsyncSession, days: int) -> float:
        """Calculate success rate over specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count total applications
            total_query = select(func.count(ApplicationModel.id)).where(
                ApplicationModel.submitted_at >= cutoff_date
            )
            total_result = await db.execute(total_query)
            total_applications = total_result.scalar() or 0
            
            if total_applications == 0:
                return 0.0
            
            # Count successful applications (hired or interview scheduled)
            success_query = select(func.count(ApplicationModel.id)).where(
                and_(
                    ApplicationModel.submitted_at >= cutoff_date,
                    (ApplicationModel.hired == True) | (ApplicationModel.interview_scheduled == True)
                )
            )
            success_result = await db.execute(success_query)
            successful_applications = success_result.scalar() or 0
            
            return successful_applications / total_applications
            
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.0
    
    async def _count_consecutive_failures(self, db: AsyncSession) -> int:
        """Count consecutive failures from most recent applications"""
        try:
            # Get last 10 applications ordered by submission time
            query = select(ApplicationModel).order_by(
                desc(ApplicationModel.submitted_at)
            ).limit(10)
            
            result = await db.execute(query)
            recent_applications = result.scalars().all()
            
            consecutive_failures = 0
            for app in recent_applications:
                # Consider failure if not hired and no interview scheduled
                if not app.hired and not app.interview_scheduled:
                    consecutive_failures += 1
                else:
                    break
            
            return consecutive_failures
            
        except Exception as e:
            logger.error(f"Error counting consecutive failures: {e}")
            return 0
    
    async def _get_days_active(self, db: AsyncSession) -> int:
        """Get number of days the system has been active"""
        try:
            first_app_query = select(ApplicationModel.submitted_at).order_by(
                ApplicationModel.submitted_at
            ).limit(1)
            
            result = await db.execute(first_app_query)
            first_app_date = result.scalar_one_or_none()
            
            if not first_app_date:
                return 0
            
            return (datetime.utcnow() - first_app_date).days
            
        except Exception as e:
            logger.error(f"Error getting days active: {e}")
            return 0


# Global service instance
safety_service = SafetyService()