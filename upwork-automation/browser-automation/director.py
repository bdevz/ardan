"""
Director Session Orchestration System for managing multiple browser sessions and parallel workflows
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from shared.config import BrowserAutomationConfig, settings
from shared.utils import setup_logging, retry_async
from shared.models import BrowserSession
from browserbase_client import BrowserbaseClient
from session_manager import SessionManager, SessionType
from stagehand_controller import StagehandController

logger = setup_logging("director")


class WorkflowStatus(Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of individual workflow steps"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowPriority(Enum):
    """Priority levels for workflow execution"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    id: str
    name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300  # 5 minutes default
    retry_count: int = 0
    max_retries: int = 3
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    session_id: Optional[str] = None


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    session_requirements: Dict[str, Any] = field(default_factory=dict)
    parallel_execution: bool = False
    max_concurrent_steps: int = 3
    timeout: int = 1800  # 30 minutes default
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Runtime execution state of a workflow"""
    id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: Optional[str] = None
    progress: float = 0.0
    session_assignments: Dict[str, str] = field(default_factory=dict)  # step_id -> session_id
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class DirectorOrchestrator:
    """Main orchestrator for managing multiple browser sessions and parallel workflows"""
    
    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        stagehand_controller: Optional[StagehandController] = None,
        browserbase_client: Optional[BrowserbaseClient] = None
    ):
        self.session_manager = session_manager or SessionManager()
        self.stagehand_controller = stagehand_controller or StagehandController()
        self.browserbase_client = browserbase_client or BrowserbaseClient()
        
        # Workflow management
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Session distribution and load balancing
        self.session_workload: Dict[str, int] = {}  # session_id -> active_tasks
        self.session_capabilities: Dict[str, List[str]] = {}  # session_id -> capabilities
        
        # Monitoring and logging
        self.execution_history: List[WorkflowExecution] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        # Control flags
        self.is_running = False
        self.max_concurrent_workflows = 5
        self.workflow_executor_task: Optional[asyncio.Task] = None
        
        # Recovery and checkpointing
        self.checkpoint_interval = 60  # seconds
        self.checkpoint_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the Director orchestration system"""
        logger.info("Initializing Director orchestration system...")
        
        try:
            # Initialize session manager
            await self.session_manager.initialize_session_pools()
            
            # Start workflow executor
            self.is_running = True
            self.workflow_executor_task = asyncio.create_task(self._workflow_executor())
            
            # Start checkpoint system
            self.checkpoint_task = asyncio.create_task(self._checkpoint_manager())
            
            # Load predefined workflows
            await self._load_predefined_workflows()
            
            logger.info("Director orchestration system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Director: {e}")
            raise 
   
    async def _load_predefined_workflows(self):
        """Load predefined workflow definitions"""
        
        # Job Discovery Workflow
        job_discovery_workflow = WorkflowDefinition(
            id="job_discovery_parallel",
            name="Parallel Job Discovery",
            description="Discover jobs using multiple search strategies in parallel",
            steps=[
                WorkflowStep(
                    id="setup_sessions",
                    name="Setup Browser Sessions",
                    action="create_session_pool",
                    parameters={"pool_size": 3, "session_type": "job_discovery"}
                ),
                WorkflowStep(
                    id="search_agentforce",
                    name="Search Agentforce Jobs",
                    action="search_jobs",
                    parameters={
                        "keywords": ["Salesforce Agentforce"],
                        "sort": "newest"
                    },
                    dependencies=["setup_sessions"]
                ),
                WorkflowStep(
                    id="search_ai_einstein",
                    name="Search AI/Einstein Jobs",
                    action="search_jobs",
                    parameters={
                        "keywords": ["Salesforce AI", "Einstein"],
                        "sort": "best_match"
                    },
                    dependencies=["setup_sessions"]
                ),
                WorkflowStep(
                    id="search_developer",
                    name="Search Developer Jobs",
                    action="search_jobs",
                    parameters={
                        "keywords": ["Salesforce Developer"],
                        "filters": ["payment_verified", "high_rating"]
                    },
                    dependencies=["setup_sessions"]
                ),
                WorkflowStep(
                    id="merge_results",
                    name="Merge and Deduplicate Results",
                    action="merge_job_results",
                    parameters={},
                    dependencies=["search_agentforce", "search_ai_einstein", "search_developer"]
                )
            ],
            parallel_execution=True,
            max_concurrent_steps=3,
            session_requirements={"min_sessions": 3, "session_type": "job_discovery"}
        )
        
        # Proposal Submission Workflow
        proposal_submission_workflow = WorkflowDefinition(
            id="proposal_submission_batch",
            name="Batch Proposal Submission",
            description="Submit multiple proposals in parallel with error handling",
            steps=[
                WorkflowStep(
                    id="validate_proposals",
                    name="Validate Proposal Data",
                    action="validate_proposals",
                    parameters={}
                ),
                WorkflowStep(
                    id="acquire_sessions",
                    name="Acquire Submission Sessions",
                    action="acquire_sessions",
                    parameters={"session_type": "proposal_submission", "count": 2},
                    dependencies=["validate_proposals"]
                ),
                WorkflowStep(
                    id="submit_batch_1",
                    name="Submit First Batch",
                    action="submit_proposals",
                    parameters={"batch_size": 5},
                    dependencies=["acquire_sessions"]
                ),
                WorkflowStep(
                    id="submit_batch_2",
                    name="Submit Second Batch",
                    action="submit_proposals",
                    parameters={"batch_size": 5},
                    dependencies=["acquire_sessions"]
                ),
                WorkflowStep(
                    id="verify_submissions",
                    name="Verify All Submissions",
                    action="verify_submissions",
                    parameters={},
                    dependencies=["submit_batch_1", "submit_batch_2"]
                )
            ],
            parallel_execution=True,
            max_concurrent_steps=2,
            session_requirements={"min_sessions": 2, "session_type": "proposal_submission"}
        )
        
        # Register workflows
        self.workflow_definitions[job_discovery_workflow.id] = job_discovery_workflow
        self.workflow_definitions[proposal_submission_workflow.id] = proposal_submission_workflow
        
        logger.info(f"Loaded {len(self.workflow_definitions)} predefined workflows")    

    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        **kwargs
    ) -> str:
        """Create a new workflow definition"""
        workflow_id = str(uuid.uuid4())
        
        # Convert step dictionaries to WorkflowStep objects
        workflow_steps = []
        for i, step_data in enumerate(steps):
            step = WorkflowStep(
                id=step_data.get("id", f"step_{i}"),
                name=step_data.get("name", f"Step {i+1}"),
                action=step_data["action"],
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", []),
                timeout=step_data.get("timeout", 300),
                max_retries=step_data.get("max_retries", 3)
            )
            workflow_steps.append(step)
        
        workflow = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps,
            session_requirements=kwargs.get("session_requirements", {}),
            parallel_execution=kwargs.get("parallel_execution", False),
            max_concurrent_steps=kwargs.get("max_concurrent_steps", 3),
            timeout=kwargs.get("timeout", 1800),
            priority=WorkflowPriority(kwargs.get("priority", 2)),
            metadata=kwargs.get("metadata", {})
        )
        
        self.workflow_definitions[workflow_id] = workflow
        
        logger.info(f"Created workflow '{name}' with ID: {workflow_id}")
        return workflow_id
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        priority: Optional[WorkflowPriority] = None
    ) -> str:
        """Queue a workflow for execution"""
        if workflow_id not in self.workflow_definitions:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow_def = self.workflow_definitions[workflow_id]
        execution_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id
        )
        
        self.active_executions[execution_id] = execution
        
        # Queue for execution with priority
        execution_priority = priority or workflow_def.priority
        await self.execution_queue.put((execution_priority.value, execution_id, input_data))
        
        logger.info(f"Queued workflow '{workflow_def.name}' for execution: {execution_id}")
        return execution_id  
  
    async def _workflow_executor(self):
        """Main workflow execution loop"""
        logger.info("Starting workflow executor...")
        
        while self.is_running:
            try:
                # Check if we can start new workflows
                if len([e for e in self.active_executions.values() 
                       if e.status == WorkflowStatus.RUNNING]) >= self.max_concurrent_workflows:
                    await asyncio.sleep(1)
                    continue
                
                # Get next workflow from queue
                try:
                    priority, execution_id, input_data = await asyncio.wait_for(
                        self.execution_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Execute workflow
                asyncio.create_task(self._execute_workflow_instance(execution_id, input_data))
                
            except Exception as e:
                logger.error(f"Error in workflow executor: {e}")
                await asyncio.sleep(5)
    
    async def _execute_workflow_instance(
        self,
        execution_id: str,
        input_data: Optional[Dict[str, Any]]
    ):
        """Execute a single workflow instance"""
        execution = self.active_executions[execution_id]
        workflow_def = self.workflow_definitions[execution.workflow_id]
        
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = datetime.utcnow()
            
            logger.info(f"Starting workflow execution: {workflow_def.name} ({execution_id})")
            
            # Acquire required sessions
            await self._acquire_workflow_sessions(execution, workflow_def)
            
            # Execute workflow steps
            if workflow_def.parallel_execution:
                await self._execute_parallel_workflow(execution, workflow_def, input_data)
            else:
                await self._execute_sequential_workflow(execution, workflow_def, input_data)
            
            # Mark as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.progress = 1.0
            
            logger.info(f"Workflow completed successfully: {execution_id}")
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_log.append(f"Workflow execution failed: {str(e)}")
            execution.completed_at = datetime.utcnow()
            
            logger.error(f"Workflow execution failed: {execution_id} - {e}")
            
        finally:
            # Release sessions
            await self._release_workflow_sessions(execution)
            
            # Move to history
            self.execution_history.append(execution)
            if len(self.execution_history) > 100:  # Keep last 100 executions
                self.execution_history.pop(0)
            
            # Remove from active executions
            self.active_executions.pop(execution_id, None)   
 
    async def _acquire_workflow_sessions(
        self,
        execution: WorkflowExecution,
        workflow_def: WorkflowDefinition
    ):
        """Acquire browser sessions required for workflow execution"""
        session_requirements = workflow_def.session_requirements
        min_sessions = session_requirements.get("min_sessions", 1)
        session_type = session_requirements.get("session_type", "general")
        
        # Convert string session type to enum
        if isinstance(session_type, str):
            session_type = SessionType(session_type)
        
        # Acquire sessions for each step that needs one
        for step in workflow_def.steps:
            if step.action in ["search_jobs", "submit_proposals", "check_profile", "navigate", "extract", "interact"]:
                try:
                    # Use session manager to get appropriate session
                    session_context = self.session_manager.get_session_for_task(session_type)
                    session_id = await session_context.__aenter__()
                    
                    execution.session_assignments[step.id] = session_id
                    self.session_workload[session_id] = self.session_workload.get(session_id, 0) + 1
                    
                    logger.debug(f"Assigned session {session_id} to step {step.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to acquire session for step {step.id}: {e}")
                    raise
    
    async def _release_workflow_sessions(self, execution: WorkflowExecution):
        """Release browser sessions used by workflow"""
        for step_id, session_id in execution.session_assignments.items():
            try:
                # Decrease workload counter
                if session_id in self.session_workload:
                    self.session_workload[session_id] = max(0, self.session_workload[session_id] - 1)
                
                # Session will be automatically released by session manager context
                logger.debug(f"Released session {session_id} from step {step_id}")
                
            except Exception as e:
                logger.error(f"Error releasing session {session_id}: {e}")
    
    async def _execute_sequential_workflow(
        self,
        execution: WorkflowExecution,
        workflow_def: WorkflowDefinition,
        input_data: Optional[Dict[str, Any]]
    ):
        """Execute workflow steps sequentially"""
        completed_steps = set()
        step_results = {}
        
        for step in workflow_def.steps:
            # Check dependencies
            if not all(dep in completed_steps for dep in step.dependencies):
                continue
            
            # Execute step
            try:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.utcnow()
                execution.current_step = step.id
                
                # Get session for this step
                session_id = execution.session_assignments.get(step.id)
                
                # Execute step action
                result = await self._execute_step_action(
                    step, session_id, input_data, step_results
                )
                
                step.result = result
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                completed_steps.add(step.id)
                step_results[step.id] = result
                
                # Update progress
                execution.progress = len(completed_steps) / len(workflow_def.steps)
                
                logger.debug(f"Step completed: {step.name}")
                
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error_message = str(e)
                step.completed_at = datetime.utcnow()
                
                # Handle step failure
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    step.status = StepStatus.RETRYING
                    logger.warning(f"Step failed, retrying: {step.name} (attempt {step.retry_count})")
                    continue
                else:
                    logger.error(f"Step failed permanently: {step.name} - {e}")
                    raise
        
        execution.result = step_results    

    async def _execute_parallel_workflow(
        self,
        execution: WorkflowExecution,
        workflow_def: WorkflowDefinition,
        input_data: Optional[Dict[str, Any]]
    ):
        """Execute workflow steps in parallel where possible"""
        completed_steps = set()
        step_results = {}
        running_tasks = {}
        
        while len(completed_steps) < len(workflow_def.steps):
            # Find steps ready to execute
            ready_steps = [
                step for step in workflow_def.steps
                if (step.id not in completed_steps and 
                    step.id not in running_tasks and
                    all(dep in completed_steps for dep in step.dependencies))
            ]
            
            # Start new tasks up to concurrency limit
            while (ready_steps and 
                   len(running_tasks) < workflow_def.max_concurrent_steps):
                step = ready_steps.pop(0)
                
                step.status = StepStatus.RUNNING
                step.started_at = datetime.utcnow()
                
                # Get session for this step
                session_id = execution.session_assignments.get(step.id)
                
                # Create task for step execution
                task = asyncio.create_task(
                    self._execute_step_action(step, session_id, input_data, step_results)
                )
                running_tasks[step.id] = (step, task)
                
                logger.debug(f"Started parallel step: {step.name}")
            
            # Wait for at least one task to complete
            if running_tasks:
                done, pending = await asyncio.wait(
                    [task for _, task in running_tasks.values()],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for task in done:
                    # Find which step this task belongs to
                    step_id = None
                    for sid, (step, t) in running_tasks.items():
                        if t == task:
                            step_id = sid
                            break
                    
                    if step_id:
                        step, _ = running_tasks.pop(step_id)
                        
                        try:
                            result = await task
                            step.result = result
                            step.status = StepStatus.COMPLETED
                            step.completed_at = datetime.utcnow()
                            completed_steps.add(step.id)
                            step_results[step.id] = result
                            
                            logger.debug(f"Parallel step completed: {step.name}")
                            
                        except Exception as e:
                            step.status = StepStatus.FAILED
                            step.error_message = str(e)
                            step.completed_at = datetime.utcnow()
                            
                            # Handle step failure
                            if step.retry_count < step.max_retries:
                                step.retry_count += 1
                                step.status = StepStatus.RETRYING
                                logger.warning(f"Parallel step failed, will retry: {step.name}")
                                # Add back to ready steps for retry
                                ready_steps.append(step)
                            else:
                                logger.error(f"Parallel step failed permanently: {step.name} - {e}")
                                # For now, continue with other steps
                                completed_steps.add(step.id)
                
                # Update progress
                execution.progress = len(completed_steps) / len(workflow_def.steps)
            
            else:
                # No tasks running and no ready steps - check for deadlock
                if not ready_steps:
                    logger.warning("Workflow may be deadlocked - no ready steps and no running tasks")
                    break
                
                await asyncio.sleep(0.1)
        
        execution.result = step_results 
   
    async def _execute_step_action(
        self,
        step: WorkflowStep,
        session_id: Optional[str],
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific step action"""
        from director_actions import DirectorActions
        
        actions = DirectorActions(self.browserbase_client, self.stagehand_controller)
        return await actions.execute_step_action(step, session_id, input_data, step_results)
    
    # Workflow management methods
    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause a running workflow"""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        if execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            
            # Create checkpoint
            await self._create_checkpoint(execution)
            
            logger.info(f"Paused workflow execution: {execution_id}")
            return True
        
        return False
    
    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume a paused workflow"""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        if execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            
            # Re-queue for execution
            workflow_def = self.workflow_definitions[execution.workflow_id]
            await self.execution_queue.put((workflow_def.priority.value, execution_id, None))
            
            logger.info(f"Resumed workflow execution: {execution_id}")
            return True
        
        return False
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a workflow execution"""
        if execution_id not in self.active_executions:
            return False
        
        execution = self.active_executions[execution_id]
        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        
        # Release sessions
        await self._release_workflow_sessions(execution)
        
        logger.info(f"Cancelled workflow execution: {execution_id}")
        return True
    
    async def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution"""
        if execution_id not in self.active_executions:
            # Check execution history
            for execution in self.execution_history:
                if execution.id == execution_id:
                    return self._execution_to_dict(execution)
            return None
        
        execution = self.active_executions[execution_id]
        return self._execution_to_dict(execution)
    
    def _execution_to_dict(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Convert workflow execution to dictionary"""
        workflow_def = self.workflow_definitions.get(execution.workflow_id)
        
        return {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "workflow_name": workflow_def.name if workflow_def else "Unknown",
            "status": execution.status.value,
            "progress": execution.progress,
            "current_step": execution.current_step,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "session_assignments": execution.session_assignments,
            "error_log": execution.error_log,
            "result": execution.result
        }    
  
  # Checkpoint and recovery system
    async def _checkpoint_manager(self):
        """Manage workflow checkpoints for recovery"""
        while self.is_running:
            try:
                # Create checkpoints for running workflows
                for execution in self.active_executions.values():
                    if execution.status == WorkflowStatus.RUNNING:
                        await self._create_checkpoint(execution)
                
                await asyncio.sleep(self.checkpoint_interval)
                
            except Exception as e:
                logger.error(f"Error in checkpoint manager: {e}")
                await asyncio.sleep(30)
    
    async def _create_checkpoint(self, execution: WorkflowExecution):
        """Create a checkpoint for workflow recovery"""
        checkpoint = {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "progress": execution.progress,
            "current_step": execution.current_step,
            "session_assignments": execution.session_assignments,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        execution.checkpoints.append(checkpoint)
        
        # Keep only last 10 checkpoints
        if len(execution.checkpoints) > 10:
            execution.checkpoints.pop(0)
        
        logger.debug(f"Created checkpoint for workflow: {execution.id}")
    
    async def recover_workflow(self, execution_id: str) -> bool:
        """Recover a workflow from the latest checkpoint"""
        # Find execution in history or active executions
        execution = None
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
        else:
            for hist_execution in self.execution_history:
                if hist_execution.id == execution_id:
                    execution = hist_execution
                    break
        
        if not execution or not execution.checkpoints:
            logger.error(f"No checkpoints found for workflow: {execution_id}")
            return False
        
        try:
            # Get latest checkpoint
            latest_checkpoint = execution.checkpoints[-1]
            
            # Restore execution state
            execution.status = WorkflowStatus.RUNNING
            execution.current_step = latest_checkpoint["current_step"]
            execution.progress = latest_checkpoint["progress"]
            execution.session_assignments = latest_checkpoint["session_assignments"]
            
            # Move back to active executions if needed
            if execution_id not in self.active_executions:
                self.active_executions[execution_id] = execution
            
            # Re-queue for execution
            workflow_def = self.workflow_definitions[execution.workflow_id]
            await self.execution_queue.put((workflow_def.priority.value, execution_id, None))
            
            logger.info(f"Recovered workflow from checkpoint: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to recover workflow {execution_id}: {e}")
            return False
    
    # Monitoring and metrics
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        active_workflows = len(self.active_executions)
        running_workflows = len([e for e in self.active_executions.values() 
                                if e.status == WorkflowStatus.RUNNING])
        
        # Session utilization
        total_sessions = len(self.session_workload)
        active_sessions = len([w for w in self.session_workload.values() if w > 0])
        
        # Performance metrics
        completed_workflows = len([e for e in self.execution_history 
                                 if e.status == WorkflowStatus.COMPLETED])
        failed_workflows = len([e for e in self.execution_history 
                              if e.status == WorkflowStatus.FAILED])
        
        success_rate = 0.0
        if completed_workflows + failed_workflows > 0:
            success_rate = completed_workflows / (completed_workflows + failed_workflows)
        
        return {
            "active_workflows": active_workflows,
            "running_workflows": running_workflows,
            "queued_workflows": self.execution_queue.qsize(),
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "session_utilization": active_sessions / max(total_sessions, 1),
            "completed_workflows": completed_workflows,
            "failed_workflows": failed_workflows,
            "success_rate": success_rate,
            "workflow_definitions": len(self.workflow_definitions),
            "system_uptime": datetime.utcnow().isoformat(),
            "is_running": self.is_running
        }
    
    async def get_session_distribution(self) -> Dict[str, Any]:
        """Get session distribution and load balancing metrics"""
        distribution = {}
        
        for session_id, workload in self.session_workload.items():
            capabilities = self.session_capabilities.get(session_id, [])
            distribution[session_id] = {
                "workload": workload,
                "capabilities": capabilities,
                "utilization": min(workload / 5.0, 1.0)  # Assume max 5 concurrent tasks per session
            }
        
        return {
            "session_distribution": distribution,
            "total_sessions": len(distribution),
            "average_workload": sum(self.session_workload.values()) / max(len(self.session_workload), 1),
            "overloaded_sessions": len([w for w in self.session_workload.values() if w > 3])
        }
    
    # Shutdown and cleanup
    async def shutdown(self):
        """Gracefully shutdown the Director orchestration system"""
        logger.info("Shutting down Director orchestration system...")
        
        self.is_running = False
        
        # Cancel running workflows
        for execution_id in list(self.active_executions.keys()):
            await self.cancel_workflow(execution_id)
        
        # Stop background tasks
        if self.workflow_executor_task:
            self.workflow_executor_task.cancel()
            try:
                await self.workflow_executor_task
            except asyncio.CancelledError:
                pass
        
        if self.checkpoint_task:
            self.checkpoint_task.cancel()
            try:
                await self.checkpoint_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown components
        await self.session_manager.shutdown()
        await self.stagehand_controller.shutdown()
        
        logger.info("Director orchestration system shutdown complete")


# Convenience functions for common workflow operations
async def create_job_discovery_workflow(
    director: DirectorOrchestrator,
    keywords: List[str],
    parallel: bool = True
) -> str:
    """Create and execute a job discovery workflow"""
    steps = [
        {
            "id": "setup_sessions",
            "name": "Setup Browser Sessions",
            "action": "create_session_pool",
            "parameters": {"pool_size": 3, "session_type": "job_discovery"}
        }
    ]
    
    # Add search steps for each keyword group
    for i, keyword_group in enumerate([keywords[i:i+2] for i in range(0, len(keywords), 2)]):
        steps.append({
            "id": f"search_keywords_{i}",
            "name": f"Search Keywords Group {i+1}",
            "action": "search_jobs",
            "parameters": {"keywords": keyword_group},
            "dependencies": ["setup_sessions"]
        })
    
    # Add merge step
    search_step_ids = [f"search_keywords_{i}" for i in range(len(steps) - 1)]
    steps.append({
        "id": "merge_results",
        "name": "Merge and Deduplicate Results",
        "action": "merge_job_results",
        "parameters": {},
        "dependencies": search_step_ids
    })
    
    workflow_id = await director.create_workflow(
        name="Dynamic Job Discovery",
        description=f"Discover jobs for keywords: {', '.join(keywords)}",
        steps=steps,
        parallel_execution=parallel,
        session_requirements={"min_sessions": 3, "session_type": "job_discovery"}
    )
    
    return await director.execute_workflow(workflow_id)


async def create_proposal_submission_workflow(
    director: DirectorOrchestrator,
    proposals: List[Dict[str, Any]],
    batch_size: int = 5
) -> str:
    """Create and execute a proposal submission workflow"""
    steps = [
        {
            "id": "validate_proposals",
            "name": "Validate Proposal Data",
            "action": "validate_proposals",
            "parameters": {"proposals": proposals}
        },
        {
            "id": "acquire_sessions",
            "name": "Acquire Submission Sessions",
            "action": "acquire_sessions",
            "parameters": {"session_type": "proposal_submission", "count": 2},
            "dependencies": ["validate_proposals"]
        }
    ]
    
    # Add batch submission steps
    num_batches = (len(proposals) + batch_size - 1) // batch_size
    for i in range(num_batches):
        batch_proposals = proposals[i * batch_size:(i + 1) * batch_size]
        steps.append({
            "id": f"submit_batch_{i}",
            "name": f"Submit Batch {i+1}",
            "action": "submit_proposals",
            "parameters": {"proposals": batch_proposals, "batch_size": batch_size},
            "dependencies": ["acquire_sessions"]
        })
    
    # Add verification step
    batch_step_ids = [f"submit_batch_{i}" for i in range(num_batches)]
    steps.append({
        "id": "verify_submissions",
        "name": "Verify All Submissions",
        "action": "verify_submissions",
        "parameters": {},
        "dependencies": batch_step_ids
    })
    
    workflow_id = await director.create_workflow(
        name="Batch Proposal Submission",
        description=f"Submit {len(proposals)} proposals in {num_batches} batches",
        steps=steps,
        parallel_execution=True,
        max_concurrent_steps=2,
        session_requirements={"min_sessions": 2, "session_type": "proposal_submission"}
    )
    
    return await director.execute_workflow(workflow_id)