"""
Slack Bot Setup and Configuration

This module handles the setup and configuration of the Slack bot,
including app manifest, permissions, and interactive components.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SlackBotConfig:
    """Configuration and setup utilities for the Slack bot"""
    
    @staticmethod
    def get_app_manifest() -> Dict[str, Any]:
        """
        Get the Slack app manifest configuration
        
        This manifest can be used to create or update the Slack app
        with all necessary permissions and features.
        """
        return {
            "display_information": {
                "name": "Upwork Automation Bot",
                "description": "AI-powered Upwork job automation and monitoring system",
                "background_color": "#2c3e50",
                "long_description": "The Upwork Automation Bot helps manage and monitor your automated job discovery, proposal generation, and application submission processes. Get real-time notifications, control system operations, and view performance metrics directly from Slack."
            },
            "features": {
                "app_home": {
                    "home_tab_enabled": True,
                    "messages_tab_enabled": True,
                    "messages_tab_read_only_enabled": False
                },
                "bot_user": {
                    "display_name": "Upwork Bot",
                    "always_online": True
                },
                "shortcuts": [
                    {
                        "name": "System Dashboard",
                        "type": "global",
                        "callback_id": "system_dashboard",
                        "description": "View system status and metrics"
                    },
                    {
                        "name": "Emergency Controls",
                        "type": "global", 
                        "callback_id": "emergency_controls",
                        "description": "Access emergency stop and system controls"
                    }
                ],
                "slash_commands": [
                    {
                        "command": "/upwork",
                        "description": "Control and monitor Upwork automation system",
                        "usage_hint": "status | pause | resume | metrics | jobs | stop | help",
                        "should_escape": False
                    }
                ]
            },
            "oauth_config": {
                "scopes": {
                    "bot": [
                        "app_mentions:read",
                        "channels:read",
                        "chat:write",
                        "chat:write.public",
                        "commands",
                        "files:write",
                        "im:history",
                        "im:read",
                        "im:write",
                        "incoming-webhook",
                        "users:read"
                    ]
                }
            },
            "settings": {
                "event_subscriptions": {
                    "request_url": "https://your-domain.com/api/slack/events",
                    "bot_events": [
                        "app_mention",
                        "message.im"
                    ]
                },
                "interactivity": {
                    "is_enabled": True,
                    "request_url": "https://your-domain.com/api/slack/interactions"
                },
                "org_deploy_enabled": False,
                "socket_mode_enabled": False,
                "token_rotation_enabled": False
            }
        }
    
    @staticmethod
    def get_required_permissions() -> List[str]:
        """Get list of required Slack permissions"""
        return [
            "app_mentions:read",      # Read mentions of the bot
            "channels:read",          # Read channel information
            "chat:write",            # Send messages
            "chat:write.public",     # Send messages to public channels
            "commands",              # Handle slash commands
            "files:write",           # Upload files (screenshots, reports)
            "im:history",            # Read DM history
            "im:read",               # Read DMs
            "im:write",              # Send DMs
            "incoming-webhook",      # Receive webhooks
            "users:read"             # Read user information
        ]
    
    @staticmethod
    def get_setup_instructions() -> Dict[str, Any]:
        """Get setup instructions for the Slack bot"""
        return {
            "title": "Slack Bot Setup Instructions",
            "steps": [
                {
                    "step": 1,
                    "title": "Create Slack App",
                    "description": "Go to https://api.slack.com/apps and create a new app",
                    "details": [
                        "Choose 'From an app manifest'",
                        "Select your workspace",
                        "Paste the app manifest JSON",
                        "Review and create the app"
                    ]
                },
                {
                    "step": 2,
                    "title": "Configure OAuth & Permissions",
                    "description": "Set up bot permissions and install to workspace",
                    "details": [
                        "Go to 'OAuth & Permissions' in your app settings",
                        "Add the required bot token scopes",
                        "Install the app to your workspace",
                        "Copy the Bot User OAuth Token"
                    ]
                },
                {
                    "step": 3,
                    "title": "Set Environment Variables",
                    "description": "Configure the required environment variables",
                    "details": [
                        "SLACK_BOT_TOKEN=xoxb-your-bot-token",
                        "SLACK_CHANNEL_ID=C1234567890",
                        "SLACK_SIGNING_SECRET=your-signing-secret"
                    ]
                },
                {
                    "step": 4,
                    "title": "Configure Event Subscriptions",
                    "description": "Set up event subscriptions for real-time interactions",
                    "details": [
                        "Go to 'Event Subscriptions' in your app settings",
                        "Enable events and set Request URL to your endpoint",
                        "Subscribe to bot events: app_mention, message.im",
                        "Save changes"
                    ]
                },
                {
                    "step": 5,
                    "title": "Configure Interactivity",
                    "description": "Enable interactive components",
                    "details": [
                        "Go to 'Interactivity & Shortcuts' in your app settings",
                        "Turn on Interactivity",
                        "Set Request URL to your interactions endpoint",
                        "Add global shortcuts if desired",
                        "Save changes"
                    ]
                },
                {
                    "step": 6,
                    "title": "Test the Integration",
                    "description": "Verify the bot is working correctly",
                    "details": [
                        "Invite the bot to your channel: /invite @upwork-bot",
                        "Test slash command: /upwork status",
                        "Test mention: @upwork-bot help",
                        "Check health endpoint: GET /api/slack/health"
                    ]
                }
            ],
            "troubleshooting": {
                "common_issues": [
                    {
                        "issue": "Bot not responding to commands",
                        "solutions": [
                            "Check SLACK_BOT_TOKEN is correct",
                            "Verify bot is invited to the channel",
                            "Check app permissions and scopes",
                            "Review server logs for errors"
                        ]
                    },
                    {
                        "issue": "Interactive components not working",
                        "solutions": [
                            "Verify SLACK_SIGNING_SECRET is set",
                            "Check interactivity is enabled in app settings",
                            "Ensure request URL is accessible",
                            "Verify SSL certificate is valid"
                        ]
                    },
                    {
                        "issue": "Events not being received",
                        "solutions": [
                            "Check event subscriptions are configured",
                            "Verify request URL responds to challenge",
                            "Review bot event subscriptions",
                            "Check server accessibility from Slack"
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def validate_configuration() -> Dict[str, Any]:
        """Validate Slack bot configuration"""
        from shared.config import settings
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "configuration": {}
        }
        
        # Check required environment variables
        required_vars = {
            "SLACK_BOT_TOKEN": settings.slack_bot_token,
            "SLACK_CHANNEL_ID": settings.slack_channel_id
        }
        
        for var_name, var_value in required_vars.items():
            if not var_value:
                validation_results["errors"].append(f"Missing required environment variable: {var_name}")
                validation_results["valid"] = False
            else:
                validation_results["configuration"][var_name] = "✓ Set"
        
        # Check optional but recommended variables
        optional_vars = {
            "SLACK_SIGNING_SECRET": getattr(settings, 'slack_signing_secret', None)
        }
        
        for var_name, var_value in optional_vars.items():
            if not var_value:
                validation_results["warnings"].append(f"Recommended environment variable not set: {var_name}")
            else:
                validation_results["configuration"][var_name] = "✓ Set"
        
        # Validate token format
        if settings.slack_bot_token:
            if not settings.slack_bot_token.startswith('xoxb-'):
                validation_results["errors"].append("SLACK_BOT_TOKEN should start with 'xoxb-'")
                validation_results["valid"] = False
        
        # Validate channel ID format
        if settings.slack_channel_id:
            if not settings.slack_channel_id.startswith('C'):
                validation_results["warnings"].append("SLACK_CHANNEL_ID should start with 'C' for channels")
        
        return validation_results
    
    @staticmethod
    def get_notification_templates() -> Dict[str, Any]:
        """Get predefined notification templates"""
        return {
            "job_discovery": {
                "title": "🎯 New Jobs Discovered",
                "color": "#36a64f",
                "fields": [
                    {"title": "Jobs Found", "value": "{job_count}", "short": True},
                    {"title": "Match Score", "value": "{avg_match_score}%", "short": True},
                    {"title": "Top Client Rating", "value": "{top_rating}⭐", "short": True},
                    {"title": "Avg Hourly Rate", "value": "${avg_rate}/hr", "short": True}
                ]
            },
            "proposal_generated": {
                "title": "📝 Proposal Generated",
                "color": "#3498db",
                "fields": [
                    {"title": "Job Title", "value": "{job_title}", "short": False},
                    {"title": "Bid Amount", "value": "${bid_amount}/hr", "short": True},
                    {"title": "Quality Score", "value": "{quality_score}%", "short": True}
                ]
            },
            "application_submitted": {
                "title": "🚀 Application Submitted",
                "color": "#e74c3c",
                "fields": [
                    {"title": "Job Title", "value": "{job_title}", "short": False},
                    {"title": "Client", "value": "{client_name}", "short": True},
                    {"title": "Bid Amount", "value": "${bid_amount}/hr", "short": True}
                ]
            },
            "system_alert": {
                "title": "⚠️ System Alert",
                "color": "#f39c12",
                "fields": [
                    {"title": "Alert Type", "value": "{alert_type}", "short": True},
                    {"title": "Severity", "value": "{severity}", "short": True},
                    {"title": "Time", "value": "{timestamp}", "short": False}
                ]
            },
            "emergency_alert": {
                "title": "🚨 EMERGENCY ALERT",
                "color": "#e74c3c",
                "fields": [
                    {"title": "Alert Type", "value": "{alert_type}", "short": True},
                    {"title": "Status", "value": "CRITICAL", "short": True},
                    {"title": "Action Required", "value": "Immediate", "short": False}
                ]
            }
        }
    
    @staticmethod
    def get_interactive_components() -> Dict[str, Any]:
        """Get predefined interactive component templates"""
        return {
            "system_controls": {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "⏸️ Pause"},
                        "style": "primary",
                        "action_id": "pause_system"
                    },
                    {
                        "type": "button", 
                        "text": {"type": "plain_text", "text": "▶️ Resume"},
                        "style": "primary",
                        "action_id": "resume_system"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🛑 Emergency Stop"},
                        "style": "danger",
                        "action_id": "emergency_stop",
                        "confirm": {
                            "title": {"type": "plain_text", "text": "Emergency Stop"},
                            "text": {"type": "mrkdwn", "text": "This will immediately stop all automation. Are you sure?"},
                            "confirm": {"type": "plain_text", "text": "Stop Now"},
                            "deny": {"type": "plain_text", "text": "Cancel"}
                        }
                    }
                ]
            },
            "job_actions": {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👀 View Job"},
                        "action_id": "view_job"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📝 Generate Proposal"},
                        "style": "primary",
                        "action_id": "generate_proposal"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Skip Job"},
                        "action_id": "skip_job"
                    }
                ]
            },
            "proposal_actions": {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve & Submit"},
                        "style": "primary",
                        "action_id": "approve_proposal"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✏️ Edit Proposal"},
                        "action_id": "edit_proposal"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject"},
                        "style": "danger",
                        "action_id": "reject_proposal"
                    }
                ]
            }
        }


def generate_app_manifest_file():
    """Generate app manifest file for easy Slack app creation"""
    manifest = SlackBotConfig.get_app_manifest()
    
    with open("slack_app_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    print("✅ Slack app manifest generated: slack_app_manifest.json")
    print("📋 Use this file to create your Slack app at https://api.slack.com/apps")


def validate_slack_setup():
    """Validate and display Slack setup status"""
    validation = SlackBotConfig.validate_configuration()
    
    print("🔍 Slack Configuration Validation")
    print("=" * 40)
    
    if validation["valid"]:
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration has errors!")
    
    print("\n📋 Configuration Status:")
    for var, status in validation["configuration"].items():
        print(f"  {var}: {status}")
    
    if validation["errors"]:
        print("\n❌ Errors:")
        for error in validation["errors"]:
            print(f"  • {error}")
    
    if validation["warnings"]:
        print("\n⚠️ Warnings:")
        for warning in validation["warnings"]:
            print(f"  • {warning}")
    
    return validation["valid"]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "manifest":
            generate_app_manifest_file()
        elif sys.argv[1] == "validate":
            validate_slack_setup()
        else:
            print("Usage: python slack_bot.py [manifest|validate]")
    else:
        print("Slack Bot Configuration Utility")
        print("Commands:")
        print("  python slack_bot.py manifest  - Generate app manifest")
        print("  python slack_bot.py validate  - Validate configuration")