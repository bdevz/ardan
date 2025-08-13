"""
WebSocket service for broadcasting real-time updates
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from shared.utils import setup_logging

logger = setup_logging("websocket_service", "INFO")

class WebSocketService:
    """Service for broadcasting real-time updates via WebSocket"""
    
    def __init__(self):
        self.manager = None
        self._initialized = False
    
    def initialize(self, connection_manager):
        """Initialize with WebSocket connection manager"""
        self.manager = connection_manager
        self._initialized = True
        logger.info("WebSocket service initialized")
    
    async def broadcast_job_discovered(self, job_data: Dict[str, Any]):
        """Broadcast when a new job is discovered"""
        if not self._initialized:
            return
        
        message = {
            "type": "job_discovered",
            "data": {
                "job_id": job_data.get("id"),
                "title": job_data.get("title"),
                "budget": job_data.get("budget_max") or job_data.get("hourly_rate"),
                "client_rating": job_data.get("client_rating"),
                "match_score": job_data.get("match_score"),
                "posted_date": job_data.get("posted_date")
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "jobs")
        logger.info(f"Broadcasted job discovery: {job_data.get('title')}")
    
    async def broadcast_job_status_update(self, job_id: str, status: str, details: Dict[str, Any] = None):
        """Broadcast job status updates"""
        if not self._initialized:
            return
        
        message = {
            "type": "job_status_update",
            "data": {
                "job_id": job_id,
                "status": status,
                "details": details or {},
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "jobs")
        logger.info(f"Broadcasted job status update: {job_id} -> {status}")
    
    async def broadcast_proposal_generated(self, proposal_data: Dict[str, Any]):
        """Broadcast when a proposal is generated"""
        if not self._initialized:
            return
        
        message = {
            "type": "proposal_generated",
            "data": {
                "proposal_id": proposal_data.get("id"),
                "job_id": proposal_data.get("job_id"),
                "job_title": proposal_data.get("job_title"),
                "bid_amount": proposal_data.get("bid_amount"),
                "generated_at": proposal_data.get("generated_at")
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "jobs")
        logger.info(f"Broadcasted proposal generation: {proposal_data.get('job_title')}")
    
    async def broadcast_application_submitted(self, application_data: Dict[str, Any]):
        """Broadcast when an application is submitted"""
        if not self._initialized:
            return
        
        message = {
            "type": "application_submitted",
            "data": {
                "application_id": application_data.get("id"),
                "job_id": application_data.get("job_id"),
                "job_title": application_data.get("job_title"),
                "proposal_id": application_data.get("proposal_id"),
                "submitted_at": application_data.get("submitted_at"),
                "status": application_data.get("status")
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "jobs")
        logger.info(f"Broadcasted application submission: {application_data.get('job_title')}")
    
    async def broadcast_queue_status_update(self, queue_data: Dict[str, Any]):
        """Broadcast job queue status updates"""
        if not self._initialized:
            return
        
        message = {
            "type": "queue_status_update",
            "data": {
                "total_jobs": queue_data.get("total_jobs", 0),
                "pending_jobs": queue_data.get("pending_jobs", 0),
                "processing_jobs": queue_data.get("processing_jobs", 0),
                "completed_jobs": queue_data.get("completed_jobs", 0),
                "failed_jobs": queue_data.get("failed_jobs", 0),
                "queue_health": queue_data.get("queue_health", "unknown"),
                "last_updated": datetime.utcnow().isoformat()
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "queue")
        logger.debug("Broadcasted queue status update")
    
    async def broadcast_system_metrics(self, metrics_data: Dict[str, Any]):
        """Broadcast system performance metrics"""
        if not self._initialized:
            return
        
        message = {
            "type": "system_metrics_update",
            "data": {
                "applications_today": metrics_data.get("applications_today", 0),
                "success_rate": metrics_data.get("success_rate", 0),
                "avg_response_time": metrics_data.get("avg_response_time", 0),
                "active_sessions": metrics_data.get("active_sessions", 0),
                "system_health": metrics_data.get("system_health", "unknown"),
                "cpu_usage": metrics_data.get("cpu_usage", 0),
                "memory_usage": metrics_data.get("memory_usage", 0),
                "last_updated": datetime.utcnow().isoformat()
            }
        }
        
        await self.manager.broadcast_to_channel(message, "dashboard")
        await self.manager.broadcast_to_channel(message, "metrics")
        logger.debug("Broadcasted system metrics update")
    
    async def broadcast_error_alert(self, error_data: Dict[str, Any]):
        """Broadcast error alerts"""
        if not self._initialized:
            return
        
        message = {
            "type": "error_alert",
            "data": {
                "error_id": error_data.get("id"),
                "error_type": error_data.get("type"),
                "message": error_data.get("message"),
                "severity": error_data.get("severity", "medium"),
                "component": error_data.get("component"),
                "timestamp": error_data.get("timestamp", datetime.utcnow().isoformat()),
                "details": error_data.get("details", {})
            }
        }
        
        await self.manager.broadcast_to_all(message)
        logger.warning(f"Broadcasted error alert: {error_data.get('message')}")
    
    async def broadcast_system_status_change(self, status: str, message: str, details: Dict[str, Any] = None):
        """Broadcast system status changes"""
        if not self._initialized:
            return
        
        message_data = {
            "type": "system_status_change",
            "data": {
                "status": status,
                "message": message,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.manager.broadcast_to_channel(message_data, "dashboard")
        await self.manager.broadcast_to_channel(message_data, "system")
        logger.info(f"Broadcasted system status change: {status} - {message}")
    
    async def broadcast_automation_control(self, action: str, details: Dict[str, Any] = None):
        """Broadcast automation control actions (pause, resume, stop)"""
        if not self._initialized:
            return
        
        message = {
            "type": "automation_control",
            "data": {
                "action": action,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self.manager.broadcast_to_all(message)
        logger.info(f"Broadcasted automation control: {action}")

# Global WebSocket service instance
websocket_service = WebSocketService()

__all__ = ["websocket_service", "WebSocketService"]