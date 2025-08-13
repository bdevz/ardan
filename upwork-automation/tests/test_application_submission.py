"""
Unit tests for the Browser-Based Application Submission System
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from shared.models import Job, JobType, JobStatus, Proposal, ProposalStatus, Application, ApplicationStatus
from services.application_submission_service import ApplicationSubmissionService, SubmissionResult
from services.application_service import ApplicationService


class TestApplicationSubmissionService:
    """Test suite for browser-based application submission"""
    
    @pytest.fixture
    def submission_service(self):
        """Application submission service instance"""
        return ApplicationSubmissionService()
    
    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing"""
        return {
            "id": str(uuid4()),
            "upwork_job_id": "upwork-123456",
            "title": "Salesforce Agentforce Developer",
            "description": "Build AI-powered customer service solutions",
            "job_url": "https://www.upwork.com/jobs/123456",
            "client_name": "TechCorp Inc",
            "hourly_rate": 75.0,
            "job_type": "hourly"
        }
    
    @pytest.fixture
    def sample_proposal_data(self):
        """Sample proposal data for testing"""
        return {
            "id": str(uuid4()),
            "content": "Dear TechCorp Inc, I am excited to apply for your Salesforce Agentforce Developer position...",
            "bid_amount": 75.0,
            "attachments": ["portfolio.pdf", "case_studies.pdf"],
            "quality_score": 0.85
        }
    
    @pytest.mark.asyncio
    async def test_rate_limit_checking(self, submission_service):
        """Test rate limit validation"""
        # Test within limits
        submission_service.submissions_today = 10
        submission_service.submissions_this_hour = 2
        submission_service.last_submission_time = datetime.utcnow() - timedelta(minutes=10)
        
        assert await submission_service._check_rate_limits() is True
        
        # Test daily limit exceeded
        submission_service.submissions_today = 35  # Over daily limit of 30
        assert await submission_service._check_rate_limits() is False
        
        # Test hourly limit exceeded
        submission_service.submissions_today = 10
        submission_service.submissions_this_hour = 6  # Over hourly limit of 5
        assert await submission_service._check_rate_limits() is False
        
        # Test minimum interval not met
        submission_service.submissions_this_hour = 2
        submission_service.last_submission_time = datetime.utcnow() - timedelta(minutes=2)  # Less than 5 min
        assert await submission_service._check_rate_limits() is False
    
    @pytest.mark.asyncio
    async def test_human_delay_calculation(self, submission_service):
        """Test human-like delay calculation"""
        # Test with randomization enabled
        submission_service.randomize_timing = True
        delay1 = await submission_service._calculate_human_delay()
        delay2 = await submission_service._calculate_human_delay()
        
        # Should be within reasonable bounds
        assert 1.0 <= delay1 <= submission_service.max_delay
        assert 1.0 <= delay2 <= submission_service.max_delay
        
        # Should be different (randomized)
        assert delay1 != delay2
        
        # Test with randomization disabled
        submission_service.randomize_timing = False
        delay3 = await submission_service._calculate_human_delay()
        delay4 = await submission_service._calculate_human_delay()
        
        # Should be consistent
        assert delay3 == delay4 == submission_service.base_delay
    
    @pytest.mark.asyncio
    async def test_batch_delay_calculation(self, submission_service):
        """Test batch delay calculation"""
        delay = await submission_service._calculate_batch_delay()
        
        # Should be between 5-15 minutes (300-900 seconds)
        assert 300 <= delay <= 900
    
    @pytest.mark.asyncio
    async def test_submission_eligibility_validation(self, submission_service):
        """Test submission eligibility validation"""
        mock_db = AsyncMock()
        job_id = uuid4()
        proposal_id = uuid4()
        
        # Mock job exists and is eligible
        mock_job = MagicMock()
        mock_job.status = "discovered"
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_job
        
        # Mock proposal exists and matches job
        mock_proposal = MagicMock()
        mock_proposal.job_id = job_id
        
        # Mock no existing application
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_job),      # Job query
            MagicMock(scalar_one_or_none=lambda: mock_proposal), # Proposal query
            MagicMock(scalar_one_or_none=lambda: None)           # Existing app query
        ]
        
        # Should not raise exception
        await submission_service._validate_submission_eligibility(mock_db, job_id, proposal_id)
        
        # Test with ineligible job status
        mock_job.status = "applied"
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_job),
        ]
        
        with pytest.raises(ValueError, match="not eligible for submission"):
            await submission_service._validate_submission_eligibility(mock_db, job_id, proposal_id)
    
    @pytest.mark.asyncio
    async def test_workflow_step_execution(self, submission_service):
        """Test individual workflow step execution"""
        # Mock Stagehand
        mock_stagehand = MagicMock()
        mock_page = MagicMock()
        mock_stagehand.page = mock_page
        
        # Test navigate step
        params = {"url": "https://example.com", "wait_for": "networkidle"}
        await submission_service._execute_navigate_step(mock_stagehand, params)
        
        mock_stagehand.act.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=30000)
        
        # Test click step
        mock_stagehand.reset_mock()
        mock_page.reset_mock()
        
        params = {"selector": ".apply-button", "wait_for_navigation": True}
        await submission_service._execute_click_step(mock_stagehand, params)
        
        mock_stagehand.act.assert_called_once()
        mock_page.wait_for_load_state.assert_called_once()
        
        # Test form filling step
        mock_stagehand.reset_mock()
        
        params = {
            "fields": {
                "cover_letter": "Test proposal content",
                "bid_amount": "75.00"
            }
        }
        await submission_service._execute_fill_form_step(mock_stagehand, params)
        
        # Should call act for each field
        assert mock_stagehand.act.call_count == 2
    
    @pytest.mark.asyncio
    async def test_realistic_typing_simulation(self, submission_service):
        """Test realistic typing simulation"""
        mock_page = MagicMock()
        mock_keyboard = MagicMock()
        mock_page.keyboard = mock_keyboard
        
        submission_service.use_realistic_typing = True
        
        test_text = "Hello world!"
        
        with patch('asyncio.sleep') as mock_sleep:
            await submission_service._type_realistically(mock_page, test_text)
            
            # Should type each character
            assert mock_keyboard.type.call_count == len(test_text)
            
            # Should add delays between characters
            assert mock_sleep.call_count == len(test_text)
            
            # Verify realistic delay ranges
            delay_calls = [call[0][0] for call in mock_sleep.call_args_list]
            
            # Space should have longer delay
            space_delays = [delay for i, delay in enumerate(delay_calls) if test_text[i] == ' ']
            if space_delays:
                assert all(0.1 <= delay <= 0.3 for delay in space_delays)
            
            # Regular characters should have shorter delays
            char_delays = [delay for i, delay in enumerate(delay_calls) if test_text[i] not in ' .,!?']
            assert all(0.05 <= delay <= 0.15 for delay in char_delays)
    
    @pytest.mark.asyncio
    async def test_stealth_configuration(self, submission_service):
        """Test stealth mode configuration"""
        mock_stagehand = MagicMock()
        mock_page = MagicMock()
        mock_stagehand.page = mock_page
        
        with patch.object(submission_service.stagehand_controller, 'get_stagehand', return_value=mock_stagehand):
            await submission_service._configure_stealth_settings("test_session")
            
            # Should set viewport
            mock_page.set_viewport_size.assert_called_once()
            
            # Should set headers
            mock_page.set_extra_http_headers.assert_called_once()
            
            # Should inject timing variations
            mock_page.evaluate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submission_stats(self, submission_service):
        """Test submission statistics retrieval"""
        submission_service.submissions_today = 15
        submission_service.submissions_this_hour = 3
        submission_service.last_submission_time = datetime.utcnow()
        
        stats = await submission_service.get_submission_stats()
        
        assert stats["submissions_today"] == 15
        assert stats["submissions_this_hour"] == 3
        assert stats["daily_limit"] == 30
        assert stats["hourly_limit"] == 5
        assert "last_submission" in stats
        assert "rate_limit_status" in stats


class TestApplicationService:
    """Test suite for enhanced application service"""
    
    @pytest.fixture
    def application_service(self):
        """Application service instance"""
        return ApplicationService()
    
    @pytest.fixture
    async def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_submission_priority_calculation(self, application_service):
        """Test submission priority scoring"""
        # High priority job/proposal
        high_job = MagicMock()
        high_job.hourly_rate = Decimal("100.0")
        high_job.client_rating = Decimal("5.0")
        high_job.match_score = Decimal("0.9")
        
        high_proposal = MagicMock()
        high_proposal.quality_score = Decimal("0.9")
        
        high_priority = application_service._calculate_submission_priority(high_job, high_proposal)
        
        # Low priority job/proposal
        low_job = MagicMock()
        low_job.hourly_rate = Decimal("30.0")
        low_job.client_rating = Decimal("3.5")
        low_job.match_score = Decimal("0.3")
        
        low_proposal = MagicMock()
        low_proposal.quality_score = Decimal("0.4")
        
        low_priority = application_service._calculate_submission_priority(low_job, low_proposal)
        
        # High priority should be greater than low priority
        assert high_priority > low_priority
        
        # Priority should be reasonable range
        assert 0 <= low_priority <= 100
        assert 0 <= high_priority <= 100
    
    @pytest.mark.asyncio
    async def test_batch_submission_request_processing(self, application_service):
        """Test batch submission request processing"""
        mock_db = AsyncMock()
        
        # Mock applications
        app_ids = [uuid4(), uuid4(), uuid4()]
        
        # Mock get_application calls
        mock_apps = []
        for i, app_id in enumerate(app_ids):
            mock_app = MagicMock()
            mock_app.id = app_id
            mock_app.job_id = uuid4()
            mock_app.proposal_id = uuid4()
            mock_app.status = ApplicationStatus.PENDING
            mock_apps.append(mock_app)
        
        application_service.get_application = AsyncMock(side_effect=mock_apps)
        
        # Mock submission service
        mock_results = [
            MagicMock(success=True, application_id=app_ids[0], execution_time=5.2, steps_completed=["step1", "step2"]),
            MagicMock(success=False, application_id=None, error_message="Rate limit exceeded", execution_time=1.0, steps_completed=["step1"]),
            MagicMock(success=True, application_id=app_ids[2], execution_time=4.8, steps_completed=["step1", "step2"])
        ]
        
        with patch('services.application_service.application_submission_service') as mock_submission_service:
            mock_submission_service.batch_submit_applications.return_value = mock_results
            
            result = await application_service.batch_submit_applications(
                db=mock_db,
                application_ids=app_ids,
                max_concurrent=2
            )
            
            # Verify results
            assert result["success"] is True
            assert result["total_processed"] == 3
            assert result["successful_submissions"] == 2
            assert result["failed_submissions"] == 1
            assert len(result["results"]) == 3
            
            # Verify individual results
            assert result["results"][0]["success"] is True
            assert result["results"][1]["success"] is False
            assert result["results"][1]["error_message"] == "Rate limit exceeded"


class TestWorkflowIntegration:
    """Integration tests for the complete application submission workflow"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_submission_workflow(self):
        """Test complete submission workflow integration"""
        # This would test the full integration from proposal to submission
        # For now, verify that all components can be instantiated together
        
        submission_service = ApplicationSubmissionService()
        application_service = ApplicationService()
        
        # Verify services are properly initialized
        assert submission_service is not None
        assert application_service is not None
        
        # Verify configuration
        assert submission_service.daily_submission_limit == 30
        assert submission_service.hourly_submission_limit == 5
        assert submission_service.stealth_mode is True
        assert submission_service.randomize_timing is True
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test rate limiting across service boundaries"""
        submission_service = ApplicationSubmissionService()
        
        # Test rate limit checking
        submission_service.submissions_today = 25
        submission_service.submissions_this_hour = 4
        
        # Should be within limits
        assert await submission_service._check_rate_limits() is True
        
        # Simulate hitting limits
        submission_service.submissions_today = 30
        assert await submission_service._check_rate_limits() is False
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        submission_service = ApplicationSubmissionService()
        
        # Test submission result error handling
        result = SubmissionResult()
        result.success = False
        result.error_message = "Browser session failed"
        result.retry_count = 2
        
        # Verify error information is properly captured
        assert result.success is False
        assert "failed" in result.error_message
        assert result.retry_count == 2
    
    @pytest.mark.asyncio
    async def test_stealth_and_compliance_features(self):
        """Test stealth and compliance features"""
        submission_service = ApplicationSubmissionService()
        
        # Verify stealth configuration
        assert submission_service.stealth_mode is True
        assert submission_service.use_realistic_typing is True
        assert submission_service.randomize_timing is True
        
        # Test human-like delays
        delay1 = await submission_service._calculate_human_delay()
        delay2 = await submission_service._calculate_human_delay()
        
        # Should be realistic human timing
        assert 1.0 <= delay1 <= 10.0
        assert 1.0 <= delay2 <= 10.0
        
        # Should be randomized
        assert delay1 != delay2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])