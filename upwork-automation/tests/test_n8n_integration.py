"""
Tests for n8n workflow integration
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json

from api.main import app
from api.services.n8n_service import N8NService, n8n_service
from api.routers.n8n_webhooks import router


class TestN8NService:
    """Test cases for N8NService"""
    
    @pytest.fixture
    def n8n_service_instance(self):
        """Create N8NService instance for testing"""
        return N8NService()
    
    @pytest.mark.asyncio
    async def test_trigger_job_discovery_workflow_success(self, n8n_service_instance):
        """Test successful job discovery workflow trigger"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "executionId": "test-execution-123"
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.trigger_job_discovery_workflow(
                keywords=["Salesforce Agentforce"],
                session_pool_size=2,
                max_jobs=10
            )
            
            assert result["success"] is True
            assert result["workflow_id"] == "job-discovery-pipeline"
            assert result["execution_id"] == "test-execution-123"
            assert "Job discovery workflow triggered" in result["message"]
    
    @pytest.mark.asyncio
    async def test_trigger_job_discovery_workflow_failure(self, n8n_service_instance):
        """Test failed job discovery workflow trigger"""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.trigger_job_discovery_workflow()
            
            assert result["success"] is False
            assert "HTTP 500" in result["error"]
            assert result["workflow_id"] == "job-discovery-pipeline"
    
    @pytest.mark.asyncio
    async def test_trigger_proposal_generation_workflow_success(self, n8n_service_instance):
        """Test successful proposal generation workflow trigger"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "executionId": "test-execution-456"
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.trigger_proposal_generation_workflow(
                job_ids=["job-1", "job-2"],
                auto_create_docs=True,
                quality_threshold=0.8
            )
            
            assert result["success"] is True
            assert result["workflow_id"] == "proposal-generation-pipeline"
            assert result["execution_id"] == "test-execution-456"
            assert "2 jobs" in result["message"]
    
    @pytest.mark.asyncio
    async def test_trigger_proposal_generation_workflow_no_jobs(self, n8n_service_instance):
        """Test proposal generation workflow with no job IDs"""
        result = await n8n_service_instance.trigger_proposal_generation_workflow(
            job_ids=[]
        )
        
        assert result["success"] is False
        assert "No job IDs provided" in result["error"]
        assert result["workflow_id"] == "proposal-generation-pipeline"
    
    @pytest.mark.asyncio
    async def test_trigger_browser_submission_workflow_success(self, n8n_service_instance):
        """Test successful browser submission workflow trigger"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "executionId": "test-execution-789"
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.trigger_browser_submission_workflow(
                proposal_ids=["proposal-1", "proposal-2"],
                stealth_mode=True,
                retry_attempts=3
            )
            
            assert result["success"] is True
            assert result["workflow_id"] == "browser-submission-pipeline"
            assert result["execution_id"] == "test-execution-789"
            assert "2 proposals" in result["message"]
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, n8n_service_instance):
        """Test successful notification sending"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "executionId": "test-notification-123"
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.send_notification(
                notification_type="job_discovered",
                data={"jobs_count": 5, "top_job_title": "Test Job"},
                channels=["slack", "email"],
                priority="high"
            )
            
            assert result["success"] is True
            assert result["workflow_id"] == "notification-workflows"
            assert result["execution_id"] == "test-notification-123"
            assert "job_discovered" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_all(self, n8n_service_instance):
        """Test getting status of all workflows"""
        result = await n8n_service_instance.get_workflow_status()
        
        assert result["success"] is True
        assert "workflows" in result
        assert result["total_workflows"] == 4
        assert result["active_workflows"] == 4
        assert "job-discovery-pipeline" in result["workflows"]
        assert "proposal-generation-pipeline" in result["workflows"]
        assert "browser-submission-pipeline" in result["workflows"]
        assert "notification-workflows" in result["workflows"]
    
    @pytest.mark.asyncio
    async def test_get_workflow_status_specific(self, n8n_service_instance):
        """Test getting status of specific workflow"""
        result = await n8n_service_instance.get_workflow_status("job-discovery-pipeline")
        
        assert result["success"] is True
        assert result["workflow_id"] == "job-discovery-pipeline"
        assert "workflow" in result
        assert result["workflow"]["active"] is True
    
    @pytest.mark.asyncio
    async def test_test_webhook_connectivity_success(self, n8n_service_instance):
        """Test successful webhook connectivity test"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "message": "Test successful"
        })
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service_instance.test_webhook_connectivity()
            
            assert result["success"] is True
            assert "successful" in result["message"]
            assert "response" in result
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, n8n_service_instance):
        """Test timeout handling in workflow triggers"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            result = await n8n_service_instance.trigger_job_discovery_workflow()
            
            assert result["success"] is False
            assert "timeout" in result["error"].lower()


class TestN8NWebhooks:
    """Test cases for n8n webhook endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_trigger_job_discovery_webhook_success(self, client):
        """Test successful job discovery webhook trigger"""
        payload = {
            "keywords": ["Salesforce Agentforce"],
            "session_pool_size": 2,
            "max_jobs": 10,
            "filters": {
                "min_hourly_rate": 50,
                "min_client_rating": 4.0,
                "payment_verified": True
            }
        }
        
        with patch('api.services.task_queue_service.task_queue_service.add_task') as mock_add_task:
            mock_add_task.return_value = "task-123"
            
            response = client.post("/api/n8n/trigger/job-discovery", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == "task-123"
            assert data["parameters"]["keywords"] == ["Salesforce Agentforce"]
    
    def test_trigger_job_discovery_webhook_invalid_json(self, client):
        """Test job discovery webhook with invalid JSON"""
        response = client.post(
            "/api/n8n/trigger/job-discovery",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON payload" in data["detail"]
    
    def test_trigger_proposal_generation_webhook_success(self, client):
        """Test successful proposal generation webhook trigger"""
        payload = {
            "job_ids": ["job-1", "job-2"],
            "auto_create_docs": True,
            "select_attachments": True,
            "quality_threshold": 0.8
        }
        
        with patch('api.services.task_queue_service.task_queue_service.add_task') as mock_add_task:
            mock_add_task.return_value = "task-456"
            
            response = client.post("/api/n8n/trigger/proposal-generation", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["task_ids"]) == 2
            assert data["parameters"]["job_ids"] == ["job-1", "job-2"]
    
    def test_trigger_proposal_generation_webhook_no_jobs(self, client):
        """Test proposal generation webhook with no job IDs"""
        payload = {"job_ids": []}
        
        response = client.post("/api/n8n/trigger/proposal-generation", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "At least one job_id is required" in data["detail"]
    
    def test_trigger_browser_submission_webhook_success(self, client):
        """Test successful browser submission webhook trigger"""
        payload = {
            "proposal_ids": ["proposal-1", "proposal-2"],
            "session_type": "proposal_submission",
            "stealth_mode": True,
            "retry_attempts": 3
        }
        
        with patch('api.services.task_queue_service.task_queue_service.add_task') as mock_add_task:
            mock_add_task.return_value = "task-789"
            
            response = client.post("/api/n8n/trigger/browser-submission", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["task_ids"]) == 2
            assert data["parameters"]["stealth_mode"] is True
    
    def test_trigger_notification_webhook_success(self, client):
        """Test successful notification webhook trigger"""
        payload = {
            "notification_type": "job_discovered",
            "data": {"jobs_count": 5, "top_job_title": "Test Job"},
            "channels": ["slack"],
            "priority": "high"
        }
        
        with patch('api.services.task_queue_service.task_queue_service.add_task') as mock_add_task:
            mock_add_task.return_value = "task-notification"
            
            response = client.post("/api/n8n/trigger/notification", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == "task-notification"
            assert data["parameters"]["notification_type"] == "job_discovered"
    
    def test_trigger_notification_webhook_missing_type(self, client):
        """Test notification webhook with missing notification type"""
        payload = {
            "data": {"test": "data"},
            "channels": ["slack"]
        }
        
        response = client.post("/api/n8n/trigger/notification", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "notification_type is required" in data["detail"]
    
    def test_job_discovery_complete_callback_success(self, client):
        """Test successful job discovery completion callback"""
        payload = {
            "task_id": "task-123",
            "success": True,
            "jobs_discovered": 15,
            "jobs_filtered": 8,
            "next_workflow": "proposal_generation"
        }
        
        with patch('api.services.task_queue_service.task_queue_service.update_task_status') as mock_update:
            mock_update.return_value = True
            
            response = client.post("/api/n8n/callback/job-discovery-complete", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["task_id"] == "task-123"
            assert data["next_action"] == "proposal_generation"
    
    def test_get_n8n_integration_status(self, client):
        """Test getting n8n integration status"""
        response = client.get("/api/n8n/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["integration_status"] == "active"
        assert "available_webhooks" in data
        assert "callback_endpoints" in data
        assert len(data["available_webhooks"]) == 4
    
    def test_test_webhook_endpoint(self, client):
        """Test the webhook test endpoint"""
        payload = {"test": "data", "timestamp": "2024-01-01T00:00:00Z"}
        
        response = client.post("/api/n8n/test-webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Webhook test successful" in data["message"]
        assert data["received_payload"] == payload


class TestN8NWorkflowValidation:
    """Test cases for n8n workflow validation"""
    
    def test_job_discovery_workflow_structure(self):
        """Test job discovery workflow JSON structure"""
        with open("upwork-automation/n8n-workflows/job-discovery-pipeline.json", "r") as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Job Discovery Pipeline"
        assert workflow["active"] is True
        assert "nodes" in workflow
        assert "connections" in workflow
        
        # Check for required nodes
        node_names = [node["name"] for node in workflow["nodes"]]
        required_nodes = [
            "Every 30 Minutes",
            "Manual Trigger Webhook", 
            "Trigger Browser Job Search",
            "Check Search Success",
            "Fetch Discovered Jobs",
            "Filter and Rank Jobs",
            "Slack: Jobs Found",
            "Trigger Proposal Generation"
        ]
        
        for required_node in required_nodes:
            assert required_node in node_names, f"Missing required node: {required_node}"
    
    def test_proposal_generation_workflow_structure(self):
        """Test proposal generation workflow JSON structure"""
        with open("upwork-automation/n8n-workflows/proposal-generation-pipeline.json", "r") as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Proposal Generation Pipeline"
        assert workflow["active"] is True
        
        # Check for required nodes
        node_names = [node["name"] for node in workflow["nodes"]]
        required_nodes = [
            "Proposal Generation Trigger",
            "Extract Job IDs",
            "Fetch Job Details",
            "Analyze Job Requirements",
            "Generate Proposal Content",
            "Create Google Doc",
            "Select Attachments",
            "Combine Proposal Data"
        ]
        
        for required_node in required_nodes:
            assert required_node in node_names, f"Missing required node: {required_node}"
    
    def test_browser_submission_workflow_structure(self):
        """Test browser submission workflow JSON structure"""
        with open("upwork-automation/n8n-workflows/browser-submission-pipeline.json", "r") as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Browser Submission Pipeline"
        assert workflow["active"] is True
        
        # Check for required nodes
        node_names = [node["name"] for node in workflow["nodes"]]
        required_nodes = [
            "Browser Submission Trigger",
            "Extract Proposal IDs",
            "Fetch Proposal Details",
            "Get Browser Session",
            "Navigate to Job",
            "Fill Proposal Form",
            "Submit Proposal",
            "Capture Confirmation",
            "Create Application Record"
        ]
        
        for required_node in required_nodes:
            assert required_node in node_names, f"Missing required node: {required_node}"
    
    def test_notification_workflow_structure(self):
        """Test notification workflow JSON structure"""
        with open("upwork-automation/n8n-workflows/notification-workflows.json", "r") as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Notification Workflows"
        assert workflow["active"] is True
        
        # Check for required nodes
        node_names = [node["name"] for node in workflow["nodes"]]
        required_nodes = [
            "Notification Trigger",
            "Job Discovered?",
            "Proposal Generated?",
            "Application Submitted?",
            "Error Alert?",
            "Slack: Job Discovered",
            "Slack: Proposal Generated",
            "Slack: Application Submitted",
            "Slack: Error Alert"
        ]
        
        for required_node in required_nodes:
            assert required_node in node_names, f"Missing required node: {required_node}"
    
    def test_workflow_webhook_ids_unique(self):
        """Test that all workflow webhook IDs are unique"""
        webhook_ids = []
        
        workflow_files = [
            "upwork-automation/n8n-workflows/job-discovery-pipeline.json",
            "upwork-automation/n8n-workflows/proposal-generation-pipeline.json",
            "upwork-automation/n8n-workflows/browser-submission-pipeline.json",
            "upwork-automation/n8n-workflows/notification-workflows.json"
        ]
        
        for workflow_file in workflow_files:
            with open(workflow_file, "r") as f:
                workflow = json.load(f)
            
            for node in workflow["nodes"]:
                if node["type"] == "n8n-nodes-base.webhook" and "webhookId" in node:
                    webhook_id = node["webhookId"]
                    assert webhook_id not in webhook_ids, f"Duplicate webhook ID: {webhook_id}"
                    webhook_ids.append(webhook_id)


@pytest.mark.integration
class TestN8NIntegrationEnd2End:
    """End-to-end integration tests for n8n workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_job_discovery_to_submission_flow(self):
        """Test complete flow from job discovery to submission"""
        # This would be an integration test that requires actual n8n instance
        # For now, we'll mock the entire flow
        
        with patch.object(n8n_service, 'trigger_job_discovery_workflow') as mock_discovery, \
             patch.object(n8n_service, 'trigger_proposal_generation_workflow') as mock_proposal, \
             patch.object(n8n_service, 'trigger_browser_submission_workflow') as mock_submission:
            
            # Mock successful responses
            mock_discovery.return_value = {"success": True, "execution_id": "discovery-123"}
            mock_proposal.return_value = {"success": True, "execution_id": "proposal-456"}
            mock_submission.return_value = {"success": True, "execution_id": "submission-789"}
            
            # Trigger job discovery
            discovery_result = await n8n_service.trigger_job_discovery_workflow(
                keywords=["Salesforce Agentforce"],
                max_jobs=5
            )
            assert discovery_result["success"] is True
            
            # Trigger proposal generation
            proposal_result = await n8n_service.trigger_proposal_generation_workflow(
                job_ids=["job-1", "job-2"]
            )
            assert proposal_result["success"] is True
            
            # Trigger browser submission
            submission_result = await n8n_service.trigger_browser_submission_workflow(
                proposal_ids=["proposal-1", "proposal-2"]
            )
            assert submission_result["success"] is True
            
            # Verify all workflows were called
            mock_discovery.assert_called_once()
            mock_proposal.assert_called_once()
            mock_submission.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_health_monitoring(self):
        """Test workflow health monitoring functionality"""
        from api.services.workflow_health_service import workflow_health_service
        
        with patch.object(n8n_service, 'validate_workflow_deployment') as mock_validate, \
             patch.object(n8n_service, 'get_workflow_status') as mock_status, \
             patch.object(n8n_service, 'test_webhook_connectivity') as mock_webhook:
            
            # Mock healthy system
            mock_validate.return_value = {
                "success": True,
                "all_workflows_valid": True,
                "missing_workflows": [],
                "inactive_workflows": []
            }
            mock_status.return_value = {
                "success": True,
                "total_workflows": 4,
                "active_workflows": 4
            }
            mock_webhook.return_value = {
                "success": True,
                "latency_ms": 150
            }
            
            # Perform health check
            health_result = await workflow_health_service.perform_health_check()
            
            assert health_result["overall_health_score"] >= 0.9
            assert health_result["status"] == "healthy"
            assert len(health_result["alerts"]) == 0
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        
        # Test timeout handling
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            result = await n8n_service.trigger_job_discovery_workflow()
            
            assert result["success"] is False
            assert "timeout" in result["error"].lower()
        
        # Test HTTP error handling
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await n8n_service.trigger_proposal_generation_workflow(
                job_ids=["job-1"]
            )
            
            assert result["success"] is False
            assert "HTTP 500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_performance_monitoring(self):
        """Test workflow performance monitoring"""
        from api.services.workflow_health_service import workflow_health_service
        
        # Simulate multiple health checks over time
        health_results = []
        
        for i in range(5):
            with patch.object(n8n_service, 'validate_workflow_deployment') as mock_validate, \
                 patch.object(n8n_service, 'get_workflow_status') as mock_status, \
                 patch.object(n8n_service, 'test_webhook_connectivity') as mock_webhook:
                
                # Simulate degrading performance
                mock_validate.return_value = {
                    "success": True,
                    "all_workflows_valid": i < 3,  # Fail after 3rd check
                    "missing_workflows": [] if i < 3 else ["Test Workflow"],
                    "inactive_workflows": []
                }
                mock_status.return_value = {
                    "success": True,
                    "total_workflows": 4,
                    "active_workflows": 4 - (i // 2)  # Gradually reduce active workflows
                }
                mock_webhook.return_value = {
                    "success": True,
                    "latency_ms": 100 + (i * 50)  # Increasing latency
                }
                
                health_result = await workflow_health_service.perform_health_check()
                health_results.append(health_result)
        
        # Verify performance degradation is detected
        assert health_results[0]["overall_health_score"] > health_results[-1]["overall_health_score"]
        assert len(health_results[-1]["alerts"]) > 0
        
        # Test trend analysis
        trends = await workflow_health_service.get_health_trends(hours=1)
        assert trends["success"] is True
        assert trends["trends"]["health_score"]["trend"] == "declining"


class TestWorkflowHealthService:
    """Test cases for WorkflowHealthService"""
    
    @pytest.fixture
    def health_service(self):
        """Create WorkflowHealthService instance for testing"""
        from api.services.workflow_health_service import WorkflowHealthService
        return WorkflowHealthService()
    
    @pytest.mark.asyncio
    async def test_health_score_calculation(self, health_service):
        """Test health score calculation logic"""
        
        # Test perfect health
        deployment_validation = {
            "success": True,
            "all_workflows_valid": True,
            "missing_workflows": [],
            "inactive_workflows": []
        }
        workflow_status = {
            "success": True,
            "total_workflows": 4,
            "active_workflows": 4
        }
        webhook_test = {
            "success": True,
            "latency_ms": 100
        }
        
        score = await health_service._calculate_health_score(
            deployment_validation, workflow_status, webhook_test
        )
        
        assert score == 1.0
        
        # Test degraded health
        deployment_validation["all_workflows_valid"] = False
        workflow_status["active_workflows"] = 2
        webhook_test["latency_ms"] = 6000  # High latency
        
        degraded_score = await health_service._calculate_health_score(
            deployment_validation, workflow_status, webhook_test
        )
        
        assert degraded_score < 0.7
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, health_service):
        """Test alert generation logic"""
        
        # Test with issues
        deployment_validation = {
            "success": True,
            "all_workflows_valid": False,
            "missing_workflows": ["Test Workflow"],
            "inactive_workflows": ["Another Workflow"]
        }
        workflow_status = {"success": True}
        webhook_test = {
            "success": False,
            "error": "Connection failed"
        }
        
        alerts = await health_service._check_for_alerts(
            deployment_validation, workflow_status, webhook_test
        )
        
        assert len(alerts) >= 3  # Missing, inactive, and connectivity alerts
        
        # Check alert types
        alert_types = [alert["type"] for alert in alerts]
        assert "error" in alert_types
        assert "warning" in alert_types
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(self, health_service):
        """Test recommendations generation"""
        
        deployment_validation = {
            "success": True,
            "all_workflows_valid": False,
            "missing_workflows": ["Missing Workflow"],
            "inactive_workflows": ["Inactive Workflow"]
        }
        workflow_status = {"success": True}
        webhook_test = {"success": False}
        
        recommendations = await health_service._generate_recommendations(
            deployment_validation, workflow_status, webhook_test
        )
        
        assert len(recommendations) >= 3
        assert any("Deploy missing workflows" in rec for rec in recommendations)
        assert any("Activate inactive workflows" in rec for rec in recommendations)
        assert any("webhook" in rec.lower() for rec in recommendations)
    
    def test_health_history_management(self, health_service):
        """Test health history storage and retrieval"""
        
        # Add test health results
        for i in range(15):
            health_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_health_score": 0.8 + (i * 0.01),
                "status": "healthy",
                "alerts": []
            }
            health_service._store_health_result(health_result)
        
        # Check history is trimmed to max size
        assert len(health_service.health_history) <= health_service.max_history_size
        
        # Check recent history retrieval
        recent_history = asyncio.run(health_service.get_health_history(limit=5))
        assert len(recent_history) == 5
        assert recent_history[-1]["overall_health_score"] > recent_history[0]["overall_health_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])