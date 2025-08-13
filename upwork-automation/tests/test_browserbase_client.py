"""
Unit tests for Browserbase client and session management
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Replace hyphens with underscores for Python imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from browserbase_client import (
    BrowserbaseClient, SessionInfo, SessionConfig, SessionStatus, SessionPool
)
from session_manager import SessionManager, SessionType


class TestSessionConfig:
    """Test SessionConfig dataclass"""
    
    def test_session_config_defaults(self):
        config = SessionConfig(project_id="test-project")
        assert config.project_id == "test-project"
        assert config.proxies is True
        assert config.stealth is True
        assert config.keep_alive is True
        assert config.timeout == 1800
        assert config.viewport == {"width": 1920, "height": 1080}
    
    def test_session_config_custom_values(self):
        config = SessionConfig(
            project_id="test-project",
            proxies=False,
            stealth=False,
            timeout=3600,
            viewport={"width": 1280, "height": 720}
        )
        assert config.proxies is False
        assert config.stealth is False
        assert config.timeout == 3600
        assert config.viewport == {"width": 1280, "height": 720}


class TestSessionPool:
    """Test SessionPool class"""
    
    @pytest.fixture
    def session_pool(self):
        return SessionPool(max_size=3)
    
    @pytest.fixture
    def sample_session_info(self):
        config = SessionConfig(project_id="test-project")
        return SessionInfo(
            id="test-session-1",
            config=config,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            last_health_check=datetime.utcnow(),
            status=SessionStatus.ACTIVE,
            context_data={}
        )
    
    @pytest.mark.asyncio
    async def test_add_and_get_session(self, session_pool, sample_session_info):
        await session_pool.add_session(sample_session_info)
        
        assert len(session_pool.sessions) == 1
        assert len(session_pool.available_sessions) == 1
        assert sample_session_info.id in session_pool.sessions
    
    @pytest.mark.asyncio
    async def test_get_available_session(self, session_pool, sample_session_info):
        await session_pool.add_session(sample_session_info)
        
        session_id = await session_pool.get_available_session()
        assert session_id == sample_session_info.id
        assert len(session_pool.available_sessions) == 0
        assert len(session_pool.in_use_sessions) == 1
    
    @pytest.mark.asyncio
    async def test_return_session(self, session_pool, sample_session_info):
        await session_pool.add_session(sample_session_info)
        session_id = await session_pool.get_available_session()
        
        await session_pool.return_session(session_id)
        assert len(session_pool.available_sessions) == 1
        assert len(session_pool.in_use_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_remove_session(self, session_pool, sample_session_info):
        await session_pool.add_session(sample_session_info)
        
        await session_pool.remove_session(sample_session_info.id)
        assert len(session_pool.sessions) == 0
        assert len(session_pool.available_sessions) == 0
    
    def test_get_pool_stats(self, session_pool):
        stats = session_pool.get_pool_stats()
        assert stats["total_sessions"] == 0
        assert stats["available_sessions"] == 0
        assert stats["in_use_sessions"] == 0
        assert stats["max_size"] == 3


class TestBrowserbaseClient:
    """Test BrowserbaseClient class"""
    
    @pytest.fixture
    def mock_settings(self):
        with patch('browserbase_client.settings') as mock:
            mock.browserbase_api_key = "test-api-key"
            mock.browserbase_project_id = "test-project-id"
            yield mock
    
    @pytest.fixture
    def browserbase_client(self, mock_settings):
        with patch.object(BrowserbaseClient, '_start_background_tasks'):
            return BrowserbaseClient()
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, browserbase_client):
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response) as mock_create:
            session_id = await browserbase_client.create_session()
            
            assert session_id.startswith("session_")
            assert session_id in browserbase_client.session_pool.sessions
            
            session_info = browserbase_client.session_pool.sessions[session_id]
            assert session_info.status == SessionStatus.ACTIVE
            assert session_info.browserbase_session_id == "browserbase-session-123"
            assert session_info.connect_url == "wss://connect.browserbase.com/session-123"
            
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_session_with_config(self, browserbase_client):
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        custom_config = {"name": "test-session", "timeout": 3600}
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            session_id = await browserbase_client.create_session(custom_config)
            
            session_info = browserbase_client.session_pool.sessions[session_id]
            assert session_info.config.name == "test-session"
            assert session_info.config.timeout == 3600
    
    @pytest.mark.asyncio
    async def test_create_session_api_failure(self, browserbase_client):
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await browserbase_client.create_session()
    
    @pytest.mark.asyncio
    async def test_get_session(self, browserbase_client):
        # Create a session first
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            session_id = await browserbase_client.create_session()
            
            # Test getting the session
            session_info = await browserbase_client.get_session(session_id)
            assert session_info is not None
            assert session_info.id == session_id
            assert session_info.status == SessionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, browserbase_client):
        session_info = await browserbase_client.get_session("non-existent-session")
        assert session_info is None
    
    @pytest.mark.asyncio
    async def test_close_session(self, browserbase_client):
        # Create a session first
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            with patch.object(browserbase_client, '_close_browserbase_session') as mock_close:
                session_id = await browserbase_client.create_session()
                
                # Close the session
                result = await browserbase_client.close_session(session_id)
                
                assert result is True
                assert session_id not in browserbase_client.session_pool.sessions
                assert session_id not in browserbase_client.context_storage
                mock_close.assert_called_once_with("browserbase-session-123")
    
    @pytest.mark.asyncio
    async def test_create_session_pool(self, browserbase_client):
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            sessions = await browserbase_client.create_session_pool(pool_size=3)
            
            assert len(sessions) == 3
            assert len(browserbase_client.session_pool.sessions) == 3
            
            for session_id in sessions:
                assert session_id in browserbase_client.session_pool.sessions
    
    @pytest.mark.asyncio
    async def test_get_session_health_healthy(self, browserbase_client):
        # Create a session first
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            with patch.object(browserbase_client, '_check_browserbase_session_health',
                             return_value={"healthy": True, "browserbase_status": "RUNNING"}):
                session_id = await browserbase_client.create_session()
                
                health = await browserbase_client.get_session_health(session_id)
                
                assert health["healthy"] is True
                assert health["status"] == SessionStatus.ACTIVE.value
                assert "age_minutes" in health
                assert "idle_minutes" in health
    
    @pytest.mark.asyncio
    async def test_get_session_health_unhealthy(self, browserbase_client):
        # Create a session first
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            with patch.object(browserbase_client, '_check_browserbase_session_health',
                             return_value={"healthy": False, "error": "Connection failed"}):
                session_id = await browserbase_client.create_session()
                
                health = await browserbase_client.get_session_health(session_id)
                
                assert health["healthy"] is False
                assert len(health["health_issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_refresh_session(self, browserbase_client):
        # Create initial session
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            with patch.object(browserbase_client, '_close_browserbase_session'):
                old_session_id = await browserbase_client.create_session()
                
                # Store some context
                await browserbase_client.store_session_context(
                    old_session_id, "test_key", {"data": "test_value"}
                )
                
                # Refresh session
                new_session_id = await browserbase_client.refresh_session(old_session_id)
                
                assert new_session_id != old_session_id
                assert old_session_id not in browserbase_client.session_pool.sessions
                assert new_session_id in browserbase_client.session_pool.sessions
                
                # Check context was transferred
                context = await browserbase_client.get_session_context(new_session_id, "test_key")
                assert context == {"data": "test_value"}
    
    @pytest.mark.asyncio
    async def test_context_storage(self, browserbase_client):
        # Create a session first
        mock_response = {
            "id": "browserbase-session-123",
            "connectUrl": "wss://connect.browserbase.com/session-123"
        }
        
        with patch.object(browserbase_client, '_create_browserbase_session', 
                         return_value=mock_response):
            session_id = await browserbase_client.create_session()
            
            # Store context
            test_data = {"login_state": "authenticated", "current_page": "job_search"}
            await browserbase_client.store_session_context(session_id, "navigation", test_data)
            
            # Retrieve context
            retrieved_data = await browserbase_client.get_session_context(session_id, "navigation")
            assert retrieved_data == test_data
            
            # Get all context
            all_context = await browserbase_client.get_session_context(session_id)
            assert "navigation" in all_context
            
            # Clear specific context
            await browserbase_client.clear_session_context(session_id, "navigation")
            retrieved_data = await browserbase_client.get_session_context(session_id, "navigation")
            assert retrieved_data is None


class TestSessionManager:
    """Test SessionManager class"""
    
    @pytest.fixture
    def mock_browserbase_client(self):
        client = Mock(spec=BrowserbaseClient)
        client.create_session_pool = AsyncMock(return_value=["session1", "session2"])
        client.get_or_create_session = AsyncMock(return_value="new_session")
        client.return_session = AsyncMock()
        client.get_session_health = AsyncMock(return_value={"healthy": True})
        client.get_session = AsyncMock()
        client.refresh_session = AsyncMock(return_value="refreshed_session")
        return client
    
    @pytest.fixture
    def session_manager(self, mock_browserbase_client):
        return SessionManager(browserbase_client=mock_browserbase_client)
    
    @pytest.mark.asyncio
    async def test_initialize_session_pools(self, session_manager, mock_browserbase_client):
        await session_manager.initialize_session_pools()
        
        # Should have created session pools for different task types
        assert len(session_manager.session_assignments) > 0
        assert SessionType.JOB_DISCOVERY in [t for t in session_manager.session_assignments.values()]
        assert SessionType.PROPOSAL_SUBMISSION in [t for t in session_manager.session_assignments.values()]
        
        # Should have called create_session_pool multiple times
        assert mock_browserbase_client.create_session_pool.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_get_session_for_task_context_manager(self, session_manager, mock_browserbase_client):
        # Setup session assignments
        session_manager.session_assignments["session1"] = SessionType.JOB_DISCOVERY
        session_manager.session_locks["session1"] = asyncio.Lock()
        
        mock_browserbase_client.get_session_health.return_value = {"healthy": True}
        
        async with session_manager.get_session_for_task(SessionType.JOB_DISCOVERY) as session_id:
            assert session_id == "session1"
            # Session should be locked during use
            assert session_manager.session_locks["session1"].locked()
        
        # Session should be released after context manager exits
        assert not session_manager.session_locks["session1"].locked()
    
    @pytest.mark.asyncio
    async def test_execute_with_session(self, session_manager, mock_browserbase_client):
        # Setup session assignments
        session_manager.session_assignments["session1"] = SessionType.JOB_DISCOVERY
        session_manager.session_locks["session1"] = asyncio.Lock()
        
        mock_browserbase_client.get_session_health.return_value = {"healthy": True}
        mock_session_info = Mock()
        mock_session_info.last_used = datetime.utcnow()
        mock_session_info.error_count = 0
        mock_browserbase_client.get_session.return_value = mock_session_info
        
        # Define a test task function
        async def test_task(session_id, test_arg):
            assert session_id == "session1"
            assert test_arg == "test_value"
            return "task_result"
        
        result = await session_manager.execute_with_session(
            SessionType.JOB_DISCOVERY, test_task, "test_value"
        )
        
        assert result == "task_result"
        mock_browserbase_client.return_session.assert_called_once_with("session1")
    
    @pytest.mark.asyncio
    async def test_execute_with_session_error_handling(self, session_manager, mock_browserbase_client):
        # Setup session assignments
        session_manager.session_assignments["session1"] = SessionType.JOB_DISCOVERY
        session_manager.session_locks["session1"] = asyncio.Lock()
        
        mock_browserbase_client.get_session_health.return_value = {"healthy": True}
        mock_session_info = Mock()
        mock_session_info.error_count = 0
        mock_browserbase_client.get_session.return_value = mock_session_info
        
        # Define a test task function that raises an error
        async def failing_task(session_id):
            raise Exception("Task failed")
        
        with pytest.raises(Exception, match="Task failed"):
            await session_manager.execute_with_session(
                SessionType.JOB_DISCOVERY, failing_task
            )
        
        # Error count should be incremented
        assert mock_session_info.error_count == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_unhealthy_sessions(self, session_manager, mock_browserbase_client):
        # Setup session assignments with unhealthy session
        session_manager.session_assignments["unhealthy_session"] = SessionType.JOB_DISCOVERY
        session_manager.session_locks["unhealthy_session"] = asyncio.Lock()
        
        mock_browserbase_client.get_session_health.return_value = {"healthy": False}
        mock_browserbase_client.refresh_session.return_value = "new_healthy_session"
        
        await session_manager.cleanup_unhealthy_sessions()
        
        # Should have attempted to refresh the unhealthy session
        mock_browserbase_client.refresh_session.assert_called_once_with("unhealthy_session")
        
        # Session assignments should be updated
        assert "unhealthy_session" not in session_manager.session_assignments
        assert "new_healthy_session" in session_manager.session_assignments
    
    @pytest.mark.asyncio
    async def test_get_session_stats_by_type(self, session_manager, mock_browserbase_client):
        # Setup session assignments
        session_manager.session_assignments["session1"] = SessionType.JOB_DISCOVERY
        session_manager.session_assignments["session2"] = SessionType.PROPOSAL_SUBMISSION
        session_manager.session_locks["session1"] = asyncio.Lock()
        session_manager.session_locks["session2"] = asyncio.Lock()
        
        mock_browserbase_client.get_session_health.return_value = {"healthy": True}
        mock_browserbase_client.get_pool_stats.return_value = {"total_sessions": 2}
        
        stats = await session_manager.get_session_stats_by_type()
        
        assert stats["total_sessions"] == 2
        assert "job_discovery" in stats["by_type"]
        assert "proposal_submission" in stats["by_type"]
        assert stats["by_type"]["job_discovery"]["count"] == 1
        assert stats["by_type"]["proposal_submission"]["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__])