"""
Tests for WebSocket functionality and real-time updates
"""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
import websockets
from unittest.mock import AsyncMock, patch

from api.main import app
from api.routers.websocket import manager
from api.services.websocket_service import websocket_service


class TestWebSocketConnections:
    """Test WebSocket connection management"""
    
    def test_websocket_connection_manager_initialization(self):
        """Test that connection manager initializes correctly"""
        assert manager is not None
        assert "dashboard" in manager.active_connections
        assert "jobs" in manager.active_connections
        assert "queue" in manager.active_connections
        assert "metrics" in manager.active_connections
        assert "system" in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_websocket_dashboard_connection(self):
        """Test WebSocket dashboard connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/api/ws/dashboard?client_id=test_client") as websocket:
            # Test connection establishment
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["channel"] == "dashboard"
            
            # Test ping/pong
            websocket.send_json({"type": "ping"})
            pong_data = websocket.receive_json()
            assert pong_data["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_websocket_jobs_connection(self):
        """Test WebSocket jobs connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/api/ws/jobs?client_id=test_client") as websocket:
            # Test connection establishment
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["channel"] == "jobs"
    
    @pytest.mark.asyncio
    async def test_websocket_queue_connection(self):
        """Test WebSocket queue connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/api/ws/queue?client_id=test_client") as websocket:
            # Test connection establishment
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["channel"] == "queue"
    
    @pytest.mark.asyncio
    async def test_websocket_metrics_connection(self):
        """Test WebSocket metrics connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/api/ws/metrics?client_id=test_client") as websocket:
            # Test connection establishment
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["channel"] == "metrics"
    
    @pytest.mark.asyncio
    async def test_websocket_system_connection(self):
        """Test WebSocket system connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/api/ws/system?client_id=test_client") as websocket:
            # Test connection establishment
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["channel"] == "system"


class TestWebSocketBroadcasting:
    """Test WebSocket message broadcasting"""
    
    @pytest.mark.asyncio
    async def test_broadcast_job_discovered(self):
        """Test broadcasting job discovery messages"""
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1  # WebSocketState.CONNECTED
        
        # Add mock connection to manager
        manager.active_connections["dashboard"].add(mock_websocket)
        manager.active_connections["jobs"].add(mock_websocket)
        
        # Initialize WebSocket service
        websocket_service.initialize(manager)
        
        # Test job discovery broadcast
        job_data = {
            "id": "test-job-id",
            "title": "Test Salesforce Job",
            "budget_max": 5000,
            "hourly_rate": 75,
            "client_rating": 4.8,
            "match_score": 0.95,
            "posted_date": "2024-01-01T12:00:00Z"
        }
        
        await websocket_service.broadcast_job_discovered(job_data)
        
        # Verify message was sent to both channels
        assert mock_websocket.send_text.call_count == 2
        
        # Clean up
        manager.active_connections["dashboard"].clear()
        manager.active_connections["jobs"].clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_proposal_generated(self):
        """Test broadcasting proposal generation messages"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1
        
        manager.active_connections["dashboard"].add(mock_websocket)
        manager.active_connections["jobs"].add(mock_websocket)
        
        websocket_service.initialize(manager)
        
        proposal_data = {
            "id": "test-proposal-id",
            "job_id": "test-job-id",
            "job_title": "Test Job",
            "bid_amount": 75.0,
            "generated_at": "2024-01-01T12:00:00Z"
        }
        
        await websocket_service.broadcast_proposal_generated(proposal_data)
        
        assert mock_websocket.send_text.call_count == 2
        
        manager.active_connections["dashboard"].clear()
        manager.active_connections["jobs"].clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_application_submitted(self):
        """Test broadcasting application submission messages"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1
        
        manager.active_connections["dashboard"].add(mock_websocket)
        manager.active_connections["jobs"].add(mock_websocket)
        
        websocket_service.initialize(manager)
        
        application_data = {
            "id": "test-application-id",
            "job_id": "test-job-id",
            "job_title": "Test Job",
            "proposal_id": "test-proposal-id",
            "submitted_at": "2024-01-01T12:00:00Z",
            "status": "SUBMITTED"
        }
        
        await websocket_service.broadcast_application_submitted(application_data)
        
        assert mock_websocket.send_text.call_count == 2
        
        manager.active_connections["dashboard"].clear()
        manager.active_connections["jobs"].clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_queue_status_update(self):
        """Test broadcasting queue status updates"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1
        
        manager.active_connections["dashboard"].add(mock_websocket)
        manager.active_connections["queue"].add(mock_websocket)
        
        websocket_service.initialize(manager)
        
        queue_data = {
            "total_jobs": 100,
            "pending_jobs": 10,
            "processing_jobs": 5,
            "completed_jobs": 80,
            "failed_jobs": 5,
            "queue_health": "healthy"
        }
        
        await websocket_service.broadcast_queue_status_update(queue_data)
        
        assert mock_websocket.send_text.call_count == 2
        
        manager.active_connections["dashboard"].clear()
        manager.active_connections["queue"].clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_system_metrics(self):
        """Test broadcasting system metrics"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1
        
        manager.active_connections["dashboard"].add(mock_websocket)
        manager.active_connections["metrics"].add(mock_websocket)
        
        websocket_service.initialize(manager)
        
        metrics_data = {
            "applications_today": 15,
            "success_rate": 0.75,
            "avg_response_time": 250,
            "active_sessions": 3,
            "system_health": "healthy",
            "cpu_usage": 45,
            "memory_usage": 60
        }
        
        await websocket_service.broadcast_system_metrics(metrics_data)
        
        assert mock_websocket.send_text.call_count == 2
        
        manager.active_connections["dashboard"].clear()
        manager.active_connections["metrics"].clear()
    
    @pytest.mark.asyncio
    async def test_broadcast_error_alert(self):
        """Test broadcasting error alerts"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 1
        
        # Add to all channels since error alerts go to all
        for channel in manager.active_connections:
            manager.active_connections[channel].add(mock_websocket)
        
        websocket_service.initialize(manager)
        
        error_data = {
            "id": "test-error-id",
            "type": "browser_automation_error",
            "message": "Failed to submit application",
            "severity": "high",
            "component": "application_submission",
            "timestamp": "2024-01-01T12:00:00Z",
            "details": {"job_id": "test-job-id"}
        }
        
        await websocket_service.broadcast_error_alert(error_data)
        
        # Should send to all 5 channels
        assert mock_websocket.send_text.call_count == 5
        
        # Clean up
        for channel in manager.active_connections:
            manager.active_connections[channel].clear()


class TestWebSocketErrorHandling:
    """Test WebSocket error handling and reconnection"""
    
    @pytest.mark.asyncio
    async def test_websocket_disconnection_handling(self):
        """Test proper handling of WebSocket disconnections"""
        mock_websocket = AsyncMock()
        mock_websocket.client_state = 0  # WebSocketState.DISCONNECTED
        
        manager.active_connections["dashboard"].add(mock_websocket)
        websocket_service.initialize(manager)
        
        # Try to broadcast to disconnected socket
        await websocket_service.broadcast_job_discovered({
            "id": "test-job-id",
            "title": "Test Job"
        })
        
        # Should handle disconnection gracefully
        assert mock_websocket not in manager.active_connections["dashboard"]
    
    @pytest.mark.asyncio
    async def test_websocket_connection_stats(self):
        """Test WebSocket connection statistics"""
        # Add mock connections
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        
        await manager.connect(mock_websocket1, "dashboard", "client1")
        await manager.connect(mock_websocket2, "jobs", "client2")
        
        stats = manager.get_connection_stats()
        
        assert stats["total_connections"] >= 2
        assert "dashboard" in stats["channels"]
        assert "jobs" in stats["channels"]
        assert stats["channels"]["dashboard"]["active_connections"] >= 1
        assert stats["channels"]["jobs"]["active_connections"] >= 1
        
        # Clean up
        manager.disconnect(mock_websocket1)
        manager.disconnect(mock_websocket2)


class TestWebSocketIntegration:
    """Test WebSocket integration with services"""
    
    @pytest.mark.asyncio
    async def test_job_service_websocket_integration(self):
        """Test that job service broadcasts WebSocket messages"""
        with patch('api.services.job_service.websocket_service') as mock_ws_service:
            from api.services.job_service import JobService
            
            job_service = JobService()
            
            # Mock database session and job model
            mock_db = AsyncMock()
            mock_job_model = AsyncMock()
            mock_job_model.id = "test-job-id"
            mock_job_model.title = "Test Job"
            mock_job_model.updated_at.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            # Mock database query
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_job_model
            mock_db.execute.return_value = mock_result
            
            # Test job status update
            await job_service.update_job_status(mock_db, "test-job-id", "APPLIED")
            
            # Verify WebSocket broadcast was called
            mock_ws_service.broadcast_job_status_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_proposal_service_websocket_integration(self):
        """Test that proposal service broadcasts WebSocket messages"""
        with patch('api.services.proposal_service.websocket_service') as mock_ws_service:
            # This would test proposal service integration
            # Implementation would depend on the actual proposal service structure
            pass
    
    @pytest.mark.asyncio
    async def test_application_service_websocket_integration(self):
        """Test that application service broadcasts WebSocket messages"""
        with patch('api.services.application_submission_service.websocket_service') as mock_ws_service:
            # This would test application service integration
            # Implementation would depend on the actual application service structure
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])