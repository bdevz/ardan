"""
Slack Integration Demo

This example demonstrates how the Slack notification system integrates
with the Upwork automation workflow.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from services.notification_service import slack_service
from shared.models import (
    Job, Proposal, Application, DashboardMetrics,
    JobStatus, ProposalStatus, ApplicationStatus, JobType
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_complete_workflow():
    """
    Demonstrate a complete workflow with Slack notifications:
    1. Job discovery notification
    2. Proposal generation notification  
    3. Application submission notification
    4. Daily summary
    """
    
    print("🚀 Starting Slack Integration Demo")
    print("=" * 50)
    
    # Test connection first
    print("\n1. Testing Slack connection...")
    connection_ok = await slack_service.test_connection()
    if not connection_ok:
        print("❌ Slack connection failed. Please check your configuration.")
        return
    print("✅ Slack connection successful!")
    
    # Step 1: Job Discovery
    print("\n2. Simulating job discovery...")
    discovered_jobs = create_sample_jobs()
    
    success = await slack_service.send_job_discovery_notification(
        discovered_jobs, 
        f"demo_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    if success:
        print(f"✅ Job discovery notification sent for {len(discovered_jobs)} jobs")
    else:
        print("❌ Failed to send job discovery notification")
    
    # Wait a bit between notifications
    await asyncio.sleep(2)
    
    # Step 2: Proposal Generation
    print("\n3. Simulating proposal generation...")
    job = discovered_jobs[0]  # Use first discovered job
    proposal = create_sample_proposal(job)
    
    success = await slack_service.send_proposal_generation_notification(proposal, job)
    
    if success:
        print("✅ Proposal generation notification sent")
    else:
        print("❌ Failed to send proposal generation notification")
    
    await asyncio.sleep(2)
    
    # Step 3: Application Submission
    print("\n4. Simulating application submission...")
    application = create_sample_application(job, proposal)
    screenshot_url = "https://example.com/demo_screenshot.png"
    
    success = await slack_service.send_application_submission_notification(
        application, job, proposal, screenshot_url
    )
    
    if success:
        print("✅ Application submission notification sent")
    else:
        print("❌ Failed to send application submission notification")
    
    await asyncio.sleep(2)
    
    # Step 4: Daily Summary
    print("\n5. Sending daily summary...")
    metrics = create_sample_metrics([application])
    
    success = await slack_service.send_daily_summary(metrics)
    
    if success:
        print("✅ Daily summary sent")
    else:
        print("❌ Failed to send daily summary")
    
    print("\n🎉 Demo completed! Check your Slack channel for notifications.")


async def demo_emergency_alerts():
    """Demonstrate emergency alert system"""
    
    print("\n🚨 Emergency Alert Demo")
    print("=" * 30)
    
    # Test different types of emergency alerts
    alerts = [
        {
            "type": "rate_limit_exceeded",
            "message": "Application rate limit exceeded. System paused automatically.",
            "details": {
                "current_rate": "35 applications/day",
                "limit": "30 applications/day",
                "action_taken": "pause_automation"
            }
        },
        {
            "type": "browser_session_failure",
            "message": "Multiple browser sessions failed. Manual intervention required.",
            "details": {
                "failed_sessions": 3,
                "error_type": "captcha_detected",
                "last_success": "2 hours ago"
            }
        },
        {
            "type": "api_quota_exceeded",
            "message": "OpenAI API quota exceeded. Proposal generation disabled.",
            "details": {
                "service": "OpenAI GPT-4",
                "quota_used": "100%",
                "reset_time": "24 hours"
            }
        }
    ]
    
    for i, alert in enumerate(alerts, 1):
        print(f"\n{i}. Sending {alert['type']} alert...")
        
        success = await slack_service.send_emergency_alert(
            alert["type"],
            alert["message"],
            alert["details"],
            escalate=(i == 2)  # Escalate the second alert
        )
        
        if success:
            print(f"✅ {alert['type']} alert sent")
        else:
            print(f"❌ Failed to send {alert['type']} alert")
        
        await asyncio.sleep(3)  # Wait between alerts


async def demo_interactive_commands():
    """Demonstrate interactive command handling"""
    
    print("\n🎮 Interactive Commands Demo")
    print("=" * 35)
    
    commands = [
        ("status", "U123456", "C123456", {}),
        ("metrics", "U123456", "C123456", {}),
        ("pause", "U123456", "C123456", {}),
        ("resume", "U123456", "C123456", {})
    ]
    
    for command, user_id, channel_id, params in commands:
        print(f"\nProcessing command: /{command}")
        
        success = await slack_service.handle_interactive_command(
            command, user_id, channel_id, params
        )
        
        if success:
            print(f"✅ Command '{command}' processed successfully")
        else:
            print(f"❌ Failed to process command '{command}'")
        
        await asyncio.sleep(2)


def create_sample_jobs():
    """Create sample jobs for demonstration"""
    jobs = []
    
    job_templates = [
        {
            "title": "Salesforce Agentforce Developer - AI Implementation",
            "description": "Looking for an experienced Salesforce developer to implement Agentforce AI solutions. Must have experience with Einstein AI and custom agent development.",
            "hourly_rate": Decimal("85.00"),
            "client_name": "TechCorp Solutions",
            "client_rating": Decimal("4.9"),
            "match_score": Decimal("0.95"),
            "match_reasons": ["Agentforce expertise", "AI implementation", "High client rating"]
        },
        {
            "title": "Salesforce Einstein Integration Specialist",
            "description": "Need a Salesforce expert to integrate Einstein AI capabilities into our existing CRM system. Experience with Agentforce preferred.",
            "hourly_rate": Decimal("75.00"),
            "client_name": "Innovation Labs",
            "client_rating": Decimal("4.7"),
            "match_score": Decimal("0.88"),
            "match_reasons": ["Einstein experience", "CRM integration", "Salesforce expertise"]
        },
        {
            "title": "Senior Salesforce Developer - Custom Agent Development",
            "description": "Seeking a senior developer to build custom AI agents using Salesforce Agentforce platform. Long-term project with growth potential.",
            "hourly_rate": Decimal("90.00"),
            "client_name": "Enterprise Dynamics",
            "client_rating": Decimal("4.8"),
            "match_score": Decimal("0.92"),
            "match_reasons": ["Senior level", "Custom development", "Long-term project"]
        }
    ]
    
    for i, template in enumerate(job_templates):
        job = Job(
            id=uuid4(),
            upwork_job_id=f"~demo_job_{i+1}",
            title=template["title"],
            description=template["description"],
            hourly_rate=template["hourly_rate"],
            client_name=template["client_name"],
            client_rating=template["client_rating"],
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED,
            match_score=template["match_score"],
            match_reasons=template["match_reasons"],
            job_url=f"https://www.upwork.com/jobs/~demo_job_{i+1}",
            created_at=datetime.now()
        )
        jobs.append(job)
    
    return jobs


def create_sample_proposal(job: Job) -> Proposal:
    """Create a sample proposal for demonstration"""
    
    proposal_content = f"""Dear {job.client_name},

I am excited to help you with your {job.title} project. With over 5 years of experience in Salesforce development and recent expertise in Agentforce implementation, I can deliver exactly what you need.

In my recent projects, I have:
• Implemented Agentforce solutions that improved lead conversion by 40%
• Integrated Einstein AI capabilities resulting in 60% faster response times  
• Developed custom agents that automated 80% of routine customer inquiries

I would love to discuss your project in detail and show you how I can help achieve your goals. I'm available to start immediately and can work within your timeline.

Best regards,
Your Salesforce Agentforce Developer"""
    
    return Proposal(
        id=uuid4(),
        job_id=job.id,
        content=proposal_content,
        bid_amount=job.hourly_rate,
        attachments=["salesforce_case_study.pdf", "agentforce_demo_video.mp4"],
        google_doc_url=f"https://docs.google.com/document/d/demo_proposal_{job.id}",
        status=ProposalStatus.DRAFT,
        quality_score=Decimal("0.91"),
        generated_at=datetime.now()
    )


def create_sample_application(job: Job, proposal: Proposal) -> Application:
    """Create a sample application for demonstration"""
    
    return Application(
        id=uuid4(),
        job_id=job.id,
        proposal_id=proposal.id,
        upwork_application_id=f"demo_app_{job.id}",
        submitted_at=datetime.now(),
        status=ApplicationStatus.SUBMITTED,
        session_recording_url=f"https://browserbase.com/session/demo_{job.id}"
    )


def create_sample_metrics(applications: list) -> DashboardMetrics:
    """Create sample dashboard metrics"""
    
    return DashboardMetrics(
        total_jobs_discovered=47,
        total_applications_submitted=32,
        applications_today=8,
        success_rate=Decimal("0.78"),
        average_response_time=Decimal("2.4"),
        top_keywords=["Salesforce", "Agentforce", "Einstein", "AI", "Developer"],
        recent_applications=applications
    )


async def main():
    """Main demo function"""
    
    print("🤖 Upwork Automation - Slack Integration Demo")
    print("=" * 60)
    
    try:
        # Run the complete workflow demo
        await demo_complete_workflow()
        
        # Wait before next demo
        await asyncio.sleep(5)
        
        # Run emergency alerts demo
        await demo_emergency_alerts()
        
        # Wait before next demo
        await asyncio.sleep(5)
        
        # Run interactive commands demo
        await demo_interactive_commands()
        
        print("\n✨ All demos completed successfully!")
        print("\nNext steps:")
        print("1. Check your Slack channel for all the notifications")
        print("2. Try using the /upwork slash commands in Slack")
        print("3. Click on the interactive buttons in the notifications")
        print("4. Set up the daily summary schedule")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Slack configuration in .env file")
        print("2. Verify the bot is invited to your channel")
        print("3. Ensure the bot has proper permissions")
        print("4. Run: python api/cli/slack_cli.py validate")


if __name__ == "__main__":
    asyncio.run(main())