"""
Tests for Director Session Orchestration System
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from browser_automation.director import (
    DirectorOrchestrator, WorkflowDefinition, WorkflowStep, WorkflowExecution,
    WorkflowStatus, StepStatus, WorkflowPriority,
    create_job_discovery_workflow, create_proposal_submission_workflow
)
from browser_automation.session_manager import SessionManager, SessionType
from browser_automation.stagehand_controller import StagehandController
from browser_automation.browserbase_client import BrowserbaseClient


class TestDirectorOrchestrator:
    """Test cases for DirectorOrchestrator"""
    
    @pytest.fixture
    async def director(self):
        """Create a Director instance for testing"""
        mock_session_manager = Mock(spec=SessionManager)
        mock_session_manager.initialize_session_pools = AsyncMock()
        mock_session_manager.get_session_for_task = AsyncMock()
        mock_session_manager.shutdown = AsyncMock()
        
        mock_stagehand = Mock(spec=StagehandController)
        mock_stagehand.shutdown = AsyncMock()
        
        mock_browserbase = Mock(spec=BrowserbaseClient)
        mock_browserbase.create_session_pool = AsyncMock(return_value=["session1", "session2", "session3"])
        
        director = DirectorOrchestrator(
            session_manager=mock_session_manager,
            stagehand_controller=mock_stagehand,
            browserbase_client=mock_browserbase
        )
        
        # Don't actually start background tasks in tests
        director.is_running = False
        
        yield director
        
        # Cleanup
        await director.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self, director):
        """Test Director initialization"""
        await director.initialize()
        
        # Check that predefined workflows are loaded
        assert len(director.workflow_definitions) > 0
        assert "job_discovery_parallel" in director.workflow_definitions
        assert "proposal_submission_batch" in director.workflow_definitions
        
        # Check that session manager was initialized
        director.session_manager.initialize_session_pools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, director):
        """Test workflow creation"""
        steps = [
            {
                "id": "step1",
                "name": "Test Step 1",
                "action": "test_action",
                "parameters": {"param1": "value1"}
            },
            {
                "id": "step2",
                "name": "Test Step 2",
                "action": "test_action2",
                "parameters": {"param2": "value2"},
                "dependencies": ["step1"]
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            parallel_execution=True,
            max_concurrent_steps=2
        )
        
        assert workflow_id in director.workflow_definitions
        
        workflow = director.workflow_definitions[workflow_id]
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.steps) == 2
        assert workflow.parallel_execution is True
        assert workflow.max_concurrent_steps == 2
        
        # Check step details
        step1 = workflow.steps[0]
        assert step1.id == "step1"
        assert step1.name == "Test Step 1"
        assert step1.action == "test_action"
        assert step1.parameters == {"param1": "value1"}
        assert step1.dependencies == []
        
        step2 = workflow.steps[1]
        assert step2.id == "step2"
        assert step2.dependencies == ["step1"]
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, director):
        """Test workflow execution queuing"""
        await director.initialize()
        
        # Use a predefined workflow
        workflow_id = "job_discovery_parallel"
        
        execution_id = await director.execute_workflow(workflow_id)
        
        assert execution_id in director.active_executions
        
        execution = director.active_executions[execution_id]
        assert execution.workflow_id == workflow_id
        assert execution.status == WorkflowStatus.PENDING
        
        # Check that workflow was queued
        assert not director.execution_queue.empty()
    
    @pytest.mark.asyncio
    async def test_workflow_step_execution(self, director):
        """Test individual workflow step execution"""
        await director.initialize()
        
        # Create a simple workflow
        steps = [
            {
                "id": "create_sessions",
                "name": "Create Sessions",
                "action": "create_session_pool",
                "parameters": {"pool_size": 2}
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Simple Test Workflow",
            description="Test workflow with one step",
            steps=steps
        )
        
        workflow_def = director.workflow_definitions[workflow_id]
        execution = WorkflowExecution(id="test_exec", workflow_id=workflow_id)
        
        # Mock the step action execution
        with patch.object(director, '_execute_step_action') as mock_execute:
            mock_execute.return_value = {"sessions_created": 2, "session_ids": ["s1", "s2"]}
            
            await director._execute_sequential_workflow(execution, workflow_def, None)
            
            # Check that step was executed
            mock_execute.assert_called_once()
            
            # Check execution result
            assert execution.result is not None
            assert "create_sessions" in execution.result
    
    @pytest.mark.asyncio
    async def test_parallel_workflow_execution(self, director):
        """Test parallel workflow execution"""
        await director.initialize()
        
        # Create a workflow with parallel steps
        steps = [
            {
                "id": "step1",
                "name": "Parallel Step 1",
                "action": "test_action",
                "parameters": {}
            },
            {
                "id": "step2",
                "name": "Parallel Step 2",
                "action": "test_action",
                "parameters": {}
            },
            {
                "id": "step3",
                "name": "Dependent Step",
                "action": "test_action",
                "parameters": {},
                "dependencies": ["step1", "step2"]
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Parallel Test Workflow",
            description="Test parallel execution",
            steps=steps,
            parallel_execution=True,
            max_concurrent_steps=2
        )
        
        workflow_def = director.workflow_definitions[workflow_id]
        execution = WorkflowExecution(id="test_parallel", workflow_id=workflow_id)
        
        # Mock the step action execution
        with patch.object(director, '_execute_step_action') as mock_execute:
            mock_execute.return_value = {"success": True}
            
            await director._execute_parallel_workflow(execution, workflow_def, None)
            
            # Check that all steps were executed
            assert mock_execute.call_count == 3
            
            # Check execution result
            assert execution.result is not None
            assert len(execution.result) == 3
    
    @pytest.mark.asyncio
    async def test_workflow_pause_resume(self, director):
        """Test workflow pause and resume functionality"""
        await director.initialize()
        
        workflow_id = "job_discovery_parallel"
        execution_id = await director.execute_workflow(workflow_id)
        
        # Set execution to running state
        execution = director.active_executions[execution_id]
        execution.status = WorkflowStatus.RUNNING
        
        # Test pause
        result = await director.pause_workflow(execution_id)
        assert result is True
        assert execution.status == WorkflowStatus.PAUSED
        assert len(execution.checkpoints) > 0
        
        # Test resume
        result = await director.resume_workflow(execution_id)
        assert result is True
        assert execution.status == WorkflowStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, director):
        """Test workflow cancellation"""
        await director.initialize()
        
        workflow_id = "job_discovery_parallel"
        execution_id = await director.execute_workflow(workflow_id)
        
        # Test cancel
        result = await director.cancel_workflow(execution_id)
        assert result is True
        
        execution = director.active_executions[execution_id]
        assert execution.status == WorkflowStatus.CANCELLED
        assert execution.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_workflow_status_retrieval(self, director):
        """Test workflow status retrieval"""
        await director.initialize()
        
        workflow_id = "job_discovery_parallel"
        execution_id = await director.execute_workflow(workflow_id)
        
        # Get status
        status = await director.get_workflow_status(execution_id)
        
        assert status is not None
        assert status["id"] == execution_id
        assert status["workflow_id"] == workflow_id
        assert status["status"] == WorkflowStatus.PENDING.value
        assert "workflow_name" in status
        assert "progress" in status
    
    @pytest.mark.asyncio
    async def test_checkpoint_creation(self, director):
        """Test checkpoint creation and recovery"""
        await director.initialize()
        
        workflow_id = "job_discovery_parallel"
        execution_id = await director.execute_workflow(workflow_id)
        
        execution = director.active_executions[execution_id]
        execution.status = WorkflowStatus.RUNNING
        execution.current_step = "test_step"
        execution.progress = 0.5
        
        # Create checkpoint
        await director._create_checkpoint(execution)
        
        assert len(execution.checkpoints) == 1
        checkpoint = execution.checkpoints[0]
        assert checkpoint["execution_id"] == execution_id
        assert checkpoint["status"] == WorkflowStatus.RUNNING.value
        assert checkpoint["current_step"] == "test_step"
        assert checkpoint["progress"] == 0.5
    
    @pytest.mark.asyncio
    async def test_workflow_recovery(self, director):
        """Test workflow recovery from checkpoint"""
        await director.initialize()
        
        workflow_id = "job_discovery_parallel"
        execution_id = await director.execute_workflow(workflow_id)
        
        execution = director.active_executions[execution_id]
        execution.status = WorkflowStatus.RUNNING
        execution.current_step = "test_step"
        execution.progress = 0.5
        
        # Create checkpoint
        await director._create_checkpoint(execution)
        
        # Simulate failure
        execution.status = WorkflowStatus.FAILED
        
        # Recover workflow
        result = await director.recover_workflow(execution_id)
        assert result is True
        assert execution.status == WorkflowStatus.RUNNING
        assert execution.current_step == "test_step"
        assert execution.progress == 0.5
    
    @pytest.mark.asyncio
    async def test_system_metrics(self, director):
        """Test system metrics collection"""
        await director.initialize()
        
        # Add some test executions
        workflow_id = "job_discovery_parallel"
        execution_id1 = await director.execute_workflow(workflow_id)
        execution_id2 = await director.execute_workflow(workflow_id)
        
        # Set different statuses
        director.active_executions[execution_id1].status = WorkflowStatus.RUNNING
        director.active_executions[execution_id2].status = WorkflowStatus.PENDING
        
        # Add some completed workflows to history
        completed_execution = WorkflowExecution(id="completed", workflow_id=workflow_id)
        completed_execution.status = WorkflowStatus.COMPLETED
        director.execution_history.append(completed_execution)
        
        failed_execution = WorkflowExecution(id="failed", workflow_id=workflow_id)
        failed_execution.status = WorkflowStatus.FAILED
        director.execution_history.append(failed_execution)
        
        # Get metrics
        metrics = await director.get_system_metrics()
        
        assert metrics["active_workflows"] == 2
        assert metrics["running_workflows"] == 1
        assert metrics["completed_workflows"] == 1
        assert metrics["failed_workflows"] == 1
        assert metrics["success_rate"] == 0.5
        assert metrics["workflow_definitions"] > 0
        assert "system_uptime" in metrics
    
    @pytest.mark.asyncio
    async def test_session_distribution(self, director):
        """Test session distribution metrics"""
        await director.initialize()
        
        # Add some session workload data
        director.session_workload = {
            "session1": 2,
            "session2": 1,
            "session3": 0
        }
        
        director.session_capabilities = {
            "session1": ["job_discovery", "proposal_submission"],
            "session2": ["job_discovery"],
            "session3": ["profile_management"]
        }
        
        distribution = await director.get_session_distribution()
        
        assert distribution["total_sessions"] == 3
        assert distribution["average_workload"] == 1.0
        assert distribution["overloaded_sessions"] == 0
        
        session_dist = distribution["session_distribution"]
        assert session_dist["session1"]["workload"] == 2
        assert session_dist["session1"]["utilization"] == 0.4  # 2/5
        assert len(session_dist["session1"]["capabilities"]) == 2


class TestWorkflowConvenienceFunctions:
    """Test convenience functions for workflow creation"""
    
    @pytest.fixture
    async def director(self):
        """Create a Director instance for testing"""
        mock_session_manager = Mock(spec=SessionManager)
        mock_session_manager.initialize_session_pools = AsyncMock()
        mock_session_manager.shutdown = AsyncMock()
        
        mock_stagehand = Mock(spec=StagehandController)
        mock_stagehand.shutdown = AsyncMock()
        
        mock_browserbase = Mock(spec=BrowserbaseClient)
        
        director = DirectorOrchestrator(
            session_manager=mock_session_manager,
            stagehand_controller=mock_stagehand,
            browserbase_client=mock_browserbase
        )
        
        director.is_running = False
        
        yield director
        
        await director.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_job_discovery_workflow(self, director):
        """Test job discovery workflow creation"""
        keywords = ["Salesforce", "Agentforce", "Einstein", "AI"]
        
        execution_id = await create_job_discovery_workflow(director, keywords, parallel=True)
        
        assert execution_id in director.active_executions
        
        # Find the created workflow
        execution = director.active_executions[execution_id]
        workflow = director.workflow_definitions[execution.workflow_id]
        
        assert "Dynamic Job Discovery" in workflow.name
        assert workflow.parallel_execution is True
        assert len(workflow.steps) >= 3  # setup + search steps + merge
        
        # Check that merge step depends on search steps
        merge_step = next(step for step in workflow.steps if step.id == "merge_results")
        assert len(merge_step.dependencies) > 0
    
    @pytest.mark.asyncio
    async def test_create_proposal_submission_workflow(self, director):
        """Test proposal submission workflow creation"""
        proposals = [
            {"job_url": "url1", "content": "content1", "bid_amount": 50},
            {"job_url": "url2", "content": "content2", "bid_amount": 60},
            {"job_url": "url3", "content": "content3", "bid_amount": 70},
        ]
        
        execution_id = await create_proposal_submission_workflow(
            director, proposals, batch_size=2
        )
        
        assert execution_id in director.active_executions
        
        # Find the created workflow
        execution = director.active_executions[execution_id]
        workflow = director.workflow_definitions[execution.workflow_id]
        
        assert "Batch Proposal Submission" in workflow.name
        assert workflow.parallel_execution is True
        
        # Should have validation, acquire, batch steps, and verification
        step_actions = [step.action for step in workflow.steps]
        assert "validate_proposals" in step_actions
        assert "acquire_sessions" in step_actions
        assert "submit_proposals" in step_actions
        assert "verify_submissions" in step_actions
        
        # Check batch steps
        batch_steps = [step for step in workflow.steps if "submit_batch" in step.id]
        assert len(batch_steps) == 2  # 3 proposals with batch_size=2 should create 2 batches


class TestWorkflowStepRetry:
    """Test workflow step retry logic"""
    
    @pytest.fixture
    async def director(self):
        """Create a Director instance for testing"""
        mock_session_manager = Mock(spec=SessionManager)
        mock_session_manager.initialize_session_pools = AsyncMock()
        mock_session_manager.shutdown = AsyncMock()
        
        mock_stagehand = Mock(spec=StagehandController)
        mock_stagehand.shutdown = AsyncMock()
        
        mock_browserbase = Mock(spec=BrowserbaseClient)
        
        director = DirectorOrchestrator(
            session_manager=mock_session_manager,
            stagehand_controller=mock_stagehand,
            browserbase_client=mock_browserbase
        )
        
        director.is_running = False
        
        yield director
        
        await director.shutdown()
    
    @pytest.mark.asyncio
    async def test_step_retry_logic(self, director):
        """Test that failed steps are retried according to max_retries"""
        await director.initialize()
        
        # Create a workflow with a step that will fail
        steps = [
            {
                "id": "failing_step",
                "name": "Failing Step",
                "action": "test_action",
                "parameters": {},
                "max_retries": 2
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Retry Test Workflow",
            description="Test retry logic",
            steps=steps
        )
        
        workflow_def = director.workflow_definitions[workflow_id]
        execution = WorkflowExecution(id="test_retry", workflow_id=workflow_id)
        
        # Mock the step action to fail initially, then succeed
        call_count = 0
        def mock_execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 times
                raise Exception("Simulated failure")
            return {"success": True}  # Succeed on 3rd try
        
        with patch.object(director, '_execute_step_action', side_effect=mock_execute_side_effect):
            await director._execute_sequential_workflow(execution, workflow_def, None)
            
            # Check that step was retried and eventually succeeded
            step = workflow_def.steps[0]
            assert step.retry_count == 2
            assert step.status == StepStatus.COMPLETED
            assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_step_max_retries_exceeded(self, director):
        """Test that steps fail permanently after max retries"""
        await director.initialize()
        
        steps = [
            {
                "id": "always_failing_step",
                "name": "Always Failing Step",
                "action": "test_action",
                "parameters": {},
                "max_retries": 1
            }
        ]
        
        workflow_id = await director.create_workflow(
            name="Max Retry Test Workflow",
            description="Test max retry logic",
            steps=steps
        )
        
        workflow_def = director.workflow_definitions[workflow_id]
        execution = WorkflowExecution(id="test_max_retry", workflow_id=workflow_id)
        
        # Mock the step action to always fail
        with patch.object(director, '_execute_step_action', side_effect=Exception("Always fails")):
            with pytest.raises(Exception, match="Always fails"):
                await director._execute_sequential_workflow(execution, workflow_def, None)
            
            # Check that step failed permanently
            step = workflow_def.steps[0]
            assert step.retry_count == 1
            assert step.status == StepStatus.FAILED
            assert "Always fails" in step.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])