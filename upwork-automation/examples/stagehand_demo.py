"""
Demonstration of Stagehand AI Browser Control Implementation
This example shows how to use the Stagehand controller for Ardan automation
"""
import sys
import os
import importlib.util
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

# Import modules using importlib due to hyphenated directory name
def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import the modules
base_path = Path(__file__).parent.parent / "browser-automation"
shared_path = Path(__file__).parent.parent / "shared"

stagehand_controller = import_from_path("stagehand_controller", base_path / "stagehand_controller.py")
stagehand_error_handler = import_from_path("stagehand_error_handler", base_path / "stagehand_error_handler.py")
session_manager = import_from_path("session_manager", base_path / "session_manager.py")
shared_config = import_from_path("shared_config", shared_path / "config.py")
shared_utils = import_from_path("shared_utils", shared_path / "utils.py")

# Import classes directly
StagehandController = stagehand_controller.StagehandController
ArdanJobSearchController = stagehand_controller.ArdanJobSearchController
ArdanApplicationController = stagehand_controller.ArdanApplicationController
NavigationStrategy = stagehand_controller.NavigationStrategy
ExtractionType = stagehand_controller.ExtractionType

StagehandErrorHandler = stagehand_error_handler.StagehandErrorHandler
with_error_handling = stagehand_error_handler.with_error_handling

SessionManager = session_manager.SessionManager
SessionType = session_manager.SessionType

# Import shared utilities
settings = shared_config.settings
setup_logging = shared_utils.setup_logging

logger = setup_logging("stagehand-demo")


class StagehandDemo:
    """Demonstration class for Stagehand browser automation"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.job_search_controller = ArdanJobSearchController()
        self.application_controller = ArdanApplicationController()
        self.error_handler = StagehandErrorHandler()
    
    async def initialize(self):
        """Initialize the demo environment"""
        logger.info("Initializing Stagehand demo...")
        
        # Initialize session pools
        await self.session_manager.initialize_session_pools()
        
        logger.info("Demo initialization complete")
    
    async def demo_job_search(self) -> List[Dict[str, Any]]:
        """Demonstrate intelligent job search using Stagehand"""
        logger.info("=== Job Search Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.JOB_DISCOVERY) as session_id:
            try:
                # Search for Salesforce Agentforce jobs
                search_result = await self.job_search_controller.search_jobs(
                    session_id,
                    keywords=["Salesforce", "Agentforce", "Einstein AI"],
                    filters={
                        "hourly_rate_min": "60",
                        "client_rating_min": "4.0",
                        "payment_verified": True
                    }
                )
                
                if search_result.success:
                    jobs = search_result.data.get("jobs", [])
                    logger.info(f"Found {len(jobs)} jobs matching criteria")
                    
                    # Display job summaries
                    for i, job in enumerate(jobs[:3], 1):  # Show first 3 jobs
                        logger.info(f"Job {i}: {job.get('title', 'N/A')}")
                        logger.info(f"  Client: {job.get('client_name', 'N/A')}")
                        logger.info(f"  Budget: {job.get('budget', 'N/A')}")
                        logger.info(f"  Posted: {job.get('posted_time', 'N/A')}")
                        logger.info(f"  Proposals: {job.get('proposals', 'N/A')}")
                        logger.info("---")
                    
                    return jobs
                else:
                    logger.error(f"Job search failed: {search_result.error_message}")
                    return []
                    
            except Exception as e:
                logger.error(f"Job search demo failed: {e}")
                return []
    
    async def demo_job_details_extraction(self, job_url: str) -> Dict[str, Any]:
        """Demonstrate detailed job information extraction"""
        logger.info("=== Job Details Extraction Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.JOB_DISCOVERY) as session_id:
            try:
                # Extract detailed job information
                details_result = await self.job_search_controller.extract_job_details(
                    session_id,
                    job_url
                )
                
                if details_result.success:
                    job_details = details_result.data
                    logger.info(f"Extracted details for: {job_details.get('title', 'N/A')}")
                    logger.info(f"Budget Type: {job_details.get('budget_type', 'N/A')}")
                    logger.info(f"Budget Range: ${job_details.get('budget_min', 0)}-${job_details.get('budget_max', 0)}")
                    logger.info(f"Skills Required: {', '.join(job_details.get('skills_required', []))}")
                    logger.info(f"Timeline: {job_details.get('timeline', 'N/A')}")
                    
                    client_info = job_details.get('client_info', {})
                    logger.info(f"Client: {client_info.get('name', 'N/A')} (Rating: {client_info.get('rating', 'N/A')})")
                    
                    return job_details
                else:
                    logger.error(f"Job details extraction failed: {details_result.error_message}")
                    return {}
                    
            except Exception as e:
                logger.error(f"Job details demo failed: {e}")
                return {}
    
    async def demo_intelligent_navigation(self) -> bool:
        """Demonstrate intelligent navigation capabilities"""
        logger.info("=== Intelligent Navigation Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.GENERAL) as session_id:
            try:
                controller = StagehandController()
                
                # Demo 1: Direct URL navigation
                logger.info("Testing direct URL navigation...")
                nav_result = await controller.intelligent_navigate(
                    session_id,
                    "https://www.ardan.com/nx/search/jobs",
                    NavigationStrategy.DIRECT_URL
                )
                
                if nav_result.success:
                    logger.info(f"✓ Successfully navigated to: {nav_result.page_title}")
                else:
                    logger.error(f"✗ Navigation failed: {nav_result.error_message}")
                    return False
                
                # Demo 2: Search and click navigation
                logger.info("Testing search and click navigation...")
                nav_result = await controller.intelligent_navigate(
                    session_id,
                    "advanced search filters",
                    NavigationStrategy.SEARCH_AND_CLICK
                )
                
                if nav_result.success:
                    logger.info("✓ Successfully found and navigated to advanced filters")
                else:
                    logger.warning(f"⚠ Advanced filter navigation failed: {nav_result.error_message}")
                
                # Demo 3: Form-based navigation
                logger.info("Testing form-based navigation...")
                nav_result = await controller.intelligent_navigate(
                    session_id,
                    "job search results",
                    NavigationStrategy.FORM_BASED,
                    context={
                        "form_data": {
                            "search_query": "Salesforce Agentforce",
                            "category": "Web Development"
                        }
                    }
                )
                
                if nav_result.success:
                    logger.info("✓ Successfully performed form-based search navigation")
                else:
                    logger.warning(f"⚠ Form navigation failed: {nav_result.error_message}")
                
                return True
                
            except Exception as e:
                logger.error(f"Navigation demo failed: {e}")
                return False
    
    async def demo_content_extraction(self) -> Dict[str, Any]:
        """Demonstrate AI-powered content extraction"""
        logger.info("=== Content Extraction Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.JOB_DISCOVERY) as session_id:
            try:
                controller = StagehandController()
                
                # Navigate to a job search page first
                await controller.intelligent_navigate(
                    session_id,
                    "https://www.ardan.com/nx/search/jobs?q=salesforce",
                    NavigationStrategy.DIRECT_URL
                )
                
                # Demo 1: Extract job listings with schema
                logger.info("Testing structured job listings extraction...")
                
                job_schema = {
                    "required": ["title", "client_name", "budget", "posted_time"],
                    "properties": {
                        "title": {"type": "string"},
                        "client_name": {"type": "string"},
                        "budget": {"type": "string"},
                        "posted_time": {"type": "string"},
                        "proposals": {"type": "string"},
                        "client_rating": {"type": "number"},
                        "job_url": {"type": "string"}
                    }
                }
                
                extraction_result = await controller.extract_content(
                    session_id,
                    """Extract all job listings visible on this page. For each job, get:
                    - title: The job title
                    - client_name: Name of the client posting the job
                    - budget: Budget or hourly rate information
                    - posted_time: When the job was posted
                    - proposals: Number of proposals received
                    - client_rating: Client's star rating
                    - job_url: Link to the full job posting""",
                    ExtractionType.JOB_LISTINGS,
                    job_schema
                )
                
                if extraction_result.success:
                    jobs = extraction_result.data.get("jobs", [])
                    logger.info(f"✓ Extracted {len(jobs)} job listings with confidence {extraction_result.confidence_score:.2f}")
                    
                    # Show sample extracted data
                    if jobs:
                        sample_job = jobs[0]
                        logger.info("Sample extracted job:")
                        for key, value in sample_job.items():
                            logger.info(f"  {key}: {value}")
                else:
                    logger.error(f"✗ Job listings extraction failed: {extraction_result.error_message}")
                
                # Demo 2: Extract page metadata
                logger.info("Testing page metadata extraction...")
                
                metadata_result = await controller.extract_content(
                    session_id,
                    """Analyze this page and extract:
                    - page_type: What type of page this is
                    - search_results_count: How many search results are shown
                    - filters_available: What search filters are available
                    - pagination_info: Current page and total pages if available""",
                    ExtractionType.PAGE_CONTENT
                )
                
                if metadata_result.success:
                    logger.info("✓ Page metadata extracted successfully")
                    logger.info(f"Page analysis: {json.dumps(metadata_result.data, indent=2)}")
                else:
                    logger.warning(f"⚠ Metadata extraction failed: {metadata_result.error_message}")
                
                return extraction_result.data
                
            except Exception as e:
                logger.error(f"Content extraction demo failed: {e}")
                return {}
    
    async def demo_form_interaction(self) -> bool:
        """Demonstrate intelligent form filling and interaction"""
        logger.info("=== Form Interaction Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.JOB_DISCOVERY) as session_id:
            try:
                controller = StagehandController()
                
                # Navigate to job search page
                await controller.intelligent_navigate(
                    session_id,
                    "https://www.ardan.com/nx/search/jobs",
                    NavigationStrategy.DIRECT_URL
                )
                
                # Demo 1: Basic form filling
                logger.info("Testing basic search form interaction...")
                
                search_form_data = {
                    "search_query": "Salesforce Agentforce Developer",
                    "location": "Anywhere",
                    "job_type": "Hourly",
                    "experience_level": "Expert"
                }
                
                form_result = await controller.interact_with_form(
                    session_id,
                    search_form_data,
                    submit=True
                )
                
                if form_result.success:
                    logger.info(f"✓ Form interaction successful: {form_result.action_performed}")
                    logger.info(f"Elements affected: {', '.join(form_result.elements_affected)}")
                else:
                    logger.error(f"✗ Form interaction failed: {form_result.error_message}")
                    if form_result.validation_errors:
                        for error in form_result.validation_errors:
                            logger.error(f"  Validation error: {error}")
                
                # Demo 2: Advanced form with validation
                logger.info("Testing advanced form with validation...")
                
                advanced_form_data = {
                    "hourly_rate_min": "60",
                    "hourly_rate_max": "100",
                    "client_rating_min": "4.0",
                    "payment_verified": "true"
                }
                
                validation_rules = {
                    "hourly_rate_min": {"required": True, "min_length": 1},
                    "hourly_rate_max": {"required": True, "min_length": 1},
                    "client_rating_min": {"required": True}
                }
                
                advanced_result = await controller.interact_with_form(
                    session_id,
                    advanced_form_data,
                    submit=False,  # Don't submit, just fill
                    validation_rules=validation_rules
                )
                
                if advanced_result.success:
                    logger.info("✓ Advanced form filling successful with validation")
                else:
                    logger.warning(f"⚠ Advanced form had issues: {advanced_result.error_message}")
                
                return form_result.success
                
            except Exception as e:
                logger.error(f"Form interaction demo failed: {e}")
                return False
    
    async def demo_error_handling(self) -> bool:
        """Demonstrate error handling and recovery capabilities"""
        logger.info("=== Error Handling Demo ===")
        
        async with self.session_manager.get_session_for_task(SessionType.GENERAL) as session_id:
            try:
                controller = StagehandController()
                
                # Simulate various error scenarios
                logger.info("Testing error classification...")
                
                # Test different error types
                test_errors = [
                    Exception("Navigation to page failed"),
                    Exception("Element with selector '.apply-button' not found"),
                    Exception("Operation timed out after 30 seconds"),
                    Exception("CAPTCHA verification required"),
                    Exception("Rate limit exceeded - too many requests")
                ]
                
                for error in test_errors:
                    error_context = self.error_handler.create_error_context(
                        error, session_id, "test_operation"
                    )
                    
                    logger.info(f"Error: '{error}' classified as: {error_context.error_type.value}")
                    self.error_handler.record_error(error_context)
                
                # Test error statistics
                stats = self.error_handler.get_error_statistics(session_id)
                logger.info(f"Error statistics: {json.dumps(stats, indent=2)}")
                
                # Test recovery strategy selection
                logger.info("Testing recovery strategies...")
                
                from browser_automation.stagehand_error_handler import ErrorType, RecoveryStrategy
                
                for error_type in ErrorType:
                    strategies = self.error_handler.recovery_strategies.get(error_type, [])
                    logger.info(f"{error_type.value}: {[s.value for s in strategies]}")
                
                logger.info("✓ Error handling system working correctly")
                return True
                
            except Exception as e:
                logger.error(f"Error handling demo failed: {e}")
                return False
    
    async def demo_application_submission(self, job_url: str) -> bool:
        """Demonstrate job application submission (simulation)"""
        logger.info("=== Application Submission Demo (Simulation) ===")
        
        # Note: This is a simulation - in production, be very careful with actual submissions
        logger.warning("This is a SIMULATION - no actual applications will be submitted")
        
        async with self.session_manager.get_session_for_task(SessionType.PROPOSAL_SUBMISSION) as session_id:
            try:
                # Simulate proposal content
                proposal_content = """
                Dear Hiring Manager,
                
                I am an experienced Salesforce Agentforce Developer with over 5 years of expertise in building 
                intelligent AI-powered solutions on the Salesforce platform. I have successfully implemented 
                Agentforce solutions for enterprise clients, resulting in 40% improvement in customer service 
                efficiency and 60% reduction in response times.
                
                My recent project involved developing a custom Agentforce implementation for a Fortune 500 
                company, where I integrated Einstein AI capabilities with their existing Salesforce ecosystem. 
                The solution automated complex customer inquiries and provided intelligent routing, leading to 
                significant cost savings and improved customer satisfaction scores.
                
                I would love to discuss how my expertise in Salesforce Agentforce, Einstein AI, and Lightning 
                development can help bring your project to success. I'm available for a quick call to understand 
                your specific requirements and provide a detailed project approach.
                
                Best regards,
                [Your Name]
                """
                
                # Simulate application submission process
                logger.info("Simulating application submission process...")
                
                # Step 1: Navigate to job page
                nav_result = await self.application_controller.intelligent_navigate(
                    session_id,
                    job_url,
                    NavigationStrategy.DIRECT_URL
                )
                
                if not nav_result.success:
                    logger.error(f"Failed to navigate to job page: {nav_result.error_message}")
                    return False
                
                logger.info("✓ Successfully navigated to job page")
                
                # Step 2: Simulate form filling (without actual submission)
                logger.info("Simulating proposal form filling...")
                
                # In a real scenario, this would fill the actual application form
                form_data = {
                    "cover_letter": proposal_content,
                    "bid_amount": "75.00",
                    "estimated_duration": "3-6 months"
                }
                
                # Simulate form interaction
                logger.info("Form data prepared:")
                logger.info(f"  Proposal length: {len(proposal_content)} characters")
                logger.info(f"  Bid amount: ${form_data['bid_amount']}/hr")
                logger.info(f"  Duration: {form_data['estimated_duration']}")
                
                # Step 3: Simulate attachment handling
                logger.info("Simulating attachment selection...")
                attachments = ["portfolio.pdf", "salesforce_case_study.pdf"]
                logger.info(f"  Attachments: {', '.join(attachments)}")
                
                # Step 4: Simulate submission verification
                logger.info("Simulating submission verification...")
                
                # In real implementation, this would verify the submission
                verification_result = {
                    "success": True,
                    "confirmation_message": "Application would be submitted successfully",
                    "application_id": "SIMULATED_APP_123456",
                    "errors": []
                }
                
                logger.info("✓ Application submission simulation completed successfully")
                logger.info(f"Simulated confirmation: {verification_result['confirmation_message']}")
                
                return True
                
            except Exception as e:
                logger.error(f"Application submission demo failed: {e}")
                return False
    
    async def run_complete_demo(self):
        """Run the complete Stagehand demonstration"""
        logger.info("🚀 Starting Complete Stagehand Demo")
        logger.info("=" * 50)
        
        try:
            # Initialize the demo
            await self.initialize()
            
            # Run all demo components
            demos = [
                ("Intelligent Navigation", self.demo_intelligent_navigation()),
                ("Content Extraction", self.demo_content_extraction()),
                ("Form Interaction", self.demo_form_interaction()),
                ("Job Search", self.demo_job_search()),
                ("Error Handling", self.demo_error_handling())
            ]
            
            results = {}
            
            for demo_name, demo_coro in demos:
                logger.info(f"\n🔄 Running {demo_name} Demo...")
                try:
                    result = await demo_coro
                    results[demo_name] = result
                    
                    if isinstance(result, bool):
                        status = "✅ PASSED" if result else "❌ FAILED"
                    else:
                        status = "✅ COMPLETED"
                    
                    logger.info(f"{status} {demo_name} Demo")
                    
                except Exception as e:
                    logger.error(f"❌ FAILED {demo_name} Demo: {e}")
                    results[demo_name] = False
            
            # Run job details demo if we have jobs from search
            if results.get("Job Search") and isinstance(results["Job Search"], list) and results["Job Search"]:
                sample_job = results["Job Search"][0]
                job_url = sample_job.get("job_url")
                
                if job_url:
                    logger.info(f"\n🔄 Running Job Details Extraction Demo...")
                    try:
                        job_details = await self.demo_job_details_extraction(job_url)
                        results["Job Details"] = job_details
                        logger.info("✅ COMPLETED Job Details Demo")
                        
                        # Run application demo with the job URL
                        logger.info(f"\n🔄 Running Application Submission Demo...")
                        app_result = await self.demo_application_submission(job_url)
                        results["Application Submission"] = app_result
                        status = "✅ PASSED" if app_result else "❌ FAILED"
                        logger.info(f"{status} Application Submission Demo")
                        
                    except Exception as e:
                        logger.error(f"❌ FAILED Job Details/Application Demo: {e}")
            
            # Summary
            logger.info("\n" + "=" * 50)
            logger.info("📊 DEMO SUMMARY")
            logger.info("=" * 50)
            
            for demo_name, result in results.items():
                if isinstance(result, bool):
                    status = "✅ PASSED" if result else "❌ FAILED"
                elif isinstance(result, (list, dict)) and result:
                    status = "✅ COMPLETED"
                else:
                    status = "⚠️  PARTIAL"
                
                logger.info(f"{status} {demo_name}")
            
            # Error statistics
            total_stats = self.error_handler.get_error_statistics()
            if total_stats["total_errors"] > 0:
                logger.info(f"\n📈 Error Statistics:")
                logger.info(f"Total Errors: {total_stats['total_errors']}")
                logger.info(f"Recent Errors: {total_stats['recent_errors']}")
                logger.info(f"Most Common: {total_stats.get('most_common_error', 'N/A')}")
            else:
                logger.info("\n✨ No errors encountered during demo!")
            
            logger.info("\n🎉 Stagehand Demo Complete!")
            
        except Exception as e:
            logger.error(f"Demo failed with error: {e}")
        
        finally:
            # Cleanup
            await self.session_manager.shutdown()


async def main():
    """Main function to run the Stagehand demo"""
    demo = StagehandDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())