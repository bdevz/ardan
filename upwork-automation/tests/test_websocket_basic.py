"""
Basic tests for WebSocket functionality
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

# Test the WebSocket service without FastAPI dependencies
def test_websocket_service_initialization():
    """Test WebSocket service initialization"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    assert service.manager is None
    assert not service._initialized
    
    # Mock connection manager
    mock_manager = MagicMock()
    service.initialize(mock_manager)
    
    assert service.manager == mock_manager
    assert service._initialized


@pytest.mark.asyncio
async def test_websocket_service_broadcast_job_discovered():
    """Test broadcasting job discovery messages"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    job_data = {
        "id": "test-job-id",
        "title": "Test Salesforce Job",
        "budget_max": 5000,
        "hourly_rate": 75,
        "client_rating": 4.8,
        "match_score": 0.95,
        "posted_date": "2024-01-01T12:00:00Z"
    }
    
    await service.broadcast_job_discovered(job_data)
    
    # Verify broadcast_to_channel was called twice (dashboard and jobs channels)
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    # Check the calls
    calls = mock_manager.broadcast_to_channel.call_args_list
    
    # First call should be to dashboard channel
    dashboard_call = calls[0]
    assert dashboard_call[0][1] == "dashboard"  # channel argument
    message = dashboard_call[0][0]  # message argument
    assert message["type"] == "job_discovered"
    assert message["data"]["job_id"] == "test-job-id"
    assert message["data"]["title"] == "Test Salesforce Job"
    
    # Second call should be to jobs channel
    jobs_call = calls[1]
    assert jobs_call[0][1] == "jobs"


@pytest.mark.asyncio
async def test_websocket_service_broadcast_proposal_generated():
    """Test broadcasting proposal generation messages"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    proposal_data = {
        "id": "test-proposal-id",
        "job_id": "test-job-id",
        "job_title": "Test Job",
        "bid_amount": 75.0,
        "generated_at": "2024-01-01T12:00:00Z"
    }
    
    await service.broadcast_proposal_generated(proposal_data)
    
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    calls = mock_manager.broadcast_to_channel.call_args_list
    message = calls[0][0][0]
    assert message["type"] == "proposal_generated"
    assert message["data"]["proposal_id"] == "test-proposal-id"


@pytest.mark.asyncio
async def test_websocket_service_broadcast_application_submitted():
    """Test broadcasting application submission messages"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    application_data = {
        "id": "test-application-id",
        "job_id": "test-job-id",
        "job_title": "Test Job",
        "proposal_id": "test-proposal-id",
        "submitted_at": "2024-01-01T12:00:00Z",
        "status": "SUBMITTED"
    }
    
    await service.broadcast_application_submitted(application_data)
    
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    calls = mock_manager.broadcast_to_channel.call_args_list
    message = calls[0][0][0]
    assert message["type"] == "application_submitted"
    assert message["data"]["application_id"] == "test-application-id"


@pytest.mark.asyncio
async def test_websocket_service_broadcast_queue_status_update():
    """Test broadcasting queue status updates"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    queue_data = {
        "total_jobs": 100,
        "pending_jobs": 10,
        "processing_jobs": 5,
        "completed_jobs": 80,
        "failed_jobs": 5,
        "queue_health": "healthy"
    }
    
    await service.broadcast_queue_status_update(queue_data)
    
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    calls = mock_manager.broadcast_to_channel.call_args_list
    
    # Should broadcast to dashboard and queue channels
    channels = [call[0][1] for call in calls]
    assert "dashboard" in channels
    assert "queue" in channels
    
    message = calls[0][0][0]
    assert message["type"] == "queue_status_update"
    assert message["data"]["total_jobs"] == 100


@pytest.mark.asyncio
async def test_websocket_service_broadcast_system_metrics():
    """Test broadcasting system metrics"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    metrics_data = {
        "applications_today": 15,
        "success_rate": 0.75,
        "avg_response_time": 250,
        "active_sessions": 3,
        "system_health": "healthy",
        "cpu_usage": 45,
        "memory_usage": 60
    }
    
    await service.broadcast_system_metrics(metrics_data)
    
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    calls = mock_manager.broadcast_to_channel.call_args_list
    
    # Should broadcast to dashboard and metrics channels
    channels = [call[0][1] for call in calls]
    assert "dashboard" in channels
    assert "metrics" in channels
    
    message = calls[0][0][0]
    assert message["type"] == "system_metrics_update"
    assert message["data"]["applications_today"] == 15


@pytest.mark.asyncio
async def test_websocket_service_broadcast_error_alert():
    """Test broadcasting error alerts"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    error_data = {
        "id": "test-error-id",
        "type": "browser_automation_error",
        "message": "Failed to submit application",
        "severity": "high",
        "component": "application_submission",
        "timestamp": "2024-01-01T12:00:00Z",
        "details": {"job_id": "test-job-id"}
    }
    
    await service.broadcast_error_alert(error_data)
    
    # Error alerts should broadcast to all channels
    mock_manager.broadcast_to_all.assert_called_once()
    
    call_args = mock_manager.broadcast_to_all.call_args[0][0]
    assert call_args["type"] == "error_alert"
    assert call_args["data"]["error_id"] == "test-error-id"
    assert call_args["data"]["severity"] == "high"


@pytest.mark.asyncio
async def test_websocket_service_broadcast_system_status_change():
    """Test broadcasting system status changes"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    await service.broadcast_system_status_change(
        status="paused",
        message="System paused by user",
        details={"user": "admin", "reason": "maintenance"}
    )
    
    assert mock_manager.broadcast_to_channel.call_count == 2
    
    calls = mock_manager.broadcast_to_channel.call_args_list
    
    # Should broadcast to dashboard and system channels
    channels = [call[0][1] for call in calls]
    assert "dashboard" in channels
    assert "system" in channels
    
    message = calls[0][0][0]
    assert message["type"] == "system_status_change"
    assert message["data"]["status"] == "paused"
    assert message["data"]["message"] == "System paused by user"


@pytest.mark.asyncio
async def test_websocket_service_broadcast_automation_control():
    """Test broadcasting automation control actions"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    mock_manager = AsyncMock()
    service.initialize(mock_manager)
    
    await service.broadcast_automation_control(
        action="pause",
        details={"reason": "rate_limit_reached", "duration": "30_minutes"}
    )
    
    # Automation control should broadcast to all channels
    mock_manager.broadcast_to_all.assert_called_once()
    
    call_args = mock_manager.broadcast_to_all.call_args[0][0]
    assert call_args["type"] == "automation_control"
    assert call_args["data"]["action"] == "pause"
    assert call_args["data"]["details"]["reason"] == "rate_limit_reached"


def test_websocket_service_not_initialized():
    """Test that service handles not being initialized gracefully"""
    from api.services.websocket_service import WebSocketService
    
    service = WebSocketService()
    
    # These should not raise exceptions when service is not initialized
    asyncio.run(service.broadcast_job_discovered({}))
    asyncio.run(service.broadcast_proposal_generated({}))
    asyncio.run(service.broadcast_application_submitted({}))
    asyncio.run(service.broadcast_queue_status_update({}))
    asyncio.run(service.broadcast_system_metrics({}))
    asyncio.run(service.broadcast_error_alert({}))
    asyncio.run(service.broadcast_system_status_change("test", "test"))
    asyncio.run(service.broadcast_automation_control("test"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])