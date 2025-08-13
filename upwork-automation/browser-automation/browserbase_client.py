"""
Browserbase client for managing browser sessions with advanced session management
"""
from typing import Dict, List, Optional, Any
import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from shared.config import settings, BrowserAutomationConfig
from shared.utils import setup_logging, retry_async

logger = setup_logging("browserbase-client")


class SessionStatus(Enum):
    """Browser session status enumeration"""
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    UNHEALTHY = "unhealthy"
    EXPIRED = "expired"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class SessionConfig:
    """Configuration for browser session creation"""
    project_id: str
    proxies: bool = True
    stealth: bool = True
    keep_alive: bool = True
    timeout: int = 1800  # 30 minutes
    viewport: Dict[str, int] = None
    user_agent: str = None
    name: str = None
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}


@dataclass
class SessionInfo:
    """Information about a browser session"""
    id: str
    config: SessionConfig
    created_at: datetime
    last_used: datetime
    last_health_check: datetime
    status: SessionStatus
    context_data: Dict[str, Any]
    error_count: int = 0
    browserbase_session_id: str = None
    connect_url: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session info to dictionary"""
        return {
            "id": self.id,
            "config": asdict(self.config),
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "last_health_check": self.last_health_check.isoformat(),
            "status": self.status.value,
            "context_data": self.context_data,
            "error_count": self.error_count,
            "browserbase_session_id": self.browserbase_session_id,
            "connect_url": self.connect_url
        }


class SessionPool:
    """Manages a pool of browser sessions"""
    
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.sessions: Dict[str, SessionInfo] = {}
        self.available_sessions: List[str] = []
        self.in_use_sessions: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get_available_session(self) -> Optional[str]:
        """Get an available session from the pool"""
        async with self._lock:
            if self.available_sessions:
                session_id = self.available_sessions.pop(0)
                self.in_use_sessions.append(session_id)
                return session_id
            return None
    
    async def return_session(self, session_id: str):
        """Return a session to the available pool"""
        async with self._lock:
            if session_id in self.in_use_sessions:
                self.in_use_sessions.remove(session_id)
                if session_id in self.sessions and self.sessions[session_id].status == SessionStatus.ACTIVE:
                    self.available_sessions.append(session_id)
    
    async def add_session(self, session_info: SessionInfo):
        """Add a new session to the pool"""
        async with self._lock:
            self.sessions[session_info.id] = session_info
            if session_info.status == SessionStatus.ACTIVE:
                self.available_sessions.append(session_info.id)
    
    async def remove_session(self, session_id: str):
        """Remove a session from the pool"""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.available_sessions:
                self.available_sessions.remove(session_id)
            if session_id in self.in_use_sessions:
                self.in_use_sessions.remove(session_id)
    
    def get_pool_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            "total_sessions": len(self.sessions),
            "available_sessions": len(self.available_sessions),
            "in_use_sessions": len(self.in_use_sessions),
            "max_size": self.max_size
        }


class BrowserbaseClient:
    """Enhanced Browserbase client with session pool management and health monitoring"""
    
    def __init__(self):
        self.api_key = settings.browserbase_api_key
        self.project_id = settings.browserbase_project_id
        self.base_url = "https://api.browserbase.com/v1"
        self.session_pool = SessionPool(max_size=BrowserAutomationConfig.SESSION_POOL_SIZE)
        self.context_storage: Dict[str, Dict[str, Any]] = {}
        self._health_check_task = None
        self._cleanup_task = None
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for health monitoring and cleanup"""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _health_monitor_loop(self):
        """Background task for monitoring session health"""
        while True:
            try:
                await self.check_all_sessions_health()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Background task for cleaning up expired sessions"""
        while True:
            try:
                await self.cleanup_expired_sessions()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)
    
    @retry_async(max_retries=3, delay=1.0)
    async def create_session(self, config: Optional[Dict] = None) -> str:
        """Create a new browser session with Browserbase API"""
        session_config = SessionConfig(
            project_id=self.project_id,
            proxies=True,
            stealth=True,
            keep_alive=True,
            timeout=BrowserAutomationConfig.SESSION_TIMEOUT_MINUTES * 60,
            **(config or {})
        )
        
        session_id = f"session_{datetime.utcnow().timestamp()}"
        now = datetime.utcnow()
        
        # Create session info
        session_info = SessionInfo(
            id=session_id,
            config=session_config,
            created_at=now,
            last_used=now,
            last_health_check=now,
            status=SessionStatus.CREATING,
            context_data={}
        )
        
        try:
            # Make actual Browserbase API call
            browserbase_session = await self._create_browserbase_session(session_config)
            session_info.browserbase_session_id = browserbase_session["id"]
            session_info.connect_url = browserbase_session["connectUrl"]
            session_info.status = SessionStatus.ACTIVE
            
            # Add to session pool
            await self.session_pool.add_session(session_info)
            
            logger.info(f"Created browser session: {session_id} (Browserbase ID: {browserbase_session['id']})")
            return session_id
            
        except Exception as e:
            session_info.status = SessionStatus.ERROR
            logger.error(f"Failed to create browser session: {e}")
            raise
    
    async def _create_browserbase_session(self, config: SessionConfig) -> Dict[str, Any]:
        """Create session using Browserbase API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "projectId": config.project_id,
            "proxies": config.proxies,
            "stealth": config.stealth,
            "keepAlive": config.keep_alive,
            "timeout": config.timeout,
            "viewport": config.viewport
        }
        
        if config.user_agent:
            payload["userAgent"] = config.user_agent
        if config.name:
            payload["name"] = config.name
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/sessions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Browserbase API error: {response.status} - {error_text}")
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        return self.session_pool.sessions.get(session_id)
    
    async def get_or_create_session(self, session_type: str = "default") -> str:
        """Get an available session from pool or create a new one"""
        # Try to get available session from pool
        session_id = await self.session_pool.get_available_session()
        
        if session_id:
            # Update last used time
            session_info = self.session_pool.sessions[session_id]
            session_info.last_used = datetime.utcnow()
            logger.info(f"Reusing session from pool: {session_id}")
            return session_id
        
        # Create new session if pool is not full
        if len(self.session_pool.sessions) < self.session_pool.max_size:
            return await self.create_session({"name": f"{session_type}_session"})
        
        # Wait for available session if pool is full
        logger.warning("Session pool is full, waiting for available session")
        for _ in range(30):  # Wait up to 30 seconds
            await asyncio.sleep(1)
            session_id = await self.session_pool.get_available_session()
            if session_id:
                session_info = self.session_pool.sessions[session_id]
                session_info.last_used = datetime.utcnow()
                return session_id
        
        raise Exception("No available sessions and pool is full")
    
    async def return_session(self, session_id: str):
        """Return a session to the pool"""
        await self.session_pool.return_session(session_id)
        logger.debug(f"Returned session to pool: {session_id}")
    
    @retry_async(max_retries=2, delay=2.0)
    async def close_session(self, session_id: str) -> bool:
        """Close a browser session"""
        session_info = self.session_pool.sessions.get(session_id)
        if not session_info:
            return False
        
        try:
            # Close session via Browserbase API
            if session_info.browserbase_session_id:
                await self._close_browserbase_session(session_info.browserbase_session_id)
            
            # Update status and remove from pool
            session_info.status = SessionStatus.CLOSED
            await self.session_pool.remove_session(session_id)
            
            # Clean up context storage
            if session_id in self.context_storage:
                del self.context_storage[session_id]
            
            logger.info(f"Closed browser session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
            return False
    
    async def _close_browserbase_session(self, browserbase_session_id: str):
        """Close session using Browserbase API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.base_url}/sessions/{browserbase_session_id}",
                headers=headers
            ) as response:
                if response.status not in [200, 204, 404]:
                    error_text = await response.text()
                    raise Exception(f"Failed to close Browserbase session: {response.status} - {error_text}")
    
    async def create_session_pool(self, pool_size: int = 5) -> List[str]:
        """Create multiple browser sessions for parallel processing"""
        sessions = []
        tasks = []
        
        for i in range(pool_size):
            task = self.create_session({"name": f"pool_session_{i}"})
            tasks.append(task)
        
        # Create sessions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to create session in pool: {result}")
            else:
                sessions.append(result)
        
        logger.info(f"Created session pool with {len(sessions)}/{pool_size} sessions")
        return sessions
    
    async def get_session_health(self, session_id: str) -> Dict[str, Any]:
        """Check detailed session health status"""
        session_info = self.session_pool.sessions.get(session_id)
        if not session_info:
            return {"status": "not_found", "healthy": False}
        
        now = datetime.utcnow()
        age_minutes = (now - session_info.created_at).total_seconds() / 60
        idle_minutes = (now - session_info.last_used).total_seconds() / 60
        
        # Determine health status
        healthy = True
        health_issues = []
        
        if session_info.status != SessionStatus.ACTIVE:
            healthy = False
            health_issues.append(f"Session status is {session_info.status.value}")
        
        if age_minutes > BrowserAutomationConfig.SESSION_TIMEOUT_MINUTES:
            healthy = False
            health_issues.append("Session has expired")
        
        if session_info.error_count > 3:
            healthy = False
            health_issues.append(f"High error count: {session_info.error_count}")
        
        # Try to ping the session via Browserbase API
        try:
            if session_info.browserbase_session_id:
                browserbase_health = await self._check_browserbase_session_health(
                    session_info.browserbase_session_id
                )
                if not browserbase_health.get("healthy", False):
                    healthy = False
                    health_issues.append("Browserbase session is unhealthy")
        except Exception as e:
            healthy = False
            health_issues.append(f"Failed to check Browserbase health: {str(e)}")
        
        # Update session health check time
        session_info.last_health_check = now
        if not healthy and session_info.status == SessionStatus.ACTIVE:
            session_info.status = SessionStatus.UNHEALTHY
        
        return {
            "session_id": session_id,
            "status": session_info.status.value,
            "healthy": healthy,
            "age_minutes": age_minutes,
            "idle_minutes": idle_minutes,
            "error_count": session_info.error_count,
            "health_issues": health_issues,
            "last_health_check": session_info.last_health_check.isoformat(),
            "browserbase_session_id": session_info.browserbase_session_id
        }
    
    async def _check_browserbase_session_health(self, browserbase_session_id: str) -> Dict[str, Any]:
        """Check session health via Browserbase API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/sessions/{browserbase_session_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "healthy": data.get("status") == "RUNNING",
                        "browserbase_status": data.get("status"),
                        "details": data
                    }
                else:
                    return {"healthy": False, "error": f"HTTP {response.status}"}
    
    async def check_all_sessions_health(self):
        """Check health of all active sessions"""
        session_ids = list(self.session_pool.sessions.keys())
        health_tasks = [self.get_session_health(sid) for sid in session_ids]
        
        if health_tasks:
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            unhealthy_count = 0
            for result in health_results:
                if isinstance(result, dict) and not result.get("healthy", False):
                    unhealthy_count += 1
            
            if unhealthy_count > 0:
                logger.warning(f"Found {unhealthy_count} unhealthy sessions out of {len(session_ids)}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired and unhealthy sessions"""
        now = datetime.utcnow()
        sessions_to_cleanup = []
        
        for session_id, session_info in self.session_pool.sessions.items():
            age = now - session_info.created_at
            idle_time = now - session_info.last_used
            
            should_cleanup = (
                session_info.status in [SessionStatus.EXPIRED, SessionStatus.ERROR, SessionStatus.UNHEALTHY] or
                age > timedelta(minutes=BrowserAutomationConfig.SESSION_TIMEOUT_MINUTES) or
                (idle_time > timedelta(minutes=30) and session_info.status == SessionStatus.IDLE)
            )
            
            if should_cleanup:
                sessions_to_cleanup.append(session_id)
        
        # Cleanup sessions
        cleanup_tasks = [self.close_session(sid) for sid in sessions_to_cleanup]
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            logger.info(f"Cleaned up {len(sessions_to_cleanup)} expired/unhealthy sessions")
    
    async def refresh_session(self, session_id: str) -> str:
        """Refresh an expired or unhealthy session"""
        old_session = self.session_pool.sessions.get(session_id)
        if not old_session:
            raise ValueError(f"Session {session_id} not found")
        
        # Close old session
        await self.close_session(session_id)
        
        # Create new session with same config
        new_session_id = await self.create_session(asdict(old_session.config))
        
        # Transfer context data
        if session_id in self.context_storage:
            self.context_storage[new_session_id] = self.context_storage[session_id]
            del self.context_storage[session_id]
        
        logger.info(f"Refreshed session {session_id} -> {new_session_id}")
        return new_session_id
    
    # Context storage methods
    async def store_session_context(self, session_id: str, context_key: str, context_data: Any):
        """Store context data for a session"""
        if session_id not in self.context_storage:
            self.context_storage[session_id] = {}
        
        self.context_storage[session_id][context_key] = {
            "data": context_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update session info
        session_info = self.session_pool.sessions.get(session_id)
        if session_info:
            session_info.context_data[context_key] = context_data
    
    async def get_session_context(self, session_id: str, context_key: str = None) -> Any:
        """Retrieve context data for a session"""
        if session_id not in self.context_storage:
            return None
        
        if context_key:
            context_item = self.context_storage[session_id].get(context_key)
            return context_item["data"] if context_item else None
        
        return self.context_storage[session_id]
    
    async def clear_session_context(self, session_id: str, context_key: str = None):
        """Clear context data for a session"""
        if session_id not in self.context_storage:
            return
        
        if context_key:
            self.context_storage[session_id].pop(context_key, None)
        else:
            self.context_storage[session_id] = {}
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics"""
        stats = self.session_pool.get_pool_stats()
        
        # Add status breakdown
        status_counts = {}
        for session_info in self.session_pool.sessions.values():
            status = session_info.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats["status_breakdown"] = status_counts
        stats["context_storage_size"] = len(self.context_storage)
        
        return stats
    
    async def shutdown(self):
        """Gracefully shutdown the client and cleanup resources"""
        logger.info("Shutting down Browserbase client...")
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close all sessions
        session_ids = list(self.session_pool.sessions.keys())
        close_tasks = [self.close_session(sid) for sid in session_ids]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        logger.info("Browserbase client shutdown complete")