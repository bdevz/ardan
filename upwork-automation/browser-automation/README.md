# Browser Automation - Browserbase Integration and Session Management

This module implements comprehensive Browserbase integration with advanced session management capabilities for the Ardan Automation System.

## Overview

The browser automation module provides:

- **Browserbase SDK Integration**: Full integration with Browserbase API for managed browser sessions
- **Session Pool Management**: Efficient management of multiple browser sessions with automatic scaling
- **Health Monitoring**: Continuous monitoring and automatic refresh of unhealthy sessions
- **Context Storage**: Persistent storage and retrieval of session state across operations
- **Session Types**: Specialized session management for different automation tasks

## Key Components

### 1. BrowserbaseClient

The core client for managing Browserbase browser sessions with advanced features:

```python
from browserbase_client import BrowserbaseClient

client = BrowserbaseClient()

# Create a session with stealth mode and proxy support
session_id = await client.create_session({
    "stealth": True,
    "proxies": True,
    "name": "job_discovery_session"
})

# Store context data
await client.store_session_context(session_id, "login_state", {
    "authenticated": True,
    "username": "user@example.com"
})

# Check session health
health = await client.get_session_health(session_id)
print(f"Session healthy: {health['healthy']}")
```

**Features:**
- Automatic session creation with configurable options
- Session pool management with availability tracking
- Health monitoring with automatic refresh
- Context storage and retrieval
- Background cleanup of expired sessions
- Retry logic with exponential backoff

### 2. SessionManager

High-level session manager for coordinating browser sessions across different automation tasks:

```python
from session_manager import SessionManager, SessionType

manager = SessionManager()
await manager.initialize_session_pools()

# Execute a task with automatic session management
async def job_discovery_task(session_id):
    # Your automation logic here
    return {"jobs_found": 15}

result = await manager.execute_with_session(
    SessionType.JOB_DISCOVERY, 
    job_discovery_task
)
```

**Features:**
- Task-specific session pools (job discovery, proposal submission, etc.)
- Context manager for automatic session acquisition and release
- Error handling with session health tracking
- Concurrent session usage with proper locking
- Automatic session refresh and cleanup

### 3. Session Configuration

Flexible configuration system for different session requirements:

```python
from browserbase_client import SessionConfig

config = SessionConfig(
    project_id="ardan-automation",
    stealth=True,
    proxies=True,
    timeout=1800,  # 30 minutes
    viewport={"width": 1920, "height": 1080},
    name="custom_session"
)
```

### 4. Session Types and Status

Enumerated types for better session management:

```python
from session_manager import SessionType
from browserbase_client import SessionStatus

# Session types for different automation tasks
SessionType.JOB_DISCOVERY
SessionType.PROPOSAL_SUBMISSION
SessionType.PROFILE_MANAGEMENT
SessionType.GENERAL

# Session status tracking
SessionStatus.CREATING
SessionStatus.ACTIVE
SessionStatus.IDLE
SessionStatus.UNHEALTHY
SessionStatus.EXPIRED
SessionStatus.CLOSED
SessionStatus.ERROR
```

## Architecture

### Session Pool Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SessionManager                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Job Discovery   │  │ Proposal Sub.   │  │ Profile Mgmt │ │
│  │ Session Pool    │  │ Session Pool    │  │ Session Pool │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                 BrowserbaseClient                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Session Pool                               │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │ │
│  │  │Session 1│ │Session 2│ │Session 3│ │Session 4│ ...  │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                 Browserbase API                             │
└─────────────────────────────────────────────────────────────┘
```

### Health Monitoring System

- **Continuous Monitoring**: Background task checks session health every minute
- **Automatic Refresh**: Unhealthy sessions are automatically refreshed
- **Context Preservation**: Session context is transferred during refresh
- **Error Tracking**: Sessions with high error counts are marked as unhealthy
- **Cleanup**: Expired and unhealthy sessions are automatically cleaned up

## Configuration

### Environment Variables

```bash
BROWSERBASE_API_KEY=your_api_key_here
BROWSERBASE_PROJECT_ID=your_project_id_here
```

### Configuration Options

```python
class BrowserAutomationConfig:
    SESSION_POOL_SIZE = 5
    SESSION_TIMEOUT_MINUTES = 30
    SESSION_KEEPALIVE = True
    STEALTH_MODE = True
    USE_PROXIES = True
    HUMAN_LIKE_DELAYS = True
    MIN_ACTION_DELAY = 1.0
    MAX_ACTION_DELAY = 3.0
    APPLICATIONS_PER_HOUR = 5
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0
```

## Usage Examples

### Basic Session Management

```python
import asyncio
from browserbase_client import BrowserbaseClient

async def basic_example():
    client = BrowserbaseClient()
    
    # Create session
    session_id = await client.create_session()
    
    # Store context
    await client.store_session_context(session_id, "page_state", {
        "current_url": "https://www.ardan.com/nx/search/jobs",
        "search_filters": ["Salesforce", "Agentforce"]
    })
    
    # Retrieve context
    context = await client.get_session_context(session_id, "page_state")
    print(f"Current URL: {context['current_url']}")
    
    # Close session
    await client.close_session(session_id)
    await client.shutdown()

asyncio.run(basic_example())
```

### Advanced Session Management

```python
import asyncio
from session_manager import SessionManager, SessionType

async def advanced_example():
    manager = SessionManager()
    await manager.initialize_session_pools()
    
    # Define automation task
    async def job_search_task(session_id):
        # Simulate job search automation
        await manager.browserbase_client.store_session_context(
            session_id, "search_results", {"jobs_found": 25}
        )
        return {"success": True, "jobs_found": 25}
    
    # Execute with automatic session management
    result = await manager.execute_with_session(
        SessionType.JOB_DISCOVERY, 
        job_search_task
    )
    
    print(f"Job search result: {result}")
    
    # Get session statistics
    stats = await manager.get_session_stats_by_type()
    print(f"Session stats: {stats}")
    
    await manager.shutdown()

asyncio.run(advanced_example())
```

### Context Manager Usage

```python
async def context_manager_example():
    manager = SessionManager()
    await manager.initialize_session_pools()
    
    # Use context manager for automatic session handling
    async with manager.get_session_for_task(SessionType.PROPOSAL_SUBMISSION) as session_id:
        # Session is automatically acquired
        print(f"Using session: {session_id}")
        
        # Do automation work
        await asyncio.sleep(1)  # Simulate work
        
        # Store results
        await manager.browserbase_client.store_session_context(
            session_id, "proposal_status", {"submitted": True}
        )
    
    # Session is automatically returned to pool
    await manager.shutdown()
```

## Testing

### Unit Tests

Run the comprehensive unit test suite:

```bash
# Run all tests
python -m pytest tests/test_browserbase_client.py -v

# Run specific test classes
python -m pytest tests/test_browserbase_client.py::TestSessionConfig -v
python -m pytest tests/test_browserbase_client.py::TestSessionPool -v
python -m pytest tests/test_browserbase_client.py::TestBrowserbaseClient -v
python -m pytest tests/test_browserbase_client.py::TestSessionManager -v
```

### Integration Tests

Run integration tests with real Browserbase API (requires credentials):

```bash
# Set environment variables
export BROWSERBASE_API_KEY=your_api_key
export BROWSERBASE_PROJECT_ID=your_project_id

# Run integration tests
python -m pytest tests/test_browserbase_integration.py -v -m integration
```

### Demo Scripts

Run demo scripts to see the functionality in action:

```bash
# Basic demo (no external dependencies)
python examples/basic_demo.py

# Full demo (requires Browserbase credentials)
python examples/session_management_demo.py
```

## Error Handling

The system includes comprehensive error handling:

- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Health Monitoring**: Continuous monitoring with automatic session refresh
- **Graceful Degradation**: System continues operating with reduced capacity during failures
- **Error Tracking**: Session error counts are tracked and used for health decisions
- **Cleanup**: Automatic cleanup of failed or expired sessions

## Performance Considerations

- **Session Pooling**: Reuse of browser sessions reduces creation overhead
- **Concurrent Operations**: Multiple sessions can be used simultaneously
- **Background Tasks**: Health monitoring and cleanup run in background
- **Resource Management**: Automatic cleanup prevents resource leaks
- **Configurable Limits**: Pool sizes and timeouts are configurable

## Security Features

- **Stealth Mode**: Advanced fingerprinting protection
- **Proxy Support**: Automatic proxy rotation for IP diversity
- **Rate Limiting**: Built-in rate limiting to avoid detection
- **Secure Context Storage**: Session context is stored securely in memory
- **Credential Management**: API keys are handled securely

## Monitoring and Observability

- **Health Metrics**: Comprehensive session health reporting
- **Pool Statistics**: Real-time pool utilization statistics
- **Error Tracking**: Detailed error tracking and reporting
- **Performance Metrics**: Session creation and usage metrics
- **Logging**: Structured logging for debugging and monitoring

## Future Enhancements

- **Session Persistence**: Save/restore session state across restarts
- **Load Balancing**: Intelligent session distribution across multiple Browserbase projects
- **Metrics Export**: Export metrics to monitoring systems
- **Session Recording**: Optional session recording for debugging
- **Advanced Scheduling**: Priority-based session scheduling

## Requirements

- Python 3.7+
- aiohttp
- pydantic
- pydantic-settings
- asyncio support

## Installation

```bash
pip install aiohttp pydantic pydantic-settings
```

## License

This module is part of the Ardan Automation System and follows the same licensing terms.