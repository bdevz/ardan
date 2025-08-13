"""
Standalone tests for Director data models
"""
import pytest
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# Copy the data models here for standalone testing
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


class TestDirectorDataModels:
    """Test Director data models"""
    
    def test_workflow_status_enum(self):
        """Test WorkflowStatus enum values"""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.PAUSED.value == "paused"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
    
    def test_step_status_enum(self):
        """Test StepStatus enum values"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.RETRYING.value == "retrying"
    
    def test_workflow_priority_enum(self):
        """Test WorkflowPriority enum values"""
        assert WorkflowPriority.LOW.value == 1
        assert WorkflowPriority.NORMAL.value == 2
        assert WorkflowPriority.HIGH.value == 3
        assert WorkflowPriority.CRITICAL.value == 4
    
    def test_workflow_step_creation(self):
        """Test WorkflowStep creation and default values"""
        step = WorkflowStep(
            id="test_step",
            name="Test Step",
            action="test_action"
        )
        
        assert step.id == "test_step"
        assert step.name == "Test Step"
        assert step.action == "test_action"
        assert step.parameters == {}
        assert step.dependencies == []
        assert step.timeout == 300
        assert step.retry_count == 0
        assert step.max_retries == 3
        assert step.status == StepStatus.PENDING
        assert step.result is None
        assert step.error_message is None
        assert step.started_at is None
        assert step.completed_at is None
        assert step.session_id is None
    
    def test_workflow_step_with_parameters(self):
        """Test WorkflowStep with custom parameters"""
        step = WorkflowStep(
            id="custom_step",
            name="Custom Step",
            action="custom_action",
            parameters={"param1": "value1", "param2": 42},
            dependencies=["dep1", "dep2"],
            timeout=600,
            max_retries=5
        )
        
        assert step.parameters == {"param1": "value1", "param2": 42}
        assert step.dependencies == ["dep1", "dep2"]
        assert step.timeout == 600
        assert step.max_retries == 5
    
    def test_workflow_definition_creation(self):
        """Test WorkflowDefinition creation"""
        steps = [
            WorkflowStep(id="step1", name="Step 1", action="action1"),
            WorkflowStep(id="step2", name="Step 2", action="action2", dependencies=["step1"])
        ]
        
        workflow = WorkflowDefinition(
            id="test_workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=steps
        )
        
        assert workflow.id == "test_workflow"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.steps) == 2
        assert workflow.session_requirements == {}
        assert workflow.parallel_execution is False
        assert workflow.max_concurrent_steps == 3
        assert workflow.timeout == 1800
        assert workflow.priority == WorkflowPriority.NORMAL
        assert workflow.metadata == {}
    
    def test_workflow_definition_with_custom_settings(self):
        """Test WorkflowDefinition with custom settings"""
        steps = [WorkflowStep(id="step1", name="Step 1", action="action1")]
        
        workflow = WorkflowDefinition(
            id="custom_workflow",
            name="Custom Workflow",
            description="Custom workflow",
            steps=steps,
            session_requirements={"min_sessions": 2, "session_type": "job_discovery"},
            parallel_execution=True,
            max_concurrent_steps=5,
            timeout=3600,
            priority=WorkflowPriority.HIGH,
            metadata={"created_by": "test", "version": "1.0"}
        )
        
        assert workflow.session_requirements == {"min_sessions": 2, "session_type": "job_discovery"}
        assert workflow.parallel_execution is True
        assert workflow.max_concurrent_steps == 5
        assert workflow.timeout == 3600
        assert workflow.priority == WorkflowPriority.HIGH
        assert workflow.metadata == {"created_by": "test", "version": "1.0"}
    
    def test_workflow_execution_creation(self):
        """Test WorkflowExecution creation"""
        execution = WorkflowExecution(
            id="exec_1",
            workflow_id="workflow_1"
        )
        
        assert execution.id == "exec_1"
        assert execution.workflow_id == "workflow_1"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.current_step is None
        assert execution.progress == 0.0
        assert execution.session_assignments == {}
        assert execution.checkpoints == []
        assert execution.error_log == []
        assert execution.started_at is None
        assert execution.completed_at is None
        assert execution.result is None
    
    def test_workflow_execution_state_changes(self):
        """Test WorkflowExecution state changes"""
        execution = WorkflowExecution(
            id="exec_test",
            workflow_id="workflow_test"
        )
        
        # Test status change
        execution.status = WorkflowStatus.RUNNING
        assert execution.status == WorkflowStatus.RUNNING
        
        # Test progress update
        execution.progress = 0.5
        assert execution.progress == 0.5
        
        # Test current step update
        execution.current_step = "step_1"
        assert execution.current_step == "step_1"
        
        # Test session assignments
        execution.session_assignments["step_1"] = "session_123"
        assert execution.session_assignments["step_1"] == "session_123"
        
        # Test error log
        execution.error_log.append("Test error message")
        assert len(execution.error_log) == 1
        assert execution.error_log[0] == "Test error message"
        
        # Test checkpoints
        checkpoint = {
            "execution_id": execution.id,
            "timestamp": datetime.utcnow().isoformat(),
            "progress": execution.progress
        }
        execution.checkpoints.append(checkpoint)
        assert len(execution.checkpoints) == 1
        assert execution.checkpoints[0]["execution_id"] == execution.id
    
    def test_workflow_step_status_transitions(self):
        """Test WorkflowStep status transitions"""
        step = WorkflowStep(
            id="transition_test",
            name="Transition Test",
            action="test_action"
        )
        
        # Initial state
        assert step.status == StepStatus.PENDING
        assert step.retry_count == 0
        
        # Start execution
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None
        
        # Fail and retry
        step.status = StepStatus.FAILED
        step.error_message = "Test failure"
        step.retry_count += 1
        assert step.status == StepStatus.FAILED
        assert step.error_message == "Test failure"
        assert step.retry_count == 1
        
        # Retry
        step.status = StepStatus.RETRYING
        assert step.status == StepStatus.RETRYING
        
        # Complete successfully
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        step.result = {"success": True, "data": "test_result"}
        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None
        assert step.result["success"] is True
    
    def test_workflow_dependency_validation(self):
        """Test workflow step dependency relationships"""
        step1 = WorkflowStep(id="step1", name="Step 1", action="action1")
        step2 = WorkflowStep(id="step2", name="Step 2", action="action2", dependencies=["step1"])
        step3 = WorkflowStep(id="step3", name="Step 3", action="action3", dependencies=["step1", "step2"])
        
        workflow = WorkflowDefinition(
            id="dependency_test",
            name="Dependency Test",
            description="Test workflow dependencies",
            steps=[step1, step2, step3]
        )
        
        # Verify dependencies are correctly set
        assert step1.dependencies == []
        assert step2.dependencies == ["step1"]
        assert step3.dependencies == ["step1", "step2"]
        
        # Create a simple dependency checker
        def can_execute_step(step, completed_steps):
            return all(dep in completed_steps for dep in step.dependencies)
        
        completed_steps = set()
        
        # Initially, only step1 can execute
        assert can_execute_step(step1, completed_steps) is True
        assert can_execute_step(step2, completed_steps) is False
        assert can_execute_step(step3, completed_steps) is False
        
        # After step1 completes, step2 can execute
        completed_steps.add("step1")
        assert can_execute_step(step1, completed_steps) is True
        assert can_execute_step(step2, completed_steps) is True
        assert can_execute_step(step3, completed_steps) is False
        
        # After step2 completes, step3 can execute
        completed_steps.add("step2")
        assert can_execute_step(step1, completed_steps) is True
        assert can_execute_step(step2, completed_steps) is True
        assert can_execute_step(step3, completed_steps) is True
    
    def test_workflow_step_retry_logic(self):
        """Test workflow step retry logic"""
        step = WorkflowStep(
            id="retry_test",
            name="Retry Test",
            action="failing_action",
            max_retries=3
        )
        
        # Simulate multiple failures
        for i in range(3):
            step.status = StepStatus.FAILED
            step.error_message = f"Failure {i+1}"
            step.retry_count += 1
            
            if step.retry_count < step.max_retries:
                step.status = StepStatus.RETRYING
                assert step.status == StepStatus.RETRYING
            else:
                # Max retries reached
                assert step.retry_count == step.max_retries
                assert step.status == StepStatus.FAILED
        
        # Verify final state
        assert step.retry_count == 3
        assert step.status == StepStatus.FAILED
        assert "Failure 3" in step.error_message
    
    def test_workflow_execution_progress_tracking(self):
        """Test workflow execution progress tracking"""
        execution = WorkflowExecution(
            id="progress_test",
            workflow_id="test_workflow"
        )
        
        # Initial progress
        assert execution.progress == 0.0
        
        # Simulate progress updates
        progress_values = [0.2, 0.4, 0.6, 0.8, 1.0]
        
        for progress in progress_values:
            execution.progress = progress
            assert execution.progress == progress
        
        # Test that progress is within valid range
        assert 0.0 <= execution.progress <= 1.0
    
    def test_workflow_checkpoint_system(self):
        """Test workflow checkpoint system"""
        execution = WorkflowExecution(
            id="checkpoint_test",
            workflow_id="test_workflow"
        )
        
        # Create multiple checkpoints
        for i in range(5):
            checkpoint = {
                "execution_id": execution.id,
                "step": f"step_{i}",
                "progress": i * 0.2,
                "timestamp": datetime.utcnow().isoformat(),
                "session_assignments": {f"step_{i}": f"session_{i}"}
            }
            execution.checkpoints.append(checkpoint)
        
        assert len(execution.checkpoints) == 5
        
        # Verify checkpoint data
        for i, checkpoint in enumerate(execution.checkpoints):
            assert checkpoint["execution_id"] == execution.id
            assert checkpoint["step"] == f"step_{i}"
            assert checkpoint["progress"] == i * 0.2
            assert "timestamp" in checkpoint
            assert f"step_{i}" in checkpoint["session_assignments"]
        
        # Test checkpoint retrieval (latest)
        latest_checkpoint = execution.checkpoints[-1]
        assert latest_checkpoint["step"] == "step_4"
        assert latest_checkpoint["progress"] == 0.8


class TestWorkflowLogic:
    """Test workflow execution logic"""
    
    def test_parallel_vs_sequential_execution(self):
        """Test parallel vs sequential execution settings"""
        steps = [
            WorkflowStep(id="step1", name="Step 1", action="action1"),
            WorkflowStep(id="step2", name="Step 2", action="action2"),
            WorkflowStep(id="step3", name="Step 3", action="action3")
        ]
        
        # Sequential workflow
        sequential_workflow = WorkflowDefinition(
            id="sequential",
            name="Sequential Workflow",
            description="Sequential execution",
            steps=steps,
            parallel_execution=False
        )
        
        # Parallel workflow
        parallel_workflow = WorkflowDefinition(
            id="parallel",
            name="Parallel Workflow", 
            description="Parallel execution",
            steps=steps,
            parallel_execution=True,
            max_concurrent_steps=2
        )
        
        assert sequential_workflow.parallel_execution is False
        assert parallel_workflow.parallel_execution is True
        assert parallel_workflow.max_concurrent_steps == 2
    
    def test_workflow_priority_ordering(self):
        """Test workflow priority ordering"""
        priorities = [
            WorkflowPriority.LOW,
            WorkflowPriority.NORMAL,
            WorkflowPriority.HIGH,
            WorkflowPriority.CRITICAL
        ]
        
        # Test that priorities are ordered correctly
        priority_values = [p.value for p in priorities]
        assert priority_values == sorted(priority_values)
        
        # Test priority comparison
        assert WorkflowPriority.CRITICAL.value > WorkflowPriority.HIGH.value
        assert WorkflowPriority.HIGH.value > WorkflowPriority.NORMAL.value
        assert WorkflowPriority.NORMAL.value > WorkflowPriority.LOW.value
    
    def test_session_requirements_specification(self):
        """Test session requirements specification"""
        workflow = WorkflowDefinition(
            id="session_req_test",
            name="Session Requirements Test",
            description="Test session requirements",
            steps=[WorkflowStep(id="step1", name="Step 1", action="action1")],
            session_requirements={
                "min_sessions": 3,
                "session_type": "job_discovery",
                "capabilities": ["search", "extract"],
                "timeout": 300
            }
        )
        
        requirements = workflow.session_requirements
        assert requirements["min_sessions"] == 3
        assert requirements["session_type"] == "job_discovery"
        assert requirements["capabilities"] == ["search", "extract"]
        assert requirements["timeout"] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])