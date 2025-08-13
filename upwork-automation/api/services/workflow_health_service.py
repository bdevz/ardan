"""
Workflow Health Monitoring Service - monitors n8n workflow health and performance
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from shared.config import settings
from shared.utils import setup_logging
from .n8n_service import n8n_service

logger = setup_logging("workflow-health")


class WorkflowHealthService:
    """Service for monitoring n8n workflow health and performance"""
    
    def __init__(self):
        self.health_check_interval = 300  # 5 minutes
        self.alert_thresholds = {
            "success_rate": 0.8,  # Alert if success rate drops below 80%
            "avg_execution_time": 30000,  # Alert if avg execution time > 30s
            "webhook_latency": 5000,  # Alert if webhook latency > 5s
            "inactive_workflows": 0  # Alert if any workflows are inactive
        }
        self.health_history = []
        self.max_history_size = 100
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all n8n workflows
        
        Returns:
            Dict containing health check results
        """
        try:
            logger.info("Starting workflow health check")
            
            # Get workflow deployment validation
            deployment_validation = await n8n_service.validate_workflow_deployment()
            
            # Get workflow status
            workflow_status = await n8n_service.get_workflow_status()
            
            # Test webhook connectivity
            webhook_test = await n8n_service.test_webhook_connectivity()
            
            # Calculate overall health score
            health_score = await self._calculate_health_score(
                deployment_validation,
                workflow_status,
                webhook_test
            )
            
            # Check for alerts
            alerts = await self._check_for_alerts(
                deployment_validation,
                workflow_status,
                webhook_test
            )
            
            health_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_health_score": health_score,
                "status": "healthy" if health_score >= 0.8 else "degraded" if health_score >= 0.6 else "unhealthy",
                "deployment_validation": deployment_validation,
                "workflow_status": workflow_status,
                "webhook_connectivity": webhook_test,
                "alerts": alerts,
                "recommendations": await self._generate_recommendations(deployment_validation, workflow_status, webhook_test)
            }
            
            # Store in history
            self._store_health_result(health_result)
            
            logger.info(f"Health check completed. Score: {health_score:.2f}, Status: {health_result['status']}")
            
            return health_result
            
        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_health_score": 0.0,
                "status": "error",
                "error": str(e),
                "alerts": [{"type": "error", "message": f"Health check failed: {str(e)}"}]
            }
    
    async def _calculate_health_score(
        self,
        deployment_validation: Dict[str, Any],
        workflow_status: Dict[str, Any],
        webhook_test: Dict[str, Any]
    ) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        try:
            score_components = []
            
            # Deployment validation score (40% weight)
            if deployment_validation.get("success"):
                deployment_score = 1.0 if deployment_validation.get("all_workflows_valid") else 0.5
                score_components.append(("deployment", deployment_score, 0.4))
            else:
                score_components.append(("deployment", 0.0, 0.4))
            
            # Workflow status score (40% weight)
            if workflow_status.get("success"):
                total_workflows = workflow_status.get("total_workflows", 1)
                active_workflows = workflow_status.get("active_workflows", 0)
                status_score = active_workflows / total_workflows if total_workflows > 0 else 0.0
                score_components.append(("status", status_score, 0.4))
            else:
                score_components.append(("status", 0.0, 0.4))
            
            # Webhook connectivity score (20% weight)
            webhook_score = 1.0 if webhook_test.get("success") else 0.0
            if webhook_test.get("success") and webhook_test.get("latency_ms", 0) > self.alert_thresholds["webhook_latency"]:
                webhook_score *= 0.7  # Reduce score for high latency
            score_components.append(("webhook", webhook_score, 0.2))
            
            # Calculate weighted average
            total_score = sum(score * weight for _, score, weight in score_components)
            
            return round(total_score, 3)
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 0.0
    
    async def _check_for_alerts(
        self,
        deployment_validation: Dict[str, Any],
        workflow_status: Dict[str, Any],
        webhook_test: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        
        try:
            # Check deployment issues
            if deployment_validation.get("success"):
                missing_workflows = deployment_validation.get("missing_workflows", [])
                inactive_workflows = deployment_validation.get("inactive_workflows", [])
                
                if missing_workflows:
                    alerts.append({
                        "type": "error",
                        "category": "deployment",
                        "message": f"Missing workflows: {', '.join(missing_workflows)}",
                        "severity": "high",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                if inactive_workflows:
                    alerts.append({
                        "type": "warning",
                        "category": "deployment", 
                        "message": f"Inactive workflows: {', '.join(inactive_workflows)}",
                        "severity": "medium",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Check webhook connectivity
            if not webhook_test.get("success"):
                alerts.append({
                    "type": "error",
                    "category": "connectivity",
                    "message": f"Webhook connectivity failed: {webhook_test.get('error', 'Unknown error')}",
                    "severity": "high",
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif webhook_test.get("latency_ms", 0) > self.alert_thresholds["webhook_latency"]:
                alerts.append({
                    "type": "warning",
                    "category": "performance",
                    "message": f"High webhook latency: {webhook_test.get('latency_ms')}ms",
                    "severity": "medium",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check workflow status
            if workflow_status.get("success"):
                total_workflows = workflow_status.get("total_workflows", 0)
                active_workflows = workflow_status.get("active_workflows", 0)
                
                if total_workflows == 0:
                    alerts.append({
                        "type": "error",
                        "category": "status",
                        "message": "No workflows found in n8n instance",
                        "severity": "high",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif active_workflows < total_workflows:
                    alerts.append({
                        "type": "warning",
                        "category": "status",
                        "message": f"Only {active_workflows}/{total_workflows} workflows are active",
                        "severity": "medium",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")
            alerts.append({
                "type": "error",
                "category": "system",
                "message": f"Error during alert checking: {str(e)}",
                "severity": "high",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return alerts
    
    async def _generate_recommendations(
        self,
        deployment_validation: Dict[str, Any],
        workflow_status: Dict[str, Any],
        webhook_test: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on health check results"""
        recommendations = []
        
        try:
            # Deployment recommendations
            if deployment_validation.get("success"):
                missing_workflows = deployment_validation.get("missing_workflows", [])
                inactive_workflows = deployment_validation.get("inactive_workflows", [])
                
                if missing_workflows:
                    recommendations.append(f"Deploy missing workflows: {', '.join(missing_workflows)}")
                
                if inactive_workflows:
                    recommendations.append(f"Activate inactive workflows: {', '.join(inactive_workflows)}")
            else:
                recommendations.append("Check n8n instance connectivity and API access")
            
            # Webhook recommendations
            if not webhook_test.get("success"):
                recommendations.append("Check n8n webhook configuration and network connectivity")
            elif webhook_test.get("latency_ms", 0) > self.alert_thresholds["webhook_latency"]:
                recommendations.append("Investigate high webhook latency - check network and n8n performance")
            
            # General recommendations
            if not recommendations:
                recommendations.append("All workflows are healthy - continue monitoring")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Error generating recommendations - manual investigation required")
        
        return recommendations
    
    def _store_health_result(self, health_result: Dict[str, Any]):
        """Store health result in history"""
        try:
            # Add to history
            self.health_history.append(health_result)
            
            # Trim history if too large
            if len(self.health_history) > self.max_history_size:
                self.health_history = self.health_history[-self.max_history_size:]
                
        except Exception as e:
            logger.error(f"Error storing health result: {e}")
    
    async def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent health check history"""
        try:
            return self.health_history[-limit:] if self.health_history else []
        except Exception as e:
            logger.error(f"Error getting health history: {e}")
            return []
    
    async def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over specified time period"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter history by time
            recent_history = [
                result for result in self.health_history
                if datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00')) >= cutoff_time
            ]
            
            if not recent_history:
                return {
                    "success": False,
                    "message": "No health data available for specified time period"
                }
            
            # Calculate trends
            health_scores = [result["overall_health_score"] for result in recent_history]
            alert_counts = [len(result.get("alerts", [])) for result in recent_history]
            
            trends = {
                "time_period_hours": hours,
                "data_points": len(recent_history),
                "health_score": {
                    "current": health_scores[-1] if health_scores else 0,
                    "average": sum(health_scores) / len(health_scores) if health_scores else 0,
                    "min": min(health_scores) if health_scores else 0,
                    "max": max(health_scores) if health_scores else 0,
                    "trend": "improving" if len(health_scores) >= 2 and health_scores[-1] > health_scores[0] else "declining" if len(health_scores) >= 2 and health_scores[-1] < health_scores[0] else "stable"
                },
                "alert_frequency": {
                    "current": alert_counts[-1] if alert_counts else 0,
                    "average": sum(alert_counts) / len(alert_counts) if alert_counts else 0,
                    "total_alerts": sum(alert_counts),
                    "trend": "increasing" if len(alert_counts) >= 2 and alert_counts[-1] > alert_counts[0] else "decreasing" if len(alert_counts) >= 2 and alert_counts[-1] < alert_counts[0] else "stable"
                }
            }
            
            return {
                "success": True,
                "trends": trends,
                "recent_history": recent_history
            }
            
        except Exception as e:
            logger.error(f"Error getting health trends: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start_continuous_monitoring(self):
        """Start continuous health monitoring"""
        logger.info("Starting continuous workflow health monitoring")
        
        while True:
            try:
                health_result = await self.perform_health_check()
                
                # Send alerts if needed
                if health_result.get("alerts"):
                    await self._send_health_alerts(health_result["alerts"])
                
                # Wait for next check
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _send_health_alerts(self, alerts: List[Dict[str, Any]]):
        """Send health alerts via notification system"""
        try:
            high_severity_alerts = [alert for alert in alerts if alert.get("severity") == "high"]
            
            if high_severity_alerts:
                # Send high severity alerts immediately
                await n8n_service.send_notification(
                    notification_type="error_alert",
                    data={
                        "error_type": "Workflow Health Alert",
                        "error_message": f"{len(high_severity_alerts)} high severity workflow issues detected",
                        "component": "n8n_workflows",
                        "severity": "high",
                        "alerts": high_severity_alerts
                    },
                    channels=["slack"],
                    priority="urgent"
                )
                
        except Exception as e:
            logger.error(f"Error sending health alerts: {e}")


# Global service instance
workflow_health_service = WorkflowHealthService()