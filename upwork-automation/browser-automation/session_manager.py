"""
Session manager for coordinating browser sessions across different automation tasks
"""
from typing import Dict, List, Optional, Any, Callable
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from contextlib import asynccontextmanager

from browserbase_client import BrowserbaseClient, SessionInfo, SessionStatus
from shared.config import BrowserAutomationConfig
from shared.utils import setup_logging

logger = setup_logging("session-manager")


class SessionType(Enum):
    """Types of browser sessions for different automation tasks"""
    JOB_DISCOVERY = "job_discovery"
    PROPOSAL_SUBMISSION = "proposal_submission"
    PROFILE_MANAGEMENT = "profile_management"
    GENERAL = "general"


class SessionManager:
    """High-level session manager for coordinating browser automation tasks"""
    
    def __init__(self, browserbase_client: Optional[BrowserbaseClient] = None):
        self.browserbase_client = browserbase_client or BrowserbaseClient()
        self.session_assignments: Dict[str, SessionType] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.task_queues: Dict[SessionType, asyncio.Queue] = {
            session_type: asyncio.Queue() for session_type in SessionType
        }
        self._assignment_lock = asyncio.Lock()
    
    async def initialize_session_pools(self):
        """Initialize session pools for different task types"""
        logger.info("Initializing session pools...")
        
        # Create dedicated sessions for different task types
        pool_configs = {
            SessionType.JOB_DISCOVERY: {"pool_size": 2, "name": "job_discovery"},
            SessionType.PROPOSAL_SUBMISSION: {"pool_size": 2, "name": "proposal_submission"},
            SessionType.PROFILE_MANAGEMENT: {"pool_size": 1, "name": "profile_management"}
        }
        
        for session_type, config in pool_configs.items():
            try:
                sessions = await self.browserbase_client.create_session_pool(
                    pool_size=config["pool_size"]
                )
                
                # Assign sessions to task types
                for session_id in sessions:
                    await self._assign_session_type(session_id, session_type)
                
                logger.info(f"Created {len(sessions)} sessions for {session_type.value}")
                
            except Exception as e:
                logger.error(f"Failed to create session pool for {session_type.value}: {e}")
    
    async def _assign_session_type(self, session_id: str, session_type: SessionType):
        """Assign a session to a specific task type"""
        async with self._assignment_lock:
            self.session_assignments[session_id] = session_type
            self.session_locks[session_id] = asyncio.Lock()
    
    @asynccontextmanager
    async def get_session_for_task(self, task_type: SessionType, timeout: int = 30):
        """Context manager to get and automatically return a session for a specific task"""
        session_id = None
        try:
            session_id = await self._acquire_session_for_task(task_type, timeout)
            yield session_id
        finally:
            if session_id:
                await self._release_session(session_id)
    
    async def _acquire_session_for_task(self, task_type: SessionType, timeout: int) -> str:
        """Acquire a session for a specific task type"""
        # First, try to get a dedicated session for this task type
        for session_id, assigned_type in self.session_assignments.items():
            if assigned_type == task_type:
                session_lock = self.session_locks.get(session_id)
                if session_lock and not session_lock.locked():
                    try:
                        await asyncio.wait_for(session_lock.acquire(), timeout=1.0)
                        
                        # Check if session is still healthy
                        health = await self.browserbase_client.get_session_health(session_id)
                        if health.get("healthy", False):
                            logger.debug(f"Acquired dedicated session {session_id} for {task_type.value}")
                            return session_id
                        else:
                            # Session is unhealthy, try to refresh it
                            try:
                                new_session_id = await self.browserbase_client.refresh_session(session_id)
                                await self._reassign_session(session_id, new_session_id, task_type)
                                logger.info(f"Refreshed unhealthy session {session_id} -> {new_session_id}")
                                return new_session_id
                            except Exception as e:
                                logger.error(f"Failed to refresh session {session_id}: {e}")
                                session_lock.release()
                                continue
                    except asyncio.TimeoutError:
                        continue
        
        # If no dedicated session available, try to get any available session
        try:
            session_id = await asyncio.wait_for(
                self.browserbase_client.get_or_create_session(task_type.value),
                timeout=timeout
            )
            
            # Assign this session to the task type temporarily
            await self._assign_session_type(session_id, task_type)
            
            # Acquire lock
            session_lock = self.session_locks[session_id]
            await session_lock.acquire()
            
            logger.debug(f"Acquired new/available session {session_id} for {task_type.value}")
            return session_id
            
        except asyncio.TimeoutError:
            raise Exception(f"Timeout waiting for session for task type {task_type.value}")
    
    async def _release_session(self, session_id: str):
        """Release a session back to the pool"""
        session_lock = self.session_locks.get(session_id)
        if session_lock and session_lock.locked():
            session_lock.release()
            
            # Return session to browserbase client pool
            await self.browserbase_client.return_session(session_id)
            
            logger.debug(f"Released session {session_id}")
    
    async def _reassign_session(self, old_session_id: str, new_session_id: str, task_type: SessionType):
        """Reassign a session ID after refresh"""
        async with self._assignment_lock:
            # Remove old session
            self.session_assignments.pop(old_session_id, None)
            old_lock = self.session_locks.pop(old_session_id, None)
            
            # Add new session
            self.session_assignments[new_session_id] = task_type
            self.session_locks[new_session_id] = old_lock or asyncio.Lock()
    
    async def execute_with_session(
        self,
        task_type: SessionType,
        task_func: Callable,
        *args,
        timeout: int = 300,
        **kwargs
    ) -> Any:
        """Execute a task function with an appropriate session"""
        async with self.get_session_for_task(task_type, timeout=30) as session_id:
            try:
                # Add session_id as first argument to task function
                result = await asyncio.wait_for(
                    task_func(session_id, *args, **kwargs),
                    timeout=timeout
                )
                
                # Update session last used time
                session_info = await self.browserbase_client.get_session(session_id)
                if session_info:
                    session_info.last_used = datetime.utcnow()
                
                return result
                
            except Exception as e:
                # Increment error count for session
                session_info = await self.browserbase_client.get_session(session_id)
                if session_info:
                    session_info.error_count += 1
                    if session_info.error_count > 3:
                        session_info.status = SessionStatus.UNHEALTHY
                        logger.warning(f"Session {session_id} marked as unhealthy due to high error count")
                
                logger.error(f"Task execution failed with session {session_id}: {e}")
                raise
    
    async def get_session_stats_by_type(self) -> Dict[str, Any]:
        """Get session statistics grouped by task type"""
        stats = {
            "total_sessions": len(self.session_assignments),
            "by_type": {},
            "pool_stats": self.browserbase_client.get_pool_stats()
        }
        
        # Count sessions by type
        for session_id, session_type in self.session_assignments.items():
            type_name = session_type.value
            if type_name not in stats["by_type"]:
                stats["by_type"][type_name] = {
                    "count": 0,
                    "locked": 0,
                    "healthy": 0,
                    "unhealthy": 0
                }
            
            stats["by_type"][type_name]["count"] += 1
            
            # Check if session is locked
            session_lock = self.session_locks.get(session_id)
            if session_lock and session_lock.locked():
                stats["by_type"][type_name]["locked"] += 1
            
            # Check session health
            try:
                health = await self.browserbase_client.get_session_health(session_id)
                if health.get("healthy", False):
                    stats["by_type"][type_name]["healthy"] += 1
                else:
                    stats["by_type"][type_name]["unhealthy"] += 1
            except Exception:
                stats["by_type"][type_name]["unhealthy"] += 1
        
        return stats
    
    async def cleanup_unhealthy_sessions(self):
        """Clean up unhealthy sessions and replace them"""
        logger.info("Cleaning up unhealthy sessions...")
        
        sessions_to_refresh = []
        
        # Check all assigned sessions
        for session_id, session_type in list(self.session_assignments.items()):
            try:
                health = await self.browserbase_client.get_session_health(session_id)
                if not health.get("healthy", False):
                    sessions_to_refresh.append((session_id, session_type))
            except Exception as e:
                logger.error(f"Error checking health for session {session_id}: {e}")
                sessions_to_refresh.append((session_id, session_type))
        
        # Refresh unhealthy sessions
        for session_id, session_type in sessions_to_refresh:
            try:
                # Only refresh if session is not currently locked
                session_lock = self.session_locks.get(session_id)
                if session_lock and not session_lock.locked():
                    new_session_id = await self.browserbase_client.refresh_session(session_id)
                    await self._reassign_session(session_id, new_session_id, session_type)
                    logger.info(f"Refreshed unhealthy session {session_id} -> {new_session_id}")
            except Exception as e:
                logger.error(f"Failed to refresh session {session_id}: {e}")
        
        if sessions_to_refresh:
            logger.info(f"Processed {len(sessions_to_refresh)} unhealthy sessions")
    
    async def ensure_minimum_sessions(self):
        """Ensure minimum number of sessions are available for each task type"""
        min_sessions_per_type = {
            SessionType.JOB_DISCOVERY: 1,
            SessionType.PROPOSAL_SUBMISSION: 1,
            SessionType.PROFILE_MANAGEMENT: 1
        }
        
        for session_type, min_count in min_sessions_per_type.items():
            current_count = sum(
                1 for assigned_type in self.session_assignments.values()
                if assigned_type == session_type
            )
            
            if current_count < min_count:
                sessions_needed = min_count - current_count
                logger.info(f"Creating {sessions_needed} additional sessions for {session_type.value}")
                
                for i in range(sessions_needed):
                    try:
                        session_id = await self.browserbase_client.create_session({
                            "name": f"{session_type.value}_session_{i}"
                        })
                        await self._assign_session_type(session_id, session_type)
                    except Exception as e:
                        logger.error(f"Failed to create additional session for {session_type.value}: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the session manager"""
        logger.info("Shutting down session manager...")
        
        # Release all locked sessions
        for session_id, session_lock in self.session_locks.items():
            if session_lock.locked():
                session_lock.release()
        
        # Shutdown browserbase client
        await self.browserbase_client.shutdown()
        
        logger.info("Session manager shutdown complete")


# Convenience functions for common session operations
async def with_job_discovery_session(task_func: Callable, *args, **kwargs):
    """Execute a task with a job discovery session"""
    session_manager = SessionManager()
    return await session_manager.execute_with_session(
        SessionType.JOB_DISCOVERY, task_func, *args, **kwargs
    )


async def with_proposal_submission_session(task_func: Callable, *args, **kwargs):
    """Execute a task with a proposal submission session"""
    session_manager = SessionManager()
    return await session_manager.execute_with_session(
        SessionType.PROPOSAL_SUBMISSION, task_func, *args, **kwargs
    )


async def with_profile_management_session(task_func: Callable, *args, **kwargs):
    """Execute a task with a profile management session"""
    session_manager = SessionManager()
    return await session_manager.execute_with_session(
        SessionType.PROFILE_MANAGEMENT, task_func, *args, **kwargs
    )