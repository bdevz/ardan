"""
Slack Integration Router

Handles Slack slash commands, interactive components, and webhook events
for the Upwork automation system.
"""

import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from slack_sdk.signature import SignatureVerifier

from shared.config import settings
from services.notification_service import slack_service
from services.system_service import system_service
from services.metrics_service import metrics_service
from services.job_service import job_service
from services.application_service import application_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slack", tags=["slack"])

# Initialize signature verifier for Slack request verification
signature_verifier = SignatureVerifier(settings.slack_signing_secret) if hasattr(settings, 'slack_signing_secret') else None


@router.post("/commands")
async def handle_slash_command(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack slash commands for system control and monitoring
    
    Supported commands:
    - /upwork status - Show system status
    - /upwork pause - Pause automation
    - /upwork resume - Resume automation  
    - /upwork metrics - Show performance metrics
    - /upwork stop - Emergency stop
    """
    try:
        # Verify Slack request signature
        if signature_verifier:
            body = await request.body()
            timestamp = request.headers.get("X-Slack-Request-Timestamp")
            signature = request.headers.get("X-Slack-Signature")
            
            if not signature_verifier.is_valid_request(body, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
        
        # Parse form data
        form_data = await request.form()
        command_data = {
            "command": form_data.get("command", "").replace("/upwork", "").strip(),
            "text": form_data.get("text", ""),
            "user_id": form_data.get("user_id"),
            "user_name": form_data.get("user_name"),
            "channel_id": form_data.get("channel_id"),
            "channel_name": form_data.get("channel_name"),
            "team_id": form_data.get("team_id"),
            "response_url": form_data.get("response_url")
        }
        
        logger.info(f"Received slash command: {command_data['command']} from {command_data['user_name']}")
        
        # Handle command asynchronously
        background_tasks.add_task(
            process_slash_command,
            command_data
        )
        
        # Return immediate response
        return {
            "response_type": "ephemeral",
            "text": f"Processing command: {command_data['command']}..."
        }
        
    except Exception as e:
        logger.error(f"Error handling slash command: {e}")
        return {
            "response_type": "ephemeral",
            "text": "❌ Error processing command. Please try again."
        }


@router.post("/interactions")
async def handle_interactive_components(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack interactive components (buttons, select menus, etc.)
    """
    try:
        # Verify Slack request signature
        if signature_verifier:
            body = await request.body()
            timestamp = request.headers.get("X-Slack-Request-Timestamp")
            signature = request.headers.get("X-Slack-Signature")
            
            if not signature_verifier.is_valid_request(body, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
        
        # Parse payload
        form_data = await request.form()
        payload = json.loads(form_data.get("payload", "{}"))
        
        action_type = payload.get("type")
        user = payload.get("user", {})
        channel = payload.get("channel", {})
        
        logger.info(f"Received interactive component: {action_type} from {user.get('name')}")
        
        if action_type == "block_actions":
            # Handle button clicks and other block actions
            background_tasks.add_task(
                process_block_actions,
                payload
            )
        elif action_type == "shortcut":
            # Handle global shortcuts
            background_tasks.add_task(
                process_shortcut,
                payload
            )
        
        # Return immediate acknowledgment
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling interactive component: {e}")
        return {"status": "error"}


@router.post("/events")
async def handle_slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhooks
    """
    try:
        # Verify Slack request signature
        if signature_verifier:
            body = await request.body()
            timestamp = request.headers.get("X-Slack-Request-Timestamp")
            signature = request.headers.get("X-Slack-Signature")
            
            if not signature_verifier.is_valid_request(body, timestamp, signature):
                raise HTTPException(status_code=401, detail="Invalid Slack signature")
        
        event_data = await request.json()
        
        # Handle URL verification challenge
        if event_data.get("type") == "url_verification":
            return {"challenge": event_data.get("challenge")}
        
        # Handle actual events
        if event_data.get("type") == "event_callback":
            event = event_data.get("event", {})
            event_type = event.get("type")
            
            logger.info(f"Received Slack event: {event_type}")
            
            # Process event asynchronously
            background_tasks.add_task(
                process_slack_event,
                event
            )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        return {"status": "error"}


async def process_slash_command(command_data: Dict[str, Any]):
    """Process slash command asynchronously"""
    try:
        command = command_data["command"]
        user_id = command_data["user_id"]
        channel_id = command_data["channel_id"]
        text = command_data["text"]
        
        # Parse command parameters
        parameters = {}
        if text:
            # Simple parameter parsing (could be enhanced)
            parts = text.split()
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    parameters[key] = value
        
        # Handle different commands
        if command == "status":
            await handle_status_command(user_id, channel_id, parameters)
        elif command == "pause":
            await handle_pause_command(user_id, channel_id, parameters)
        elif command == "resume":
            await handle_resume_command(user_id, channel_id, parameters)
        elif command == "metrics":
            await handle_metrics_command(user_id, channel_id, parameters)
        elif command == "stop":
            await handle_emergency_stop_command(user_id, channel_id, parameters)
        elif command == "jobs":
            await handle_jobs_command(user_id, channel_id, parameters)
        elif command == "help":
            await handle_help_command(user_id, channel_id, parameters)
        else:
            await slack_service.handle_interactive_command(
                command, user_id, channel_id, parameters
            )
        
    except Exception as e:
        logger.error(f"Error processing slash command: {e}")


async def process_block_actions(payload: Dict[str, Any]):
    """Process block action interactions"""
    try:
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        channel = payload.get("channel", {})
        
        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")
            
            logger.info(f"Processing block action: {action_id}")
            
            if action_id == "view_job":
                await handle_view_job_action(action, user, channel)
            elif action_id == "view_all_jobs":
                await handle_view_all_jobs_action(action, user, channel)
            elif action_id == "generate_proposals":
                await handle_generate_proposals_action(action, user, channel)
            elif action_id == "pause_discovery":
                await handle_pause_discovery_action(action, user, channel)
            elif action_id == "approve_proposal":
                await handle_approve_proposal_action(action, user, channel)
            elif action_id == "edit_proposal":
                await handle_edit_proposal_action(action, user, channel)
            elif action_id == "emergency_stop":
                await handle_emergency_stop_action(action, user, channel)
            elif action_id == "acknowledge_alert":
                await handle_acknowledge_alert_action(action, user, channel)
            elif action_id == "view_dashboard":
                await handle_view_dashboard_action(action, user, channel)
            elif action_id == "view_settings":
                await handle_view_settings_action(action, user, channel)
            
    except Exception as e:
        logger.error(f"Error processing block actions: {e}")


async def process_shortcut(payload: Dict[str, Any]):
    """Process global shortcuts"""
    try:
        callback_id = payload.get("callback_id")
        user = payload.get("user", {})
        
        logger.info(f"Processing shortcut: {callback_id}")
        
        if callback_id == "system_dashboard":
            await show_system_dashboard(user)
        elif callback_id == "emergency_controls":
            await show_emergency_controls(user)
        
    except Exception as e:
        logger.error(f"Error processing shortcut: {e}")


async def process_slack_event(event: Dict[str, Any]):
    """Process Slack events"""
    try:
        event_type = event.get("type")
        
        if event_type == "app_mention":
            # Handle @bot mentions
            await handle_app_mention(event)
        elif event_type == "message":
            # Handle direct messages
            await handle_direct_message(event)
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}")


# Command handlers
async def handle_status_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle system status command"""
    try:
        # Get system status
        status = await system_service.get_system_status()
        
        blocks = []
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔍 System Status"
            }
        })
        
        status_text = f"*Automation:* {'✅ Running' if status.automation_enabled else '⏸️ Paused'}\n"
        status_text += f"*Jobs in Queue:* {status.jobs_in_queue}\n"
        status_text += f"*Applications Today:* {status.applications_today}/{status.daily_limit}\n"
        
        if status.success_rate:
            status_text += f"*Success Rate:* {status.success_rate:.1%}\n"
        
        if status.last_application:
            status_text += f"*Last Application:* {status.last_application.strftime('%H:%M:%S')}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": status_text
            }
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="System Status",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling status command: {e}")


async def handle_pause_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle system pause command"""
    try:
        # Pause the system
        await system_service.pause_automation()
        
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
                "text": f"Automation paused by <@{user_id}>.\n\nNo new jobs will be processed until resumed."
            }
        })
        
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "▶️ Resume"
                    },
                    "style": "primary",
                    "action_id": "resume_system"
                }
            ]
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="System Paused",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling pause command: {e}")


async def handle_resume_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle system resume command"""
    try:
        # Resume the system
        await system_service.resume_automation()
        
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
                "text": f"Automation resumed by <@{user_id}>.\n\nJob processing will continue normally."
            }
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="System Resumed",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling resume command: {e}")


async def handle_metrics_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle metrics display command"""
    try:
        # Get metrics
        metrics = await metrics_service.get_dashboard_metrics()
        
        blocks = []
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Performance Metrics"
            }
        })
        
        metrics_text = f"*Today's Performance:*\n"
        metrics_text += f"• Applications: {metrics.applications_today}\n"
        metrics_text += f"• Success Rate: {metrics.success_rate:.1%}\n"
        metrics_text += f"• Jobs Discovered: {metrics.total_jobs_discovered}\n"
        metrics_text += f"• Total Applications: {metrics.total_applications_submitted}"
        
        if metrics.average_response_time:
            metrics_text += f"\n• Avg Response Time: {metrics.average_response_time:.1f}h"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        })
        
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
        
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📈 Full Dashboard"
                    },
                    "style": "primary",
                    "action_id": "view_dashboard"
                }
            ]
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="Performance Metrics",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling metrics command: {e}")


async def handle_emergency_stop_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle emergency stop command"""
    try:
        # Emergency stop
        await system_service.emergency_stop()
        
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
                "text": f"⚠️ *Emergency stop activated by <@{user_id}>*\n\nAll automation has been immediately stopped:\n• Job discovery\n• Proposal generation\n• Application submission\n• Background tasks"
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
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="Emergency Stop",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling emergency stop command: {e}")


async def handle_jobs_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle jobs listing command"""
    try:
        # Get recent jobs
        jobs = await job_service.get_recent_jobs(limit=5)
        
        blocks = []
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "💼 Recent Jobs"
            }
        })
        
        if not jobs:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No recent jobs found."
                }
            })
        else:
            for job in jobs:
                job_text = f"*{job.title}*\n"
                job_text += f"💰 ${job.hourly_rate}/hr | ⭐ {job.client_rating} | "
                job_text += f"📊 {job.status.title()}"
                
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
                            "text": "View"
                        },
                        "action_id": "view_job",
                        "value": str(job.id)
                    }
                })
        
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
                }
            ]
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="Recent Jobs",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling jobs command: {e}")


async def handle_help_command(user_id: str, channel_id: str, parameters: Dict):
    """Handle help command"""
    try:
        blocks = []
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "❓ Upwork Automation Help"
            }
        })
        
        help_text = "*Available Commands:*\n"
        help_text += "• `/upwork status` - Show system status\n"
        help_text += "• `/upwork pause` - Pause automation\n"
        help_text += "• `/upwork resume` - Resume automation\n"
        help_text += "• `/upwork metrics` - Show performance metrics\n"
        help_text += "• `/upwork jobs` - List recent jobs\n"
        help_text += "• `/upwork stop` - Emergency stop (immediate)\n"
        help_text += "• `/upwork help` - Show this help message"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": help_text
            }
        })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 You can also use interactive buttons in notifications for quick actions."
                }
            ]
        })
        
        await slack_service.client.chat_postMessage(
            channel=channel_id,
            text="Help",
            blocks=blocks
        )
        
    except Exception as e:
        logger.error(f"Error handling help command: {e}")


# Action handlers
async def handle_view_job_action(action: Dict, user: Dict, channel: Dict):
    """Handle view job button click"""
    job_id = action.get("value")
    # Implementation would show job details
    logger.info(f"User {user.get('name')} requested to view job {job_id}")


async def handle_view_all_jobs_action(action: Dict, user: Dict, channel: Dict):
    """Handle view all jobs button click"""
    # Implementation would show job list
    logger.info(f"User {user.get('name')} requested to view all jobs")


async def handle_generate_proposals_action(action: Dict, user: Dict, channel: Dict):
    """Handle generate proposals button click"""
    # Implementation would trigger proposal generation
    logger.info(f"User {user.get('name')} requested to generate proposals")


async def handle_pause_discovery_action(action: Dict, user: Dict, channel: Dict):
    """Handle pause discovery button click"""
    # Implementation would pause job discovery
    logger.info(f"User {user.get('name')} requested to pause discovery")


async def handle_approve_proposal_action(action: Dict, user: Dict, channel: Dict):
    """Handle approve proposal button click"""
    proposal_id = action.get("value")
    # Implementation would approve and submit proposal
    logger.info(f"User {user.get('name')} approved proposal {proposal_id}")


async def handle_edit_proposal_action(action: Dict, user: Dict, channel: Dict):
    """Handle edit proposal button click"""
    proposal_id = action.get("value")
    # Implementation would open proposal for editing
    logger.info(f"User {user.get('name')} requested to edit proposal {proposal_id}")


async def handle_emergency_stop_action(action: Dict, user: Dict, channel: Dict):
    """Handle emergency stop button click"""
    await system_service.emergency_stop()
    logger.critical(f"Emergency stop activated by user {user.get('name')}")


async def handle_acknowledge_alert_action(action: Dict, user: Dict, channel: Dict):
    """Handle acknowledge alert button click"""
    alert_type = action.get("value")
    # Implementation would acknowledge the alert
    logger.info(f"User {user.get('name')} acknowledged alert: {alert_type}")


async def handle_view_dashboard_action(action: Dict, user: Dict, channel: Dict):
    """Handle view dashboard button click"""
    # Implementation would show dashboard link or summary
    logger.info(f"User {user.get('name')} requested dashboard view")


async def handle_view_settings_action(action: Dict, user: Dict, channel: Dict):
    """Handle view settings button click"""
    # Implementation would show settings interface
    logger.info(f"User {user.get('name')} requested settings view")


# Event handlers
async def handle_app_mention(event: Dict[str, Any]):
    """Handle @bot mentions"""
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")
    
    # Simple mention response
    await slack_service.client.chat_postMessage(
        channel=channel,
        text=f"Hi <@{user}>! Use `/upwork help` to see available commands."
    )


async def handle_direct_message(event: Dict[str, Any]):
    """Handle direct messages to the bot"""
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")
    
    # Simple DM response
    await slack_service.client.chat_postMessage(
        channel=channel,
        text="Hello! I'm the Upwork Automation bot. Use `/upwork help` to see what I can do."
    )


# Health check endpoint
@router.get("/health")
async def slack_health_check():
    """Health check for Slack integration"""
    try:
        connection_ok = await slack_service.test_connection()
        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "slack_connected": connection_ok
        }
    except Exception as e:
        logger.error(f"Slack health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }