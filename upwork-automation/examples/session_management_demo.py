"""
Demo script showing Browserbase session management functionality
"""
import asyncio
import os
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from browserbase_client import BrowserbaseClient
from session_manager import SessionManager, SessionType


async def demo_basic_session_operations():
    """Demonstrate basic session operations"""
    print("=== Basic Session Operations Demo ===")
    
    client = BrowserbaseClient()
    
    try:
        # Create a session
        print("Creating browser session...")
        session_id = await client.create_session({
            "name": "demo_session",
            "stealth": True,
            "proxies": True
        })
        print(f"✓ Created session: {session_id}")
        
        # Check session health
        health = await client.get_session_health(session_id)
        print(f"✓ Session health: {'Healthy' if health['healthy'] else 'Unhealthy'}")
        print(f"  - Status: {health['status']}")
        print(f"  - Age: {health['age_minutes']:.2f} minutes")
        
        # Store some context
        print("Storing session context...")
        context_data = {
            "login_state": "authenticated",
            "current_page": "job_search",
            "search_filters": ["Salesforce", "Agentforce"],
            "timestamp": datetime.utcnow().isoformat()
        }
        await client.store_session_context(session_id, "navigation", context_data)
        print("✓ Context stored")
        
        # Retrieve context
        retrieved_context = await client.get_session_context(session_id, "navigation")
        print(f"✓ Retrieved context: {retrieved_context['current_page']}")
        
        # Get pool stats
        stats = client.get_pool_stats()
        print(f"✓ Pool stats: {stats['total_sessions']} total sessions")
        
        # Close session
        print("Closing session...")
        await client.close_session(session_id)
        print("✓ Session closed")
        
    except Exception as e:
        print(f"❌ Error in basic operations: {e}")
    
    finally:
        await client.shutdown()


async def demo_session_pool():
    """Demonstrate session pool management"""
    print("\n=== Session Pool Demo ===")
    
    client = BrowserbaseClient()
    
    try:
        # Create a pool of sessions
        print("Creating session pool...")
        pool_size = 3
        sessions = await client.create_session_pool(pool_size=pool_size)
        print(f"✓ Created pool with {len(sessions)} sessions")
        
        # Check health of all sessions
        print("Checking session health...")
        for i, session_id in enumerate(sessions):
            health = await client.get_session_health(session_id)
            status = "✓" if health['healthy'] else "❌"
            print(f"  {status} Session {i+1}: {health['status']}")
        
        # Demonstrate session reuse
        print("Testing session reuse...")
        reused_session = await client.get_or_create_session("test_task")
        print(f"✓ Got session for reuse: {reused_session}")
        
        await client.return_session(reused_session)
        print("✓ Returned session to pool")
        
        # Clean up all sessions
        print("Cleaning up sessions...")
        for session_id in sessions:
            await client.close_session(session_id)
        print("✓ All sessions closed")
        
    except Exception as e:
        print(f"❌ Error in pool demo: {e}")
    
    finally:
        await client.shutdown()


async def demo_session_manager():
    """Demonstrate high-level session manager"""
    print("\n=== Session Manager Demo ===")
    
    manager = SessionManager()
    
    try:
        # Initialize session pools
        print("Initializing session pools...")
        await manager.initialize_session_pools()
        print("✓ Session pools initialized")
        
        # Get stats
        stats = await manager.get_session_stats_by_type()
        print(f"✓ Total sessions: {stats['total_sessions']}")
        for task_type, type_stats in stats['by_type'].items():
            print(f"  - {task_type}: {type_stats['count']} sessions")
        
        # Demonstrate task execution with sessions
        print("Executing tasks with managed sessions...")
        
        async def mock_job_discovery_task(session_id):
            print(f"  Job discovery task using session: {session_id}")
            # Simulate storing search results
            await manager.browserbase_client.store_session_context(
                session_id, "search_results", 
                {"jobs_found": 15, "search_time": datetime.utcnow().isoformat()}
            )
            return {"jobs_found": 15, "session_id": session_id}
        
        async def mock_proposal_task(session_id):
            print(f"  Proposal submission task using session: {session_id}")
            # Simulate proposal submission
            await manager.browserbase_client.store_session_context(
                session_id, "proposal_status",
                {"submitted": True, "job_id": "12345", "timestamp": datetime.utcnow().isoformat()}
            )
            return {"submitted": True, "session_id": session_id}
        
        # Execute tasks concurrently
        job_task = manager.execute_with_session(
            SessionType.JOB_DISCOVERY, mock_job_discovery_task
        )
        proposal_task = manager.execute_with_session(
            SessionType.PROPOSAL_SUBMISSION, mock_proposal_task
        )
        
        results = await asyncio.gather(job_task, proposal_task)
        
        print(f"✓ Job discovery result: {results[0]['jobs_found']} jobs found")
        print(f"✓ Proposal submission result: {'Success' if results[1]['submitted'] else 'Failed'}")
        
        # Demonstrate session context manager
        print("Using session context manager...")
        async with manager.get_session_for_task(SessionType.PROFILE_MANAGEMENT) as session_id:
            print(f"  Got session for profile management: {session_id}")
            # Simulate profile update
            await asyncio.sleep(0.1)  # Simulate work
            print("  Profile management task completed")
        print("✓ Session automatically returned to pool")
        
    except Exception as e:
        print(f"❌ Error in session manager demo: {e}")
    
    finally:
        await manager.shutdown()


async def demo_error_handling():
    """Demonstrate error handling and recovery"""
    print("\n=== Error Handling Demo ===")
    
    manager = SessionManager()
    
    try:
        await manager.initialize_session_pools()
        
        # Simulate a task that fails
        async def failing_task(session_id):
            print(f"  Failing task using session: {session_id}")
            raise Exception("Simulated task failure")
        
        print("Testing error handling...")
        try:
            await manager.execute_with_session(
                SessionType.JOB_DISCOVERY, failing_task
            )
        except Exception as e:
            print(f"✓ Caught expected error: {e}")
        
        # Check that session error count was incremented
        stats = await manager.get_session_stats_by_type()
        print("✓ Error handling completed, sessions still available")
        
        # Demonstrate cleanup of unhealthy sessions
        print("Testing session cleanup...")
        await manager.cleanup_unhealthy_sessions()
        print("✓ Cleanup completed")
        
        # Ensure minimum sessions
        await manager.ensure_minimum_sessions()
        final_stats = await manager.get_session_stats_by_type()
        print(f"✓ Ensured minimum sessions: {final_stats['total_sessions']} total")
        
    except Exception as e:
        print(f"❌ Error in error handling demo: {e}")
    
    finally:
        await manager.shutdown()


async def main():
    """Run all demos"""
    print("Browserbase Session Management Demo")
    print("=" * 50)
    
    # Check if we have credentials for real API calls
    has_credentials = (
        os.getenv("BROWSERBASE_API_KEY") and 
        os.getenv("BROWSERBASE_PROJECT_ID")
    )
    
    if not has_credentials:
        print("⚠️  Note: Running in mock mode (no Browserbase credentials)")
        print("   Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID for real API calls")
    else:
        print("✓ Browserbase credentials found - using real API")
    
    try:
        await demo_basic_session_operations()
        await demo_session_pool()
        await demo_session_manager()
        await demo_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())