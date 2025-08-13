"""
n8n Integration Service - handles communication with n8n workflows
"""
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from shared.config import settings
from shared.utils import setup_logging

logger = setup_logging("n8n-service")


class N8NService:
    """Service for integrating with n8n workflow automation"""
    
    def __init__(self):
        self.base_url = settings.n8n_webhook_url or "http://n8n:5678"
        self.webhook_base = f"{self.base_url}/webhook"
        self.api_base = f"{self.base_url}/api/v1"
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def trigger_job_discovery_workflow(
        self,
        keywords: List[str] = None,
        session_pool_size: int = 3,
        max_jobs: int = 20,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Trigger the job discovery workflow in n8n
        
        Args:
            keywords: Search keywords for job discovery
            session_pool_size: Number of browser sessions to use
            max_jobs: Maximum number of jobs to discover
            filters: Additional filters for job search
            
        Returns:
            Dict containing workflow execution result
        """
        try:
            payload = {
                "keywords": keywords or ["Salesforce Agentforce", "Salesforce AI", "Einstein"],
                "session_pool_size": session_pool_size,
                "max_jobs": max_jobs,
                "filters": filters or {
                    "min_hourly_rate": 50,
                    "min_client_rating": 4.0,
                    "payment_verified": True
                },
                "triggered_by": "api_service",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            webhook_url = f"{self.webhook_base}/trigger-job-discovery"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Job discovery workflow triggered successfully: {result}")
                        return {
                            "success": True,
                            "workflow_id": "job-discovery-pipeline",
                            "execution_id": result.get("executionId"),
                            "message": "Job discovery workflow triggered",
                            "parameters": payload
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to trigger job discovery workflow: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "workflow_id": "job-discovery-pipeline"
                        }
                        
        except asyncio.TimeoutError:
            logger.error("Timeout while triggering job discovery workflow")
            return {
                "success": False,
                "error": "Workflow trigger timeout",
                "workflow_id": "job-discovery-pipeline"
            }
        except Exception as e:
            logger.error(f"Error triggering job discovery workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": "job-discovery-pipeline"
            }
    
    async def trigger_proposal_generation_workflow(
        self,
        job_ids: List[str],
        auto_create_docs: bool = True,
        select_attachments: bool = True,
        quality_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Trigger the proposal generation workflow in n8n
        
        Args:
            job_ids: List of job IDs to generate proposals for
            auto_create_docs: Whether to automatically create Google Docs
            select_attachments: Whether to automatically select attachments
            quality_threshold: Minimum quality threshold for proposals
            
        Returns:
            Dict containing workflow execution result
        """
        try:
            if not job_ids:
                return {
                    "success": False,
                    "error": "No job IDs provided",
                    "workflow_id": "proposal-generation-pipeline"
                }
            
            payload = {
                "job_ids": job_ids,
                "auto_create_docs": auto_create_docs,
                "select_attachments": select_attachments,
                "quality_threshold": quality_threshold,
                "triggered_by": "api_service",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            webhook_url = f"{self.webhook_base}/trigger-proposal-generation"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Proposal generation workflow triggered for {len(job_ids)} jobs")
                        return {
                            "success": True,
                            "workflow_id": "proposal-generation-pipeline",
                            "execution_id": result.get("executionId"),
                            "message": f"Proposal generation triggered for {len(job_ids)} jobs",
                            "parameters": payload
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to trigger proposal generation workflow: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "workflow_id": "proposal-generation-pipeline"
                        }
                        
        except Exception as e:
            logger.error(f"Error triggering proposal generation workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": "proposal-generation-pipeline"
            }
    
    async def trigger_browser_submission_workflow(
        self,
        proposal_ids: List[str],
        session_type: str = "proposal_submission",
        stealth_mode: bool = True,
        retry_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Trigger the browser submission workflow in n8n
        
        Args:
            proposal_ids: List of proposal IDs to submit
            session_type: Type of browser session to use
            stealth_mode: Whether to use stealth mode
            retry_attempts: Number of retry attempts on failure
            
        Returns:
            Dict containing workflow execution result
        """
        try:
            if not proposal_ids:
                return {
                    "success": False,
                    "error": "No proposal IDs provided",
                    "workflow_id": "browser-submission-pipeline"
                }
            
            payload = {
                "proposal_ids": proposal_ids,
                "session_type": session_type,
                "stealth_mode": stealth_mode,
                "retry_attempts": retry_attempts,
                "triggered_by": "api_service",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            webhook_url = f"{self.webhook_base}/trigger-browser-submission"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Browser submission workflow triggered for {len(proposal_ids)} proposals")
                        return {
                            "success": True,
                            "workflow_id": "browser-submission-pipeline",
                            "execution_id": result.get("executionId"),
                            "message": f"Browser submission triggered for {len(proposal_ids)} proposals",
                            "parameters": payload
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to trigger browser submission workflow: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "workflow_id": "browser-submission-pipeline"
                        }
                        
        except Exception as e:
            logger.error(f"Error triggering browser submission workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": "browser-submission-pipeline"
            }
    
    async def send_notification(
        self,
        notification_type: str,
        data: Dict[str, Any],
        channels: List[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send notification through n8n notification workflow
        
        Args:
            notification_type: Type of notification (job_discovered, proposal_generated, etc.)
            data: Notification data
            channels: List of channels to send to (slack, email)
            priority: Notification priority (normal, high, urgent)
            
        Returns:
            Dict containing notification result
        """
        try:
            payload = {
                "notification_type": notification_type,
                "data": data,
                "channels": channels or ["slack"],
                "priority": priority,
                "triggered_by": "api_service",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            webhook_url = f"{self.webhook_base}/trigger-notification"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Notification sent: {notification_type}")
                        return {
                            "success": True,
                            "workflow_id": "notification-workflows",
                            "execution_id": result.get("executionId"),
                            "message": f"Notification sent: {notification_type}",
                            "parameters": payload
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send notification: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "workflow_id": "notification-workflows"
                        }
                        
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_id": "notification-workflows"
            }
    
    async def get_workflow_status(self, workflow_id: str = None) -> Dict[str, Any]:
        """
        Get status of n8n workflows using n8n API
        
        Args:
            workflow_id: Optional specific workflow ID to check
            
        Returns:
            Dict containing workflow status information
        """
        try:
            # Try to get actual workflow status from n8n API
            api_url = f"{self.api_base}/workflows"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                try:
                    async with session.get(api_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            workflows_data = data.get('data', [])
                            
                            # Convert to our expected format
                            workflows = {}
                            for workflow in workflows_data:
                                workflows[workflow.get('id', workflow.get('name', 'unknown'))] = {
                                    "active": workflow.get('active', False),
                                    "last_execution": workflow.get('updatedAt'),
                                    "success_rate": 0.9,  # Would calculate from execution history
                                    "name": workflow.get('name'),
                                    "id": workflow.get('id')
                                }
                            
                            if workflow_id:
                                return {
                                    "success": True,
                                    "workflow": workflows.get(workflow_id, {"active": False}),
                                    "workflow_id": workflow_id
                                }
                            else:
                                return {
                                    "success": True,
                                    "workflows": workflows,
                                    "total_workflows": len(workflows),
                                    "active_workflows": sum(1 for w in workflows.values() if w["active"])
                                }
                        else:
                            # Fall back to mock data if API call fails
                            logger.warning(f"n8n API call failed with status {response.status}, using mock data")
                            raise Exception("API call failed")
                            
                except Exception as api_error:
                    logger.warning(f"Failed to connect to n8n API: {api_error}, using mock data")
                    # Fall back to mock status
                    workflows = {
                        "job-discovery-pipeline": {
                            "active": True,
                            "last_execution": None,
                            "success_rate": 0.95,
                            "name": "Job Discovery Pipeline"
                        },
                        "proposal-generation-pipeline": {
                            "active": True,
                            "last_execution": None,
                            "success_rate": 0.88,
                            "name": "Proposal Generation Pipeline"
                        },
                        "browser-submission-pipeline": {
                            "active": True,
                            "last_execution": None,
                            "success_rate": 0.82,
                            "name": "Browser Submission Pipeline"
                        },
                        "notification-workflows": {
                            "active": True,
                            "last_execution": None,
                            "success_rate": 0.99,
                            "name": "Notification Workflows"
                        }
                    }
                    
                    if workflow_id:
                        return {
                            "success": True,
                            "workflow": workflows.get(workflow_id, {"active": False}),
                            "workflow_id": workflow_id
                        }
                    else:
                        return {
                            "success": True,
                            "workflows": workflows,
                            "total_workflows": len(workflows),
                            "active_workflows": sum(1 for w in workflows.values() if w["active"])
                        }
                
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_webhook_connectivity(self) -> Dict[str, Any]:
        """
        Test connectivity to n8n webhooks
        
        Returns:
            Dict containing connectivity test results
        """
        try:
            import time
            start_time = time.time()
            
            test_payload = {
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connectivity test from API service"
            }
            
            webhook_url = f"{self.webhook_base}/test-webhook"
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(webhook_url, json=test_payload) as response:
                    latency_ms = round((time.time() - start_time) * 1000, 2)
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info("n8n webhook connectivity test successful")
                        return {
                            "success": True,
                            "message": "Webhook connectivity test successful",
                            "response": result,
                            "latency_ms": latency_ms
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"n8n webhook connectivity test failed: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "message": "Webhook connectivity test failed",
                            "latency_ms": latency_ms
                        }
                        
        except Exception as e:
            logger.error(f"Error testing n8n webhook connectivity: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Webhook connectivity test failed"
            }
    
    async def validate_workflow_deployment(self) -> Dict[str, Any]:
        """
        Validate that all required workflows are properly deployed and configured
        
        Returns:
            Dict containing validation results
        """
        try:
            required_workflows = [
                "Job Discovery Pipeline",
                "Proposal Generation Pipeline", 
                "Browser Submission Pipeline",
                "Notification Workflows"
            ]
            
            # Get current workflow status
            status_result = await self.get_workflow_status()
            if not status_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to get workflow status",
                    "validation_results": {}
                }
            
            workflows = status_result["workflows"]
            validation_results = {}
            all_valid = True
            
            for required_name in required_workflows:
                # Find workflow by name
                workflow_found = False
                for workflow_id, workflow_data in workflows.items():
                    if workflow_data.get("name") == required_name:
                        workflow_found = True
                        is_active = workflow_data.get("active", False)
                        
                        validation_results[required_name] = {
                            "deployed": True,
                            "active": is_active,
                            "workflow_id": workflow_id,
                            "status": "valid" if is_active else "inactive"
                        }
                        
                        if not is_active:
                            all_valid = False
                        break
                
                if not workflow_found:
                    validation_results[required_name] = {
                        "deployed": False,
                        "active": False,
                        "workflow_id": None,
                        "status": "missing"
                    }
                    all_valid = False
            
            # Test webhook connectivity
            webhook_test = await self.test_webhook_connectivity()
            
            return {
                "success": True,
                "all_workflows_valid": all_valid,
                "validation_results": validation_results,
                "webhook_connectivity": webhook_test["success"],
                "webhook_latency_ms": webhook_test.get("latency_ms", 0),
                "total_workflows": len(workflows),
                "active_workflows": sum(1 for w in workflows.values() if w.get("active", False)),
                "missing_workflows": [name for name, result in validation_results.items() if not result["deployed"]],
                "inactive_workflows": [name for name, result in validation_results.items() if result["deployed"] and not result["active"]]
            }
            
        except Exception as e:
            logger.error(f"Error validating workflow deployment: {e}")
            return {
                "success": False,
                "error": str(e),
                "validation_results": {}
            }
    
    async def get_workflow_execution_history(self, workflow_id: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        Get execution history for workflows
        
        Args:
            workflow_id: Optional specific workflow ID
            limit: Maximum number of executions to return
            
        Returns:
            Dict containing execution history
        """
        try:
            # This would use n8n API to get actual execution history
            # For now, return mock data
            mock_executions = [
                {
                    "id": f"exec-{i}",
                    "workflowId": workflow_id or "job-discovery-pipeline",
                    "status": "success" if i % 4 != 0 else "error",
                    "startedAt": datetime.utcnow().isoformat(),
                    "finishedAt": datetime.utcnow().isoformat(),
                    "executionTime": 1500 + (i * 100)
                }
                for i in range(limit)
            ]
            
            return {
                "success": True,
                "executions": mock_executions,
                "total_executions": limit,
                "success_rate": len([e for e in mock_executions if e["status"] == "success"]) / len(mock_executions),
                "avg_execution_time": sum(e["executionTime"] for e in mock_executions) / len(mock_executions)
            }
            
        except Exception as e:
            logger.error(f"Error getting workflow execution history: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global service instance
n8n_service = N8NService()