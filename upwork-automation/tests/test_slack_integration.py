"""
Tests for Slack Integration

Tests cover:
- Notification service functionality
- Slack command handling
- Interactive components
- Emergency alerts
- Configuration validation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from api.services.notification_service import SlackNotificationService, slack_service
from api.slack_bot import SlackBotConfig
from shared.models import (
    Job, Proposal, Application, DashboardMetrics,
    JobStatus, ProposalStatus, ApplicationStatus, JobType
)


class TestSlackNotificationService:
    """Test the Slack notification service"""
    
    @pytest.fixture
    def mock_slack_client(self):
        """Mock Slack client"""
        client = AsyncMock()
        client.auth_test.return_value = {"user": "test_bot"}
        client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}
        return client
    
    @pytest.fixture
    def notification_service(self, mock_slack_client):
        """Create notification service with mocked client"""
        service = SlackNotificationService()
        service.client = mock_slack_client
        return service
    
    @pytest.fixture
    def sample_job(self):
        """Create sample job for testing"""
        return Job(
            id=uuid4(),
            upwork_job_id="~123456789",
            title="Salesforce Agentforce Developer Needed",
            description="Looking for an experienced Salesforce developer...",
            hourly_rate=Decimal("75.00"),
            client_name="Tech Corp",
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            match_score=Decimal("0.92"),
            match_reasons=["Salesforce experience", "Agentforce expertise", "High client rating"],
            job_url="https://www.upwork.com/jobs/~123456789",
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_proposal(self, sample_job):
        """Create sample proposal for testing"""
        return Proposal(
            id=uuid4(),
            job_id=sample_job.id,
            content="Dear Client,\n\nI am excited to help you with your Salesforce Agentforce project...",
            bid_amount=Decimal("75.00"),
            attachments=["file1.pdf", "file2.pdf"],
            google_doc_url="https://docs.google.com/document/d/abc123",
            status=ProposalStatus.DRAFT,
            quality_score=Decimal("0.88"),
            generated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_application(self, sample_job, sample_proposal):
        """Create sample application for testing"""
        return Application(
            id=uuid4(),
            job_id=sample_job.id,
            proposal_id=sample_proposal.id,
            upwork_application_id="app_123456",
            submitted_at=datetime.now(),
            status=ApplicationStatus.SUBMITTED,
            session_recording_url="https://browserbase.com/session/abc123"
        )
    
    @pytest.fixture
    def sample_metrics(self):
        """Create sample dashboard metrics"""
        return DashboardMetrics(
            total_jobs_discovered=45,
            total_applications_submitted=28,
            applications_today=12,
            success_rate=Decimal("0.85"),
            average_response_time=Decimal("2.3"),
            top_keywords=["Salesforce", "Agentforce", "Einstein", "Developer"],
            recent_applications=[]
        )
    
    @pytest.mark.asyncio
    async def test_job_discovery_notification(self, notification_service, sample_job, mock_slack_client):
        """Test job discovery notification"""
        jobs = [sample_job]
        
        result = await notification_service.send_job_discovery_notification(jobs, "session_123")
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        
        # Check call arguments
        call_args = mock_slack_client.chat_postMessage.call_args
        assert call_args[1]["text"] == "🎯 Discovered 1 high-quality jobs"
        assert "blocks" in call_args[1]
        assert len(call_args[1]["blocks"]) > 0
    
    @pytest.mark.asyncio
    async def test_job_discovery_notification_filtered_by_score(self, notification_service, mock_slack_client):
        """Test job discovery notification filters by match score"""
        # Create jobs with different match scores
        low_score_job = Job(
            id=uuid4(),
            title="Low Score Job",
            description="Test job",
            hourly_rate=Decimal("50.00"),
            client_rating=Decimal("4.0"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.5"),
            job_type=JobType.HOURLY,
            match_score=Decimal("0.5")  # Below threshold
        )
        
        high_score_job = Job(
            id=uuid4(),
            title="High Score Job", 
            description="Test job",
            hourly_rate=Decimal("75.00"),
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            match_score=Decimal("0.9")  # Above threshold
        )
        
        jobs = [low_score_job, high_score_job]
        
        result = await notification_service.send_job_discovery_notification(jobs)
        
        assert result is True
        # Should only notify about the high-score job
        mock_slack_client.chat_postMessage.assert_called_once()
        call_args = mock_slack_client.chat_postMessage.call_args
        assert "1 high-quality jobs" in call_args[1]["text"]
    
    @pytest.mark.asyncio
    async def test_proposal_generation_notification(self, notification_service, sample_proposal, sample_job, mock_slack_client):
        """Test proposal generation notification"""
        result = await notification_service.send_proposal_generation_notification(sample_proposal, sample_job)
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        
        call_args = mock_slack_client.chat_postMessage.call_args
        assert sample_job.title in call_args[1]["text"]
        assert "blocks" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_application_submission_notification(self, notification_service, sample_application, sample_job, sample_proposal, mock_slack_client):
        """Test application submission notification"""
        screenshot_url = "https://example.com/screenshot.png"
        
        result = await notification_service.send_application_submission_notification(
            sample_application, sample_job, sample_proposal, screenshot_url
        )
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        
        call_args = mock_slack_client.chat_postMessage.call_args
        assert sample_job.title in call_args[1]["text"]
        assert "blocks" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_emergency_alert(self, notification_service, mock_slack_client):
        """Test emergency alert notification"""
        alert_type = "system_failure"
        message = "Critical system error detected"
        details = {"error_code": "500", "component": "browser_automation"}
        
        result = await notification_service.send_emergency_alert(alert_type, message, details)
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        
        call_args = mock_slack_client.chat_postMessage.call_args
        assert "EMERGENCY ALERT" in call_args[1]["text"]
        assert "blocks" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_daily_summary(self, notification_service, sample_metrics, mock_slack_client):
        """Test daily summary notification"""
        result = await notification_service.send_daily_summary(sample_metrics)
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        
        call_args = mock_slack_client.chat_postMessage.call_args
        assert "Daily Summary" in call_args[1]["text"]
        assert "blocks" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_interactive_command_handling(self, notification_service, mock_slack_client):
        """Test interactive command handling"""
        result = await notification_service.handle_interactive_command(
            "status", "U123456", "C123456"
        )
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_test(self, notification_service, mock_slack_client):
        """Test Slack connection test"""
        result = await notification_service.test_connection()
        
        assert result is True
        mock_slack_client.auth_test.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self, notification_service, mock_slack_client):
        """Test Slack connection test failure"""
        from slack_sdk.errors import SlackApiError
        
        mock_slack_client.auth_test.side_effect = SlackApiError("Connection failed", response=Mock())
        
        result = await notification_service.test_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_notification_preferences_disabled(self, notification_service, sample_job, mock_slack_client):
        """Test that notifications are skipped when disabled"""
        # Disable job discovery notifications
        notification_service.notification_preferences["job_discovery"]["enabled"] = False
        
        result = await notification_service.send_job_discovery_notification([sample_job])
        
        assert result is True
        mock_slack_client.chat_postMessage.assert_not_called()
    
    def test_create_job_discovery_blocks(self, notification_service, sample_job):
        """Test job discovery block creation"""
        blocks = notification_service._create_job_discovery_blocks([sample_job], "session_123")
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "New Jobs Discovered" in blocks[0]["text"]["text"]
        
        # Check for job details
        job_section = next((block for block in blocks if block.get("type") == "section" and sample_job.title in str(block)), None)
        assert job_section is not None
    
    def test_create_proposal_notification_blocks(self, notification_service, sample_proposal, sample_job):
        """Test proposal notification block creation"""
        blocks = notification_service._create_proposal_notification_blocks(sample_proposal, sample_job)
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "Proposal Generated" in blocks[0]["text"]["text"]
    
    def test_create_emergency_alert_blocks(self, notification_service):
        """Test emergency alert block creation"""
        blocks = notification_service._create_emergency_alert_blocks(
            "system_failure", "Critical error", {"component": "browser"}
        )
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "EMERGENCY ALERT" in blocks[0]["text"]["text"]
        
        # Check for emergency stop button
        actions_block = next((block for block in blocks if block.get("type") == "actions"), None)
        assert actions_block is not None
        
        emergency_button = next((
            element for element in actions_block["elements"] 
            if element.get("action_id") == "emergency_stop"
        ), None)
        assert emergency_button is not None
    
    def test_update_notification_preferences(self, notification_service):
        """Test updating notification preferences"""
        new_preferences = {
            "job_discovery": {
                "enabled": False,
                "min_match_score": 0.8
            }
        }
        
        result = asyncio.run(notification_service.update_notification_preferences(new_preferences))
        
        assert result is True
        assert notification_service.notification_preferences["job_discovery"]["enabled"] is False
        assert notification_service.notification_preferences["job_discovery"]["min_match_score"] == 0.8


class TestSlackBotConfig:
    """Test Slack bot configuration utilities"""
    
    def test_get_app_manifest(self):
        """Test app manifest generation"""
        manifest = SlackBotConfig.get_app_manifest()
        
        assert "display_information" in manifest
        assert "features" in manifest
        assert "oauth_config" in manifest
        assert "settings" in manifest
        
        # Check required features
        assert "bot_user" in manifest["features"]
        assert "slash_commands" in manifest["features"]
        assert "shortcuts" in manifest["features"]
        
        # Check slash command
        slash_commands = manifest["features"]["slash_commands"]
        upwork_command = next((cmd for cmd in slash_commands if cmd["command"] == "/upwork"), None)
        assert upwork_command is not None
    
    def test_get_required_permissions(self):
        """Test required permissions list"""
        permissions = SlackBotConfig.get_required_permissions()
        
        assert "chat:write" in permissions
        assert "commands" in permissions
        assert "app_mentions:read" in permissions
        assert "files:write" in permissions
    
    def test_get_setup_instructions(self):
        """Test setup instructions"""
        instructions = SlackBotConfig.get_setup_instructions()
        
        assert "title" in instructions
        assert "steps" in instructions
        assert "troubleshooting" in instructions
        
        # Check that all steps are present
        assert len(instructions["steps"]) >= 6
        
        # Check troubleshooting section
        assert "common_issues" in instructions["troubleshooting"]
    
    @patch('shared.config.settings')
    def test_validate_configuration_valid(self, mock_settings):
        """Test configuration validation with valid settings"""
        mock_settings.slack_bot_token = "xoxb-123456789-abcdef"
        mock_settings.slack_channel_id = "C1234567890"
        mock_settings.slack_signing_secret = "signing_secret"
        
        validation = SlackBotConfig.validate_configuration()
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert "SLACK_BOT_TOKEN" in validation["configuration"]
        assert "SLACK_CHANNEL_ID" in validation["configuration"]
    
    @patch('shared.config.settings')
    def test_validate_configuration_missing_token(self, mock_settings):
        """Test configuration validation with missing token"""
        mock_settings.slack_bot_token = None
        mock_settings.slack_channel_id = "C1234567890"
        
        validation = SlackBotConfig.validate_configuration()
        
        assert validation["valid"] is False
        assert any("SLACK_BOT_TOKEN" in error for error in validation["errors"])
    
    @patch('shared.config.settings')
    def test_validate_configuration_invalid_token_format(self, mock_settings):
        """Test configuration validation with invalid token format"""
        mock_settings.slack_bot_token = "invalid-token-format"
        mock_settings.slack_channel_id = "C1234567890"
        
        validation = SlackBotConfig.validate_configuration()
        
        assert validation["valid"] is False
        assert any("should start with 'xoxb-'" in error for error in validation["errors"])
    
    def test_get_notification_templates(self):
        """Test notification templates"""
        templates = SlackBotConfig.get_notification_templates()
        
        assert "job_discovery" in templates
        assert "proposal_generated" in templates
        assert "application_submitted" in templates
        assert "emergency_alert" in templates
        
        # Check template structure
        job_template = templates["job_discovery"]
        assert "title" in job_template
        assert "color" in job_template
        assert "fields" in job_template
    
    def test_get_interactive_components(self):
        """Test interactive components"""
        components = SlackBotConfig.get_interactive_components()
        
        assert "system_controls" in components
        assert "job_actions" in components
        assert "proposal_actions" in components
        
        # Check system controls
        system_controls = components["system_controls"]
        assert system_controls["type"] == "actions"
        assert len(system_controls["elements"]) >= 3
        
        # Check for emergency stop with confirmation
        emergency_button = next((
            element for element in system_controls["elements"]
            if element.get("action_id") == "emergency_stop"
        ), None)
        assert emergency_button is not None
        assert "confirm" in emergency_button


class TestSlackRouterIntegration:
    """Test Slack router integration"""
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request"""
        request = Mock()
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test_signature"
        }
        request.body = AsyncMock(return_value=b"test_body")
        return request
    
    @pytest.mark.asyncio
    async def test_slash_command_parsing(self, mock_request):
        """Test slash command parsing"""
        from api.routers.slack import handle_slash_command
        
        # Mock form data
        form_data = {
            "command": "/upwork",
            "text": "status",
            "user_id": "U123456",
            "user_name": "testuser",
            "channel_id": "C123456",
            "channel_name": "general"
        }
        
        mock_request.form = AsyncMock(return_value=Mock(get=lambda key, default="": form_data.get(key, default)))
        
        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        with patch('api.routers.slack.signature_verifier', None):  # Skip signature verification
            response = await handle_slash_command(mock_request, background_tasks)
        
        assert "Processing command" in response["text"]
        background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_interactive_components_handling(self, mock_request):
        """Test interactive components handling"""
        from api.routers.slack import handle_interactive_components
        
        payload = {
            "type": "block_actions",
            "user": {"id": "U123456", "name": "testuser"},
            "channel": {"id": "C123456", "name": "general"},
            "actions": [
                {
                    "action_id": "emergency_stop",
                    "value": "confirm"
                }
            ]
        }
        
        form_data = {"payload": json.dumps(payload)}
        mock_request.form = AsyncMock(return_value=Mock(get=lambda key, default="": form_data.get(key, default)))
        
        background_tasks = Mock()
        background_tasks.add_task = Mock()
        
        with patch('api.routers.slack.signature_verifier', None):  # Skip signature verification
            response = await handle_interactive_components(mock_request, background_tasks)
        
        assert response["status"] == "ok"
        background_tasks.add_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_slack_events_url_verification(self, mock_request):
        """Test Slack events URL verification"""
        from api.routers.slack import handle_slack_events
        
        event_data = {
            "type": "url_verification",
            "challenge": "test_challenge_string"
        }
        
        mock_request.json = AsyncMock(return_value=event_data)
        background_tasks = Mock()
        
        with patch('api.routers.slack.signature_verifier', None):  # Skip signature verification
            response = await handle_slack_events(mock_request, background_tasks)
        
        assert response["challenge"] == "test_challenge_string"


@pytest.mark.integration
class TestSlackIntegrationEnd2End:
    """End-to-end integration tests for Slack functionality"""
    
    @pytest.mark.asyncio
    async def test_full_notification_workflow(self):
        """Test complete notification workflow"""
        # This would test the full workflow from job discovery to Slack notification
        # Requires actual Slack credentials and would be run in integration environment
        pass
    
    @pytest.mark.asyncio
    async def test_emergency_alert_escalation(self):
        """Test emergency alert escalation workflow"""
        # This would test the emergency alert system end-to-end
        pass
    
    @pytest.mark.asyncio
    async def test_interactive_system_control(self):
        """Test interactive system control via Slack"""
        # This would test the full interactive control workflow
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])