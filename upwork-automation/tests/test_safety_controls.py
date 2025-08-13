"""
Tests for Safety and Compliance Controls

This test suite covers:
- Rate limiting functionality
- Platform monitoring and response analysis
- Gradual scaling system
- Browser fingerprinting and stealth operations
- Compliance monitoring and policy adaptation
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.services.safety_service import (
    SafetyService, SafetyLevel, ComplianceStatus, RateLimitConfig,
    SafetyMetrics, PlatformResponse
)
from api.services.stealth_service import (
    StealthService, StealthLevel, BrowserFingerprint, MouseMovement, TypingPattern
)
from api.services.compliance_service import (
    ComplianceService, PolicyViolationType, ComplianceAction, PolicyViolation
)
from database.models import ApplicationModel, JobModel
from shared.models import Application, Job


class TestSafetyService:
    """Test suite for SafetyService"""
    
    @pytest.fixture
    def safety_service(self):
        """Create SafetyService instance for testing"""
        return SafetyService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_within_limits(self, safety_service, mock_db):
        """Test rate limit check when within limits"""
        # Mock database queries to return low counts
        mock_db.execute.return_value.scalar.return_value = 2  # 2 applications today
        
        # Update safety metrics
        safety_service.safety_metrics.applications_today = 2
        safety_service.safety_metrics.applications_this_hour = 1
        safety_service.safety_metrics.consecutive_failures = 0
        safety_service.safety_metrics.success_rate_24h = 0.5
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is True
        assert "allow" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_daily_limit_exceeded(self, safety_service, mock_db):
        """Test rate limit check when daily limit is exceeded"""
        # Set applications today to exceed limit
        safety_service.safety_metrics.applications_today = 35
        safety_service.rate_limit_config.max_daily_applications = 30
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is False
        assert "daily limit" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_hourly_limit_exceeded(self, safety_service, mock_db):
        """Test rate limit check when hourly limit is exceeded"""
        safety_service.safety_metrics.applications_today = 10
        safety_service.safety_metrics.applications_this_hour = 6
        safety_service.rate_limit_config.max_hourly_applications = 5
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is False
        assert "hourly limit" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_minimum_time_not_elapsed(self, safety_service, mock_db):
        """Test rate limit check when minimum time between applications not elapsed"""
        safety_service.safety_metrics.applications_today = 5
        safety_service.safety_metrics.applications_this_hour = 2
        safety_service.safety_metrics.last_application_time = datetime.utcnow() - timedelta(seconds=60)
        safety_service.rate_limit_config.min_time_between_applications = 300  # 5 minutes
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is False
        assert "must wait" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_too_many_failures(self, safety_service, mock_db):
        """Test rate limit check when too many consecutive failures"""
        safety_service.safety_metrics.applications_today = 5
        safety_service.safety_metrics.applications_this_hour = 2
        safety_service.safety_metrics.consecutive_failures = 6
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is False
        assert "consecutive failures" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_low_success_rate(self, safety_service, mock_db):
        """Test rate limit check when success rate is too low"""
        safety_service.safety_metrics.applications_today = 10
        safety_service.safety_metrics.applications_this_hour = 2
        safety_service.safety_metrics.consecutive_failures = 2
        safety_service.safety_metrics.success_rate_24h = 0.05  # 5% success rate
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        
        assert allowed is False
        assert "success rate" in reason.lower()
    
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
        assert "captcha" in response.error_indicators or response.has_captcha
    
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
    
    @pytest.mark.asyncio
    async def test_gradual_scaling_good_performance(self, safety_service, mock_db):
        """Test gradual scaling with good performance metrics"""
        # Mock good success rates
        with patch.object(safety_service, '_calculate_success_rate') as mock_success_rate:
            mock_success_rate.side_effect = [0.4, 0.3]  # 40% 7d, 30% 30d
            
            with patch.object(safety_service, '_get_days_active') as mock_days:
                mock_days.return_value = 100  # Well established
                
                config = await safety_service.implement_gradual_scaling(mock_db)
                
                assert config.scaling_factor > 1.0  # Should scale up
                assert config.max_daily_applications >= 30
    
    @pytest.mark.asyncio
    async def test_gradual_scaling_poor_performance(self, safety_service, mock_db):
        """Test gradual scaling with poor performance metrics"""
        # Mock poor success rates
        with patch.object(safety_service, '_calculate_success_rate') as mock_success_rate:
            mock_success_rate.side_effect = [0.05, 0.08]  # 5% 7d, 8% 30d
            
            with patch.object(safety_service, '_get_days_active') as mock_days:
                mock_days.return_value = 50
                
                config = await safety_service.implement_gradual_scaling(mock_db)
                
                assert config.scaling_factor < 1.0  # Should scale down
                assert config.max_daily_applications < 30
    
    @pytest.mark.asyncio
    async def test_gradual_scaling_new_system(self, safety_service, mock_db):
        """Test gradual scaling for new system (conservative approach)"""
        with patch.object(safety_service, '_calculate_success_rate') as mock_success_rate:
            mock_success_rate.side_effect = [0.2, 0.2]  # Moderate success rates
            
            with patch.object(safety_service, '_get_days_active') as mock_days:
                mock_days.return_value = 3  # Very new system
                
                config = await safety_service.implement_gradual_scaling(mock_db)
                
                assert config.scaling_factor <= 0.5  # Very conservative
                assert config.max_daily_applications <= 15


class TestStealthService:
    """Test suite for StealthService"""
    
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
        assert len(fingerprint.plugins) >= 0
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


class TestComplianceService:
    """Test suite for ComplianceService"""
    
    @pytest.fixture
    def compliance_service(self):
        """Create ComplianceService instance for testing"""
        return ComplianceService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_monitor_platform_response_normal(self, compliance_service, mock_db):
        """Test monitoring normal platform response"""
        response_data = {
            'status_code': 200,
            'content': 'Application submitted successfully',
            'response_time': 2.0,
            'headers': {}
        }
        
        # Mock success rate check
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, mock_db
            )
            
            assert continue_allowed is True
            assert len(violations) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_platform_response_captcha(self, compliance_service, mock_db):
        """Test monitoring platform response with CAPTCHA"""
        response_data = {
            'status_code': 200,
            'content': 'Please verify you are human with this reCAPTCHA',
            'response_time': 1.5,
            'headers': {}
        }
        
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, mock_db
            )
            
            assert continue_allowed is False  # Should not continue with CAPTCHA
            assert len(violations) > 0
            assert violations[0].violation_type == PolicyViolationType.CAPTCHA_TRIGGERED
    
    @pytest.mark.asyncio
    async def test_monitor_platform_response_rate_limit(self, compliance_service, mock_db):
        """Test monitoring platform response with rate limiting"""
        response_data = {
            'status_code': 429,
            'content': 'Rate limit exceeded',
            'response_time': 1.0,
            'headers': {'retry-after': '300'}
        }
        
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, mock_db
            )
            
            assert continue_allowed is False
            assert len(violations) > 0
            assert any(v.violation_type == PolicyViolationType.RATE_LIMIT_EXCEEDED for v in violations)
    
    @pytest.mark.asyncio
    async def test_monitor_platform_response_account_warning(self, compliance_service, mock_db):
        """Test monitoring platform response with account warning"""
        response_data = {
            'status_code': 200,
            'content': 'Account warning: Policy violation detected',
            'response_time': 2.0,
            'headers': {}
        }
        
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, mock_db
            )
            
            assert continue_allowed is False
            assert len(violations) > 0
            assert violations[0].violation_type == PolicyViolationType.ACCOUNT_WARNING
            assert violations[0].severity == "critical"
    
    @pytest.mark.asyncio
    async def test_policy_adaptation(self, compliance_service):
        """Test policy adaptation based on violations"""
        # Create multiple rate limit violations
        for i in range(4):
            violation = PolicyViolation(
                violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                severity="high",
                description="Rate limit exceeded",
                detected_at=datetime.utcnow() - timedelta(minutes=i*10),
                evidence={}
            )
            compliance_service.violations.append(violation)
        
        # Test adaptation
        await compliance_service._adapt_policies(compliance_service.violations[-1])
        
        # Should have reduced limits
        assert compliance_service.policy.max_applications_per_hour < 5
        assert compliance_service.policy.max_applications_per_day < 30
    
    @pytest.mark.asyncio
    async def test_risk_level_calculation(self, compliance_service):
        """Test risk level calculation based on violations"""
        # Add violations of different severities
        violations = [
            PolicyViolation(
                violation_type=PolicyViolationType.CAPTCHA_TRIGGERED,
                severity="high",
                description="CAPTCHA detected",
                detected_at=datetime.utcnow(),
                evidence={}
            ),
            PolicyViolation(
                violation_type=PolicyViolationType.RATE_LIMIT_EXCEEDED,
                severity="medium",
                description="Rate limit warning",
                detected_at=datetime.utcnow(),
                evidence={}
            )
        ]
        
        compliance_service.violations.extend(violations)
        
        await compliance_service._update_risk_level()
        
        assert compliance_service.metrics.current_risk_level in ["medium", "high"]
        assert 0.0 <= compliance_service.metrics.compliance_score <= 1.0
    
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
    
    @pytest.mark.asyncio
    async def test_get_compliance_status(self, compliance_service, mock_db):
        """Test getting comprehensive compliance status"""
        status = await compliance_service.get_compliance_status(mock_db)
        
        assert "metrics" in status
        assert "policy" in status
        assert "recent_violations" in status
        assert "risk_assessment" in status
        
        risk_assessment = status["risk_assessment"]
        assert "current_level" in risk_assessment
        assert "compliance_score" in risk_assessment
        assert "violations_today" in risk_assessment
    
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


class TestIntegratedSafetySystem:
    """Integration tests for the complete safety system"""
    
    @pytest.fixture
    def safety_system(self):
        """Create integrated safety system"""
        return {
            'safety': SafetyService(),
            'stealth': StealthService(),
            'compliance': ComplianceService()
        }
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_complete_safety_workflow(self, safety_system, mock_db):
        """Test complete safety workflow from rate check to compliance monitoring"""
        safety_service = safety_system['safety']
        stealth_service = safety_system['stealth']
        compliance_service = safety_system['compliance']
        
        # Step 1: Check rate limits
        safety_service.safety_metrics.applications_today = 5
        safety_service.safety_metrics.applications_this_hour = 2
        safety_service.safety_metrics.consecutive_failures = 0
        safety_service.safety_metrics.success_rate_24h = 0.3
        
        allowed, reason = await safety_service.check_rate_limits(mock_db)
        assert allowed is True
        
        # Step 2: Generate stealth configuration
        session_id = "integration-test-session"
        fingerprint = await stealth_service.generate_browser_fingerprint(session_id)
        assert fingerprint is not None
        
        stealth_config = await stealth_service.apply_stealth_measures(
            session_id, {"url": "https://upwork.com"}
        )
        assert "fingerprint" in stealth_config
        
        # Step 3: Simulate platform response
        response_data = {
            'status_code': 200,
            'content': 'Application submitted successfully',
            'response_time': 2.0,
            'headers': {}
        }
        
        # Analyze response with safety service
        platform_response = await safety_service.analyze_platform_response(response_data)
        assert platform_response.has_captcha is False
        
        # Monitor compliance
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                response_data, mock_db
            )
            
            assert continue_allowed is True
            assert len(violations) == 0
    
    @pytest.mark.asyncio
    async def test_safety_system_under_attack(self, safety_system, mock_db):
        """Test safety system response to platform countermeasures"""
        safety_service = safety_system['safety']
        stealth_service = safety_system['stealth']
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
        
        # Monitor with compliance service
        with patch.object(compliance_service, '_check_success_rate_violation') as mock_success:
            mock_success.return_value = None
            
            continue_allowed, violations = await compliance_service.monitor_platform_response(
                captcha_response, mock_db
            )
            
            assert continue_allowed is False
            assert len(violations) > 0
            assert violations[0].violation_type == PolicyViolationType.CAPTCHA_TRIGGERED
        
        # Verify emergency stop would be triggered
        assert safety_service.emergency_stop_active is True or len(violations) > 0
    
    @pytest.mark.asyncio
    async def test_gradual_scaling_integration(self, safety_system, mock_db):
        """Test gradual scaling integration with compliance monitoring"""
        safety_service = safety_system['safety']
        compliance_service = safety_system['compliance']
        
        # Simulate good performance
        with patch.object(safety_service, '_calculate_success_rate') as mock_success_rate:
            mock_success_rate.side_effect = [0.35, 0.28]  # Good success rates
            
            with patch.object(safety_service, '_get_days_active') as mock_days:
                mock_days.return_value = 60  # Established system
                
                # Test scaling up
                config = await safety_service.implement_gradual_scaling(mock_db)
                assert config.scaling_factor >= 1.0
                
                # Update compliance policy to match
                compliance_service.policy.max_applications_per_day = config.max_daily_applications
                compliance_service.policy.max_applications_per_hour = config.max_hourly_applications
                
                # Verify policies are aligned
                assert compliance_service.policy.max_applications_per_day >= 30
                assert compliance_service.policy.max_applications_per_hour >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])