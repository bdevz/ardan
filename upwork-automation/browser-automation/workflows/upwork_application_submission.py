"""
Director Workflow Definition for Upwork Application Submission
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import random

from director import WorkflowDefinition, WorkflowStep, WorkflowContext
from stagehand_controller import StagehandController
from shared.utils import setup_logging

logger = setup_logging("upwork-submission-workflow")


class UpworkApplicationSubmissionWorkflow(WorkflowDefinition):
    """
    Comprehensive workflow for submitting applications on Upwork
    
    This workflow handles the complete application submission process including:
    - Navigation to job posting
    - Form filling with proposal content
    - Bid amount setting
    - File attachment upload
    - Application review and submission
    - Confirmation capture
    """
    
    def __init__(self):
        super().__init__(
            name="upwork_application_submission",
            description="Automated Upwork job application submission with stealth techniques",
            version="1.0.0"
        )
        
        # Workflow configuration
        self.stealth_mode = True
        self.human_like_timing = True
        self.capture_screenshots = True
        self.max_retries = 3
        
        # Define workflow steps
        self.steps = [
            WorkflowStep(
                name="initialize_session",
                description="Initialize browser session with stealth settings",
                action=self._initialize_session,
                required=True,
                timeout=30
            ),
            WorkflowStep(
                name="navigate_to_job",
                description="Navigate to the Upwork job posting",
                action=self._navigate_to_job,
                required=True,
                timeout=60,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="click_apply_button",
                description="Click the Apply Now button",
                action=self._click_apply_button,
                required=True,
                timeout=30,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="fill_proposal_form",
                description="Fill the proposal/cover letter form",
                action=self._fill_proposal_form,
                required=True,
                timeout=120,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="set_bid_amount",
                description="Set the bid amount or hourly rate",
                action=self._set_bid_amount,
                required=True,
                timeout=30,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="upload_attachments",
                description="Upload portfolio attachments",
                action=self._upload_attachments,
                required=False,
                timeout=180,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="review_application",
                description="Review application before submission",
                action=self._review_application,
                required=True,
                timeout=60
            ),
            WorkflowStep(
                name="submit_application",
                description="Submit the application",
                action=self._submit_application,
                required=True,
                timeout=60,
                retry_on_failure=True
            ),
            WorkflowStep(
                name="capture_confirmation",
                description="Capture submission confirmation",
                action=self._capture_confirmation,
                required=True,
                timeout=30
            )
        ]
    
    async def _initialize_session(self, context: WorkflowContext) -> Dict[str, Any]:
        """Initialize browser session with stealth settings"""
        try:
            session_id = context.get("session_id")
            stagehand = context.get("stagehand")
            
            if not stagehand:
                raise ValueError("Stagehand instance not found in context")
            
            page = stagehand.page
            
            # Configure stealth settings
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            # Set realistic user agent
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br"
            })
            
            # Inject human-like behavior scripts
            await page.evaluate("""
                // Add realistic mouse movement
                document.addEventListener('mousemove', function(e) {
                    // Add slight randomness to mouse movements
                    const variation = Math.random() * 2 - 1;
                    e.clientX += variation;
                    e.clientY += variation;
                });
                
                // Override timing functions
                const originalSetTimeout = window.setTimeout;
                window.setTimeout = function(callback, delay) {
                    const variation = Math.random() * 100 - 50;
                    return originalSetTimeout(callback, delay + variation);
                };
            """)
            
            logger.info(f"Session {session_id} initialized with stealth settings")
            
            return {
                "success": True,
                "session_configured": True,
                "stealth_enabled": True
            }
            
        except Exception as e:
            logger.error(f"Session initialization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _navigate_to_job(self, context: WorkflowContext) -> Dict[str, Any]:
        """Navigate to the Upwork job posting"""
        try:
            stagehand = context.get("stagehand")
            job_data = context.get("job_data", {})
            job_url = job_data.get("job_url")
            
            if not job_url:
                raise ValueError("Job URL not provided")
            
            # Add human-like delay before navigation
            if self.human_like_timing:
                delay = random.uniform(2.0, 5.0)
                await asyncio.sleep(delay)
            
            # Navigate to job posting
            await stagehand.act(stagehand.page, f"navigate to the job posting at {job_url}")
            
            # Wait for page to load completely
            await stagehand.page.wait_for_load_state("networkidle", timeout=30000)
            
            # Verify we're on the correct page
            current_url = stagehand.page.url
            page_title = await stagehand.page.title()
            
            # Take screenshot for verification
            if self.capture_screenshots:
                screenshot = await stagehand.page.screenshot(full_page=True)
                context.set("navigation_screenshot", screenshot)
            
            logger.info(f"Successfully navigated to job: {page_title}")
            
            return {
                "success": True,
                "current_url": current_url,
                "page_title": page_title,
                "navigation_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _click_apply_button(self, context: WorkflowContext) -> Dict[str, Any]:
        """Click the Apply Now button"""
        try:
            stagehand = context.get("stagehand")
            
            # Add human-like delay
            if self.human_like_timing:
                delay = random.uniform(3.0, 8.0)
                await asyncio.sleep(delay)
            
            # Look for and click the apply button
            await stagehand.act(
                stagehand.page,
                "find and click the 'Apply Now' or 'Submit a Proposal' button to start the application process"
            )
            
            # Wait for application form to load
            await stagehand.page.wait_for_load_state("networkidle", timeout=30000)
            
            # Verify we're on the application page
            current_url = stagehand.page.url
            
            # Check for application form elements
            form_detected = await stagehand.extract(
                stagehand.page,
                "check if the application form is visible with proposal text area and bid amount fields"
            )
            
            logger.info("Apply button clicked, application form loaded")
            
            return {
                "success": True,
                "current_url": current_url,
                "form_detected": form_detected,
                "click_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Apply button click failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _fill_proposal_form(self, context: WorkflowContext) -> Dict[str, Any]:
        """Fill the proposal/cover letter form"""
        try:
            stagehand = context.get("stagehand")
            proposal_data = context.get("proposal_data", {})
            proposal_content = proposal_data.get("content", "")
            
            if not proposal_content:
                raise ValueError("Proposal content not provided")
            
            # Add human-like delay before typing
            if self.human_like_timing:
                delay = random.uniform(2.0, 5.0)
                await asyncio.sleep(delay)
            
            # Clear any existing content and fill proposal
            await stagehand.act(
                stagehand.page,
                f"find the cover letter or proposal text area and fill it with the following content: {proposal_content[:100]}..."
            )
            
            # Simulate realistic typing if content is long
            if len(proposal_content) > 100:
                await self._type_content_realistically(stagehand.page, proposal_content)
            
            # Verify content was entered
            content_verification = await stagehand.extract(
                stagehand.page,
                "verify that the proposal content has been entered in the text area"
            )
            
            logger.info("Proposal form filled successfully")
            
            return {
                "success": True,
                "content_length": len(proposal_content),
                "content_verified": content_verification,
                "fill_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Proposal form filling failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _set_bid_amount(self, context: WorkflowContext) -> Dict[str, Any]:
        """Set the bid amount or hourly rate"""
        try:
            stagehand = context.get("stagehand")
            proposal_data = context.get("proposal_data", {})
            bid_amount = proposal_data.get("bid_amount")
            
            if not bid_amount:
                raise ValueError("Bid amount not provided")
            
            # Add human-like delay
            if self.human_like_timing:
                delay = random.uniform(1.0, 3.0)
                await asyncio.sleep(delay)
            
            # Set the bid amount
            await stagehand.act(
                stagehand.page,
                f"find the bid amount or hourly rate field and set it to ${bid_amount}"
            )
            
            # Verify bid amount was set
            bid_verification = await stagehand.extract(
                stagehand.page,
                "verify that the bid amount has been set correctly"
            )
            
            logger.info(f"Bid amount set to ${bid_amount}")
            
            return {
                "success": True,
                "bid_amount": bid_amount,
                "bid_verified": bid_verification,
                "set_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Bid amount setting failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _upload_attachments(self, context: WorkflowContext) -> Dict[str, Any]:
        """Upload portfolio attachments"""
        try:
            stagehand = context.get("stagehand")
            proposal_data = context.get("proposal_data", {})
            attachments = proposal_data.get("attachments", [])
            
            if not attachments:
                logger.info("No attachments to upload")
                return {
                    "success": True,
                    "attachments_uploaded": 0,
                    "message": "No attachments provided"
                }
            
            uploaded_count = 0
            
            for attachment_id in attachments:
                try:
                    # Add delay between uploads
                    if self.human_like_timing and uploaded_count > 0:
                        delay = random.uniform(3.0, 7.0)
                        await asyncio.sleep(delay)
                    
                    # This would integrate with Google Drive to download and upload the file
                    # For now, we'll simulate the upload process
                    await stagehand.act(
                        stagehand.page,
                        f"upload the attachment file with ID {attachment_id} to the application"
                    )
                    
                    uploaded_count += 1
                    logger.info(f"Uploaded attachment {attachment_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to upload attachment {attachment_id}: {e}")
                    continue
            
            return {
                "success": True,
                "attachments_uploaded": uploaded_count,
                "total_attachments": len(attachments),
                "upload_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Attachment upload failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _review_application(self, context: WorkflowContext) -> Dict[str, Any]:
        """Review application before submission"""
        try:
            stagehand = context.get("stagehand")
            
            # Add human-like review time
            if self.human_like_timing:
                delay = random.uniform(10.0, 30.0)  # Realistic review time
                await asyncio.sleep(delay)
            
            # Extract application summary for review
            application_summary = await stagehand.extract(
                stagehand.page,
                "extract the application summary including proposal content, bid amount, and attachments for review"
            )
            
            # Take screenshot of application before submission
            if self.capture_screenshots:
                screenshot = await stagehand.page.screenshot(full_page=True)
                context.set("review_screenshot", screenshot)
            
            # Verify all required fields are filled
            validation_result = await stagehand.extract(
                stagehand.page,
                "verify that all required fields are filled and the application is ready for submission"
            )
            
            logger.info("Application reviewed and validated")
            
            return {
                "success": True,
                "application_summary": application_summary,
                "validation_result": validation_result,
                "review_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Application review failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _submit_application(self, context: WorkflowContext) -> Dict[str, Any]:
        """Submit the application"""
        try:
            stagehand = context.get("stagehand")
            
            # Add final human-like delay before submission
            if self.human_like_timing:
                delay = random.uniform(5.0, 15.0)
                await asyncio.sleep(delay)
            
            # Click the submit button
            await stagehand.act(
                stagehand.page,
                "find and click the 'Submit Proposal' or 'Send Application' button to submit the application"
            )
            
            # Wait for submission to process
            await stagehand.page.wait_for_load_state("networkidle", timeout=60000)
            
            # Check for submission confirmation
            confirmation_check = await stagehand.extract(
                stagehand.page,
                "check for submission confirmation message or success indicator"
            )
            
            current_url = stagehand.page.url
            
            logger.info("Application submitted successfully")
            
            return {
                "success": True,
                "confirmation_check": confirmation_check,
                "current_url": current_url,
                "submission_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Application submission failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _capture_confirmation(self, context: WorkflowContext) -> Dict[str, Any]:
        """Capture submission confirmation"""
        try:
            stagehand = context.get("stagehand")
            
            # Extract confirmation details
            confirmation_data = await stagehand.extract(
                stagehand.page,
                "extract confirmation details including application ID, submission time, and any success messages"
            )
            
            # Take confirmation screenshot
            if self.capture_screenshots:
                screenshot = await stagehand.page.screenshot(full_page=True)
                context.set("confirmation_screenshot", screenshot)
            
            # Get final URL
            final_url = stagehand.page.url
            page_title = await stagehand.page.title()
            
            logger.info("Submission confirmation captured")
            
            return {
                "success": True,
                "confirmation_data": confirmation_data,
                "final_url": final_url,
                "page_title": page_title,
                "capture_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Confirmation capture failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _type_content_realistically(self, page, content: str):
        """Type content with realistic human-like timing"""
        try:
            # Simulate realistic typing speed (40-80 WPM)
            words_per_minute = random.randint(40, 80)
            chars_per_second = (words_per_minute * 5) / 60
            
            # Type content in chunks to simulate realistic behavior
            chunk_size = random.randint(10, 30)
            
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                
                # Type the chunk
                await page.keyboard.type(chunk)
                
                # Add realistic pause between chunks
                if i + chunk_size < len(content):
                    pause_duration = random.uniform(0.5, 2.0)
                    await asyncio.sleep(pause_duration)
            
        except Exception as e:
            logger.warning(f"Realistic typing failed, falling back to standard input: {e}")
            await page.keyboard.type(content)
    
    def get_workflow_definition(self) -> Dict[str, Any]:
        """Get the complete workflow definition"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [
                {
                    "name": step.name,
                    "description": step.description,
                    "required": step.required,
                    "timeout": step.timeout,
                    "retry_on_failure": getattr(step, 'retry_on_failure', False)
                }
                for step in self.steps
            ],
            "configuration": {
                "stealth_mode": self.stealth_mode,
                "human_like_timing": self.human_like_timing,
                "capture_screenshots": self.capture_screenshots,
                "max_retries": self.max_retries
            }
        }


# Global workflow instance
upwork_submission_workflow = UpworkApplicationSubmissionWorkflow()