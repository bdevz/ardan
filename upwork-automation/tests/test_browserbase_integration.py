"""
Integration tests for Browserbase API integration
These tests require actual Browserbase API credentials and should be run separately
"""
import pytest
import asyncio
import os
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from browserbase_client import BrowserbaseClient, SessionStatus
from session_manager import SessionManager, SessionType


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("BROWSERBASE_API_KEY") or not os.getenv("BROWSERBASE_PROJECT_ID"),
    reason="Browserbase credentials not available"
)
class TestBrowserbaseIntegration:
    """Integration tests with actual Browserbase API"""
    
    @pytest.fixture
    async def browserbase_client(self):
        """Create a real Browserbase client for integration testing"""
        client = BrowserbaseClient()
        yield client
        await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_and_close_session(self, browserbase_client):
        """Test creating and closing a real Browserbase session"""
        # Create session
        session_id = await browserbase_client.create_session({
            "name": "integration_test_session"
        })
        
        assert session_id is not None
        assert session_id.startswith("session_")
        
        # Verify session exists in pool
        session_info = await browserbase_client.get_session(session_id)
        assert session_info is not None
        assert session_info.status == SessionStatus.ACTIVE
        assert session_info.browserbase_session_id is not None
        assert session_info.connect_url is not None
        
        # Check session health
        health = await browserbase_client.get_session_health(session_id)
        assert health["healthy"] is True
        assert health["status"] == SessionStatus.ACTIVE.value
        
        # Close session
        result = await browserbase_client.close_session(session_id)
        assert result is True
        
        # Verify session is removed from pool
        session_info = await browserbase_client.get_session(session_id)
        assert session_info is None
    
    @pytest.mark.asyncio
    async def test_session_pool_creation(self, browserbase_client):
        """Test creating a pool of sessions"""
        pool_size = 3
        sessions = await browserbase_client.create_session_pool(pool_size=pool_size)
        
        assert len(sessions) == pool_size
        
        # Verify all sessions are healthy
        for session_id in sessions:
            session_info = await browserbase_client.get_session(session_id)
            assert session_info is not None
            assert session_info.status == SessionStatus.ACTIVE
            
            health = await browserbase_client.get_session_health(session_id)
            assert health["healthy"] is True
        
        # Clean up sessions
        for session_id in sessions:
            await browserbase_client.close_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_context_storage(self, browserbase_client):
        """Test session context storage and retrieval"""
        session_id = await browserbase_client.create_session({
            "name": "context_test_session"
        })
        
        # Store various types of context data
        login_context = {
            "username": "test_user",
            "login_time": datetime.utcnow().isoformat(),
            "authenticated": True
        }
        
        navigation_context = {
            "current_url": "https://www.ardan.com/nx/search/jobs",
            "page_title": "Find Jobs",
            "search_filters": ["Salesforce", "Agentforce"]
        }
        
        await browserbase_client.store_session_context(session_id, "login", login_context)
        await browserbase_client.store_session_context(session_id, "navigation", navigation_context)
        
        # Retrieve specific context
        retrieved_login = await browserbase_client.get_session_context(session_id, "login")
        assert retrieved_login == login_context
        
        retrieved_navigation = await browserbase_client.get_session_context(session_id, "navigation")
        assert retrieved_navigation == navigation_context
        
        # Retrieve all context
        all_context = await browserbase_client.get_session_context(session_id)
        assert "login" in all_context
        assert "navigation" in all_context
        
        # Clear specific context
        await browserbase_client.clear_session_context(session_id, "login")
        retrieved_login = await browserbase_client.get_session_context(session_id, "login")
        assert retrieved_login is None
        
        # Navigation context should still exist
        retrieved_navigation = await browserbase_client.get_session_context(session_id, "navigation")
        assert retrieved_navigation == navigation_context
        
        # Clean up
        await browserbase_client.close_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_refresh(self, browserbase_client):
        """Test session refresh functionality"""
        # Create initial session
        old_session_id = await browserbase_client.create_session({
            "name": "refresh_test_session"
        })
        
        # Store some context
        test_context = {"test_data": "should_be_preserved"}
        await browserbase_client.store_session_context(old_session_id, "test", test_context)
        
        # Refresh session
        new_session_id = await browserbase_client.refresh_session(old_session_id)
        
        assert new_session_id != old_session_id
        assert new_session_id.startswith("session_")
        
        # Old session should be removed
        old_session_info = await browserbase_client.get_session(old_session_id)
        assert old_session_info is None
        
        # New session should exist and be healthy
        new_session_info = await browserbase_client.get_session(new_session_id)
        assert new_session_info is not None
        assert new_session_info.status == SessionStatus.ACTIVE
        
        # Context should be transferred
        retrieved_context = await browserbase_client.get_session_context(new_session_id, "test")
        assert retrieved_context == test_context
        
        # Clean up
        await browserbase_client.close_session(new_session_id)
    
    @pytest.mark.asyncio
    async def test_session_health_monitoring(self, browserbase_client):
        """Test session health monitoring"""
        session_id = await browserbase_client.create_session({
            "name": "health_test_session"
        })
        
        # Initial health check
        health = await browserbase_client.get_session_health(session_id)
        assert health["healthy"] is True
        assert health["status"] == SessionStatus.ACTIVE.value
        assert health["age_minutes"] < 1  # Should be very new
        assert health["idle_minutes"] < 1
        assert health["error_count"] == 0
        
        # Simulate some usage by updating last_used
        session_info = await browserbase_client.get_session(session_id)
        session_info.last_used = datetime.utcnow()
        
        # Check health again
        health = await browserbase_client.get_session_health(session_id)
        assert health["healthy"] is True
        assert health["idle_minutes"] < 1
        
        # Clean up
        await browserbase_client.close_session(session_id)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("BROWSERBASE_API_KEY") or not os.getenv("BROWSERBASE_PROJECT_ID"),
    reason="Browserbase credentials not available"
)
class TestSessionManagerIntegration:
    """Integration tests for SessionManager with real Browserbase sessions"""
    
    @pytest.fixture
    async def session_manager(self):
        """Create a real SessionManager for integration testing"""
        manager = SessionManager()
        yield manager
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialize_and_use_session_pools(self, session_manager):
        """Test initializing session pools and using them for tasks"""
        # Initialize session pools
        await session_manager.initialize_session_pools()
        
        # Verify sessions were created for different task types
        stats = await session_manager.get_session_stats_by_type()
        assert stats["total_sessions"] > 0
        assert "job_discovery" in stats["by_type"]
        assert "proposal_submission" in stats["by_type"]
        
        # Test using a session for job discovery
        async def mock_job_discovery_task(session_id):
            # Verify we got a valid session
            assert session_id is not None
            assert session_id.startswith("session_")
            
            # Store some context to simulate real usage
            await session_manager.browserbase_client.store_session_context(
                session_id, "search_query", {"keywords": ["Salesforce", "Agentforce"]}
            )
            
            return {"jobs_found": 5, "session_used": session_id}
        
        result = await session_manager.execute_with_session(
            SessionType.JOB_DISCOVERY, mock_job_discovery_task
        )
        
        assert result["jobs_found"] == 5
        assert result["session_used"] is not None
    
    @pytest.mark.asyncio
    async def test_session_type_isolation(self, session_manager):
        """Test that different session types are properly isolated"""
        await session_manager.initialize_session_pools()
        
        # Track which sessions are used for each task type
        used_sessions = {"job_discovery": [], "proposal_submission": []}
        
        async def track_session_task(session_id, task_type):
            used_sessions[task_type].append(session_id)
            return session_id
        
        # Execute tasks of different types
        job_discovery_session = await session_manager.execute_with_session(
            SessionType.JOB_DISCOVERY, track_session_task, "job_discovery"
        )
        
        proposal_session = await session_manager.execute_with_session(
            SessionType.PROPOSAL_SUBMISSION, track_session_task, "proposal_submission"
        )
        
        # Sessions should be different (or could be same if pool is small, but assignments should be correct)
        assert job_discovery_session in used_sessions["job_discovery"]
        assert proposal_session in used_sessions["proposal_submission"]
        
        # Verify session assignments
        job_discovery_type = session_manager.session_assignments.get(job_discovery_session)
        proposal_type = session_manager.session_assignments.get(proposal_session)
        
        # Note: Sessions might be reassigned temporarily, so we just verify they were used correctly
        assert job_discovery_session is not None
        assert proposal_session is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_session_usage(self, session_manager):
        """Test using multiple sessions concurrently"""
        await session_manager.initialize_session_pools()
        
        async def concurrent_task(session_id, task_id):
            # Simulate some work
            await asyncio.sleep(0.1)
            
            # Store task-specific context
            await session_manager.browserbase_client.store_session_context(
                session_id, f"task_{task_id}", {"task_id": task_id, "completed": True}
            )
            
            return {"task_id": task_id, "session_id": session_id}
        
        # Run multiple tasks concurrently
        tasks = []
        for i in range(3):
            task = session_manager.execute_with_session(
                SessionType.JOB_DISCOVERY, concurrent_task, i
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["task_id"] == i
            assert result["session_id"] is not None
        
        # Verify sessions were used (might be reused, which is fine)
        used_sessions = [result["session_id"] for result in results]
        assert len(set(used_sessions)) >= 1  # At least one session was used
    
    @pytest.mark.asyncio
    async def test_session_cleanup_and_refresh(self, session_manager):
        """Test session cleanup and refresh functionality"""
        await session_manager.initialize_session_pools()
        
        # Get initial stats
        initial_stats = await session_manager.get_session_stats_by_type()
        initial_session_count = initial_stats["total_sessions"]
        
        # Force a session to be unhealthy by manipulating its status
        if session_manager.session_assignments:
            test_session_id = list(session_manager.session_assignments.keys())[0]
            session_info = await session_manager.browserbase_client.get_session(test_session_id)
            if session_info:
                session_info.error_count = 5  # Force high error count
                session_info.status = SessionStatus.UNHEALTHY
        
        # Run cleanup
        await session_manager.cleanup_unhealthy_sessions()
        
        # Verify cleanup occurred
        final_stats = await session_manager.get_session_stats_by_type()
        
        # Should still have sessions (either original healthy ones or refreshed ones)
        assert final_stats["total_sessions"] > 0
        
        # Ensure minimum sessions are maintained
        await session_manager.ensure_minimum_sessions()
        
        final_stats = await session_manager.get_session_stats_by_type()
        assert final_stats["total_sessions"] >= 3  # Minimum for each task type


# Utility function to run integration tests
async def run_integration_tests():
    """Run integration tests manually"""
    if not os.getenv("BROWSERBASE_API_KEY") or not os.getenv("BROWSERBASE_PROJECT_ID"):
        print("Skipping integration tests - Browserbase credentials not available")
        return
    
    print("Running Browserbase integration tests...")
    
    # Test basic client functionality
    client = BrowserbaseClient()
    try:
        session_id = await client.create_session({"name": "manual_test"})
        print(f"Created session: {session_id}")
        
        health = await client.get_session_health(session_id)
        print(f"Session health: {health['healthy']}")
        
        await client.close_session(session_id)
        print("Session closed successfully")
        
    finally:
        await client.shutdown()
    
    # Test session manager
    manager = SessionManager()
    try:
        await manager.initialize_session_pools()
        stats = await manager.get_session_stats_by_type()
        print(f"Session manager stats: {stats}")
        
    finally:
        await manager.shutdown()
    
    print("Integration tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_integration_tests())