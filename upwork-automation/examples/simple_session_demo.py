"""
Simple demo of session management functionality without external dependencies
"""
import asyncio
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Mock the settings to avoid dependency issues
class MockSettings:
    browserbase_api_key = "mock-api-key"
    browserbase_project_id = "mock-project-id"

# Patch the settings import
import shared.config
shared.config.settings = MockSettings()

from browserbase_client import SessionConfig, SessionStatus, SessionPool, SessionInfo
from session_manager import SessionType
from datetime import datetime


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
        viewport={"width": 1280, "height": 720}
    )
    print(f"✓ Custom config created:")
    print(f"  - Timeout: {custom_config.timeout} seconds")
    print(f"  - Viewport: {custom_config.viewport}")


async def demo_session_pool():
    """Demo SessionPool functionality"""
    print("\n=== Session Pool Demo ===")
    
    # Create session pool
    pool = SessionPool(max_size=3)
    print(f"✓ Created session pool with max size: {pool.max_size}")
    
    # Create sample session info
    config = SessionConfig(project_id="demo-project")
    session_info = SessionInfo(
        id="demo-session-1",
        config=config,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow(),
        last_health_check=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        context_data={}
    )
    
    # Add session to pool
    await pool.add_session(session_info)
    print(f"✓ Added session to pool")
    
    # Get pool stats
    stats = pool.get_pool_stats()
    print(f"✓ Pool stats: {stats}")
    
    # Get available session
    session_id = await pool.get_available_session()
    print(f"✓ Got available session: {session_id}")
    
    # Return session
    await pool.return_session(session_id)
    print(f"✓ Returned session to pool")
    
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
        print(f"  - {session_type.value}")


async def demo_session_status():
    """Demo SessionStatus enum"""
    print("\n=== Session Status Demo ===")
    
    statuses = [
        SessionStatus.CREATING,
        SessionStatus.ACTIVE,
        SessionStatus.IDLE,
        SessionStatus.UNHEALTHY,
        SessionStatus.EXPIRED,
        SessionStatus.CLOSED,
        SessionStatus.ERROR
    ]
    
    print("✓ Available session statuses:")
    for status in statuses:
        print(f"  - {status.value}")


async def demo_session_info():
    """Demo SessionInfo functionality"""
    print("\n=== Session Info Demo ===")
    
    config = SessionConfig(project_id="demo-project")
    session_info = SessionInfo(
        id="demo-session-info",
        config=config,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow(),
        last_health_check=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        context_data={"login_state": "authenticated"},
        browserbase_session_id="browserbase-123",
        connect_url="wss://connect.browserbase.com/session-123"
    )
    
    print(f"✓ Created session info:")
    print(f"  - ID: {session_info.id}")
    print(f"  - Status: {session_info.status.value}")
    print(f"  - Browserbase ID: {session_info.browserbase_session_id}")
    print(f"  - Context data: {session_info.context_data}")
    
    # Convert to dict
    session_dict = session_info.to_dict()
    print(f"✓ Session as dict: {len(session_dict)} fields")


async def main():
    """Run all demos"""
    print("Browserbase Session Management - Simple Demo")
    print("=" * 60)
    
    try:
        await demo_session_config()
        await demo_session_pool()
        await demo_session_types()
        await demo_session_status()
        await demo_session_info()
        
        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Session configuration with customizable options")
        print("- Session pool management with availability tracking")
        print("- Session type enumeration for different automation tasks")
        print("- Session status tracking throughout lifecycle")
        print("- Session info storage with context data")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())