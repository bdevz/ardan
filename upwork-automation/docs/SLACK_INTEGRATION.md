# Slack Integration Guide

The Upwork Automation system includes comprehensive Slack integration for real-time notifications, system control, and monitoring. This guide covers setup, configuration, and usage.

## Features

### 🔔 Real-time Notifications
- **Job Discovery**: Rich notifications when new jobs are found
- **Proposal Generation**: Updates when proposals are created
- **Application Submission**: Confirmation when applications are submitted
- **System Events**: Alerts for important system changes
- **Emergency Alerts**: Critical failure notifications with escalation

### 🎮 Interactive Controls
- **Slash Commands**: Control the system directly from Slack
- **Interactive Buttons**: Quick actions on notifications
- **System Status**: Real-time status monitoring
- **Emergency Controls**: Immediate system shutdown capabilities

### 📊 Performance Dashboards
- **Daily Summaries**: Automated daily performance reports
- **Metrics Display**: Key performance indicators
- **Success Tracking**: Application success rates and trends

## Quick Setup

### 1. Create Slack App

```bash
# Generate app manifest
python api/cli/slack_cli.py generate-manifest

# This creates slack_app_manifest.json
```

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From an app manifest"
3. Select your workspace
4. Upload the generated `slack_app_manifest.json`
5. Review and create the app

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_ID=C1234567890

# Optional but recommended
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_EMERGENCY_CHANNEL=C0987654321
SLACK_NOTIFICATIONS_ENABLED=true
```

### 3. Install Bot to Workspace

1. In your Slack app settings, go to "OAuth & Permissions"
2. Click "Install to Workspace"
3. Authorize the app
4. Copy the "Bot User OAuth Token" to `SLACK_BOT_TOKEN`

### 4. Invite Bot to Channel

```
/invite @upwork-automation-bot
```

### 5. Test Integration

```bash
# Validate configuration
python api/cli/slack_cli.py validate

# Test connection
python api/cli/slack_cli.py test-connection --channel C1234567890

# Run comprehensive tests
python api/cli/slack_cli.py test-all
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot User OAuth Token (starts with `xoxb-`) |
| `SLACK_CHANNEL_ID` | Yes | Default channel for notifications |
| `SLACK_SIGNING_SECRET` | Recommended | For request verification |
| `SLACK_EMERGENCY_CHANNEL` | Optional | Separate channel for emergency alerts |
| `SLACK_NOTIFICATIONS_ENABLED` | Optional | Enable/disable all notifications (default: true) |

### Notification Preferences

Customize notification behavior in the notification service:

```python
notification_preferences = {
    "job_discovery": {
        "enabled": True,
        "min_match_score": 0.7,  # Only notify for jobs above this score
        "channels": ["C1234567890"],
        "frequency": "immediate"
    },
    "emergency_alerts": {
        "enabled": True,
        "escalation": True,  # Escalate to additional contacts
        "channels": ["C0987654321"]
    },
    "daily_summary": {
        "enabled": True,
        "time": "18:00"  # Send at 6 PM
    }
}
```

## Usage

### Slash Commands

The bot supports these slash commands:

```
/upwork status          # Show system status
/upwork pause           # Pause automation
/upwork resume          # Resume automation
/upwork metrics         # Show performance metrics
/upwork jobs            # List recent jobs
/upwork stop            # Emergency stop (immediate)
/upwork help            # Show help message
```

### Interactive Notifications

Notifications include interactive buttons for quick actions:

#### Job Discovery Notifications
- **View Job**: Open job in browser
- **Generate Proposals**: Start proposal generation
- **Pause Discovery**: Temporarily pause job discovery

#### Proposal Notifications
- **View Full Proposal**: Open Google Doc
- **Approve & Submit**: Approve and submit proposal
- **Edit Proposal**: Open for editing

#### Application Notifications
- **View Application**: Open Upwork application
- **View Metrics**: Show performance dashboard

#### Emergency Alerts
- **Emergency Stop**: Immediately stop all automation
- **View System Status**: Check system health
- **Acknowledge**: Mark alert as acknowledged

### System Control

Control the automation system directly from Slack:

```python
# Programmatic control
from services.notification_service import slack_service

# Send custom notification
await slack_service.client.chat_postMessage(
    channel="C1234567890",
    text="Custom system message",
    blocks=[...]
)

# Handle interactive command
await slack_service.handle_interactive_command(
    "pause", "U123456", "C1234567890"
)
```

## Notification Types

### 1. Job Discovery Notifications

Sent when new jobs are discovered:

```
🎯 3 New Jobs Discovered

💰 $85/hr | ⭐ 4.9 | 📊 Match: 95%
Salesforce Agentforce Developer - AI Implementation
🏢 TechCorp Solutions ✅

🎯 Match Reasons: Agentforce expertise • AI implementation • High client rating

[View Job] [Generate Proposals] [Pause Discovery]
```

### 2. Proposal Generation Notifications

Sent when proposals are generated:

```
📝 Proposal Generated

Job: Salesforce Agentforce Developer
Bid Amount: $85/hr
Status: Draft
Quality Score: 92%

Preview:
Dear TechCorp Solutions,
I am excited to help you with your Salesforce Agentforce project...

📎 Attachments: 2 files

[View Full Proposal] [Approve & Submit] [Edit Proposal]
```

### 3. Application Submission Notifications

Sent when applications are submitted:

```
🚀 Application Submitted Successfully

Job: Salesforce Agentforce Developer
Bid Amount: $85/hr
Client: TechCorp Solutions (⭐ 4.9)
Submitted: 2024-01-15 14:30:25

📹 View Session Recording

[View Application] [View Metrics]
```

### 4. Emergency Alerts

Sent for critical system issues:

```
🚨 EMERGENCY ALERT: SYSTEM_FAILURE

Message: Multiple browser sessions failed
Time: 2024-01-15 14:30:25

Details:
failed_sessions: 3
error_type: captcha_detected
last_success: 2 hours ago

[🛑 Emergency Stop] [📊 View System Status] [🔧 Acknowledge]
```

### 5. Daily Summary

Automated daily performance report:

```
📊 Daily Summary - 2024-01-15

Applications Today: 12
Total Jobs Discovered: 45
Total Applications: 128
Success Rate: 78%
Avg Response Time: 2.3h

🔍 Top Keywords: Salesforce • Agentforce • Einstein • Developer • AI

Recent Applications:
• Submitted - 14:30
• Viewed - 13:45
• Interview - 12:15

[📈 View Full Dashboard] [⚙️ System Settings]
```

## Advanced Features

### Custom Notification Templates

Create custom notification templates:

```python
from services.notification_service import slack_service

# Custom job notification
custom_blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Custom Job Alert*\n{job.title}"
        }
    }
]

await slack_service.client.chat_postMessage(
    channel="C1234567890",
    blocks=custom_blocks
)
```

### Notification Filtering

Filter notifications based on criteria:

```python
# Only notify for high-value jobs
if job.hourly_rate >= 75 and job.match_score >= 0.8:
    await slack_service.send_job_discovery_notification([job])
```

### Emergency Escalation

Configure emergency alert escalation:

```python
# Emergency alert with escalation
await slack_service.send_emergency_alert(
    "critical_failure",
    "System requires immediate attention",
    {"severity": "critical"},
    escalate=True  # Escalate to additional contacts
)
```

## Troubleshooting

### Common Issues

#### Bot Not Responding to Commands

**Symptoms**: Slash commands don't work, no response from bot

**Solutions**:
1. Check `SLACK_BOT_TOKEN` is correct and starts with `xoxb-`
2. Verify bot is invited to the channel: `/invite @upwork-automation-bot`
3. Check app permissions include `commands` scope
4. Review server logs for errors

#### Interactive Components Not Working

**Symptoms**: Buttons don't respond, no action when clicked

**Solutions**:
1. Verify `SLACK_SIGNING_SECRET` is set correctly
2. Check interactivity is enabled in app settings
3. Ensure request URL is accessible from Slack
4. Verify SSL certificate is valid

#### Events Not Being Received

**Symptoms**: No notifications for mentions or DMs

**Solutions**:
1. Check event subscriptions are configured
2. Verify request URL responds to challenge
3. Review bot event subscriptions include `app_mention`, `message.im`
4. Check server accessibility from Slack

#### Notifications Not Sending

**Symptoms**: No Slack notifications despite system activity

**Solutions**:
1. Check `SLACK_NOTIFICATIONS_ENABLED=true`
2. Verify channel ID is correct (starts with `C`)
3. Ensure bot has `chat:write` permission
4. Check notification preferences aren't disabled

### Validation Commands

```bash
# Validate configuration
python api/cli/slack_cli.py validate

# Test connection
python api/cli/slack_cli.py test-connection

# Test specific notification types
python api/cli/slack_cli.py test-job-notification
python api/cli/slack_cli.py test-proposal-notification
python api/cli/slack_cli.py test-application-notification
python api/cli/slack_cli.py test-emergency-alert

# Run all tests
python api/cli/slack_cli.py test-all
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Run with debug output
python api/cli/slack_cli.py test-connection --verbose
```

## API Reference

### Notification Service

```python
from services.notification_service import slack_service

# Test connection
await slack_service.test_connection()

# Send job discovery notification
await slack_service.send_job_discovery_notification(jobs, session_id)

# Send proposal notification
await slack_service.send_proposal_generation_notification(proposal, job)

# Send application notification
await slack_service.send_application_submission_notification(
    application, job, proposal, screenshot_url
)

# Send emergency alert
await slack_service.send_emergency_alert(
    alert_type, message, details, escalate=True
)

# Send daily summary
await slack_service.send_daily_summary(metrics)

# Handle interactive command
await slack_service.handle_interactive_command(
    command, user_id, channel_id, parameters
)

# Update preferences
await slack_service.update_notification_preferences(preferences)
```

### REST API Endpoints

```bash
# Slack webhook endpoints
POST /api/slack/commands        # Slash commands
POST /api/slack/interactions    # Interactive components
POST /api/slack/events          # Event subscriptions

# Health check
GET /api/slack/health           # Connection status
```

## Security

### Request Verification

The integration verifies Slack requests using the signing secret:

```python
from slack_sdk.signature import SignatureVerifier

verifier = SignatureVerifier(settings.slack_signing_secret)
is_valid = verifier.is_valid_request(body, timestamp, signature)
```

### Permissions

Required Slack app permissions:

- `app_mentions:read` - Read mentions of the bot
- `channels:read` - Read channel information
- `chat:write` - Send messages
- `chat:write.public` - Send messages to public channels
- `commands` - Handle slash commands
- `files:write` - Upload files (screenshots, reports)
- `im:history` - Read DM history
- `im:read` - Read DMs
- `im:write` - Send DMs
- `incoming-webhook` - Receive webhooks
- `users:read` - Read user information

### Rate Limiting

Slack API calls are rate limited:

- Standard rate limit: 1 request per second per workspace
- Burst allowance: Up to 100 requests in first minute
- The integration handles rate limiting automatically with exponential backoff

## Examples

### Complete Integration Demo

```bash
# Run the comprehensive demo
python examples/slack_integration_demo.py
```

This demo shows:
1. Job discovery notifications
2. Proposal generation notifications
3. Application submission notifications
4. Emergency alerts
5. Interactive command handling
6. Daily summary reports

### Custom Integration

```python
import asyncio
from services.notification_service import slack_service
from shared.models import Job, JobType

async def custom_notification_example():
    # Create custom job notification
    job = Job(
        title="Custom Salesforce Job",
        description="Custom job description",
        hourly_rate=Decimal("80.00"),
        client_rating=Decimal("4.8"),
        job_type=JobType.HOURLY,
        match_score=Decimal("0.9")
    )
    
    # Send notification
    await slack_service.send_job_discovery_notification([job])
    
    # Send custom message
    await slack_service.client.chat_postMessage(
        channel="C1234567890",
        text="Custom automation update",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Custom Update*\nSystem is running smoothly!"
                }
            }
        ]
    )

# Run the example
asyncio.run(custom_notification_example())
```

## Support

For issues with Slack integration:

1. Check the troubleshooting section above
2. Run validation commands to identify configuration issues
3. Review server logs for detailed error messages
4. Test individual components using the CLI utilities
5. Refer to [Slack API documentation](https://api.slack.com/) for platform-specific issues

The Slack integration is designed to be robust and self-healing, with automatic retry logic and graceful error handling to ensure reliable operation.