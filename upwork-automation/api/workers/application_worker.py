"""
Application Submission Worker for background job processing
"""
import logging
from typing import Dict, Any
from uuid import UUID

from workers.base_worker import BaseWorker
from services.application_submission_service import application_submission_service
from services.proposal_service import proposal_service
from services.job_service import job_service
from services.browser_service import browser_service

logger = logging.getLogger(__name__)


class ApplicationWorker(BaseWorker):
    """Worker for processing application submission tasks"""
    
    def __init__(self, concurrency: int = 2):
        super().__init__(
            worker_name="application_submission",
            task_types=["submit_application", "batch_submit_applications", "verify_submission"],
            concurrency=concurrency
        )
    
    async def process_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process application submission tasks"""
        logger.info(f"Processing {task_type} task {task_id}")
        
        if task_type == "submit_application":
            return await self._process_submit_application(task_data)
        elif task_type == "batch_submit_applications":
            return await self._process_batch_submit_applications(task_data)
        elif task_type == "verify_submission":
            return await self._process_verify_submission(task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _process_submit_application(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process single application submission"""
        job_id = UUID(task_data["job_id"])
        proposal_id = UUID(task_data["proposal_id"])
        confirm_submission = task_data.get("confirm_submission", False)
        
        try:
            # Get job and proposal details
            job = await job_service.get_job(job_id)
            proposal = await proposal_service.get_proposal(proposal_id)
            
            if not job:
                raise ValueError(f"Job {job_id} not found")
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            # Check if we should proceed with submission
            if not confirm_submission:
                # Create application record but don't submit yet
                application = await application_submission_service.create_application(
                    job_id=job_id,
                    proposal_id=proposal_id
                )
                
                return {
                    "application_id": str(application.id),
                    "status": "created_pending_confirmation",
                    "job_id": str(job_id),
                    "proposal_id": str(proposal_id)
                }
            
            # Get or create browser session for submission
            session_id = await browser_service.get_session("proposal_submission")
            
            # Execute browser automation workflow
            submission_result = await browser_service.submit_proposal(
                session_id=session_id,
                job_url=job.job_url,
                proposal_content=proposal.content,
                bid_amount=float(proposal.bid_amount),
                attachments=proposal.attachments
            )
            
            # Create application record
            application = await application_submission_service.create_application(
                job_id=job_id,
                proposal_id=proposal_id,
                upwork_application_id=submission_result.get("application_id"),
                session_recording_url=submission_result.get("recording_url")
            )
            
            # Update proposal status
            await proposal_service.update_proposal_status(proposal_id, "submitted")
            
            # Update job status
            await job_service.update_job_status(job_id, "applied")
            
            return {
                "application_id": str(application.id),
                "status": "submitted",
                "job_id": str(job_id),
                "proposal_id": str(proposal_id),
                "upwork_application_id": submission_result.get("application_id"),
                "session_recording_url": submission_result.get("recording_url"),
                "submission_confirmed": submission_result.get("confirmed", False)
            }
            
        except Exception as e:
            logger.error(f"Application submission failed for job {job_id}: {str(e)}")
            
            # Update application status to failed if it exists
            try:
                applications = await application_submission_service.get_applications_by_job(job_id)
                if applications:
                    await application_submission_service.update_application_status(
                        applications[0].id, "failed"
                    )
            except:
                pass
            
            raise
    
    async def _process_batch_submit_applications(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process batch application submissions"""
        applications = task_data["applications"]  # List of {job_id, proposal_id} dicts
        confirm_submission = task_data.get("confirm_submission", False)
        max_daily_limit = task_data.get("max_daily_limit", 30)
        
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total_processed": 0,
            "daily_limit_reached": False
        }
        
        # Check current daily application count
        daily_count = await application_submission_service.get_daily_application_count()
        
        for app_data in applications:
            # Check daily limit
            if daily_count >= max_daily_limit:
                results["daily_limit_reached"] = True
                results["skipped"].append({
                    "job_id": app_data["job_id"],
                    "reason": "Daily limit reached"
                })
                continue
            
            try:
                result = await self._process_submit_application({
                    "job_id": app_data["job_id"],
                    "proposal_id": app_data["proposal_id"],
                    "confirm_submission": confirm_submission
                })
                
                results["successful"].append({
                    "job_id": app_data["job_id"],
                    "proposal_id": app_data["proposal_id"],
                    "application_id": result["application_id"]
                })
                
                if result["status"] == "submitted":
                    daily_count += 1
                
            except Exception as e:
                logger.error(f"Failed to submit application for job {app_data['job_id']}: {str(e)}")
                results["failed"].append({
                    "job_id": app_data["job_id"],
                    "proposal_id": app_data["proposal_id"],
                    "error": str(e)
                })
            
            results["total_processed"] += 1
            
            # Add delay between submissions to avoid rate limiting
            import asyncio
            await asyncio.sleep(30)  # 30 second delay between submissions
        
        return results
    
    async def _process_verify_submission(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process submission verification"""
        application_id = UUID(task_data["application_id"])
        
        try:
            # Get application details
            application = await application_submission_service.get_application(application_id)
            if not application:
                raise ValueError(f"Application {application_id} not found")
            
            # Get job details for verification
            job = await job_service.get_job(application.job_id)
            if not job:
                raise ValueError(f"Job {application.job_id} not found")
            
            # Use browser automation to verify submission
            session_id = await browser_service.get_session("profile_management")
            
            verification_result = await browser_service.verify_application_submission(
                session_id=session_id,
                job_url=job.job_url,
                application_id=application.upwork_application_id
            )
            
            # Update application status based on verification
            if verification_result["found"]:
                await application_submission_service.update_application_status(
                    application_id, "submitted"
                )
                
                # Update with any additional information found
                if verification_result.get("client_response"):
                    await application_submission_service.update_application(
                        application_id,
                        client_response=verification_result["client_response"],
                        client_response_date=verification_result.get("response_date")
                    )
            else:
                await application_submission_service.update_application_status(
                    application_id, "failed"
                )
            
            return {
                "application_id": str(application_id),
                "verification_status": "found" if verification_result["found"] else "not_found",
                "client_response": verification_result.get("client_response"),
                "additional_info": verification_result.get("additional_info", {})
            }
            
        except Exception as e:
            logger.error(f"Application verification failed for {application_id}: {str(e)}")
            raise


# Create worker instance
application_worker = ApplicationWorker()