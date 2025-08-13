"""
Basic tests for Director Session Orchestration System
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from director import (
    DirectorOrchestrator, WorkflowDefinition, WorkflowStep, WorkflowExecution,
    WorkflowStatus, StepStatus, WorkflowPriority
)


class TestDirectorBasic:
    """Basic test cases for DirectorOrchestrator"""
    
    @pytest.fixture
    def director(self):
        """Create a basic Director instance for testing"""
        # Create with minimal mocking
        director = DirectorOrchestrator()
        
        # Mock the components to avoid actual initialization
        director.session_manager = Mock()
        director.session_manager.initialize_session_pools = AsyncMock()
        director.session_manager.shutdown = AsyncMock()
        director.session_manager.get_session_for_task = Mock()
        
        director.stagehand_controller = Mock()
        director.stagehand_controller.shutdown = AsyncMock()
        
        director.browserbase_client = Mock()
        director.browserbase_client.create_session_pool = AsyncMock(return_value=["s1", "s2", "s3"])
        
        # Don't start background tasks
        director.is_running = False
        
        return director
    
    def test_workflow_step_creation(self):
        """Test WorkflowStep creation"""
        step = WorkflowStep(
            id="test_step",
            name="Test Step",
            action="test_action",
            parameters={"param1": "value1"},
            dependencies=["dep1"],
            timeout=300,
            max_retries=3
        )
        
        assert step.id == "test_step"
        assert step.name == "Test Step"
        assert step.action == "test_action"
        assert step.parameters == {"param1": "value1"}
        assert step.dependencies == ["dep1"]
        assert step.timeout == 300
        assert step.max_retries == 3
        assert step.status == StepStatus.PENDING
        assert step.retry_count == 0
    
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
            steps=steps,
            parallel_execution=True,
            max_concurrent_steps=2,
            priority=WorkflowPriority.HIGH
        )
        
        assert workflow.id == "test_workflow"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.steps) == 2
        assert workflow.parallel_execution is True
        assert workflow.max_concurrent_steps == 2
        assert workflow.priority == WorkflowPriority.HIGH
    
    def test_workflow_execution_creation(self):
        """Test WorkflowExecution creation"""
        execution = WorkflowExecution(
            id="exec_1",
            workflow_id="workflow_1"
        )
        
        assert execution.id == "exec_1"
        assert execution.workflow_id == "workflow_1"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.progress == 0.0
        assert execution.session_assignments == {}
        assert execution.checkpoints == []
        assert execution.error_log == []
    
    @pytest.mark.asyncio
    async def test_director_initialization(self, director):
        """Test Director initialization"""
        await director.initialize()
        
        # Check that session manager was initialized
        director.session_manager.initialize_session_pools.assert_called_once()
        
        # Check that predefined workflows are loaded
        assert len(director.workflow_definitions) > 0
    
    @pytest.mark.asyncio
    async def test_create_simple_workflow(self, director):
        """Test creating a simple workflow"""
        steps = [
            {
                "id": "step1",
                "name": "Test Step",
                "action": "test_action",
                "parameters": {"test": "value"}
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Simple Test",
            description="A simple test workflow",
            steps=steps
        )
        
        assert workflow_id in director.workflow_definitions
        
        workflow = director.workflow_definitions[workflow_id]
        assert workflow.name == "Simple Test"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step1"
        assert workflow.steps[0].action == "test_action"
    
    @pytest.mark.asyncio
    async def test_execute_workflow_queuing(self, director):
        """Test workflow execution queuing"""
        await director.initialize()
        
        # Use a predefined workflow
        workflow_id = list(director.workflow_definitions.keys())[0]
        
        execution_id = await director.execute_workflow(workflow_id)
        
        assert execution_id in director.active_executions
        
        execution = director.active_executions[execution_id]
        assert execution.workflow_id == workflow_id
        assert execution.status == WorkflowStatus.PENDING
        
        # Check that workflow was queued
        assert not director.execution_queue.empty()
    
    @pytest.mark.asyncio
    async def test_workflow_status_retrieval(self, director):
        """Test getting workflow status"""
        await director.initialize()
        
        workflow_id = list(director.workflow_definitions.keys())[0]
        execution_id = await director.execute_workflow(workflow_id)
        
        status = await director.get_workflow_status(execution_id)
        
        assert status is not None
        assert status["id"] == execution_id
        assert status["workflow_id"] == workflow_id
        assert status["status"] == WorkflowStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_system_metrics(self, director):
        """Test system metrics collection"""
        await director.initialize()
        
        metrics = await director.get_system_metrics()
        
        assert "active_workflows" in metrics
        assert "running_workflows" in metrics
        assert "queued_workflows" in metrics
        assert "success_rate" in metrics
        assert "workflow_definitions" in metrics
        assert "is_running" in metrics
        
        assert metrics["workflow_definitions"] > 0
    
    @pytest.mark.asyncio
    async def test_director_shutdown(self, director):
        """Test Director shutdown"""
        await director.initialize()
        
        # Add a test execution
        workflow_id = list(director.workflow_definitions.keys())[0]
        execution_id = await director.execute_workflow(workflow_id)
        
        # Shutdown
        await director.shutdown()
        
        # Check that components were shut down
        director.session_manager.shutdown.assert_called_once()
        director.stagehand_controller.shutdown.assert_called_once()
        
        # Check that running flag is set to False
        assert director.is_running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])