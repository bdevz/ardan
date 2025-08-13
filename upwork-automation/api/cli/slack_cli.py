"""
Slack CLI Utility

Command-line interface for managing Slack notifications and testing integration.
"""

import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from services.notification_service import slack_service
from api.slack_bot import SlackBotConfig, validate_slack_setup
from shared.models import Job, Proposal, Application, DashboardMetrics, JobType, JobStatus, ProposalStatus, ApplicationStatus

console = Console()


@click.group()
def slack():
    """Slack integration management commands"""
    pass


@slack.command()
def setup():
    """Display Slack setup instructions"""
    instructions = SlackBotConfig.get_setup_instructions()
    
    console.print(Panel(
        f"[bold blue]{instructions['title']}[/bold blue]",
        expand=False
    ))
    
    for step in instructions["steps"]:
        console.print(f"\n[bold yellow]Step {step['step']}: {step['title']}[/bold yellow]")
        console.print(step["description"])
        
        if step.get("details"):
            for detail in step["details"]:
                console.print(f"  • {detail}")


@slack.command()
def validate():
    """Validate Slack configuration"""
    console.print("[bold blue]Validating Slack Configuration...[/bold blue]\n")
    
    validation = SlackBotConfig.validate_configuration()
    
    # Configuration status table
    table = Table(title="Configuration Status")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="green")
    
    for var, status in validation["configuration"].items():
        table.add_row(var, status)
    
    console.print(table)
    
    # Errors
    if validation["errors"]:
        console.print("\n[bold red]❌ Errors:[/bold red]")
        for error in validation["errors"]:
            console.print(f"  • {error}")
    
    # Warnings
    if validation["warnings"]:
        console.print("\n[bold yellow]⚠️ Warnings:[/bold yellow]")
        for warning in validation["warnings"]:
            console.print(f"  • {warning}")
    
    # Overall status
    if validation["valid"]:
        console.print("\n[bold green]✅ Configuration is valid![/bold green]")
    else:
        console.print("\n[bold red]❌ Configuration has errors that need to be fixed.[/bold red]")
    
    return validation["valid"]


@slack.command()
@click.option('--channel', help='Slack channel ID (optional)')
def test_connection(channel: Optional[str]):
    """Test Slack API connection"""
    async def _test():
        console.print("[bold blue]Testing Slack connection...[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to Slack API...", total=None)
            
            try:
                result = await slack_service.test_connection()
                
                if result:
                    progress.update(task, description="✅ Connection successful!")
                    console.print("\n[bold green]✅ Slack connection test passed![/bold green]")
                    
                    # Test sending a message if channel provided
                    if channel:
                        progress.update(task, description="Sending test message...")
                        await slack_service.client.chat_postMessage(
                            channel=channel,
                            text="🧪 Test message from Upwork Automation Bot",
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": "✅ *Connection Test Successful*\n\nThe Upwork Automation Bot is working correctly!"
                                    }
                                }
                            ]
                        )
                        console.print(f"[bold green]✅ Test message sent to {channel}[/bold green]")
                else:
                    progress.update(task, description="❌ Connection failed!")
                    console.print("\n[bold red]❌ Slack connection test failed![/bold red]")
                    
            except Exception as e:
                progress.update(task, description="❌ Connection error!")
                console.print(f"\n[bold red]❌ Connection error: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
@click.option('--count', default=3, help='Number of sample jobs to create')
def test_job_notification(count: int):
    """Send test job discovery notification"""
    async def _test():
        console.print(f"[bold blue]Sending test job discovery notification ({count} jobs)...[/bold blue]")
        
        # Create sample jobs
        sample_jobs = []
        for i in range(count):
            job = Job(
                id=uuid4(),
                upwork_job_id=f"~test_job_{i+1}",
                title=f"Test Salesforce Agentforce Developer Job {i+1}",
                description=f"This is a test job description for job {i+1}. Looking for Salesforce Agentforce expertise.",
                hourly_rate=Decimal(str(50 + i * 10)),
                client_name=f"Test Client {i+1}",
                client_rating=Decimal("4.5") + Decimal(str(i * 0.1)),
                client_payment_verified=True,
                client_hire_rate=Decimal("0.8") + Decimal(str(i * 0.05)),
                job_type=JobType.HOURLY,
                status=JobStatus.DISCOVERED,
                match_score=Decimal("0.8") + Decimal(str(i * 0.05)),
                match_reasons=["Salesforce experience", "Agentforce expertise", "High client rating"],
                job_url=f"https://www.upwork.com/jobs/~test_job_{i+1}",
                created_at=datetime.now()
            )
            sample_jobs.append(job)
        
        try:
            result = await slack_service.send_job_discovery_notification(
                sample_jobs, f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if result:
                console.print("[bold green]✅ Test job notification sent successfully![/bold green]")
            else:
                console.print("[bold red]❌ Failed to send test job notification![/bold red]")
                
        except Exception as e:
            console.print(f"[bold red]❌ Error sending test notification: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
def test_proposal_notification():
    """Send test proposal generation notification"""
    async def _test():
        console.print("[bold blue]Sending test proposal notification...[/bold blue]")
        
        # Create sample job and proposal
        job = Job(
            id=uuid4(),
            title="Test Salesforce Agentforce Developer Position",
            description="Test job for proposal notification",
            hourly_rate=Decimal("75.00"),
            client_name="Test Client Corp",
            client_rating=Decimal("4.8"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.85"),
            job_type=JobType.HOURLY,
            status=JobStatus.DISCOVERED
        )
        
        proposal = Proposal(
            id=uuid4(),
            job_id=job.id,
            content="Dear Test Client,\n\nI am excited to help you with your Salesforce Agentforce project. With over 5 years of experience in Salesforce development and recent expertise in Agentforce implementation, I can deliver exactly what you need.\n\nI have successfully implemented similar solutions for clients, resulting in 40% improved lead conversion rates and 60% faster response times.\n\nI would love to discuss your project in detail and show you how I can help achieve your goals.\n\nBest regards,\nYour Salesforce Developer",
            bid_amount=Decimal("75.00"),
            attachments=["salesforce_case_study.pdf", "agentforce_demo.pdf"],
            google_doc_url="https://docs.google.com/document/d/test_proposal_123",
            status=ProposalStatus.DRAFT,
            quality_score=Decimal("0.92"),
            generated_at=datetime.now()
        )
        
        try:
            result = await slack_service.send_proposal_generation_notification(proposal, job)
            
            if result:
                console.print("[bold green]✅ Test proposal notification sent successfully![/bold green]")
            else:
                console.print("[bold red]❌ Failed to send test proposal notification![/bold red]")
                
        except Exception as e:
            console.print(f"[bold red]❌ Error sending test notification: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
def test_application_notification():
    """Send test application submission notification"""
    async def _test():
        console.print("[bold blue]Sending test application notification...[/bold blue]")
        
        # Create sample job, proposal, and application
        job = Job(
            id=uuid4(),
            title="Test Salesforce Agentforce Implementation",
            description="Test job for application notification",
            hourly_rate=Decimal("80.00"),
            client_name="Innovation Corp",
            client_rating=Decimal("4.9"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.90"),
            job_type=JobType.HOURLY,
            status=JobStatus.APPLIED
        )
        
        proposal = Proposal(
            id=uuid4(),
            job_id=job.id,
            content="Test proposal content",
            bid_amount=Decimal("80.00"),
            status=ProposalStatus.SUBMITTED
        )
        
        application = Application(
            id=uuid4(),
            job_id=job.id,
            proposal_id=proposal.id,
            upwork_application_id="test_app_123",
            submitted_at=datetime.now(),
            status=ApplicationStatus.SUBMITTED,
            session_recording_url="https://browserbase.com/session/test_123"
        )
        
        try:
            result = await slack_service.send_application_submission_notification(
                application, job, proposal, "https://example.com/test_screenshot.png"
            )
            
            if result:
                console.print("[bold green]✅ Test application notification sent successfully![/bold green]")
            else:
                console.print("[bold red]❌ Failed to send test application notification![/bold red]")
                
        except Exception as e:
            console.print(f"[bold red]❌ Error sending test notification: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
@click.option('--alert-type', default='system_test', help='Type of emergency alert')
@click.option('--escalate/--no-escalate', default=False, help='Whether to escalate the alert')
def test_emergency_alert(alert_type: str, escalate: bool):
    """Send test emergency alert"""
    async def _test():
        console.print(f"[bold red]Sending test emergency alert ({alert_type})...[/bold red]")
        
        message = "This is a test emergency alert from the Upwork Automation system."
        details = {
            "test_mode": True,
            "timestamp": datetime.now().isoformat(),
            "component": "slack_cli",
            "severity": "test"
        }
        
        try:
            result = await slack_service.send_emergency_alert(
                alert_type, message, details, escalate
            )
            
            if result:
                console.print("[bold green]✅ Test emergency alert sent successfully![/bold green]")
                if escalate:
                    console.print("[bold yellow]⚠️ Alert was escalated as requested[/bold yellow]")
            else:
                console.print("[bold red]❌ Failed to send test emergency alert![/bold red]")
                
        except Exception as e:
            console.print(f"[bold red]❌ Error sending test alert: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
def test_daily_summary():
    """Send test daily summary"""
    async def _test():
        console.print("[bold blue]Sending test daily summary...[/bold blue]")
        
        # Create sample metrics
        sample_applications = [
            Application(
                id=uuid4(),
                job_id=uuid4(),
                proposal_id=uuid4(),
                status=ApplicationStatus.SUBMITTED,
                submitted_at=datetime.now()
            ),
            Application(
                id=uuid4(),
                job_id=uuid4(),
                proposal_id=uuid4(),
                status=ApplicationStatus.VIEWED,
                submitted_at=datetime.now()
            )
        ]
        
        metrics = DashboardMetrics(
            total_jobs_discovered=42,
            total_applications_submitted=28,
            applications_today=8,
            success_rate=Decimal("0.78"),
            average_response_time=Decimal("3.2"),
            top_keywords=["Salesforce", "Agentforce", "Einstein", "Developer", "AI"],
            recent_applications=sample_applications
        )
        
        try:
            result = await slack_service.send_daily_summary(metrics)
            
            if result:
                console.print("[bold green]✅ Test daily summary sent successfully![/bold green]")
            else:
                console.print("[bold red]❌ Failed to send test daily summary![/bold red]")
                
        except Exception as e:
            console.print(f"[bold red]❌ Error sending test summary: {e}[/bold red]")
    
    asyncio.run(_test())


@slack.command()
def generate_manifest():
    """Generate Slack app manifest file"""
    try:
        manifest = SlackBotConfig.get_app_manifest()
        
        filename = "slack_app_manifest.json"
        with open(filename, "w") as f:
            json.dump(manifest, f, indent=2)
        
        console.print(f"[bold green]✅ Slack app manifest generated: {filename}[/bold green]")
        console.print("\n[bold blue]Next steps:[/bold blue]")
        console.print("1. Go to https://api.slack.com/apps")
        console.print("2. Click 'Create New App'")
        console.print("3. Choose 'From an app manifest'")
        console.print("4. Select your workspace")
        console.print(f"5. Upload the {filename} file")
        console.print("6. Review and create the app")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error generating manifest: {e}[/bold red]")


@slack.command()
def show_templates():
    """Show available notification templates"""
    templates = SlackBotConfig.get_notification_templates()
    
    console.print("[bold blue]Available Notification Templates[/bold blue]\n")
    
    for template_name, template_config in templates.items():
        panel_content = f"[bold]{template_config['title']}[/bold]\n"
        panel_content += f"Color: {template_config['color']}\n"
        panel_content += f"Fields: {len(template_config['fields'])}"
        
        console.print(Panel(
            panel_content,
            title=template_name,
            expand=False
        ))


@slack.command()
def show_components():
    """Show available interactive components"""
    components = SlackBotConfig.get_interactive_components()
    
    console.print("[bold blue]Available Interactive Components[/bold blue]\n")
    
    for component_name, component_config in components.items():
        panel_content = f"Type: {component_config['type']}\n"
        panel_content += f"Elements: {len(component_config['elements'])}\n"
        
        for element in component_config['elements']:
            panel_content += f"  • {element.get('text', {}).get('text', 'N/A')} ({element.get('action_id', 'N/A')})\n"
        
        console.print(Panel(
            panel_content,
            title=component_name,
            expand=False
        ))


@slack.command()
@click.option('--all-tests', is_flag=True, help='Run all notification tests')
def test_all(all_tests: bool):
    """Run comprehensive Slack integration tests"""
    async def _test_all():
        console.print("[bold blue]Running comprehensive Slack integration tests...[/bold blue]\n")
        
        tests = [
            ("Connection Test", lambda: slack_service.test_connection()),
            ("Job Discovery Notification", lambda: _test_job_notification()),
            ("Proposal Notification", lambda: _test_proposal_notification()),
            ("Application Notification", lambda: _test_application_notification()),
            ("Daily Summary", lambda: _test_daily_summary())
        ]
        
        if all_tests:
            tests.append(("Emergency Alert", lambda: _test_emergency_alert()))
        
        results = []
        
        for test_name, test_func in tests:
            console.print(f"[bold yellow]Running {test_name}...[/bold yellow]")
            
            try:
                result = await test_func()
                if result:
                    console.print(f"[bold green]✅ {test_name} passed[/bold green]")
                    results.append((test_name, True, None))
                else:
                    console.print(f"[bold red]❌ {test_name} failed[/bold red]")
                    results.append((test_name, False, "Test returned False"))
            except Exception as e:
                console.print(f"[bold red]❌ {test_name} error: {e}[/bold red]")
                results.append((test_name, False, str(e)))
            
            console.print()
        
        # Summary
        console.print("[bold blue]Test Results Summary[/bold blue]")
        
        table = Table()
        table.add_column("Test", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Error", style="red")
        
        passed = 0
        for test_name, success, error in results:
            status = "✅ PASS" if success else "❌ FAIL"
            table.add_row(test_name, status, error or "")
            if success:
                passed += 1
        
        console.print(table)
        console.print(f"\n[bold blue]Results: {passed}/{len(results)} tests passed[/bold blue]")
    
    async def _test_job_notification():
        jobs = [Job(
            id=uuid4(),
            title="Test Job",
            description="Test",
            hourly_rate=Decimal("75"),
            client_rating=Decimal("4.5"),
            client_payment_verified=True,
            client_hire_rate=Decimal("0.8"),
            job_type=JobType.HOURLY,
            match_score=Decimal("0.9")
        )]
        return await slack_service.send_job_discovery_notification(jobs)
    
    async def _test_proposal_notification():
        job = Job(id=uuid4(), title="Test", description="Test", hourly_rate=Decimal("75"), 
                 client_rating=Decimal("4.5"), client_payment_verified=True, 
                 client_hire_rate=Decimal("0.8"), job_type=JobType.HOURLY)
        proposal = Proposal(id=uuid4(), job_id=job.id, content="Test", bid_amount=Decimal("75"))
        return await slack_service.send_proposal_generation_notification(proposal, job)
    
    async def _test_application_notification():
        job = Job(id=uuid4(), title="Test", description="Test", hourly_rate=Decimal("75"),
                 client_rating=Decimal("4.5"), client_payment_verified=True,
                 client_hire_rate=Decimal("0.8"), job_type=JobType.HOURLY)
        proposal = Proposal(id=uuid4(), job_id=job.id, content="Test", bid_amount=Decimal("75"))
        app = Application(id=uuid4(), job_id=job.id, proposal_id=proposal.id, 
                         submitted_at=datetime.now(), status=ApplicationStatus.SUBMITTED)
        return await slack_service.send_application_submission_notification(app, job, proposal)
    
    async def _test_daily_summary():
        metrics = DashboardMetrics(
            total_jobs_discovered=10, total_applications_submitted=5, applications_today=2,
            success_rate=Decimal("0.8"), top_keywords=["test"], recent_applications=[]
        )
        return await slack_service.send_daily_summary(metrics)
    
    async def _test_emergency_alert():
        return await slack_service.send_emergency_alert("test_alert", "Test message", {"test": True}, False)
    
    asyncio.run(_test_all())


if __name__ == "__main__":
    slack()