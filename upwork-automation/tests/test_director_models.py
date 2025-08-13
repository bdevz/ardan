"""
Tests for Director data models and basic functionality
"""
import pytest
from datetime import datetime
from enum import Enum

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

# Import only the data models to avoid dependency issues
from director import (
    WorkflowStep, WorkflowDefinition, WorkflowExecution,
    WorkflowStatus, StepStatus, WorkflowPriority
)


class TestWorkflowModels:
    """Test workflow data models"""
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])