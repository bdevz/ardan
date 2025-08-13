"""
Browser-Based Application Submission Service
Handles automated proposal submission using Stagehand and Director orchestration
"""
import asyncio
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import base64
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'browser-automation'))

from database.models import JobModel, ProposalModel, ApplicationModel, BrowserSessionModel
from shared.models import Application, ApplicationStatus, Job, Proposal
from shared.utils import setup_logging
from stagehand_controller import StagehandController, ExtractionResult, ExtractionType
from director import DirectorOrchestrator
from browserbase_client import BrowserbaseClient
from .google_services import google_drive_service
from .websocket_service import websocket_service

logger = setup_logging("application-submission-service")


class SubmissionResult:
    """Result of application submission attempt"""
    
    def __init__(self):
        self.success = False
        self.application_id: Optional[UUID] = None
        self.upwork_application_id: Optional[str] = None
        self.submission_time: Optional[datetime] = None
        self.confirmation_screenshot: Optional[str] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0
        self.execution_time: float = 0.0
        self.steps_completed: List[str] = []
        self.metadata: Dict[str, Any] = {}


class ApplicationSubmissionService:
    """Service for automated application submission using browser automation"""
    
    def __init__(self):
        self.browserbase_client = BrowserbaseClient()
        self.stagehand_controller = StagehandController()
        self.director = DirectorOrchestrator()
        
        # Submission configuration
        self.max_retries = 3
        self.base_delay = 2.0  # Base delay between actions
        self.max_delay = 10.0  # Maximum delay
        self.human_like_delays = True
        
        # Rate limiting
        self.daily_submission_limit = 30
        self.hourly_submission_limit = 5
        self.submissions_today = 0
        self.submissions_this_hour = 0
        self.last_submission_time: Optional[datetime] = None
        
        # Stealth configuration
        self.stealth_mode = True
        self.randomize_timing = True
        self.use_realistic_typing = True
    
    async def submit_application(
        self,
        db: AsyncSession,
        job_id: UUID,
        proposal_id: UUID,
        confirm_submission: bool = True
    ) -> SubmissionResult:
        """
        Submit application for a job using browser automation
        
        This is the main entry point for automated application submission.
        It orchestrates the complete submission workflow using Director.
        """
        result = SubmissionResult()
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting application submission for job {job_id}")
            
            # Step 1: Validate submission eligibility
            await self._validate_submission_eligibility(db, job_id, proposal_id)
            result.steps_completed.append("validation")
            
            # Step 2: Check rate limits
            if not await self._check_rate_limits():
                raise Exception("Rate limit exceeded - submission paused")
            result.steps_completed.append("rate_limit_check")
            
            # Step 3: Get job and proposal data
            job_data, proposal_data = await self._get_submission_data(db, job_id, proposal_id)
            result.steps_completed.append("data_retrieval")
            
            # Step 4: Create browser session
            session_id = await self._create_submission_session()
            result.steps_completed.append("session_creation")
            
            try:
                # Step 5: Execute submission workflow using Director
                submission_data = await self._execute_submission_workflow(
                    session_id, job_data, proposal_data, confirm_submission
                )
                result.steps_completed.append("submission_workflow")
                
                # Step 6: Create application record
                if confirm_submission:
                    application = await self._create_application_record(
                        db, job_id, proposal_id, submission_data
                    )
                    result.application_id = application.id
                    result.upwork_application_id = submission_data.get("upwork_application_id")
                    result.steps_completed.append("application_record")
                
                # Step 7: Capture confirmation
                result.confirmation_screenshot = submission_data.get("confirmation_screenshot")
                result.submission_time = submission_data.get("submission_time")
                result.success = True
                
                # Update rate limiting counters
                await self._update_submission_counters()
                
                logger.info(f"Application submitted successfully for job {job_id}")
                
            finally:
                # Always cleanup session
                await self._cleanup_submission_session(session_id)
                result.steps_completed.append("session_cleanup")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Application submission failed for job {job_id}: {e}")
        
        result.execution_time = (datetime.utcnow() - start_time).total_seconds()
        return result
    
    async def batch_submit_applications(
        self,
        db: AsyncSession,
        submission_requests: List[Tuple[UUID, UUID]],  # (job_id, proposal_id) pairs
        max_concurrent: int = 2
    ) -> List[SubmissionResult]:
        """
        Submit multiple applications in batch with rate limiting and concurrency control
        """
        results = []
        
        # Process in batches to respect rate limits
        for i in range(0, len(submission_requests), max_concurrent):
            batch = submission_requests[i:i + max_concurrent]
            
            # Create tasks for this batch
            batch_tasks = []
            for job_id, proposal_id in batch:
                task = self.submit_application(db, job_id, proposal_id)
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    error_result = SubmissionResult()
                    error_result.error_message = str(result)
                    results.append(error_result)
                else:
                    results.append(result)
            
            # Add delay between batches
            if i + max_concurrent < len(submission_requests):
                delay = await self._calculate_batch_delay()
                await asyncio.sleep(delay)
        
        return results
    
    async def _validate_submission_eligibility(
        self,
        db: AsyncSession,
        job_id: UUID,
        proposal_id: UUID
    ):
        """Validate that the submission is eligible"""
        # Check if job exists and is in correct status
        job_query = select(JobModel).where(JobModel.id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            raise ValueError("Job not found")
        
        if job.status not in ["discovered", "filtered", "queued"]:
            raise ValueError(f"Job status '{job.status}' not eligible for submission")
        
        # Check if proposal exists
        proposal_query = select(ProposalModel).where(ProposalModel.id == proposal_id)
        proposal_result = await db.execute(proposal_query)
        proposal = proposal_result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError("Proposal not found")
        
        if proposal.job_id != job_id:
            raise ValueError("Proposal does not match job")
        
        # Check if application already exists
        existing_app_query = select(ApplicationModel).where(
            ApplicationModel.job_id == job_id,
            ApplicationModel.proposal_id == proposal_id
        )
        existing_result = await db.execute(existing_app_query)
        existing_app = existing_result.scalar_one_or_none()
        
        if existing_app:
            raise ValueError("Application already exists for this job")
    
    async def _check_rate_limits(self) -> bool:
        """Check if submission is within rate limits"""
        now = datetime.utcnow()
        
        # Check daily limit
        if self.submissions_today >= self.daily_submission_limit:
            logger.warning("Daily submission limit reached")
            return False
        
        # Check hourly limit
        if self.submissions_this_hour >= self.hourly_submission_limit:
            logger.warning("Hourly submission limit reached")
            return False
        
        # Check minimum time between submissions
        if self.last_submission_time:
            time_since_last = (now - self.last_submission_time).total_seconds()
            min_interval = 300  # 5 minutes minimum between submissions
            
            if time_since_last < min_interval:
                logger.warning(f"Minimum interval not met: {time_since_last}s < {min_interval}s")
                return False
        
        return True
    
    async def _get_submission_data(
        self,
        db: AsyncSession,
        job_id: UUID,
        proposal_id: UUID
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Get job and proposal data for submission"""
        # Get job data
        job_query = select(JobModel).where(JobModel.id == job_id)
        job_result = await db.execute(job_query)
        job_model = job_result.scalar_one()
        
        job_data = {
            "id": str(job_model.id),
            "upwork_job_id": job_model.upwork_job_id,
            "title": job_model.title,
            "description": job_model.description,
            "job_url": job_model.job_url,
            "client_name": job_model.client_name,
            "hourly_rate": float(job_model.hourly_rate) if job_model.hourly_rate else None,
            "budget_min": float(job_model.budget_min) if job_model.budget_min else None,
            "budget_max": float(job_model.budget_max) if job_model.budget_max else None,
            "job_type": job_model.job_type
        }
        
        # Get proposal data
        proposal_query = select(ProposalModel).where(ProposalModel.id == proposal_id)
        proposal_result = await db.execute(proposal_query)
        proposal_model = proposal_result.scalar_one()
        
        proposal_data = {
            "id": str(proposal_model.id),
            "content": proposal_model.content,
            "bid_amount": float(proposal_model.bid_amount),
            "attachments": proposal_model.attachments or [],
            "google_doc_url": proposal_model.google_doc_url,
            "quality_score": float(proposal_model.quality_score) if proposal_model.quality_score else None
        }
        
        return job_data, proposal_data
    
    async def _create_submission_session(self) -> str:
        """Create browser session for submission"""
        session_config = {
            "projectId": "upwork-automation",
            "stealth": self.stealth_mode,
            "keepAlive": True,
            "proxies": True,
            "fingerprinting": "random" if self.stealth_mode else "consistent"
        }
        
        session_info = await self.browserbase_client.create_session(session_config)
        session_id = session_info.id
        
        # Initialize Stagehand for the session
        await self.stagehand_controller.initialize_stagehand(session_id)
        
        # Configure stealth settings
        if self.stealth_mode:
            await self._configure_stealth_settings(session_id)
        
        logger.info(f"Created submission session: {session_id}")
        return session_id
    
    async def _configure_stealth_settings(self, session_id: str):
        """Configure stealth settings for the browser session"""
        try:
            stagehand = await self.stagehand_controller.get_stagehand(session_id)
            page = stagehand.page
            
            # Set realistic viewport
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            # Set user agent
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            # Add realistic timing variations
            await page.evaluate("""
                // Override timing functions to add realistic delays
                const originalSetTimeout = window.setTimeout;
                window.setTimeout = function(callback, delay) {
                    const variation = Math.random() * 100 - 50; // ±50ms variation
                    return originalSetTimeout(callback, delay + variation);
                };
            """)
            
        except Exception as e:
            logger.warning(f"Failed to configure stealth settings: {e}")
    
    async def _execute_submission_workflow(
        self,
        session_id: str,
        job_data: Dict[str, Any],
        proposal_data: Dict[str, Any],
        confirm_submission: bool
    ) -> Dict[str, Any]:
        """Execute the complete submission workflow using Director orchestration"""
        
        # Define workflow steps
        workflow_definition = {
            "name": "upwork_application_submission",
            "steps": [
                {
                    "name": "navigate_to_job",
                    "action": "navigate",
                    "params": {
                        "url": job_data["job_url"],
                        "wait_for": "networkidle"
                    }
                },
                {
                    "name": "click_apply_button",
                    "action": "click",
                    "params": {
                        "selector": "[data-test='apply-button'], .up-btn-primary:contains('Apply')",
                        "wait_for_navigation": True
                    }
                },
                {
                    "name": "fill_proposal_form",
                    "action": "fill_form",
                    "params": {
                        "fields": {
                            "cover_letter": proposal_data["content"],
                            "bid_amount": str(proposal_data["bid_amount"])
                        }
                    }
                },
                {
                    "name": "upload_attachments",
                    "action": "upload_files",
                    "params": {
                        "attachments": proposal_data["attachments"]
                    }
                },
                {
                    "name": "review_application",
                    "action": "review",
                    "params": {
                        "capture_screenshot": True
                    }
                }
            ]
        }
        
        # Add submission step if confirmed
        if confirm_submission:
            workflow_definition["steps"].append({
                "name": "submit_application",
                "action": "submit",
                "params": {
                    "submit_button": "[data-test='submit-application'], .up-btn-primary:contains('Submit')",
                    "capture_confirmation": True
                }
            })
        
        # Execute workflow using Director
        workflow_result = await self._execute_director_workflow(
            session_id, workflow_definition, job_data, proposal_data
        )
        
        return workflow_result
    
    async def _execute_director_workflow(
        self,
        session_id: str,
        workflow_definition: Dict[str, Any],
        job_data: Dict[str, Any],
        proposal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow using Director orchestration"""
        
        workflow_result = {
            "steps_executed": [],
            "submission_time": None,
            "upwork_application_id": None,
            "confirmation_screenshot": None,
            "metadata": {}
        }
        
        try:
            stagehand = await self.stagehand_controller.get_stagehand(session_id)
            page = stagehand.page
            
            for step in workflow_definition["steps"]:
                step_name = step["name"]
                step_action = step["action"]
                step_params = step["params"]
                
                logger.info(f"Executing step: {step_name}")
                
                # Add human-like delay before each step
                if self.randomize_timing:
                    delay = await self._calculate_human_delay()
                    await asyncio.sleep(delay)
                
                # Execute step based on action type
                if step_action == "navigate":
                    await self._execute_navigate_step(stagehand, step_params)
                
                elif step_action == "click":
                    await self._execute_click_step(stagehand, step_params)
                
                elif step_action == "fill_form":
                    await self._execute_fill_form_step(stagehand, step_params)
                
                elif step_action == "upload_files":
                    await self._execute_upload_files_step(stagehand, step_params)
                
                elif step_action == "review":
                    screenshot = await self._execute_review_step(stagehand, step_params)
                    workflow_result["metadata"]["review_screenshot"] = screenshot
                
                elif step_action == "submit":
                    submission_data = await self._execute_submit_step(stagehand, step_params)
                    workflow_result.update(submission_data)
                
                workflow_result["steps_executed"].append(step_name)
                
        except Exception as e:
            logger.error(f"Workflow execution failed at step {step_name}: {e}")
            raise
        
        return workflow_result
    
    async def _execute_navigate_step(self, stagehand, params: Dict[str, Any]):
        """Execute navigation step"""
        url = params["url"]
        wait_for = params.get("wait_for", "networkidle")
        
        await stagehand.act(stagehand.page, f"navigate to {url}")
        
        if wait_for == "networkidle":
            await stagehand.page.wait_for_load_state("networkidle", timeout=30000)
    
    async def _execute_click_step(self, stagehand, params: Dict[str, Any]):
        """Execute click step"""
        selector = params["selector"]
        wait_for_navigation = params.get("wait_for_navigation", False)
        
        # Use Stagehand's intelligent clicking
        await stagehand.act(stagehand.page, f"click on the apply button or element matching {selector}")
        
        if wait_for_navigation:
            await stagehand.page.wait_for_load_state("networkidle", timeout=30000)
    
    async def _execute_fill_form_step(self, stagehand, params: Dict[str, Any]):
        """Execute form filling step"""
        fields = params["fields"]
        
        for field_name, field_value in fields.items():
            if field_name == "cover_letter":
                # Fill proposal/cover letter
                await stagehand.act(
                    stagehand.page,
                    f"fill the cover letter or proposal text area with: {field_value[:100]}..."
                )
                
                # Add realistic typing if enabled
                if self.use_realistic_typing:
                    await self._type_realistically(stagehand.page, field_value)
            
            elif field_name == "bid_amount":
                # Fill bid amount
                await stagehand.act(
                    stagehand.page,
                    f"set the bid amount or hourly rate to {field_value}"
                )
    
    async def _execute_upload_files_step(self, stagehand, params: Dict[str, Any]):
        """Execute file upload step"""
        attachments = params["attachments"]
        
        if not attachments:
            return
        
        # Get file data from Google Drive
        for attachment_id in attachments:
            try:
                # This would download the file from Google Drive
                # For now, we'll simulate the upload
                await stagehand.act(
                    stagehand.page,
                    f"upload attachment file with ID {attachment_id}"
                )
                
                # Add delay between uploads
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to upload attachment {attachment_id}: {e}")
    
    async def _execute_review_step(self, stagehand, params: Dict[str, Any]) -> Optional[str]:
        """Execute review step and capture screenshot"""
        capture_screenshot = params.get("capture_screenshot", False)
        
        if capture_screenshot:
            screenshot = await stagehand.page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot).decode()
            return screenshot_b64
        
        return None
    
    async def _execute_submit_step(self, stagehand, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute final submission step"""
        submit_button = params["submit_button"]
        capture_confirmation = params.get("capture_confirmation", True)
        
        # Click submit button
        await stagehand.act(stagehand.page, f"click the submit button matching {submit_button}")
        
        # Wait for confirmation page
        await stagehand.page.wait_for_load_state("networkidle", timeout=30000)
        
        # Extract confirmation data
        confirmation_data = await stagehand.extract(
            stagehand.page,
            "extract application confirmation details including application ID, submission time, and success message"
        )
        
        result = {
            "submission_time": datetime.utcnow(),
            "upwork_application_id": confirmation_data.get("application_id"),
            "metadata": confirmation_data
        }
        
        # Capture confirmation screenshot
        if capture_confirmation:
            screenshot = await stagehand.page.screenshot(full_page=True)
            result["confirmation_screenshot"] = base64.b64encode(screenshot).decode()
        
        return result
    
    async def _type_realistically(self, page, text: str):
        """Type text with realistic human-like timing"""
        if not self.use_realistic_typing:
            return
        
        # Simulate realistic typing speed (40-80 WPM)
        words_per_minute = random.randint(40, 80)
        chars_per_second = (words_per_minute * 5) / 60  # Average 5 chars per word
        
        for char in text:
            await page.keyboard.type(char)
            
            # Add realistic delays
            if char == ' ':
                delay = random.uniform(0.1, 0.3)  # Longer pause for spaces
            elif char in '.,!?':
                delay = random.uniform(0.2, 0.5)  # Longer pause for punctuation
            else:
                delay = random.uniform(0.05, 0.15)  # Normal typing delay
            
            await asyncio.sleep(delay)
    
    async def _calculate_human_delay(self) -> float:
        """Calculate human-like delay between actions"""
        if not self.randomize_timing:
            return self.base_delay
        
        # Random delay between 1-8 seconds with realistic distribution
        base = random.uniform(1.0, 3.0)
        variation = random.uniform(0.5, 5.0)
        
        return min(base + variation, self.max_delay)
    
    async def _calculate_batch_delay(self) -> float:
        """Calculate delay between batches"""
        # Longer delay between batches (5-15 minutes)
        return random.uniform(300, 900)
    
    async def _create_application_record(
        self,
        db: AsyncSession,
        job_id: UUID,
        proposal_id: UUID,
        submission_data: Dict[str, Any]
    ) -> Application:
        """Create application record in database"""
        application_model = ApplicationModel(
            job_id=job_id,
            proposal_id=proposal_id,
            upwork_application_id=submission_data.get("upwork_application_id"),
            submitted_at=submission_data.get("submission_time"),
            status=ApplicationStatus.SUBMITTED,
            session_recording_url=None  # Could store session recording URL
        )
        
        db.add(application_model)
        await db.commit()
        
        # Broadcast application submission via WebSocket
        job_query = select(JobModel).where(JobModel.id == job_id)
        job_result = await db.execute(job_query)
        job_model = job_result.scalar_one_or_none()
        
        if job_model:
            await websocket_service.broadcast_application_submitted({
                "id": str(application_model.id),
                "job_id": str(job_id),
                "job_title": job_model.title,
                "proposal_id": str(proposal_id),
                "submitted_at": application_model.submitted_at.isoformat() if application_model.submitted_at else None,
                "status": application_model.status.value
            })
        
        # Update job status
        job_query = select(JobModel).where(JobModel.id == job_id)
        job_result = await db.execute(job_query)
        job_model = job_result.scalar_one()
        job_model.status = "applied"
        job_model.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Convert to shared model
        return Application(
            id=application_model.id,
            job_id=application_model.job_id,
            proposal_id=application_model.proposal_id,
            upwork_application_id=application_model.upwork_application_id,
            submitted_at=application_model.submitted_at,
            status=application_model.status,
            created_at=application_model.created_at,
            updated_at=application_model.updated_at
        )
    
    async def _update_submission_counters(self):
        """Update rate limiting counters"""
        self.submissions_today += 1
        self.submissions_this_hour += 1
        self.last_submission_time = datetime.utcnow()
    
    async def _cleanup_submission_session(self, session_id: str):
        """Clean up browser session"""
        try:
            await self.stagehand_controller.cleanup_session(session_id)
            await self.browserbase_client.end_session(session_id)
            logger.info(f"Cleaned up submission session: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup session {session_id}: {e}")
    
    async def get_submission_stats(self) -> Dict[str, Any]:
        """Get current submission statistics"""
        return {
            "submissions_today": self.submissions_today,
            "submissions_this_hour": self.submissions_this_hour,
            "daily_limit": self.daily_submission_limit,
            "hourly_limit": self.hourly_submission_limit,
            "last_submission": self.last_submission_time.isoformat() if self.last_submission_time else None,
            "rate_limit_status": "ok" if await self._check_rate_limits() else "limited"
        }


# Global service instance
application_submission_service = ApplicationSubmissionService()