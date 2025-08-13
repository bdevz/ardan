"""
Google Services Integration Demo
Demonstrates the complete Google services integration functionality
"""
import asyncio
import json
from datetime import datetime
from uuid import uuid4

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.google_services import google_services_manager
from shared.config import settings


async def demo_google_docs():
    """Demonstrate Google Docs integration"""
    print("\n=== Google Docs Demo ===")
    
    docs_service = google_services_manager.get_docs_service()
    
    # Create a proposal document
    print("Creating proposal document...")
    job_id = uuid4()
    proposal_content = """
# Salesforce Agentforce Developer Proposal

## Introduction
I am excited to help you implement your Salesforce Agentforce solution. With over 5 years of experience in Salesforce development and AI integration, I can deliver a robust and scalable solution that meets your business needs.

## Relevant Experience
- Implemented 15+ Salesforce Agentforce projects with 95% client satisfaction
- Reduced customer service response time by 60% through intelligent automation
- Certified Salesforce Developer with Einstein AI specialization

## Next Steps
I would love to discuss your specific requirements in detail. I'm available for a quick call this week to understand your vision and provide a detailed implementation plan.

Best regards,
Your Salesforce Agentforce Developer
    """
    
    doc_result = await docs_service.create_proposal_document(
        title="Salesforce Agentforce Implementation",
        content=proposal_content,
        job_id=job_id
    )
    
    print(f"✅ Created document: {doc_result['document_id']}")
    print(f"📄 Document URL: {doc_result['document_url']}")
    
    # Update the document
    print("\nUpdating document with additional content...")
    updated_content = proposal_content + "\n\n## Additional Information\nI can start immediately and deliver within 2 weeks."
    
    update_success = await docs_service.update_proposal_document(
        document_id=doc_result['document_id'],
        content=updated_content
    )
    
    if update_success:
        print("✅ Document updated successfully")
    
    # Get document content
    print("\nRetrieving document content...")
    content_result = await docs_service.get_document_content(doc_result['document_id'])
    
    if content_result:
        print(f"📖 Document title: {content_result['title']}")
        print(f"📝 Content length: {len(content_result['content'])} characters")
    
    return doc_result


async def demo_google_drive():
    """Demonstrate Google Drive integration"""
    print("\n=== Google Drive Demo ===")
    
    drive_service = google_services_manager.get_drive_service()
    
    # List portfolio files
    print("Listing portfolio files...")
    portfolio_files = await drive_service.list_portfolio_files()
    
    print(f"📁 Found {len(portfolio_files)} portfolio files:")
    for file in portfolio_files[:3]:  # Show first 3
        print(f"  - {file['name']} ({file['size']} bytes)")
    
    # Select relevant attachments
    print("\nSelecting relevant attachments for Salesforce job...")
    job_requirements = ["Salesforce", "Agentforce", "Einstein AI", "Lightning"]
    job_description = "Looking for an experienced Salesforce Agentforce developer to implement AI-powered customer service automation."
    
    selected_files = await drive_service.select_relevant_attachments(
        job_requirements=job_requirements,
        job_description=job_description,
        max_attachments=3
    )
    
    print(f"🎯 Selected {len(selected_files)} relevant attachments:")
    for file in selected_files:
        print(f"  - {file['name']} (relevance: {file.get('relevance_score', 0):.2f})")
    
    # Create a folder
    print("\nCreating project folder...")
    folder_result = await drive_service.create_folder(
        folder_name=f"Upwork Project {datetime.now().strftime('%Y-%m-%d')}"
    )
    
    print(f"📂 Created folder: {folder_result['folder_name']}")
    print(f"🔗 Folder URL: {folder_result['folder_url']}")
    
    # Upload a sample file
    print("\nUploading sample file...")
    sample_content = b"This is a sample portfolio document for demonstration purposes."
    
    upload_result = await drive_service.upload_file(
        file_content=sample_content,
        filename="sample_portfolio.txt",
        mime_type="text/plain",
        folder_id=folder_result['folder_id'],
        description="Sample portfolio document created by demo"
    )
    
    print(f"📤 Uploaded file: {upload_result['filename']}")
    print(f"🆔 File ID: {upload_result['file_id']}")
    
    return selected_files


async def demo_google_sheets():
    """Demonstrate Google Sheets integration"""
    print("\n=== Google Sheets Demo ===")
    
    sheets_service = google_services_manager.get_sheets_service()
    
    # Create sample data
    jobs_data = [
        {
            "id": "job_001",
            "title": "Salesforce Agentforce Developer",
            "client_name": "Tech Startup Inc",
            "hourly_rate": 75,
            "client_rating": 4.8,
            "client_payment_verified": True,
            "status": "APPLIED",
            "match_score": 0.92,
            "skills_required": ["Salesforce", "Agentforce", "Einstein AI"],
            "posted_date": "2024-01-15",
            "job_url": "https://upwork.com/jobs/salesforce-agentforce-dev",
            "created_at": "2024-01-15T10:00:00Z"
        },
        {
            "id": "job_002", 
            "title": "Einstein AI Integration Specialist",
            "client_name": "Enterprise Corp",
            "hourly_rate": 85,
            "client_rating": 4.9,
            "client_payment_verified": True,
            "status": "DISCOVERED",
            "match_score": 0.88,
            "skills_required": ["Salesforce", "Einstein AI", "Integration"],
            "posted_date": "2024-01-16",
            "job_url": "https://upwork.com/jobs/einstein-ai-integration",
            "created_at": "2024-01-16T14:30:00Z"
        }
    ]
    
    proposals_data = [
        {
            "id": "prop_001",
            "job_id": "job_001",
            "job_title": "Salesforce Agentforce Developer",
            "bid_amount": 75,
            "status": "SUBMITTED",
            "generated_at": "2024-01-15T11:00:00Z",
            "submitted_at": "2024-01-15T11:30:00Z",
            "google_doc_url": "https://docs.google.com/document/d/abc123/edit",
            "attachments": ["portfolio.pdf", "case_study.pdf"]
        }
    ]
    
    analytics_data = {
        "total_jobs": 50,
        "total_proposals": 25,
        "success_rate": 0.16,
        "avg_bid_amount": 78.5,
        "jobs_this_week": 8,
        "proposals_this_week": 4,
        "response_rate": 0.32,
        "avg_response_time_hours": 24.5,
        "daily_stats": [
            {"date": "2024-01-15", "jobs_found": 3, "proposals_sent": 2, "responses": 1},
            {"date": "2024-01-16", "jobs_found": 2, "proposals_sent": 1, "responses": 0},
            {"date": "2024-01-17", "jobs_found": 3, "proposals_sent": 1, "responses": 1}
        ]
    }
    
    # Export jobs data
    print("Exporting jobs data...")
    jobs_export = await sheets_service.export_jobs_data(jobs_data)
    print(f"✅ Exported {jobs_export['rows_exported']} jobs")
    print(f"📊 Spreadsheet: {jobs_export['spreadsheet_url']}")
    
    # Export proposals data
    print("\nExporting proposals data...")
    proposals_export = await sheets_service.export_proposals_data(
        proposals_data,
        spreadsheet_id=jobs_export['spreadsheet_id']
    )
    print(f"✅ Exported {proposals_export['rows_exported']} proposals")
    
    # Export analytics data
    print("\nExporting analytics data...")
    analytics_export = await sheets_service.export_analytics_data(
        analytics_data,
        spreadsheet_id=jobs_export['spreadsheet_id']
    )
    print(f"✅ Exported analytics data")
    
    # Create dashboard
    print("\nCreating dashboard spreadsheet...")
    dashboard = await sheets_service.create_dashboard_spreadsheet()
    print(f"📈 Dashboard created: {dashboard['spreadsheet_url']}")
    
    return jobs_export


async def demo_integration_workflow():
    """Demonstrate complete integration workflow"""
    print("\n=== Complete Integration Workflow Demo ===")
    
    # Simulate a complete job application workflow
    print("Simulating complete job application workflow...")
    
    # 1. Create proposal document
    docs_service = google_services_manager.get_docs_service()
    drive_service = google_services_manager.get_drive_service()
    sheets_service = google_services_manager.get_sheets_service()
    
    job_data = {
        "id": "workflow_job_001",
        "title": "Senior Salesforce Agentforce Architect",
        "description": "We need an experienced Salesforce Agentforce developer to build an AI-powered customer service solution.",
        "requirements": ["Salesforce", "Agentforce", "Einstein AI", "Lightning", "Apex"]
    }
    
    print(f"📋 Processing job: {job_data['title']}")
    
    # Create proposal
    proposal_content = f"""
# Proposal for {job_data['title']}

## Executive Summary
I'm excited to help you build your Salesforce Agentforce solution. With extensive experience in AI-powered customer service automation, I can deliver exactly what you need.

## Technical Approach
- Implement Einstein AI for intelligent case routing
- Build custom Lightning components for agent interface
- Develop Apex triggers for automated workflows
- Create comprehensive testing and deployment strategy

## Timeline & Investment
I can complete this project in 3-4 weeks with a rate of $85/hour. This includes full documentation and knowledge transfer.

Let's discuss your specific requirements!
    """
    
    doc_result = await docs_service.create_proposal_document(
        title=job_data['title'],
        content=proposal_content,
        job_id=uuid4()
    )
    
    print(f"📄 Created proposal document: {doc_result['document_id']}")
    
    # Select relevant attachments
    attachments = await drive_service.select_relevant_attachments(
        job_requirements=job_data['requirements'],
        job_description=job_data['description'],
        max_attachments=2
    )
    
    print(f"📎 Selected {len(attachments)} attachments")
    
    # Export workflow data
    workflow_data = [{
        **job_data,
        "proposal_doc_id": doc_result['document_id'],
        "proposal_doc_url": doc_result['document_url'],
        "attachments_count": len(attachments),
        "status": "PROPOSAL_CREATED",
        "created_at": datetime.now().isoformat()
    }]
    
    export_result = await sheets_service.export_jobs_data(
        workflow_data,
        sheet_name="Workflow_Demo"
    )
    
    print(f"📊 Exported workflow data: {export_result['spreadsheet_url']}")
    
    print("✅ Complete workflow demonstration finished!")
    
    return {
        "document": doc_result,
        "attachments": attachments,
        "export": export_result
    }


async def main():
    """Run all Google services demos"""
    print("🚀 Starting Google Services Integration Demo")
    print("=" * 50)
    
    # Check authentication status
    auth_status = google_services_manager.get_auth_status()
    print(f"🔐 Authentication Status: {'✅ Authenticated' if auth_status['authenticated'] else '❌ Not Authenticated'}")
    print(f"🔑 Using Service Account: {'Yes' if auth_status['service_account'] else 'No'}")
    
    if not auth_status['authenticated']:
        print("⚠️  Running in mock mode - no actual Google API calls will be made")
    
    try:
        # Run individual service demos
        doc_result = await demo_google_docs()
        drive_files = await demo_google_drive()
        sheets_result = await demo_google_sheets()
        
        # Run complete workflow demo
        workflow_result = await demo_integration_workflow()
        
        print("\n" + "=" * 50)
        print("🎉 All demos completed successfully!")
        print("\n📋 Summary:")
        print(f"  - Created document: {doc_result['document_id']}")
        print(f"  - Found {len(drive_files)} relevant attachments")
        print(f"  - Exported data to: {sheets_result['spreadsheet_url']}")
        print(f"  - Workflow spreadsheet: {workflow_result['export']['spreadsheet_url']}")
        
        if not auth_status['authenticated']:
            print("\n💡 To use real Google services:")
            print("  1. Set up Google service account credentials")
            print("  2. Set GOOGLE_SERVICE_ACCOUNT_FILE environment variable")
            print("  3. Or configure OAuth2 credentials")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())