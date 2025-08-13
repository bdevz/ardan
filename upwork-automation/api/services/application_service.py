"""
Enhanced Application service - business logic for application submission and tracking
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ApplicationModel, JobModel, ProposalModel
from shared.models import Application, ApplicationSubmissionRequest, ApplicationStatus
from shared.utils import setup_logging
from .application_submission_service import application_submission_service
from .websocket_service import websocket_service

logger = setup_logging("application-service")


class ApplicationService:
    """Service for application-related operations"""
    
    async def submit_application(
        self,
        db: AsyncSession,
        request: ApplicationSubmissionRequest
    ) -> Application:
        """Submit application for a job using browser automation"""
        try:
            logger.info(f"Processing application submission request for job {request.job_id}")
            
            if request.confirm_submission:
                # Use browser automation for actual submission
                submission_result = await application_submission_service.submit_application(
                    db=db,
                    job_id=request.job_id,
                    proposal_id=request.proposal_id,
                    confirm_submission=True
                )
                
                if not submission_result.success:
                    raise Exception(f"Browser submission failed: {submission_result.error_message}")
                
                # Get the created application
                if submission_result.application_id:
                    application = await self.get_application(db, submission_result.application_id)
                    if application:
                        return application
                
                raise Exception("Application was submitted but record not found")
            
            else:
                # Create pending application without browser submission
                return await self._create_pending_application(db, request)
            
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            raise
    
    async def _create_pending_application(
        self,
        db: AsyncSession,
        request: ApplicationSubmissionRequest
    ) -> Application:
        """Create pending application without browser submission"""
        # Verify job exists
        job_query = select(JobModel).where(JobModel.id == request.job_id)
        job_result = await db.execute(job_query)
        job_model = job_result.scalar_one_or_none()
        
        if not job_model:
            raise ValueError("Job not found")
        
        # Verify proposal exists
        proposal_query = select(ProposalModel).where(ProposalModel.id == request.proposal_id)
        proposal_result = await db.execute(proposal_query)
        proposal_model = proposal_result.scalar_one_or_none()
        
        if not proposal_model:
            raise ValueError("Proposal not found")
        
        # Check if application already exists
        existing_query = select(ApplicationModel).where(
            ApplicationModel.job_id == request.job_id,
            ApplicationModel.proposal_id == request.proposal_id
        )
        existing_result = await db.execute(existing_query)
        existing_app = existing_result.scalar_one_or_none()
        
        if existing_app:
            raise ValueError("Application already exists for this job and proposal")
        
        # Create pending application model
        application_model = ApplicationModel(
            job_id=request.job_id,
            proposal_id=request.proposal_id,
            submitted_at=None,
            status=ApplicationStatus.PENDING
        )
        
        db.add(application_model)
        await db.commit()
        
        logger.info(f"Created pending application for job: {job_model.title}")
        
        return self._model_to_pydantic(application_model)
    
    async def get_application(self, db: AsyncSession, application_id: UUID) -> Optional[Application]:
        """Get specific application by ID"""
        try:
            query = select(ApplicationModel).where(ApplicationModel.id == application_id)
            result = await db.execute(query)
            application_model = result.scalar_one_or_none()
            
            if application_model:
                return self._model_to_pydantic(application_model)
            return None
            
        except Exception as e:
            logger.error(f"Error getting application {application_id}: {e}")
            raise
    
    async def list_applications(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Application]:
        """List applications with optional filtering"""
        try:
            query = select(ApplicationModel)
            
            # Apply status filter
            if status:
                query = query.where(ApplicationModel.status == status)
            
            # Order by submitted_at desc
            query = query.order_by(desc(ApplicationModel.submitted_at)).limit(limit)
            
            result = await db.execute(query)
            application_models = result.scalars().all()
            
            applications = []
            for app_model in application_models:
                applications.append(self._model_to_pydantic(app_model))
            
            return applications
            
        except Exception as e:
            logger.error(f"Error listing applications: {e}")
            raise
    
    async def batch_submit_applications(
        self,
        db: AsyncSession,
        application_ids: List[UUID],
        max_concurrent: int = 2
    ) -> Dict[str, Any]:
        """Submit multiple pending applications using browser automation"""
        try:
            # Get pending applications
            pending_apps = []
            for app_id in application_ids:
                app = await self.get_application(db, app_id)
                if app and app.status == ApplicationStatus.PENDING:
                    pending_apps.append(app)
            
            if not pending_apps:
                return {
                    "success": False,
                    "message": "No pending applications found",
                    "results": []
                }
            
            # Prepare submission requests
            submission_requests = [
                (app.job_id, app.proposal_id) for app in pending_apps
            ]
            
            # Execute batch submission
            results = await application_submission_service.batch_submit_applications(
                db=db,
                submission_requests=submission_requests,
                max_concurrent=max_concurrent
            )
            
            # Process results
            successful_submissions = [r for r in results if r.success]
            failed_submissions = [r for r in results if not r.success]
            
            return {
                "success": True,
                "total_processed": len(results),
                "successful_submissions": len(successful_submissions),
                "failed_submissions": len(failed_submissions),
                "results": [
                    {
                        "application_id": str(r.application_id) if r.application_id else None,
                        "success": r.success,
                        "error_message": r.error_message,
                        "execution_time": r.execution_time,
                        "steps_completed": r.steps_completed
                    }
                    for r in results
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in batch submission: {e}")
            raise
    
    async def get_submission_queue(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get applications queued for submission"""
        try:
            # Get pending applications with job and proposal details
            query = (
                select(ApplicationModel, JobModel, ProposalModel)
                .join(JobModel, ApplicationModel.job_id == JobModel.id)
                .join(ProposalModel, ApplicationModel.proposal_id == ProposalModel.id)
                .where(ApplicationModel.status == ApplicationStatus.PENDING)
                .order_by(ApplicationModel.created_at.asc())
                .limit(limit)
            )
            
            result = await db.execute(query)
            rows = result.all()
            
            queue_items = []
            for app_model, job_model, proposal_model in rows:
                queue_items.append({
                    "application_id": str(app_model.id),
                    "job_id": str(job_model.id),
                    "proposal_id": str(proposal_model.id),
                    "job_title": job_model.title,
                    "client_name": job_model.client_name,
                    "bid_amount": float(proposal_model.bid_amount),
                    "proposal_quality": float(proposal_model.quality_score) if proposal_model.quality_score else None,
                    "created_at": app_model.created_at,
                    "priority_score": self._calculate_submission_priority(job_model, proposal_model)
                })
            
            # Sort by priority score
            queue_items.sort(key=lambda x: x["priority_score"], reverse=True)
            
            return queue_items
            
        except Exception as e:
            logger.error(f"Error getting submission queue: {e}")
            raise
    
    async def get_submission_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get submission statistics"""
        try:
            # Get application counts by status
            status_counts = {}
            for status in ApplicationStatus:
                count_query = select(func.count()).where(ApplicationModel.status == status)
                count_result = await db.execute(count_query)
                status_counts[status.value] = count_result.scalar() or 0
            
            # Get today's submissions
            today = datetime.utcnow().date()
            today_query = select(func.count()).where(
                func.date(ApplicationModel.submitted_at) == today
            )
            today_result = await db.execute(today_query)
            submissions_today = today_result.scalar() or 0
            
            # Get browser automation stats
            browser_stats = await application_submission_service.get_submission_stats()
            
            return {
                "status_counts": status_counts,
                "submissions_today": submissions_today,
                "browser_automation": browser_stats,
                "queue_size": status_counts.get("pending", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting submission stats: {e}")
            raise
    
    def _calculate_submission_priority(
        self,
        job_model: JobModel,
        proposal_model: ProposalModel
    ) -> float:
        """Calculate priority score for submission queue ordering"""
        priority = 0.0
        
        # Higher priority for higher quality proposals
        if proposal_model.quality_score:
            priority += float(proposal_model.quality_score) * 40
        
        # Higher priority for better paying jobs
        if job_model.hourly_rate:
            rate_score = min(float(job_model.hourly_rate) / 100.0, 1.0)  # Normalize to 0-1
            priority += rate_score * 30
        
        # Higher priority for better clients
        if job_model.client_rating:
            client_score = (float(job_model.client_rating) - 3.0) / 2.0  # Normalize 3-5 to 0-1
            priority += max(client_score, 0) * 20
        
        # Higher priority for jobs with good match scores
        if job_model.match_score:
            priority += float(job_model.match_score) * 10
        
        return priority
    
    async def update_application_status(
        self,
        db: AsyncSession,
        application_id: UUID,
        status: str,
        client_response: Optional[str] = None
    ) -> bool:
        """Update application status"""
        try:
            # Validate status
            try:
                app_status = ApplicationStatus(status)
            except ValueError:
                raise ValueError(f"Invalid application status: {status}")
            
            query = select(ApplicationModel).where(ApplicationModel.id == application_id)
            result = await db.execute(query)
            application_model = result.scalar_one_or_none()
            
            if not application_model:
                return False
            
            # Update status and response
            application_model.status = app_status
            application_model.updated_at = datetime.utcnow()
            
            if client_response:
                application_model.client_response = client_response
                application_model.client_response_date = datetime.utcnow()
            
            # Set interview flag if status is interview
            if app_status == ApplicationStatus.INTERVIEW:
                application_model.interview_scheduled = True
                if not application_model.interview_date:
                    application_model.interview_date = datetime.utcnow()
            
            # Set hired flag if status is hired
            if app_status == ApplicationStatus.HIRED:
                application_model.hired = True
                if not application_model.hire_date:
                    application_model.hire_date = datetime.utcnow()
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating application status: {e}")
            await db.rollback()
            raise
    
    def _model_to_pydantic(self, application_model: ApplicationModel) -> Application:
        """Convert SQLAlchemy model to Pydantic model"""
        return Application(
            id=application_model.id,
            job_id=application_model.job_id,
            proposal_id=application_model.proposal_id,
            upwork_application_id=application_model.upwork_application_id,
            submitted_at=application_model.submitted_at,
            status=application_model.status,
            client_response=application_model.client_response,
            client_response_date=application_model.client_response_date,
            interview_scheduled=application_model.interview_scheduled,
            interview_date=application_model.interview_date,
            hired=application_model.hired,
            hire_date=application_model.hire_date,
            session_recording_url=application_model.session_recording_url,
            created_at=application_model.created_at,
            updated_at=application_model.updated_at
        )


# Global service instance
application_service = ApplicationService()