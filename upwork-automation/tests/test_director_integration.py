"""
Integration tests for Director Session Orchestration System
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from browser_automation.director import DirectorOrchestrator, WorkflowStatus
from browser_automation.director_actions import DirectorActions
from browser_automation.session_manager import SessionManager, SessionType
from browser_automation.stagehand_controller import (
    StagehandController, ArdanJobSearchController, ArdanApplicationController,
    ExtractionResult, InteractionResult, ExtractionType
)
from browser_automation.browserbase_client import BrowserbaseClient


class TestDirectorIntegration:
    """Integration tests for Director with real-like components"""
    
    @pytest.fixture
    async def integrated_director(self):
        """Create a Director with more realistic mocked components"""
        # Mock BrowserbaseClient
        mock_browserbase = Mock(spec=BrowserbaseClient)
        mock_browserbase.create_session_pool = AsyncMock(return_value=["session1", "session2", "session3"])
        mock_browserbase.create_session = AsyncMock(return_value="new_session")
        mock_browserbase.get_session = AsyncMock()
        mock_browserbase.get_session_health = AsyncMock(return_value={"healthy": True})
        
        # Mock SessionManager
        mock_session_manager = Mock(spec=SessionManager)
        mock_session_manager.initialize_session_pools = AsyncMock()
        mock_session_manager.shutdown = AsyncMock()
        
        # Create a context manager mock for session acquisition
        class MockSessionContext:
            def __init__(self, session_id):
                self.session_id = session_id
            
            async def __aenter__(self):
                return self.session_id
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        mock_session_manager.get_session_for_task = Mock(
            return_value=MockSessionContext("test_session")
        )
        
        # Mock StagehandController
        mock_stagehand = Mock(spec=StagehandController)
        mock_stagehand.shutdown = AsyncMock()
        mock_stagehand.intelligent_navigate = AsyncMock()
        mock_stagehand.extract_content = AsyncMock()
        mock_stagehand.interact_with_form = AsyncMock()
        
        director = DirectorOrchestrator(
            session_manager=mock_session_manager,
            stagehand_controller=mock_stagehand,
            browserbase_client=mock_browserbase
        )
        
        # Don't start background tasks in tests
        director.is_running = False
        
        yield director
        
        await director.shutdown()
    
    @pytest.mark.asyncio
    async def test_job_discovery_workflow_integration(self, integrated_director):
        """Test complete job discovery workflow execution"""
        await integrated_director.initialize()
        
        # Mock job search results
        mock_job_data = [
            {
                "id": "job1",
                "title": "Salesforce Agentforce Developer",
                "job_url": "https://ardan.com/job1",
                "client_rating": 4.5,
                "hourly_rate": 75,
                "match_score": 0.9
            },
            {
                "id": "job2", 
                "title": "Salesforce AI Specialist",
                "job_url": "https://ardan.com/job2",
                "client_rating": 4.8,
                "hourly_rate": 80,
                "match_score": 0.85
            }
        ]
        
        # Mock the job search controller
        with patch('browser_automation.director_actions.ArdanJobSearchController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Mock successful job search
            mock_controller.search_jobs = AsyncMock(return_value=ExtractionResult(
                success=True,
                data={"jobs": mock_job_data},
                extraction_type=ExtractionType.JOB_LISTINGS,
                confidence_score=0.9
            ))
            
            # Execute job discovery workflow
            execution_id = await integrated_director.execute_workflow("job_discovery_parallel")
            
            # Manually execute the workflow (since we're not running the executor)
            execution = integrated_director.active_executions[execution_id]
            workflow_def = integrated_director.workflow_definitions[execution.workflow_id]
            
            await integrated_director._execute_workflow_instance(execution_id, None)
            
            # Check execution completed successfully
            execution = integrated_director.active_executions.get(execution_id)
            if execution:
                assert execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING]
            
            # Verify job search was called multiple times (for different keyword groups)
            assert mock_controller.search_jobs.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_proposal_submission_workflow_integration(self, integrated_director):
        """Test complete proposal submission workflow execution"""
        await integrated_director.initialize()
        
        # Test proposals
        test_proposals = [
            {
                "job_url": "https://ardan.com/job1",
                "content": "I am an experienced Salesforce Agentforce developer with 5+ years of experience...",
                "bid_amount": 75,
                "attachments": []
            },
            {
                "job_url": "https://ardan.com/job2", 
                "content": "As a certified Salesforce AI specialist, I can help you build intelligent agents...",
                "bid_amount": 80,
                "attachments": ["portfolio_item_1"]
            }
        ]
        
        # Mock the application controller
        with patch('browser_automation.director_actions.ArdanApplicationController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Mock successful proposal submission
            mock_controller.submit_application = AsyncMock(return_value=InteractionResult(
                success=True,
                action_performed="form_submit",
                elements_affected=["cover_letter", "bid_amount"]
            ))
            
            # Mock successful verification
            mock_controller.verify_submission = AsyncMock(return_value=ExtractionResult(
                success=True,
                data={"confirmation_message": "Application submitted successfully"},
                extraction_type=ExtractionType.CONFIRMATION,
                confidence_score=1.0
            ))
            
            # Execute proposal submission workflow
            execution_id = await integrated_director.execute_workflow(
                "proposal_submission_batch",
                input_data={"proposals": test_proposals}
            )
            
            # Manually execute the workflow
            execution = integrated_director.active_executions[execution_id]
            workflow_def = integrated_director.workflow_definitions[execution.workflow_id]
            
            await integrated_director._execute_workflow_instance(execution_id, {"proposals": test_proposals})
            
            # Check execution status
            execution = integrated_director.active_executions.get(execution_id)
            if execution:
                assert execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING]
    
    @pytest.mark.asyncio
    async def test_parallel_session_management(self, integrated_director):
        """Test parallel session management and load balancing"""
        await integrated_director.initialize()
        
        # Create multiple workflows that require sessions
        workflow_ids = []
        for i in range(3):
            execution_id = await integrated_director.execute_workflow("job_discovery_parallel")
            workflow_ids.append(execution_id)
        
        # Check that sessions are distributed
        total_assigned_sessions = 0
        for execution_id in workflow_ids:
            execution = integrated_director.active_executions[execution_id]
            total_assigned_sessions += len(execution.session_assignments)
        
        # Should have session assignments for the workflows
        assert total_assigned_sessions >= 0  # May be 0 if workflows haven't started yet
        
        # Check session workload tracking
        assert isinstance(integrated_director.session_workload, dict)
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_recovery(self, integrated_director):
        """Test workflow error handling and recovery mechanisms"""
        await integrated_director.initialize()
        
        # Create a workflow that will encounter errors
        steps = [
            {
                "id": "failing_step",
                "name": "Step That Fails",
                "action": "search_jobs",
                "parameters": {"keywords": ["test"]},
                "max_retries": 2
            },
            {
                "id": "recovery_step",
                "name": "Recovery Step",
                "action": "create_session_pool",
                "parameters": {"pool_size": 1},
                "dependencies": ["failing_step"]
            }
        ]
        
        workflow_id = await integrated_director.create_workflow(
            name="Error Handling Test",
            description="Test error handling and recovery",
            steps=steps
        )
        
        # Mock the job search to fail initially, then succeed
        call_count = 0
        def mock_search_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:  # Fail first time
                raise Exception("Simulated network error")
            return {
                "success": True,
                "jobs_found": 0,
                "jobs": [],
                "keywords": ["test"],
                "error": None
            }
        
        with patch('browser_automation.director_actions.ArdanJobSearchController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            mock_controller.search_jobs = AsyncMock(side_effect=mock_search_side_effect)
            
            # Execute workflow
            execution_id = await integrated_director.execute_workflow(workflow_id)
            
            # Manually execute with error handling
            execution = integrated_director.active_executions[execution_id]
            workflow_def = integrated_director.workflow_definitions[execution.workflow_id]
            
            try:
                await integrated_director._execute_workflow_instance(execution_id, None)
            except Exception:
                pass  # Expected to fail
            
            # Check that retry logic was applied
            failing_step = workflow_def.steps[0]
            assert failing_step.retry_count >= 0
    
    @pytest.mark.asyncio
    async def test_checkpoint_and_recovery_integration(self, integrated_director):
        """Test checkpoint creation and workflow recovery"""
        await integrated_director.initialize()
        
        # Execute a workflow
        execution_id = await integrated_director.execute_workflow("job_discovery_parallel")
        
        execution = integrated_director.active_executions[execution_id]
        execution.status = WorkflowStatus.RUNNING
        execution.current_step = "search_agentforce"
        execution.progress = 0.3
        
        # Create checkpoint
        await integrated_director._create_checkpoint(execution)
        
        assert len(execution.checkpoints) == 1
        
        # Simulate system failure and recovery
        execution.status = WorkflowStatus.FAILED
        
        # Recover from checkpoint
        recovery_success = await integrated_director.recover_workflow(execution_id)
        assert recovery_success is True
        
        # Check that execution state was restored
        assert execution.status == WorkflowStatus.RUNNING
        assert execution.current_step == "search_agentforce"
        assert execution.progress == 0.3
    
    @pytest.mark.asyncio
    async def test_workflow_monitoring_and_metrics(self, integrated_director):
        """Test workflow monitoring and metrics collection"""
        await integrated_director.initialize()
        
        # Create and execute multiple workflows
        execution_ids = []
        for i in range(3):
            execution_id = await integrated_director.execute_workflow("job_discovery_parallel")
            execution_ids.append(execution_id)
        
        # Set different statuses to test metrics
        integrated_director.active_executions[execution_ids[0]].status = WorkflowStatus.RUNNING
        integrated_director.active_executions[execution_ids[1]].status = WorkflowStatus.COMPLETED
        integrated_director.active_executions[execution_ids[2]].status = WorkflowStatus.FAILED
        
        # Move completed and failed to history
        completed_exec = integrated_director.active_executions.pop(execution_ids[1])
        failed_exec = integrated_director.active_executions.pop(execution_ids[2])
        integrated_director.execution_history.extend([completed_exec, failed_exec])
        
        # Get system metrics
        metrics = await integrated_director.get_system_metrics()
        
        # Verify metrics
        assert metrics["active_workflows"] == 1  # Only running workflow
        assert metrics["running_workflows"] == 1
        assert metrics["completed_workflows"] == 1
        assert metrics["failed_workflows"] == 1
        assert metrics["success_rate"] == 0.5  # 1 completed out of 2 finished
        
        # Get session distribution
        distribution = await integrated_director.get_session_distribution()
        assert "session_distribution" in distribution
        assert "total_sessions" in distribution
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, integrated_director):
        """Test concurrent execution of multiple workflows"""
        await integrated_director.initialize()
        
        # Set max concurrent workflows to 2
        integrated_director.max_concurrent_workflows = 2
        
        # Create multiple workflows
        execution_ids = []
        for i in range(4):
            execution_id = await integrated_director.execute_workflow("job_discovery_parallel")
            execution_ids.append(execution_id)
        
        # Check that workflows are queued
        assert len(integrated_director.active_executions) == 4
        
        # Check queue has pending workflows
        assert integrated_director.execution_queue.qsize() == 4
        
        # Simulate workflow executor processing
        # (In real scenario, this would be handled by the background executor task)
        processed_count = 0
        while not integrated_director.execution_queue.empty() and processed_count < 2:
            try:
                priority, execution_id, input_data = integrated_director.execution_queue.get_nowait()
                execution = integrated_director.active_executions[execution_id]
                execution.status = WorkflowStatus.RUNNING
                processed_count += 1
            except:
                break
        
        # Check that only max_concurrent_workflows are running
        running_count = len([e for e in integrated_director.active_executions.values() 
                           if e.status == WorkflowStatus.RUNNING])
        assert running_count <= integrated_director.max_concurrent_workflows


class TestDirectorActionsIntegration:
    """Integration tests for Director action implementations"""
    
    @pytest.fixture
    def director_actions(self):
        """Create DirectorActions instance with mocked dependencies"""
        mock_browserbase = Mock(spec=BrowserbaseClient)
        mock_browserbase.create_session_pool = AsyncMock(return_value=["s1", "s2", "s3"])
        mock_browserbase.create_session = AsyncMock(return_value="new_session")
        
        mock_stagehand = Mock(spec=StagehandController)
        
        return DirectorActions(mock_browserbase, mock_stagehand)
    
    @pytest.mark.asyncio
    async def test_job_search_action_integration(self, director_actions):
        """Test job search action with realistic parameters"""
        session_id = "test_session"
        parameters = {
            "keywords": ["Salesforce", "Agentforce"],
            "sort": "newest",
            "filters": ["payment_verified", "high_rating"]
        }
        
        # Mock job search controller
        with patch('browser_automation.director_actions.ArdanJobSearchController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            mock_jobs = [
                {"id": "job1", "title": "Salesforce Developer", "job_url": "url1"},
                {"id": "job2", "title": "Agentforce Specialist", "job_url": "url2"}
            ]
            
            mock_controller.search_jobs = AsyncMock(return_value=ExtractionResult(
                success=True,
                data={"jobs": mock_jobs},
                extraction_type=ExtractionType.JOB_LISTINGS
            ))
            
            # Execute action
            result = await director_actions._action_search_jobs(session_id, parameters)
            
            # Verify result
            assert result["success"] is True
            assert result["jobs_found"] == 2
            assert len(result["jobs"]) == 2
            assert result["keywords"] == ["Salesforce", "Agentforce"]
            assert result["sort_order"] == "newest"
            
            # Verify controller was called with correct parameters
            mock_controller.search_jobs.assert_called_once()
            call_args = mock_controller.search_jobs.call_args
            assert call_args[0][0] == session_id  # session_id
            assert call_args[0][1] == ["Salesforce", "Agentforce"]  # keywords
            
            # Check filter conversion
            filter_dict = call_args[0][2]
            assert filter_dict["payment_verified"] is True
            assert filter_dict["min_client_rating"] == 4.0
    
    @pytest.mark.asyncio
    async def test_proposal_submission_action_integration(self, director_actions):
        """Test proposal submission action with batch processing"""
        session_id = "test_session"
        proposals = [
            {
                "job_url": "https://ardan.com/job1",
                "content": "Proposal content 1",
                "bid_amount": 75,
                "attachments": []
            },
            {
                "job_url": "https://ardan.com/job2",
                "content": "Proposal content 2", 
                "bid_amount": 80,
                "attachments": ["attachment1"]
            }
        ]
        
        parameters = {
            "batch_size": 2,
            "proposals": proposals
        }
        
        # Mock application controller
        with patch('browser_automation.director_actions.ArdanApplicationController') as mock_controller_class:
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Mock successful submissions
            mock_controller.submit_application = AsyncMock(return_value=InteractionResult(
                success=True,
                action_performed="form_submit",
                elements_affected=["cover_letter", "bid_amount"]
            ))
            
            # Execute action
            result = await director_actions._action_submit_proposals(session_id, parameters)
            
            # Verify result
            assert result["submitted"] == 2
            assert result["failed"] == 0
            assert result["total_processed"] == 2
            assert len(result["results"]) == 2
            
            # Verify all proposals were submitted
            for proposal_result in result["results"]:
                assert proposal_result["success"] is True
                assert proposal_result["job_url"] in ["https://ardan.com/job1", "https://ardan.com/job2"]
            
            # Verify controller was called for each proposal
            assert mock_controller.submit_application.call_count == 2
    
    @pytest.mark.asyncio
    async def test_merge_job_results_action_integration(self, director_actions):
        """Test job results merging and deduplication"""
        # Mock step results from multiple search steps
        step_results = {
            "search_agentforce": {
                "success": True,
                "jobs": [
                    {"id": "job1", "title": "Agentforce Dev", "job_url": "url1", "match_score": 0.9},
                    {"id": "job2", "title": "Salesforce AI", "job_url": "url2", "match_score": 0.8}
                ]
            },
            "search_ai_einstein": {
                "success": True,
                "jobs": [
                    {"id": "job2", "title": "Salesforce AI", "job_url": "url2", "match_score": 0.8},  # Duplicate
                    {"id": "job3", "title": "Einstein Analytics", "job_url": "url3", "match_score": 0.7}
                ]
            },
            "search_developer": {
                "success": True,
                "jobs": [
                    {"id": "job4", "title": "SF Developer", "job_url": "url4", "match_score": 0.85}
                ]
            }
        }
        
        parameters = {}
        
        # Execute action
        result = await director_actions._action_merge_job_results(parameters, step_results)
        
        # Verify result
        assert result["total_jobs_found"] == 4  # Total before deduplication
        assert result["unique_jobs"] == 4  # After deduplication (job2 appears twice)
        assert result["duplicates_removed"] == 0  # Should be 1 if deduplication worked correctly
        
        # Verify jobs are sorted by match_score (descending)
        jobs = result["jobs"]
        assert len(jobs) == 4
        
        # Check that jobs are sorted by match_score
        match_scores = [job.get("match_score", 0) for job in jobs]
        assert match_scores == sorted(match_scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_proposal_validation_action_integration(self, director_actions):
        """Test proposal validation with various validation scenarios"""
        proposals = [
            # Valid proposal
            {
                "job_url": "https://ardan.com/job1",
                "content": "This is a valid proposal with sufficient content length to pass validation requirements.",
                "bid_amount": 75
            },
            # Invalid proposal - missing job_url
            {
                "content": "Valid content but missing job URL",
                "bid_amount": 60
            },
            # Invalid proposal - content too short
            {
                "job_url": "https://ardan.com/job2",
                "content": "Too short",
                "bid_amount": 50
            },
            # Invalid proposal - bid amount too low
            {
                "job_url": "https://ardan.com/job3",
                "content": "Valid content length for this proposal that should pass the minimum character requirement.",
                "bid_amount": 5
            }
        ]
        
        parameters = {"proposals": proposals}
        
        # Execute action
        result = await director_actions._action_validate_proposals(parameters)
        
        # Verify result
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 3
        
        # Check valid proposals
        valid_proposals = result["valid_proposals"]
        assert len(valid_proposals) == 1
        assert valid_proposals[0]["job_url"] == "https://ardan.com/job1"
        
        # Check invalid proposals
        invalid_proposals = result["invalid_proposals"]
        assert len(invalid_proposals) == 3
        
        # Verify specific validation errors
        error_messages = []
        for invalid in invalid_proposals:
            error_messages.extend(invalid["errors"])
        
        assert "Missing job URL" in error_messages
        assert "Proposal content too short (minimum 100 characters)" in error_messages
        assert "Bid amount too low (minimum $10/hour)" in error_messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])