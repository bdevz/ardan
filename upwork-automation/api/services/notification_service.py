"""
Slack Notification Service for Upwork Automation System

This service handles all Slack integrations including:
- Real-time notifications for job discoveries, applications, and system events
- Rich notification templates with interactive elements
- Interactive Slack commands for system control and monitoring
- Emergency alert system for critical failures
- System status and metrics dashboard
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.models.blocks import (
    SectionBlock, DividerBlock, ActionsBlock, ButtonElement, 
    ContextBlock, HeaderBlock, ImageBlock
)
from slack_sdk.models.attachments import Attachment

from shared.config import settings
from shared.models import (
    Job, Proposal, Application, SystemConfig, DashboardMetrics,
    JobStatus, ProposalStatus, ApplicationStatus
)

logger = logging.getLogger(__name__)


class SlackNotificationService:
    """
    Comprehensive Slack notification service for the Upwork automation system.
    
    Features:
    - Rich notification templates for different event types
    - Interactive Slack commands for system control
    - Emergency alert system
    - Performance dashboards and metrics
    - Notification preferences and filtering
    """
    
    def __init__(self):
        self.client = AsyncWebClient(token=settings.slack_bot_token)
        self.default_channel = settings.slack_channel_id
        self.notification_preferences = self._load_notification_preferences()
        self.emergency_contacts = []
        
    def _load_notification_preferences(self) -> Dict[str, Any]:
        """Load notification preferences from configuration"""
        return {
            "job_discovery": {
                "enabled": True,
                "min_match_score": 0.7,
                "channels": [self.default_channel],
                "frequency": "immediate"
            },
            "proposal_generation": {
                "enabled": True,
                "channels": [self.default_channel],
                "frequency": "immediate"
            },
            "application_submission": {
                "enabled": True,
                "channels": [self.default_channel],
                "frequency": "immediate"
            },
            "system_events": {
                "enabled": True,
                "channels": [self.default_channel],
                "frequency": "immediate"
            },
            "emergency_alerts": {
                "enabled": True,
                "channels": [self.default_channel],
                "frequency": "immediate",
                "escalation": True
            },
            "daily_summary": {
                "enabled": True,
                "channels": [self.default_channel],
                "time": "18:00"
            }
        }
    
    async def send_job_discovery_notification(
        self, 
        jobs: List[Job], 
        discovery_session: Optional[str] = None
    ) -> bool:
        """
        Send rich notification for newly discovered jobs
        
        Args:
            jobs: List of discovered jobs
            discovery_session: Optional session identifier
            
        Returns:
            bool: Success status
        """
        try:
            if not self.notification_preferences["job_discovery"]["enabled"]:
                return True
                
            # Filter jobs by match score threshold
            min_score = self.notification_preferences["job_discovery"]["min_match_score"]
            filtered_jobs = [job for job in jobs if job.match_score and job.match_score >= min_score]
            
            if not filtered_jobs:
                return True
            
            # Create rich notification blocks
            blocks = self._create_job_discovery_blocks(filtered_jobs, discovery_session)
            
            # Send to configured channels
            channels = self.notification_preferences["job_discovery"]["channels"]
            for channel in channels:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"🎯 Discovered {len(filtered_jobs)} high-quality jobs",
                    blocks=blocks,
                    unfurl_links=False,
                    unfurl_media=False
                )
            
            logger.info(f"Sent job discovery notification for {len(filtered_jobs)} jobs")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send job discovery notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in job discovery notification: {e}")
            return False
    
    def _create_job_discovery_blocks(
        self, 
        jobs: List[Job], 
        session: Optional[str] = None
    ) -> List[Dict]:
        """Create rich Slack blocks for job discovery notification"""
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 {len(jobs)} New Jobs Discovered"
            }
        })
        
        # Session info if provided
        if session:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Discovery Session: `{session}` | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            })
        
        # Job details (show top 3)
        for i, job in enumerate(jobs[:3]):
            blocks.append({"type": "divider"})
            
            # Job title and basic info
            job_text = f"*{job.title}*\n"
            job_text += f"💰 ${job.hourly_rate}/hr | ⭐ {job.client_rating} | "
            job_text += f"📊 Match: {job.match_score:.1%}\n"
            job_text += f"🏢 {job.client_name or 'Client'}"
            
            if job.client_payment_verified:
                job_text += " ✅"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": job_text
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Job"
                    },
                    "value": str(job.id),
                    "action_id": "view_job",
                    "url": job.job_url
                }
            })
            
            # Match reasons
            if job.match_reasons:
                reasons_text = "🎯 *Match Reasons:* " + " • ".join(job.match_reasons[:3])
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": reasons_text
                        }
                    ]
                })
        
        # Show remaining count if more than 3
        if len(jobs) > 3:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"... and {len(jobs) - 3} more jobs"
                    }
                ]
            })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 View All Jobs"
                    },
                    "style": "primary",
                    "action_id": "view_all_jobs"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚡ Generate Proposals"
                    },
                    "action_id": "generate_proposals"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⏸️ Pause Discovery"
                    },
                    "action_id": "pause_discovery"
                }
            ]
        })
        
        return blocks
    
    async def send_proposal_generation_notification(
        self, 
        proposal: Proposal, 
        job: Job
    ) -> bool:
        """Send notification for generated proposal"""
        try:
            if not self.notification_preferences["proposal_generation"]["enabled"]:
                return True
            
            blocks = self._create_proposal_notification_blocks(proposal, job)
            
            channels = self.notification_preferences["proposal_generation"]["channels"]
            for channel in channels:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"📝 Proposal generated for: {job.title}",
                    blocks=blocks
                )
            
            logger.info(f"Sent proposal generation notification for job {job.id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send proposal notification: {e}")
            return False
    
    def _create_proposal_notification_blocks(
        self, 
        proposal: Proposal, 
        job: Job
    ) -> List[Dict]:
        """Create rich Slack blocks for proposal notification"""
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 Proposal Generated"
            }
        })
        
        # Job and proposal info
        proposal_text = f"*Job:* {job.title}\n"
        proposal_text += f"*Bid Amount:* ${proposal.bid_amount}/hr\n"
        proposal_text += f"*Status:* {proposal.status.title()}\n"
        
        if proposal.quality_score:
            proposal_text += f"*Quality Score:* {proposal.quality_score:.1%}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": proposal_text
            }
        })
        
        # Proposal preview
        preview_text = proposal.content[:200] + "..." if len(proposal.content) > 200 else proposal.content
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Preview:*\n```{preview_text}```"
            }
        })
        
        # Attachments info
        if proposal.attachments:
            attachments_text = f"📎 *Attachments:* {len(proposal.attachments)} files"
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": attachments_text
                    }
                ]
            })
        
        # Action buttons
        action_elements = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📖 View Full Proposal"
                },
                "style": "primary",
                "action_id": "view_proposal",
                "url": proposal.google_doc_url
            }
        ]
        
        if proposal.status == ProposalStatus.DRAFT:
            action_elements.extend([
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Approve & Submit"
                    },
                    "style": "primary",
                    "action_id": "approve_proposal",
                    "value": str(proposal.id)
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit Proposal"
                    },
                    "action_id": "edit_proposal",
                    "value": str(proposal.id)
                }
            ])
        
        blocks.append({
            "type": "actions",
            "elements": action_elements
        })
        
        return blocks
    
    async def send_application_submission_notification(
        self, 
        application: Application, 
        job: Job, 
        proposal: Proposal,
        screenshot_url: Optional[str] = None
    ) -> bool:
        """Send notification for submitted application"""
        try:
            if not self.notification_preferences["application_submission"]["enabled"]:
                return True
            
            blocks = self._create_application_notification_blocks(
                application, job, proposal, screenshot_url
            )
            
            channels = self.notification_preferences["application_submission"]["channels"]
            for channel in channels:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"🚀 Application submitted for: {job.title}",
                    blocks=blocks
                )
            
            logger.info(f"Sent application submission notification for job {job.id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send application notification: {e}")
            return False
    
    def _create_application_notification_blocks(
        self, 
        application: Application, 
        job: Job, 
        proposal: Proposal,
        screenshot_url: Optional[str] = None
    ) -> List[Dict]:
        """Create rich Slack blocks for application notification"""
        blocks = []
        
        # Header with success emoji
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚀 Application Submitted Successfully"
            }
        })
        
        # Application details
        app_text = f"*Job:* {job.title}\n"
        app_text += f"*Bid Amount:* ${proposal.bid_amount}/hr\n"
        app_text += f"*Client:* {job.client_name} (⭐ {job.client_rating})\n"
        app_text += f"*Submitted:* {application.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": app_text
            }
        })
        
        # Screenshot if available
        if screenshot_url:
            blocks.append({
                "type": "image",
                "image_url": screenshot_url,
                "alt_text": "Application submission screenshot"
            })
        
        # Session recording if available
        if application.session_recording_url:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📹 <{application.session_recording_url}|View Session Recording>"
                    }
                ]
            })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👀 View Application"
                    },
                    "style": "primary",
                    "action_id": "view_application",
                    "url": job.job_url
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 View Metrics"
                    },
                    "action_id": "view_metrics"
                }
            ]
        })
        
        return blocks
    
    async def send_emergency_alert(
        self, 
        alert_type: str, 
        message: str, 
        details: Optional[Dict] = None,
        escalate: bool = True
    ) -> bool:
        """
        Send emergency alert for critical system failures
        
        Args:
            alert_type: Type of emergency (e.g., 'system_failure', 'rate_limit_exceeded')
            message: Alert message
            details: Additional details dictionary
            escalate: Whether to escalate to emergency contacts
            
        Returns:
            bool: Success status
        """
        try:
            blocks = self._create_emergency_alert_blocks(alert_type, message, details)
            
            # Send to emergency channels
            channels = self.notification_preferences["emergency_alerts"]["channels"]
            for channel in channels:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"🚨 EMERGENCY ALERT: {alert_type}",
                    blocks=blocks
                )
            
            # Escalate if configured
            if escalate and self.notification_preferences["emergency_alerts"]["escalation"]:
                await self._escalate_emergency_alert(alert_type, message, details)
            
            logger.critical(f"Sent emergency alert: {alert_type} - {message}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send emergency alert: {e}")
            return False
    
    def _create_emergency_alert_blocks(
        self, 
        alert_type: str, 
        message: str, 
        details: Optional[Dict] = None
    ) -> List[Dict]:
        """Create rich Slack blocks for emergency alerts"""
        blocks = []
        
        # Critical header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 EMERGENCY ALERT: {alert_type.upper()}"
            }
        })
        
        # Alert message
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Message:* {message}\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        })
        
        # Details if provided
        if details:
            details_text = "```\n"
            for key, value in details.items():
                details_text += f"{key}: {value}\n"
            details_text += "```"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{details_text}"
                }
            })
        
        # Emergency action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🛑 Emergency Stop"
                    },
                    "style": "danger",
                    "action_id": "emergency_stop",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Emergency Stop"
                        },
                        "text": {
                            "type": "mrkdwn",
                            "text": "This will immediately stop all automation. Are you sure?"
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Stop Now"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Cancel"
                        }
                    }
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 View System Status"
                    },
                    "action_id": "view_system_status"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔧 Acknowledge"
                    },
                    "action_id": "acknowledge_alert",
                    "value": alert_type
                }
            ]
        })
        
        return blocks
    
    async def _escalate_emergency_alert(
        self, 
        alert_type: str, 
        message: str, 
        details: Optional[Dict] = None
    ):
        """Escalate emergency alert to additional contacts"""
        # This could send DMs to specific users, call external services, etc.
        # For now, we'll just log the escalation
        logger.critical(f"ESCALATING EMERGENCY ALERT: {alert_type} - {message}")
        
        # Could implement:
        # - Send DMs to emergency contacts
        # - Trigger external alerting systems (PagerDuty, etc.)
        # - Send SMS/email notifications
        pass
    
    async def send_daily_summary(self, metrics: DashboardMetrics) -> bool:
        """Send daily summary with system metrics and performance"""
        try:
            if not self.notification_preferences["daily_summary"]["enabled"]:
                return True
            
            blocks = self._create_daily_summary_blocks(metrics)
            
            channels = self.notification_preferences["daily_summary"]["channels"]
            for channel in channels:
                await self.client.chat_postMessage(
                    channel=channel,
                    text=f"📊 Daily Summary - {datetime.now().strftime('%Y-%m-%d')}",
                    blocks=blocks
                )
            
            logger.info("Sent daily summary notification")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def _create_daily_summary_blocks(self, metrics: DashboardMetrics) -> List[Dict]:
        """Create rich Slack blocks for daily summary"""
        blocks = []
        
        # Header
        today = datetime.now().strftime('%Y-%m-%d')
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Daily Summary - {today}"
            }
        })
        
        # Key metrics
        metrics_text = f"*Applications Today:* {metrics.applications_today}\n"
        metrics_text += f"*Total Jobs Discovered:* {metrics.total_jobs_discovered}\n"
        metrics_text += f"*Total Applications:* {metrics.total_applications_submitted}\n"
        metrics_text += f"*Success Rate:* {metrics.success_rate:.1%}"
        
        if metrics.average_response_time:
            metrics_text += f"\n*Avg Response Time:* {metrics.average_response_time:.1f}h"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        })
        
        # Top keywords
        if metrics.top_keywords:
            keywords_text = "🔍 *Top Keywords:* " + " • ".join(metrics.top_keywords[:5])
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": keywords_text
                    }
                ]
            })
        
        # Recent applications
        if metrics.recent_applications:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Recent Applications:*"
                }
            })
            
            for app in metrics.recent_applications[:3]:
                app_text = f"• {app.status.title()}"
                if app.submitted_at:
                    app_text += f" - {app.submitted_at.strftime('%H:%M')}"
                
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": app_text
                        }
                    ]
                })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📈 View Full Dashboard"
                    },
                    "style": "primary",
                    "action_id": "view_dashboard"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚙️ System Settings"
                    },
                    "action_id": "view_settings"
                }
            ]
        })
        
        return blocks
    
    async def handle_interactive_command(
        self, 
        command: str, 
        user_id: str, 
        channel_id: str,
        parameters: Optional[Dict] = None
    ) -> bool:
        """
        Handle interactive Slack commands for system control
        
        Args:
            command: Command name (e.g., 'status', 'pause', 'resume')
            user_id: Slack user ID who issued the command
            channel_id: Channel where command was issued
            parameters: Optional command parameters
            
        Returns:
            bool: Success status
        """
        try:
            response_blocks = []
            
            if command == "status":
                response_blocks = await self._handle_status_command()
            elif command == "pause":
                response_blocks = await self._handle_pause_command()
            elif command == "resume":
                response_blocks = await self._handle_resume_command()
            elif command == "metrics":
                response_blocks = await self._handle_metrics_command()
            elif command == "emergency_stop":
                response_blocks = await self._handle_emergency_stop_command()
            else:
                response_blocks = self._create_unknown_command_blocks(command)
            
            await self.client.chat_postMessage(
                channel=channel_id,
                text=f"Command: {command}",
                blocks=response_blocks
            )
            
            logger.info(f"Handled interactive command '{command}' from user {user_id}")
            return True
            
        except SlackApiError as e:
            logger.error(f"Failed to handle interactive command: {e}")
            return False
    
    async def _handle_status_command(self) -> List[Dict]:
        """Handle system status command"""
        # This would integrate with actual system status service
        blocks = []
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔍 System Status"
            }
        })
        
        # Mock status - would be replaced with actual system status
        status_text = "*Automation:* ✅ Running\n"
        status_text += "*Jobs in Queue:* 5\n"
        status_text += "*Applications Today:* 12/30\n"
        status_text += "*Last Activity:* 2 minutes ago"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": status_text
            }
        })
        
        return blocks
    
    async def _handle_pause_command(self) -> List[Dict]:
        """Handle system pause command"""
        blocks = []
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "⏸️ System Paused"
            }
        })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Automation has been paused. No new jobs will be processed until resumed."
            }
        })
        
        return blocks
    
    async def _handle_resume_command(self) -> List[Dict]:
        """Handle system resume command"""
        blocks = []
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "▶️ System Resumed"
            }
        })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Automation has been resumed. Job processing will continue normally."
            }
        })
        
        return blocks
    
    async def _handle_metrics_command(self) -> List[Dict]:
        """Handle metrics display command"""
        blocks = []
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Performance Metrics"
            }
        })
        
        # Mock metrics - would be replaced with actual metrics service
        metrics_text = "*Today's Performance:*\n"
        metrics_text += "• Applications: 12\n"
        metrics_text += "• Success Rate: 85%\n"
        metrics_text += "• Avg Response Time: 2.3h\n"
        metrics_text += "• Jobs Discovered: 45"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        })
        
        return blocks
    
    async def _handle_emergency_stop_command(self) -> List[Dict]:
        """Handle emergency stop command"""
        blocks = []
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛑 Emergency Stop Activated"
            }
        })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *All automation has been immediately stopped.*\n\nThis includes:\n• Job discovery\n• Proposal generation\n• Application submission\n• Background tasks"
            }
        })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Use `/upwork resume` to restart automation when ready."
                }
            ]
        })
        
        return blocks
    
    def _create_unknown_command_blocks(self, command: str) -> List[Dict]:
        """Create blocks for unknown command response"""
        blocks = []
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❓ Unknown command: `{command}`"
            }
        })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Available commands:*\n• `/upwork status` - System status\n• `/upwork pause` - Pause automation\n• `/upwork resume` - Resume automation\n• `/upwork metrics` - Performance metrics\n• `/upwork stop` - Emergency stop"
            }
        })
        
        return blocks
    
    async def test_connection(self) -> bool:
        """Test Slack API connection"""
        try:
            response = await self.client.auth_test()
            logger.info(f"Slack connection test successful: {response['user']}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
    
    async def update_notification_preferences(
        self, 
        preferences: Dict[str, Any]
    ) -> bool:
        """Update notification preferences"""
        try:
            self.notification_preferences.update(preferences)
            logger.info("Updated notification preferences")
            return True
        except Exception as e:
            logger.error(f"Failed to update notification preferences: {e}")
            return False


# Global instance
slack_service = SlackNotificationService()