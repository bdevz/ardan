"""
Basic demo of session management data structures
"""
import asyncio
import sys
import os
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


class SessionStatus(Enum):
    """Browser session status enumeration"""
    CREATING = "creating"
    ACTIVE = "active"
    IDLE = "idle"
    UNHEALTHY = "unhealthy"
    EXPIRED = "expired"
    CLOSED = "closed"
    ERROR = "error"


class SessionType(Enum):
    """Types of browser sessions for different automation tasks"""
    JOB_DISCOVERY = "job_discovery"
    PROPOSAL_SUBMISSION = "proposal_submission"
    PROFILE_MANAGEMENT = "profile_management"
    GENERAL = "general"


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
        self.available_sessions: list = []
        self.in_use_sessions: list = []
    
    async def add_session(self, session_info: SessionInfo):
        """Add a new session to the pool"""
        self.sessions[session_info.id] = session_info
        if session_info.status == SessionStatus.ACTIVE:
            self.available_sessions.append(session_info.id)
    
    async def get_available_session(self) -> Optional[str]:
        """Get an available session from the pool"""
        if self.available_sessions:
            session_id = self.available_sessions.pop(0)
            self.in_use_sessions.append(session_id)
            return session_id
        return None
    
    async def return_session(self, session_id: str):
        """Return a session to the available pool"""
        if session_id in self.in_use_sessions:
            self.in_use_sessions.remove(session_id)
            if session_id in self.sessions and self.sessions[session_id].status == SessionStatus.ACTIVE:
                self.available_sessions.append(session_id)
    
    def get_pool_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            "total_sessions": len(self.sessions),
            "available_sessions": len(self.available_sessions),
            "in_use_sessions": len(self.in_use_sessions),
            "max_size": self.max_size
        }


async def demo_session_config():
    """Demo SessionConfig functionality"""
    print("=== Session Configuration Demo ===")
    
    # Create default config
    config = SessionConfig(project_id="demo-project")
    print(f"✓ Default config created:")
    print(f"  - Project ID: {config.project_id}")
    print(f"  - Stealth mode: {config.stealth}")
    print(f"  - Proxies: {config.proxies}")
    print(f"  - Viewport: {config.viewport}")
    
    # Create custom config
    custom_config = SessionConfig(
        project_id="custom-project",
        stealth=False,
        timeout=3600,
        viewport={"width": 1280, "height": 720},
        name="custom_session"
    )
    print(f"✓ Custom config created:")
    print(f"  - Name: {custom_config.name}")
    print(f"  - Timeout: {custom_config.timeout} seconds")
    print(f"  - Viewport: {custom_config.viewport}")


async def demo_session_pool():
    """Demo SessionPool functionality"""
    print("\n=== Session Pool Demo ===")
    
    # Create session pool
    pool = SessionPool(max_size=3)
    print(f"✓ Created session pool with max size: {pool.max_size}")
    
    # Create sample sessions
    sessions_to_add = []
    for i in range(3):
        config = SessionConfig(project_id="demo-project", name=f"session_{i}")
        session_info = SessionInfo(
            id=f"demo-session-{i}",
            config=config,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            last_health_check=datetime.utcnow(),
            status=SessionStatus.ACTIVE,
            context_data={"session_number": i}
        )
        sessions_to_add.append(session_info)
    
    # Add sessions to pool
    for session_info in sessions_to_add:
        await pool.add_session(session_info)
    print(f"✓ Added {len(sessions_to_add)} sessions to pool")
    
    # Get pool stats
    stats = pool.get_pool_stats()
    print(f"✓ Pool stats: {stats}")
    
    # Get and use sessions
    session1 = await pool.get_available_session()
    session2 = await pool.get_available_session()
    print(f"✓ Got sessions: {session1}, {session2}")
    
    # Check stats after getting sessions
    stats = pool.get_pool_stats()
    print(f"✓ Stats after getting sessions: {stats}")
    
    # Return sessions
    await pool.return_session(session1)
    await pool.return_session(session2)
    print(f"✓ Returned sessions to pool")
    
    # Final stats
    final_stats = pool.get_pool_stats()
    print(f"✓ Final pool stats: {final_stats}")


async def demo_session_types():
    """Demo SessionType enum"""
    print("\n=== Session Types Demo ===")
    
    session_types = [
        SessionType.JOB_DISCOVERY,
        SessionType.PROPOSAL_SUBMISSION,
        SessionType.PROFILE_MANAGEMENT,
        SessionType.GENERAL
    ]
    
    print("✓ Available session types:")
    for session_type in session_types:
        print(f"  - {session_type.value}: Used for {session_type.name.lower().replace('_', ' ')}")


async def demo_session_status():
    """Demo SessionStatus enum"""
    print("\n=== Session Status Demo ===")
    
    statuses = [
        (SessionStatus.CREATING, "Session is being created"),
        (SessionStatus.ACTIVE, "Session is ready for use"),
        (SessionStatus.IDLE, "Session is inactive but available"),
        (SessionStatus.UNHEALTHY, "Session has issues and needs attention"),
        (SessionStatus.EXPIRED, "Session has exceeded timeout"),
        (SessionStatus.CLOSED, "Session has been terminated"),
        (SessionStatus.ERROR, "Session encountered an error")
    ]
    
    print("✓ Available session statuses:")
    for status, description in statuses:
        print(f"  - {status.value}: {description}")


async def demo_session_info():
    """Demo SessionInfo functionality"""
    print("\n=== Session Info Demo ===")
    
    config = SessionConfig(
        project_id="demo-project",
        name="info_demo_session",
        stealth=True,
        proxies=True
    )
    
    session_info = SessionInfo(
        id="demo-session-info",
        config=config,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow(),
        last_health_check=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        context_data={
            "login_state": "authenticated",
            "current_page": "job_search",
            "search_filters": ["Salesforce", "Agentforce"]
        },
        browserbase_session_id="browserbase-123",
        connect_url="wss://connect.browserbase.com/session-123"
    )
    
    print(f"✓ Created session info:")
    print(f"  - ID: {session_info.id}")
    print(f"  - Status: {session_info.status.value}")
    print(f"  - Config name: {session_info.config.name}")
    print(f"  - Browserbase ID: {session_info.browserbase_session_id}")
    print(f"  - Context data keys: {list(session_info.context_data.keys())}")
    
    # Convert to dict
    session_dict = session_info.to_dict()
    print(f"✓ Session serialized to dict with {len(session_dict)} fields")
    
    # Show some dict content
    print(f"  - Dict status: {session_dict['status']}")
    print(f"  - Dict context: {session_dict['context_data']}")


async def demo_session_lifecycle():
    """Demo a complete session lifecycle"""
    print("\n=== Session Lifecycle Demo ===")
    
    # Create session pool
    pool = SessionPool(max_size=2)
    
    # Create a session
    config = SessionConfig(project_id="lifecycle-demo", name="lifecycle_session")
    session_info = SessionInfo(
        id="lifecycle-session-1",
        config=config,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow(),
        last_health_check=datetime.utcnow(),
        status=SessionStatus.CREATING,
        context_data={}
    )
    
    print(f"✓ Created session in {session_info.status.value} state")
    
    # Simulate session becoming active
    session_info.status = SessionStatus.ACTIVE
    await pool.add_session(session_info)
    print(f"✓ Session became {session_info.status.value} and added to pool")
    
    # Get session for use
    session_id = await pool.get_available_session()
    print(f"✓ Retrieved session for use: {session_id}")
    
    # Simulate adding context during use
    session_info.context_data["task"] = "job_discovery"
    session_info.context_data["jobs_found"] = 15
    session_info.last_used = datetime.utcnow()
    print(f"✓ Updated session context: {session_info.context_data}")
    
    # Return session
    await pool.return_session(session_id)
    print(f"✓ Returned session to pool")
    
    # Simulate session becoming unhealthy
    session_info.status = SessionStatus.UNHEALTHY
    session_info.error_count = 3
    print(f"✓ Session became {session_info.status.value} with {session_info.error_count} errors")
    
    # Simulate closing session
    session_info.status = SessionStatus.CLOSED
    print(f"✓ Session lifecycle complete: {session_info.status.value}")


async def main():
    """Run all demos"""
    print("Browserbase Session Management - Basic Demo")
    print("=" * 60)
    
    try:
        await demo_session_config()
        await demo_session_pool()
        await demo_session_types()
        await demo_session_status()
        await demo_session_info()
        await demo_session_lifecycle()
        
        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- ✓ Session configuration with customizable options")
        print("- ✓ Session pool management with availability tracking")
        print("- ✓ Session type enumeration for different automation tasks")
        print("- ✓ Session status tracking throughout lifecycle")
        print("- ✓ Session info storage with context data")
        print("- ✓ Complete session lifecycle from creation to closure")
        
        print("\nImplementation Highlights:")
        print("- Async/await support for non-blocking operations")
        print("- Type hints for better code clarity and IDE support")
        print("- Dataclasses for clean data structure definitions")
        print("- Enum types for controlled status and type values")
        print("- Context data storage for maintaining session state")
        print("- Pool management for efficient resource utilization")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())