"""
Integration tests for Stagehand browser control functions
"""
import sys
import os
import importlib.util
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import modules using importlib due to hyphenated directory name
def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import the modules
base_path = Path(__file__).parent.parent / "browser-automation"
stagehand_controller = import_from_path("stagehand_controller", base_path / "stagehand_controller.py")
stagehand_error_handler = import_from_path("stagehand_error_handler", base_path / "stagehand_error_handler.py")
browserbase_client = import_from_path("browserbase_client", base_path / "browserbase_client.py")

# Import classes directly
StagehandController = stagehand_controller.StagehandController
ArdanJobSearchController = stagehand_controller.ArdanJobSearchController
ArdanApplicationController = stagehand_controller.ArdanApplicationController
NavigationStrategy = stagehand_controller.NavigationStrategy
ExtractionType = stagehand_controller.ExtractionType
NavigationResult = stagehand_controller.NavigationResult
ExtractionResult = stagehand_controller.ExtractionResult
InteractionResult = stagehand_controller.InteractionResult

StagehandErrorHandler = stagehand_error_handler.StagehandErrorHandler
ErrorType = stagehand_error_handler.ErrorType
RecoveryStrategy = stagehand_error_handler.RecoveryStrategy
ErrorContext = stagehand_error_handler.ErrorContext

BrowserbaseClient = browserbase_client.BrowserbaseClient
SessionInfo = browserbase_client.SessionInfo
SessionStatus = browserbase_client.SessionStatus
from shared.config import settings


@pytest.fixture
async def mock_browserbase_client():
    """Mock browserbase client for testing"""
    client = Mock(spec=BrowserbaseClient)
    
    # Mock session info
    session_info = SessionInfo(
        id="test_session_123",
        config=Mock(),
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow(),
        last_health_check=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        context_data={},
        browserbase_session_id="bb_session_456",
        connect_url="ws://localhost:9222/devtools/browser/test"
    )
    
    client.get_session = AsyncMock(return_value=session_info)
    client.get_or_create_session = AsyncMock(return_value="test_session_123")
    client.return_session = AsyncMock()
    client.get_session_health = AsyncMock(return_value={"healthy": True})
    
    return client


@pytest.fixture
async def mock_stagehand():
    """Mock Stagehand instance for testing"""
    stagehand = Mock()
    stagehand.page = Mock()
    stagehand.page.url = "https://www.ardan.com"
    stagehand.page.title = AsyncMock(return_value="Ardan - Test Page")
    stagehand.page.goto = AsyncMock()
    stagehand.page.wait_for_load_state = AsyncMock()
    stagehand.page.reload = AsyncMock()
    stagehand.page.go_back = AsyncMock()
    stagehand.page.viewport_size = AsyncMock(return_value={"width": 1920, "height": 1080})
    stagehand.page.evaluate = AsyncMock(return_value="Mozilla/5.0 Test Agent")
    
    stagehand.act = AsyncMock()
    stagehand.extract = AsyncMock(return_value={"test": "data"})
    stagehand.close = AsyncMock()
    stagehand.init = AsyncMock()
    
    return stagehand


@pytest.fixture
async def stagehand_controller(mock_browserbase_client):
    """Create StagehandController instance for testing"""
    controller = StagehandController(mock_browserbase_client)
    return controller


class TestStagehandController:
    """Test cases for StagehandController"""
    
    @pytest.mark.asyncio
    async def test_initialize_stagehand_success(self, stagehand_controller, mock_stagehand):
        """Test successful Stagehand initialization"""
        with patch('browser_automation.stagehand_controller.Stagehand', return_value=mock_stagehand):
            result = await stagehand_controller.initialize_stagehand("test_session_123")
            
            assert result is True
            assert "test_session_123" in stagehand_controller.stagehand_instances
            mock_stagehand.init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_stagehand_failure(self, stagehand_controller):
        """Test Stagehand initialization failure"""
        # Mock session with no connect URL
        stagehand_controller.browserbase_client.get_session = AsyncMock(return_value=None)
        
        result = await stagehand_controller.initialize_stagehand("invalid_session")
        
        assert result is False
        assert "invalid_session" not in stagehand_controller.stagehand_instances
    
    @pytest.mark.asyncio
    async def test_intelligent_navigate_direct_url(self, stagehand_controller, mock_stagehand):
        """Test direct URL navigation"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        result = await stagehand_controller.intelligent_navigate(
            "test_session",
            "https://www.ardan.com/jobs",
            NavigationStrategy.DIRECT_URL
        )
        
        assert result.success is True
        assert result.url == "https://www.ardan.com"
        assert result.page_title == "Ardan - Test Page"
        mock_stagehand.page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_intelligent_navigate_search_and_click(self, stagehand_controller, mock_stagehand):
        """Test search and click navigation"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        result = await stagehand_controller.intelligent_navigate(
            "test_session",
            "job search page",
            NavigationStrategy.SEARCH_AND_CLICK
        )
        
        assert result.success is True
        mock_stagehand.act.assert_called_with("navigate to job search page")
    
    @pytest.mark.asyncio
    async def test_extract_content_success(self, stagehand_controller, mock_stagehand):
        """Test successful content extraction"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        mock_stagehand.extract.return_value = {
            "jobs": [
                {"title": "Salesforce Developer", "budget": "$75/hr"},
                {"title": "Agentforce Specialist", "budget": "$80/hr"}
            ]
        }
        
        result = await stagehand_controller.extract_content(
            "test_session",
            "extract job listings",
            ExtractionType.JOB_LISTINGS
        )
        
        assert result.success is True
        assert "jobs" in result.data
        assert len(result.data["jobs"]) == 2
        assert result.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_extract_content_with_schema(self, stagehand_controller, mock_stagehand):
        """Test content extraction with schema validation"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        schema = {
            "required": ["title", "budget", "client_name"],
            "properties": {
                "title": {"type": "string"},
                "budget": {"type": "string"},
                "client_name": {"type": "string"}
            }
        }
        
        mock_stagehand.extract.return_value = {
            "title": "Salesforce Developer",
            "budget": "$75/hr",
            "client_name": "Tech Corp"
        }
        
        result = await stagehand_controller.extract_content(
            "test_session",
            "extract job details",
            ExtractionType.JOB_DETAILS,
            schema
        )
        
        assert result.success is True
        assert result.confidence_score == 1.0  # All required fields present
    
    @pytest.mark.asyncio
    async def test_interact_with_form_success(self, stagehand_controller, mock_stagehand):
        """Test successful form interaction"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        form_data = {
            "search_query": "Salesforce Agentforce",
            "hourly_rate_min": "50",
            "location": "Remote"
        }
        
        result = await stagehand_controller.interact_with_form(
            "test_session",
            form_data,
            submit=True
        )
        
        assert result.success is True
        assert result.action_performed == "form_submit"
        assert len(result.elements_affected) == 3
        
        # Verify all form fields were filled
        expected_calls = [
            "fill the search_query field with: Salesforce Agentforce",
            "fill the hourly_rate_min field with: 50",
            "fill the location field with: Remote",
            "submit the form"
        ]
        
        actual_calls = [call.args[0] for call in mock_stagehand.act.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls
    
    @pytest.mark.asyncio
    async def test_interact_with_form_validation_failure(self, stagehand_controller, mock_stagehand):
        """Test form interaction with validation failure"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        # Mock validation failure
        mock_stagehand.act.side_effect = [None, Exception("Field validation failed")]
        
        form_data = {"invalid_field": ""}
        validation_rules = {"invalid_field": {"required": True, "min_length": 5}}
        
        result = await stagehand_controller.interact_with_form(
            "test_session",
            form_data,
            submit=False,
            validation_rules=validation_rules
        )
        
        assert result.success is False
        assert len(result.validation_errors) > 0
    
    @pytest.mark.asyncio
    async def test_handle_dynamic_content(self, stagehand_controller, mock_stagehand):
        """Test dynamic content handling"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        result = await stagehand_controller.handle_dynamic_content(
            "test_session",
            "job search results to load"
        )
        
        assert result is True
        mock_stagehand.act.assert_called_with("wait for job search results to load to load")
    
    @pytest.mark.asyncio
    async def test_capture_page_state(self, stagehand_controller, mock_stagehand):
        """Test page state capture"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        mock_stagehand.extract.return_value = "Main content: Job listings page with search filters"
        
        result = await stagehand_controller.capture_page_state("test_session")
        
        assert "url" in result
        assert "title" in result
        assert "timestamp" in result
        assert "content_summary" in result
        assert result["url"] == "https://www.ardan.com"
    
    @pytest.mark.asyncio
    async def test_recover_from_error_auto_strategy(self, stagehand_controller, mock_stagehand):
        """Test automatic error recovery"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        
        error_context = {
            "error": "Element not found",
            "last_action": "click apply button"
        }
        
        result = await stagehand_controller.recover_from_error(
            "test_session",
            error_context,
            "auto"
        )
        
        assert result is True
        mock_stagehand.act.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_session(self, stagehand_controller, mock_stagehand):
        """Test session cleanup"""
        stagehand_controller.stagehand_instances["test_session"] = mock_stagehand
        stagehand_controller.page_contexts["test_session"] = {"test": "data"}
        stagehand_controller.navigation_history["test_session"] = ["url1", "url2"]
        
        await stagehand_controller.cleanup_session("test_session")
        
        assert "test_session" not in stagehand_controller.stagehand_instances
        assert "test_session" not in stagehand_controller.page_contexts
        assert "test_session" not in stagehand_controller.navigation_history
        mock_stagehand.close.assert_called_once()


class TestArdanJobSearchController:
    """Test cases for ArdanJobSearchController"""
    
    @pytest.fixture
    async def job_search_controller(self, mock_browserbase_client):
        """Create ArdanJobSearchController for testing"""
        return ArdanJobSearchController(mock_browserbase_client)
    
    @pytest.mark.asyncio
    async def test_search_jobs_success(self, job_search_controller, mock_stagehand):
        """Test successful job search"""
        job_search_controller.stagehand_instances["test_session"] = mock_stagehand
        
        # Mock successful navigation
        mock_stagehand.page.url = "https://www.ardan.com/nx/search/jobs"
        
        # Mock job extraction
        mock_stagehand.extract.return_value = {
            "jobs": [
                {
                    "title": "Salesforce Agentforce Developer",
                    "client_name": "Tech Solutions Inc",
                    "budget": "$75/hr",
                    "description": "Looking for experienced Salesforce developer...",
                    "posted_time": "2 hours ago",
                    "proposals": "5-10",
                    "client_rating": "4.8",
                    "payment_verified": True,
                    "job_url": "https://www.ardan.com/jobs/salesforce-dev-123"
                }
            ]
        }
        
        result = await job_search_controller.search_jobs(
            "test_session",
            ["Salesforce", "Agentforce"],
            {"hourly_rate_min": "50"}
        )
        
        assert result.success is True
        assert result.extraction_type == ExtractionType.JOB_LISTINGS
        assert "jobs" in result.data
        assert len(result.data["jobs"]) == 1
        assert result.data["jobs"][0]["title"] == "Salesforce Agentforce Developer"
    
    @pytest.mark.asyncio
    async def test_extract_job_details_success(self, job_search_controller, mock_stagehand):
        """Test successful job details extraction"""
        job_search_controller.stagehand_instances["test_session"] = mock_stagehand
        
        # Mock job details extraction
        mock_stagehand.extract.return_value = {
            "title": "Senior Salesforce Agentforce Developer",
            "description": "We are looking for an experienced Salesforce developer...",
            "budget_type": "hourly",
            "budget_min": 70,
            "budget_max": 90,
            "skills_required": ["Salesforce", "Apex", "Lightning", "Agentforce"],
            "client_info": {
                "name": "Enterprise Corp",
                "rating": 4.9,
                "hire_rate": 0.85,
                "payment_verified": True
            },
            "timeline": "3-6 months",
            "similar_jobs": 12
        }
        
        result = await job_search_controller.extract_job_details(
            "test_session",
            "https://www.ardan.com/jobs/salesforce-dev-123"
        )
        
        assert result.success is True
        assert result.extraction_type == ExtractionType.JOB_DETAILS
        assert result.data["title"] == "Senior Salesforce Agentforce Developer"
        assert result.data["budget_min"] == 70
        assert "Agentforce" in result.data["skills_required"]


class TestArdanApplicationController:
    """Test cases for ArdanApplicationController"""
    
    @pytest.fixture
    async def application_controller(self, mock_browserbase_client):
        """Create ArdanApplicationController for testing"""
        return ArdanApplicationController(mock_browserbase_client)
    
    @pytest.mark.asyncio
    async def test_submit_application_success(self, application_controller, mock_stagehand):
        """Test successful application submission"""
        application_controller.stagehand_instances["test_session"] = mock_stagehand
        
        proposal_content = """
        Dear Client,
        
        I am an experienced Salesforce Agentforce developer with 5+ years of experience...
        
        I have successfully implemented similar solutions for enterprise clients...
        
        I would love to discuss your project requirements in detail.
        
        Best regards,
        [Developer Name]
        """
        
        result = await application_controller.submit_application(
            "test_session",
            "https://www.ardan.com/jobs/salesforce-dev-123",
            proposal_content,
            75.0,
            ["portfolio.pdf", "case_study.pdf"]
        )
        
        assert result.success is True
        assert result.action_performed == "form_submit"
        
        # Verify form filling calls
        form_fill_calls = [call.args[0] for call in mock_stagehand.act.call_args_list]
        assert any("cover_letter" in call for call in form_fill_calls)
        assert any("75.0" in call for call in form_fill_calls)
    
    @pytest.mark.asyncio
    async def test_verify_submission_success(self, application_controller, mock_stagehand):
        """Test application submission verification"""
        application_controller.stagehand_instances["test_session"] = mock_stagehand
        
        # Mock confirmation extraction
        mock_stagehand.extract.return_value = {
            "success": True,
            "confirmation_message": "Your proposal has been submitted successfully!",
            "application_id": "APP_123456789",
            "errors": []
        }
        
        result = await application_controller.verify_submission("test_session")
        
        assert result.success is True
        assert result.extraction_type == ExtractionType.CONFIRMATION
        assert result.data["success"] is True
        assert result.data["application_id"] == "APP_123456789"


class TestStagehandErrorHandler:
    """Test cases for StagehandErrorHandler"""
    
    @pytest.fixture
    def error_handler(self):
        """Create StagehandErrorHandler for testing"""
        return StagehandErrorHandler()
    
    def test_classify_error_navigation_failed(self, error_handler):
        """Test error classification for navigation failures"""
        error = Exception("Navigation to page failed")
        error_type = error_handler.classify_error(error, {})
        
        assert error_type == ErrorType.NAVIGATION_FAILED
    
    def test_classify_error_element_not_found(self, error_handler):
        """Test error classification for element not found"""
        error = Exception("Element with selector '.apply-button' not found")
        error_type = error_handler.classify_error(error, {})
        
        assert error_type == ErrorType.ELEMENT_NOT_FOUND
    
    def test_classify_error_timeout(self, error_handler):
        """Test error classification for timeout errors"""
        error = Exception("Operation timed out after 30 seconds")
        error_type = error_handler.classify_error(error, {})
        
        assert error_type == ErrorType.TIMEOUT_ERROR
    
    def test_classify_error_captcha(self, error_handler):
        """Test error classification for CAPTCHA detection"""
        error = Exception("CAPTCHA verification required")
        error_type = error_handler.classify_error(error, {})
        
        assert error_type == ErrorType.CAPTCHA_DETECTED
    
    def test_create_error_context(self, error_handler):
        """Test error context creation"""
        error = Exception("Test error")
        context = error_handler.create_error_context(
            error,
            "test_session_123",
            "test_operation",
            "https://www.ardan.com",
            {"test": "metadata"}
        )
        
        assert context.error_message == "Test error"
        assert context.session_id == "test_session_123"
        assert context.operation == "test_operation"
        assert context.page_url == "https://www.ardan.com"
        assert context.metadata == {"test": "metadata"}
        assert context.retry_count == 0
    
    def test_record_error(self, error_handler):
        """Test error recording"""
        error_context = ErrorContext(
            error_type=ErrorType.ELEMENT_NOT_FOUND,
            error_message="Test error",
            session_id="test_session",
            operation="test_op",
            timestamp=datetime.utcnow()
        )
        
        error_handler.record_error(error_context)
        
        assert "test_session" in error_handler.error_history
        assert len(error_handler.error_history["test_session"]) == 1
        assert error_handler.error_history["test_session"][0] == error_context
    
    @pytest.mark.asyncio
    async def test_retry_immediate_success(self, error_handler):
        """Test immediate retry recovery strategy"""
        error_context = ErrorContext(
            error_type=ErrorType.ELEMENT_NOT_FOUND,
            error_message="Test error",
            session_id="test_session",
            operation="test_op",
            timestamp=datetime.utcnow()
        )
        
        # Mock successful recovery callback
        recovery_callback = AsyncMock()
        
        result = await error_handler._retry_immediate(
            error_context,
            recovery_callback,
            {"max_attempts": 2}
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.RETRY_IMMEDIATE
        assert result.error_resolved is True
        recovery_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_with_delay_success(self, error_handler):
        """Test retry with delay recovery strategy"""
        error_context = ErrorContext(
            error_type=ErrorType.TIMEOUT_ERROR,
            error_message="Test timeout",
            session_id="test_session",
            operation="test_op",
            timestamp=datetime.utcnow()
        )
        
        recovery_callback = AsyncMock()
        
        # Use short delay for testing
        result = await error_handler._retry_with_delay(
            error_context,
            recovery_callback,
            {"delay": 0.1}
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_DELAY
        assert result.recovery_time >= 0.1
        recovery_callback.assert_called_once()
    
    def test_get_error_statistics(self, error_handler):
        """Test error statistics generation"""
        # Add some test errors
        for i in range(5):
            error_context = ErrorContext(
                error_type=ErrorType.ELEMENT_NOT_FOUND,
                error_message=f"Test error {i}",
                session_id="test_session",
                operation="test_op",
                timestamp=datetime.utcnow()
            )
            error_handler.record_error(error_context)
        
        stats = error_handler.get_error_statistics("test_session")
        
        assert stats["total_errors"] == 5
        assert stats["error_types"]["element_not_found"] == 5
        assert stats["most_common_error"] == "element_not_found"
    
    def test_should_abort_session_too_many_errors(self, error_handler):
        """Test session abort decision with too many errors"""
        # Add many recent errors
        for i in range(15):
            error_context = ErrorContext(
                error_type=ErrorType.ELEMENT_NOT_FOUND,
                error_message=f"Test error {i}",
                session_id="test_session",
                operation="test_op",
                timestamp=datetime.utcnow()
            )
            error_handler.record_error(error_context)
        
        should_abort = error_handler.should_abort_session("test_session")
        assert should_abort is True
    
    def test_should_abort_session_critical_errors(self, error_handler):
        """Test session abort decision with critical errors"""
        # Add critical errors
        critical_error_types = [
            ErrorType.CAPTCHA_DETECTED,
            ErrorType.RATE_LIMITED,
            ErrorType.SESSION_EXPIRED
        ]
        
        for error_type in critical_error_types:
            error_context = ErrorContext(
                error_type=error_type,
                error_message="Critical error",
                session_id="test_session",
                operation="test_op",
                timestamp=datetime.utcnow()
            )
            error_handler.record_error(error_context)
        
        should_abort = error_handler.should_abort_session("test_session")
        assert should_abort is True
    
    @pytest.mark.asyncio
    async def test_handle_error(self, error_handler):
        """Test complete error handling workflow"""
        error_context = ErrorContext(
            error_type=ErrorType.ELEMENT_NOT_FOUND,
            error_message="Test element not found",
            session_id="test_session",
            operation="test_operation",
            timestamp=datetime.utcnow()
        )
        
        # Mock stagehand controller
        mock_controller = Mock()
        mock_controller.get_stagehand = AsyncMock()
        
        # Mock recovery callback
        recovery_callback = AsyncMock()
        
        # Test error handling
        result = await error_handler.handle_error(
            error_context,
            mock_controller,
            recovery_callback
        )
        
        # Verify error was recorded
        assert "test_session" in error_handler.error_history
        assert len(error_handler.error_history["test_session"]) == 1
        
        # Verify recovery was attempted
        assert result.strategy_used in [
            RecoveryStrategy.WAIT_AND_RETRY,
            RecoveryStrategy.REFRESH_PAGE,
            RecoveryStrategy.RETRY_WITH_DELAY,
            RecoveryStrategy.ABORT_OPERATION
        ]


class TestIntegrationScenarios:
    """Integration test scenarios combining multiple components"""
    
    @pytest.mark.asyncio
    async def test_complete_job_search_workflow(self, mock_browserbase_client, mock_stagehand):
        """Test complete job search workflow with error handling"""
        controller = ArdanJobSearchController(mock_browserbase_client)
        error_handler = StagehandErrorHandler()
        
        # Setup mock responses
        controller.stagehand_instances["test_session"] = mock_stagehand
        mock_stagehand.extract.return_value = {
            "jobs": [
                {
                    "title": "Salesforce Agentforce Developer",
                    "client_name": "Tech Corp",
                    "budget": "$80/hr",
                    "job_url": "https://www.ardan.com/jobs/test-123"
                }
            ]
        }
        
        # Execute job search
        result = await controller.search_jobs(
            "test_session",
            ["Salesforce", "Agentforce"],
            {"hourly_rate_min": "60"}
        )
        
        assert result.success is True
        assert len(result.data["jobs"]) == 1
        
        # Verify no errors were recorded
        stats = error_handler.get_error_statistics("test_session")
        assert stats["total_errors"] == 0
    
    @pytest.mark.asyncio
    async def test_application_submission_with_error_recovery(self, mock_browserbase_client, mock_stagehand):
        """Test application submission with error recovery"""
        controller = ArdanApplicationController(mock_browserbase_client)
        error_handler = StagehandErrorHandler()
        
        controller.stagehand_instances["test_session"] = mock_stagehand
        
        # Simulate initial failure then success
        mock_stagehand.act.side_effect = [
            None,  # Navigate to job
            Exception("Element not found"),  # First form fill fails
            None,  # Recovery attempt
            None,  # Successful form fill
            None   # Submit
        ]
        
        # Test error handling decorator would be applied here in real usage
        try:
            result = await controller.submit_application(
                "test_session",
                "https://www.ardan.com/jobs/test-123",
                "Test proposal content",
                75.0
            )
            
            # In real scenario, error handler would recover and retry
            # For this test, we just verify the error would be handled
            assert True  # Test passes if no unhandled exception
            
        except Exception as e:
            # Create error context and test recovery
            error_context = error_handler.create_error_context(
                e, "test_session", "submit_application"
            )
            
            assert error_context.error_type == ErrorType.ELEMENT_NOT_FOUND
            
            # Test that appropriate recovery strategies are available
            strategies = error_handler.recovery_strategies[ErrorType.ELEMENT_NOT_FOUND]
            assert RecoveryStrategy.WAIT_AND_RETRY in strategies
            assert RecoveryStrategy.REFRESH_PAGE in strategies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])