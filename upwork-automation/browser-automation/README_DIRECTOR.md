# Director Session Orchestration System

The Director Session Orchestration System is a comprehensive workflow management and browser session orchestration layer for the Ardan Automation System. It manages multiple browser sessions, coordinates parallel workflows, and provides robust error handling and recovery mechanisms.

## Overview

The Director system consists of several key components:

- **DirectorOrchestrator**: Main orchestration engine
- **DirectorActions**: Action implementations for workflow steps
- **Workflow Models**: Data structures for workflows, steps, and executions
- **Session Management**: Integration with browser session pools
- **Checkpoint System**: Recovery and state management

## Key Features

### 1. Multi-Session Orchestration
- Manages multiple browser sessions simultaneously
- Distributes workload across available sessions
- Automatic session health monitoring and recovery
- Session pool management with load balancing

### 2. Parallel Workflow Execution
- Execute workflow steps in parallel where dependencies allow
- Configurable concurrency limits per workflow
- Intelligent dependency resolution
- Dynamic task scheduling

### 3. Workflow Definition System
- Declarative workflow definitions with steps and dependencies
- Support for both sequential and parallel execution
- Flexible parameter passing between steps
- Reusable workflow templates

### 4. Error Handling and Recovery
- Automatic retry logic with configurable retry counts
- Checkpoint system for workflow recovery
- Graceful error handling with detailed logging
- Session failover and replacement

### 5. Monitoring and Metrics
- Real-time workflow execution monitoring
- Performance metrics and success rate tracking
- Session utilization statistics
- Comprehensive logging and debugging

## Architecture

```
DirectorOrchestrator
├── Workflow Management
│   ├── Workflow Definitions
│   ├── Execution Queue
│   └── Active Executions
├── Session Distribution
│   ├── Session Pool Management
│   ├── Load Balancing
│   └── Health Monitoring
├── Execution Engine
│   ├── Sequential Executor
│   ├── Parallel Executor
│   └── Step Action Router
└── Recovery System
    ├── Checkpoint Manager
    ├── Error Recovery
    └── State Restoration
```

## Core Components

### DirectorOrchestrator

The main orchestration class that manages all workflow execution:

```python
director = DirectorOrchestrator(
    session_manager=session_manager,
    stagehand_controller=stagehand_controller,
    browserbase_client=browserbase_client
)

await director.initialize()

# Create and execute workflows
workflow_id = await director.create_workflow(
    name="Job Discovery",
    description="Parallel job discovery workflow",
    steps=workflow_steps,
    parallel_execution=True
)

execution_id = await director.execute_workflow(workflow_id)
```

### Workflow Definition

Workflows are defined using a declarative structure:

```python
steps = [
    {
        "id": "setup_sessions",
        "name": "Setup Browser Sessions",
        "action": "create_session_pool",
        "parameters": {"pool_size": 3}
    },
    {
        "id": "search_jobs",
        "name": "Search for Jobs",
        "action": "search_jobs",
        "parameters": {"keywords": ["Salesforce", "Agentforce"]},
        "dependencies": ["setup_sessions"]
    },
    {
        "id": "process_results",
        "name": "Process Search Results",
        "action": "merge_job_results",
        "dependencies": ["search_jobs"]
    }
]
```

### Predefined Workflows

The system comes with several predefined workflows:

#### 1. Job Discovery Workflow
- Parallel job search across multiple keyword strategies
- Automatic result merging and deduplication
- Session pool management for concurrent searches

#### 2. Proposal Submission Workflow
- Batch proposal validation and submission
- Parallel submission with error handling
- Submission verification and confirmation

#### 3. Profile Management Workflow
- Profile status monitoring
- Availability updates
- Portfolio and skills management

## Usage Examples

### Basic Workflow Creation

```python
# Initialize Director
director = DirectorOrchestrator()
await director.initialize()

# Create a simple workflow
steps = [
    {
        "id": "step1",
        "name": "Search Jobs",
        "action": "search_jobs",
        "parameters": {"keywords": ["Salesforce"]}
    }
]

workflow_id = await director.create_workflow(
    name="Simple Job Search",
    description="Basic job search workflow",
    steps=steps
)

# Execute workflow
execution_id = await director.execute_workflow(workflow_id)

# Monitor execution
status = await director.get_workflow_status(execution_id)
print(f"Workflow status: {status['status']}")
```

### Parallel Job Discovery

```python
from browser_automation.director import create_job_discovery_workflow

# Create and execute parallel job discovery
keywords = ["Salesforce Agentforce", "Salesforce AI", "Einstein"]
execution_id = await create_job_discovery_workflow(
    director, 
    keywords, 
    parallel=True
)

# Monitor progress
while True:
    status = await director.get_workflow_status(execution_id)
    if status['status'] in ['completed', 'failed']:
        break
    print(f"Progress: {status['progress']:.1%}")
    await asyncio.sleep(5)
```

### Batch Proposal Submission

```python
from browser_automation.director import create_proposal_submission_workflow

proposals = [
    {
        "job_url": "https://ardan.com/job1",
        "content": "Proposal content...",
        "bid_amount": 75
    },
    # ... more proposals
]

execution_id = await create_proposal_submission_workflow(
    director,
    proposals,
    batch_size=5
)
```

### Workflow Control

```python
# Pause a running workflow
await director.pause_workflow(execution_id)

# Resume a paused workflow
await director.resume_workflow(execution_id)

# Cancel a workflow
await director.cancel_workflow(execution_id)

# Recover from checkpoint
await director.recover_workflow(execution_id)
```

## Action Types

The Director supports various action types for workflow steps:

### Session Management Actions
- `create_session_pool`: Create browser session pools
- `acquire_sessions`: Acquire additional sessions
- `release_sessions`: Release sessions back to pool

### Job Discovery Actions
- `search_jobs`: Search for jobs using keywords and filters
- `merge_job_results`: Merge and deduplicate job results
- `extract_job_details`: Extract detailed job information

### Proposal Actions
- `validate_proposals`: Validate proposal data
- `submit_proposals`: Submit proposals in batches
- `verify_submissions`: Verify submission success

### Profile Management Actions
- `check_profile`: Check profile status
- `update_availability`: Update availability status
- `refresh_portfolio`: Refresh portfolio items
- `update_skills`: Update skills and certifications

## Error Handling

The Director provides comprehensive error handling:

### Retry Logic
```python
WorkflowStep(
    id="retry_step",
    name="Step with Retry",
    action="search_jobs",
    max_retries=3,  # Retry up to 3 times
    timeout=300     # 5 minute timeout
)
```

### Error Recovery
- Automatic session replacement on failure
- Checkpoint-based workflow recovery
- Graceful degradation on partial failures
- Detailed error logging and reporting

### Checkpoint System
```python
# Checkpoints are created automatically
# Recovery can be triggered manually
success = await director.recover_workflow(execution_id)
```

## Monitoring and Metrics

### System Metrics
```python
metrics = await director.get_system_metrics()
print(f"Active workflows: {metrics['active_workflows']}")
print(f"Success rate: {metrics['success_rate']:.1%}")
```

### Session Distribution
```python
distribution = await director.get_session_distribution()
print(f"Total sessions: {distribution['total_sessions']}")
print(f"Average workload: {distribution['average_workload']}")
```

### Workflow Status
```python
status = await director.get_workflow_status(execution_id)
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']:.1%}")
print(f"Current step: {status['current_step']}")
```

## Configuration

### Director Configuration
```python
director = DirectorOrchestrator(
    session_manager=session_manager,
    stagehand_controller=stagehand_controller,
    browserbase_client=browserbase_client
)

# Configure limits
director.max_concurrent_workflows = 5
director.checkpoint_interval = 60  # seconds
```

### Workflow Configuration
```python
workflow = WorkflowDefinition(
    id="custom_workflow",
    name="Custom Workflow",
    description="Custom workflow description",
    steps=steps,
    parallel_execution=True,
    max_concurrent_steps=3,
    timeout=1800,  # 30 minutes
    priority=WorkflowPriority.HIGH,
    session_requirements={
        "min_sessions": 2,
        "session_type": "job_discovery"
    }
)
```

## Testing

The Director system includes comprehensive tests:

### Running Tests
```bash
# Run all Director tests
python -m pytest tests/test_director_standalone.py -v

# Run specific test categories
python -m pytest tests/test_director_standalone.py::TestDirectorDataModels -v
python -m pytest tests/test_director_standalone.py::TestWorkflowLogic -v
```

### Test Coverage
- Data model validation
- Workflow creation and execution
- Error handling and recovery
- Session management
- Parallel execution logic
- Checkpoint system
- Metrics collection

## Best Practices

### Workflow Design
1. **Keep steps atomic**: Each step should perform a single, well-defined action
2. **Use dependencies wisely**: Only add dependencies when truly necessary
3. **Set appropriate timeouts**: Consider the complexity of each step
4. **Plan for failures**: Design workflows to handle partial failures gracefully

### Session Management
1. **Pool sizing**: Size session pools based on expected concurrency
2. **Health monitoring**: Regularly check session health
3. **Resource cleanup**: Ensure sessions are properly released
4. **Load balancing**: Distribute work evenly across sessions

### Error Handling
1. **Retry strategies**: Use exponential backoff for retries
2. **Checkpoint frequency**: Balance between recovery granularity and performance
3. **Error classification**: Distinguish between retryable and permanent errors
4. **Monitoring**: Set up alerts for high failure rates

### Performance Optimization
1. **Parallel execution**: Use parallel workflows where possible
2. **Batch operations**: Group similar operations together
3. **Resource limits**: Set appropriate concurrency limits
4. **Monitoring**: Track performance metrics and optimize bottlenecks

## Integration

The Director integrates with other system components:

### Session Manager Integration
- Automatic session pool initialization
- Session health monitoring
- Load balancing across session types

### Stagehand Controller Integration
- AI-powered browser automation
- Dynamic content handling
- Error recovery and adaptation

### Browserbase Integration
- Managed browser infrastructure
- Session recording and monitoring
- Stealth mode and proxy support

## Future Enhancements

Planned improvements for the Director system:

1. **Dynamic Scaling**: Automatic session pool scaling based on workload
2. **Advanced Scheduling**: Priority-based workflow scheduling
3. **Workflow Templates**: Pre-built workflow templates for common tasks
4. **Performance Analytics**: Advanced performance analysis and optimization
5. **Distributed Execution**: Support for distributed workflow execution
6. **Visual Workflow Builder**: GUI for creating and managing workflows

## Troubleshooting

### Common Issues

#### Workflow Stuck in Pending
- Check session availability
- Verify workflow dependencies
- Review system resource limits

#### High Failure Rates
- Check session health
- Review error logs
- Adjust retry settings
- Verify external service availability

#### Performance Issues
- Monitor session utilization
- Check for resource bottlenecks
- Review workflow concurrency settings
- Optimize step implementations

### Debugging

Enable detailed logging:
```python
import logging
logging.getLogger("director").setLevel(logging.DEBUG)
```

Check system metrics:
```python
metrics = await director.get_system_metrics()
distribution = await director.get_session_distribution()
```

Review workflow execution history:
```python
for execution in director.execution_history:
    print(f"Workflow: {execution.workflow_id}, Status: {execution.status}")
```

## Conclusion

The Director Session Orchestration System provides a robust, scalable foundation for managing complex browser automation workflows. Its combination of parallel execution, error handling, and monitoring capabilities makes it ideal for large-scale automation tasks while maintaining reliability and performance.