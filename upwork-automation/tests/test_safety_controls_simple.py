"""
Simplified Tests for Safety and Compliance Controls

This test suite covers basic functionality without requiring database dependencies.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import the services directly
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

from services.safety_service import (
    SafetyService, SafetyLevel, RateLimitConfig, SafetyMetrics, PlatformResponse
)
from services.stealth_service import (
    StealthService, StealthLevel, BrowserFingerprint, MouseMovement, TypingPattern
)
from services.compliance_service import (
    ComplianceService, PolicyViolationType, ComplianceAction, PolicyViolation
)


class TestSafetyServiceBasic:
    """Basic tests for SafetyService without database dependencies"""
    
    @pytest.fixture
    def safety_service(self):
        """Create SafetyService instance for testing"""
        return SafetyService()
    
    @pytest.mark.asyncio
    async def test_calculate_human_delay(self, safety_service):
        """Test human delay calculation"""
        delay = await safety_service.calculate_human_delay()
        
        assert isinstance(delay, int)
        assert delay > 0
        assert delay < 1000  # Reasonable upper bound
    
    @pytest.mark.asyncio
    async def test_calculate_human_delay_conservative_mode(self, safety_service):
        """Test human delay calculation in conservative mode"""
        safety_service.safety_metrics.current_safety_level = SafetyLevel.CONSERVATIVE
        
        delay = await safety_service.calculate_human_delay()
        
        # Should be longer in conservative mode
        assert delay > 60  # At least 1 minute
    
    @pytest.mark.asyncio
    async def test_analyze_platform_response_normal(self, safety_service):
        """Test platform response analysis for normal response"""
        response_data = {
            'status_code': 200,
            'content': 'Successfully submitted application',
            'response_time': 2.5,
            'content_length': 5000
        }
        
        response = await safety_service.analyze_platform_response(response_data)
        
        assert isinstance(response, PlatformResponse)
        assert response.status_code == 200
        assert response.has_captcha is False
        assert response.has_rate_limit_warning is False
        assert response.has_unusual_content is False
    
    @pytest.mark.asyncio
    async def test_analyze_platform_response_captcha(self, safety_service):
        """Test platform response analysis when CAPTCHA is detected"""
        response_data = {
            'status_code': 200,
            'content': 'Please verify you are human by completing this CAPTCHA',
            'response_time': 1.5,
            'content_length': 3000
        }
        
        response = await safety_service.analyze_platform_response(response_data)
        
        assert response.has_captcha is True
    
    @pytest.mark.asyncio
    async def test_analyze_platform_response_rate_limit(self, safety_service):
        """Test platform response analysis when rate limiting is detected"""
        response_data = {
            'status_code': 429,
            'content': 'Rate limit exceeded. Please slow down your requests.',
            'response_time': 1.0,
            'content_length': 2000
        }
        
        response = await safety_service.analyze_platform_response(response_data)
        
        assert response.has_rate_limit_warning is True
    
    @pytest.mark.asyncio
    async def test_analyze_platform_response_unusual_content(self, safety_service):
        """Test platform response analysis for unusual content"""
        response_data = {
            'status_code': 200,
            'content': 'Error',  # Very short content
            'response_time': 15.0,  # Very slow response
            'content_length': 5
        }
        
        response = await safety_service.analyze_platform_response(response_data)
        
        assert response.has_unusual_content is True
        assert len(response.error_indicators) > 0
    
    def test_rate_limit_config_initialization(self, safety_service):
        """Test rate limit configuration initialization"""
        config = safety_service.rate_limit_config
        
        assert isinstance(config, RateLimitConfig)
        assert config.max_daily_applications > 0
        assert config.max_hourly_applications > 0
        assert config.min_time_between_applications > 0
    
    def test_safety_metrics_initialization(self, safety_service):
        """Test safety metrics initialization"""
        metrics = safety_service.safety_metrics
        
        assert isinstance(metrics, SafetyMetrics)
        assert metrics.applications_today >= 0
        assert metrics.applications_this_hour >= 0
        assert metrics.consecutive_failures >= 0


class TestStealthServiceBasic:
    """Basic tests for StealthService"""
    
    @pytest.fixture
    def stealth_service(self):
        """Create StealthService instance for testing"""
        return StealthService()
    
    @pytest.mark.asyncio
    async def test_generate_browser_fingerprint(self, stealth_service):
        """Test browser fingerprint generation"""
        session_id = "test-session-123"
        
        fingerprint = await stealth_service.generate_browser_fingerprint(session_id)
        
        assert isinstance(fingerprint, BrowserFingerprint)
        assert fingerprint.user_agent
        assert fingerprint.viewport['width'] > 0
        assert fingerprint.viewport['height'] > 0
        assert fingerprint.timezone
        assert fingerprint.locale
        assert len(fingerprint.fonts) > 0
        assert fingerprint.canvas_fingerprint
        assert fingerprint.audio_fingerprint
    
    @pytest.mark.asyncio
    async def test_generate_browser_fingerprint_consistency(self, stealth_service):
        """Test that fingerprint generation is consistent for same session"""
        session_id = "test-session-123"
        
        fingerprint1 = await stealth_service.generate_browser_fingerprint(session_id)
        fingerprint2 = await stealth_service.generate_browser_fingerprint(session_id)
        
        # Canvas and audio fingerprints should be consistent for same session
        assert fingerprint1.canvas_fingerprint == fingerprint2.canvas_fingerprint
        assert fingerprint1.audio_fingerprint == fingerprint2.audio_fingerprint
    
    @pytest.mark.asyncio
    async def test_generate_human_mouse_movement(self, stealth_service):
        """Test human-like mouse movement generation"""
        movement = await stealth_service.generate_human_mouse_movement(
            start_x=100, start_y=100, end_x=500, end_y=300
        )
        
        assert isinstance(movement, MouseMovement)
        assert movement.x == 500
        assert movement.y == 300
        assert movement.duration > 0
        assert len(movement.curve_points) > 0
        
        # Check that curve points form a reasonable path
        first_point = movement.curve_points[0]
        last_point = movement.curve_points[-1]
        assert abs(first_point[0] - 100) < 50  # Close to start
        assert abs(first_point[1] - 100) < 50
        assert abs(last_point[0] - 500) < 50   # Close to end
        assert abs(last_point[1] - 300) < 50
    
    @pytest.mark.asyncio
    async def test_generate_human_typing_pattern(self, stealth_service):
        """Test human-like typing pattern generation"""
        text = "Hello, this is a test message!"
        
        pattern = await stealth_service.generate_human_typing_pattern(text)
        
        assert isinstance(pattern, TypingPattern)
        assert pattern.text == text
        assert len(pattern.char_delays) == len(text)
        assert pattern.total_duration > 0
        assert all(delay > 0 for delay in pattern.char_delays)
        
        # Check that delays are reasonable (not too fast or too slow)
        avg_delay = pattern.total_duration / len(text)
        assert 0.1 < avg_delay < 2.0  # Between 0.1 and 2 seconds per character
    
    @pytest.mark.asyncio
    async def test_apply_stealth_measures(self, stealth_service):
        """Test applying stealth measures to browser session"""
        session_id = "test-session-456"
        page_context = {"url": "https://upwork.com", "title": "Upwork"}
        
        stealth_config = await stealth_service.apply_stealth_measures(session_id, page_context)
        
        assert "fingerprint" in stealth_config
        assert "headers" in stealth_config
        assert "stealth_level" in stealth_config
        
        fingerprint = stealth_config["fingerprint"]
        assert "userAgent" in fingerprint
        assert "viewport" in fingerprint
        assert "fonts" in fingerprint
    
    @pytest.mark.asyncio
    async def test_detect_anti_bot_measures(self, stealth_service):
        """Test detection of anti-bot measures"""
        # Test with CAPTCHA content
        captcha_content = "Please complete this reCAPTCHA to verify you are human"
        captcha_headers = {}
        
        detection = await stealth_service.detect_anti_bot_measures(captcha_content, captcha_headers)
        
        assert detection["captcha_detected"] is True
        assert detection["risk_level"] in ["medium", "high"]
        
        # Test with rate limiting content
        rate_limit_content = "Rate limit exceeded. Too many requests."
        rate_limit_headers = {}
        
        detection = await stealth_service.detect_anti_bot_measures(rate_limit_content, rate_limit_headers)
        
        assert detection["rate_limiting"] is True
        assert detection["risk_level"] in ["medium", "high"]
        
        # Test with normal content
        normal_content = "Welcome to Upwork! Find great freelance opportunities."
        normal_headers = {}
        
        detection = await stealth_service.detect_anti_bot_measures(normal_content, normal_headers)
        
        assert detection["captcha_detected"] is False
        assert detection["rate_limiting"] is False
        assert detection["risk_level"] == "low"
    
    def test_stealth_level_setting(self, stealth_service):
        """Test setting stealth level"""
        stealth_service.set_stealth_level(StealthLevel.MAXIMUM)
        assert stealth_service.stealth_level == StealthLevel.MAXIMUM
        
        stealth_service.set_stealth_level(StealthLevel.MINIMAL)
        assert stealth_service.stealth_level == StealthLevel.MINIMAL


class TestComplianceServiceBasic:
    """Basic tests for ComplianceService"""
    
    @pytest.fixture
    def compliance_service(self):
        """Create ComplianceService instance for testing"""
        return ComplianceService()
    
    @pytest.mark.asyncio
    async def test_compliance_action_determination(self, compliance_service):
        """Test determination of compliance actions"""
        # Test critical violation
        critical_violation = PolicyViolation(
            violation_type=PolicyViolationType.ACCOUNT_WARNING,
            severity="critical",
            description="Account suspended",
            detected_at=datetime.utcnow(),
            evidence={}
        )
        
        action = await compliance_service._determine_compliance_action(critical_violation)
        assert action == ComplianceAction.EMERGENCY_STOP
        
        # Test high severity violation
        high_violation = PolicyViolation(
            violation_type=PolicyViolationType.CAPTCHA_TRIGGERED,
            severity="high",
            description="CAPTCHA detected",
            detected_at=datetime.utcnow(),
            evidence={}
        )
        
        action = await compliance_service._determine_compliance_action(high_violation)
        assert action == ComplianceAction.PAUSE_TEMPORARILY
        
        # Test low severity violation
        low_violation = PolicyViolation(
            violation_type=PolicyViolationType.UNUSUAL_RESPONSE,
            severity="low",
            description="Slow response",
            detected_at=datetime.utcnow(),
            evidence={}
        )
        
        action = await compliance_service._determine_compliance_action(low_violation)
        assert action == ComplianceAction.CONTINUE
    
    def test_policy_update(self, compliance_service):
        """Test updating compliance policy"""
        updates = {
            "max_applications_per_day": 25,
            "min_success_rate_threshold": 0.15
        }
        
        compliance_service.update_policy(updates)
        
        assert compliance_service.policy.max_applications_per_day == 25
        assert compliance_service.policy.min_success_rate_threshold == 0.15
    
    @pytest.mark.asyncio
    async def test_reset_violations(self, compliance_service):
        """Test resetting violations"""
        # Add some violations
        violations = [
            PolicyViolation(
                violation_type=PolicyViolationType.CAPTCHA_TRIGGERED,
                severity="high",
                description="CAPTCHA",
                detected_at=datetime.utcnow(),
                evidence={}
            ),
            PolicyViolation(
                violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                severity="medium",
                description="Rate limit",
                detected_at=datetime.utcnow(),
                evidence={}
            )
        ]
        
        compliance_service.violations.extend(violations)
        assert len(compliance_service.violations) == 2
        
        # Reset specific violation type
        await compliance_service.reset_violations(PolicyViolationType.CAPTCHA_TRIGGERED)
        assert len(compliance_service.violations) == 1
        assert compliance_service.violations[0].violation_type == PolicyViolationType.RATE_LIMIT_EXCEEDED
        
        # Reset all violations
        await compliance_service.reset_violations()
        assert len(compliance_service.violations) == 0
    
    def test_policy_initialization(self, compliance_service):
        """Test compliance policy initialization"""
        policy = compliance_service.policy
        
        assert policy.max_applications_per_hour > 0
        assert policy.max_applications_per_day > 0
        assert policy.min_success_rate_threshold >= 0
        assert policy.max_consecutive_failures > 0
    
    def test_platform_patterns_initialization(self, compliance_service):
        """Test platform patterns initialization"""
        patterns = compliance_service.platform_patterns
        
        assert "upwork_captcha_indicators" in patterns
        assert "upwork_rate_limit_indicators" in patterns
        assert "upwork_account_warnings" in patterns
        assert len(patterns["upwork_captcha_indicators"]) > 0
        assert len(patterns["upwork_rate_limit_indicators"]) > 0


class TestIntegratedSafetyBasic:
    """Basic integration tests for safety system"""
    
    @pytest.fixture
    def safety_system(self):
        """Create integrated safety system"""
        return {
            'safety': SafetyService(),
            'stealth': StealthService(),
            'compliance': ComplianceService()
        }
    
    @pytest.mark.asyncio
    async def test_stealth_fingerprint_integration(self, safety_system):
        """Test stealth fingerprint integration"""
        stealth_service = safety_system['stealth']
        
        # Generate fingerprint
        session_id = "integration-test-session"
        fingerprint = await stealth_service.generate_browser_fingerprint(session_id)
        assert fingerprint is not None
        
        # Apply stealth measures
        stealth_config = await stealth_service.apply_stealth_measures(
            session_id, {"url": "https://upwork.com"}
        )
        assert "fingerprint" in stealth_config
        
        # Verify fingerprint is stored
        stored_fingerprint = stealth_service.get_session_fingerprint(session_id)
        assert stored_fingerprint is not None
        assert stored_fingerprint.user_agent == fingerprint.user_agent
    
    @pytest.mark.asyncio
    async def test_safety_response_analysis_integration(self, safety_system):
        """Test safety response analysis integration"""
        safety_service = safety_system['safety']
        compliance_service = safety_system['compliance']
        
        # Test normal response
        normal_response = {
            'status_code': 200,
            'content': 'Application submitted successfully',
            'response_time': 2.0,
            'headers': {}
        }
        
        # Analyze with safety service
        platform_response = await safety_service.analyze_platform_response(normal_response)
        assert platform_response.has_captcha is False
        
        # Check compliance patterns
        captcha_violation = await compliance_service._check_captcha_violation(normal_response['content'])
        assert captcha_violation is None
        
        rate_limit_violation = await compliance_service._check_rate_limit_violation(
            normal_response['content'], normal_response['headers']
        )
        assert rate_limit_violation is None
    
    @pytest.mark.asyncio
    async def test_safety_system_captcha_response(self, safety_system):
        """Test safety system response to CAPTCHA"""
        safety_service = safety_system['safety']
        compliance_service = safety_system['compliance']
        
        # Simulate CAPTCHA response
        captcha_response = {
            'status_code': 200,
            'content': 'Please complete this reCAPTCHA to verify you are human',
            'response_time': 1.5,
            'headers': {}
        }
        
        # Analyze with safety service
        platform_response = await safety_service.analyze_platform_response(captcha_response)
        assert platform_response.has_captcha is True
        
        # Check compliance violation detection
        captcha_violation = await compliance_service._check_captcha_violation(captcha_response['content'])
        assert captcha_violation is not None
        assert captcha_violation.violation_type == PolicyViolationType.CAPTCHA_TRIGGERED
        assert captcha_violation.severity == "high"
    
    def test_safety_configuration_consistency(self, safety_system):
        """Test that safety configurations are consistent across services"""
        safety_service = safety_system['safety']
        compliance_service = safety_system['compliance']
        
        # Check that rate limits are consistent
        safety_daily_limit = safety_service.rate_limit_config.max_daily_applications
        compliance_daily_limit = compliance_service.policy.max_applications_per_day
        
        # They should be the same or compliance should be more restrictive
        assert compliance_daily_limit <= safety_daily_limit
        
        safety_hourly_limit = safety_service.rate_limit_config.max_hourly_applications
        compliance_hourly_limit = compliance_service.policy.max_applications_per_hour
        
        assert compliance_hourly_limit <= safety_hourly_limit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])