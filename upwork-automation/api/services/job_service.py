"""
Job service - business logic for job management
"""
import sys
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Add browser-automation to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'browser-automation'))

from database.models import JobModel
from shared.models import Job, JobListResponse, JobSearchParams, JobStatus
from shared.utils import setup_logging
from job_discovery_service import JobDiscoveryService, SearchStrategy
from services.websocket_service import websocket_service

logger = setup_logging("job-service")


class JobService:
    """Service for job-related operations"""
    
    def __init__(self):
        self.job_discovery_service = None
    
    async def get_job_discovery_service(self) -> JobDiscoveryService:
        """Get or create job discovery service instance"""
        if self.job_discovery_service is None:
            self.job_discovery_service = JobDiscoveryService()
            await self.job_discovery_service.initialize()
        return self.job_discovery_service
    
    async def list_jobs(
        self,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        min_rate: Optional[float] = None,
        max_rate: Optional[float] = None
    ) -> JobListResponse:
        """List jobs with filtering and pagination"""
        try:
            # Build query with filters
            query = select(JobModel)
            
            # Apply filters
            filters = []
            if status:
                filters.append(JobModel.status == status)
            if min_rate:
                filters.append(JobModel.hourly_rate >= Decimal(str(min_rate)))
            if max_rate:
                filters.append(JobModel.hourly_rate <= Decimal(str(max_rate)))
            
            if filters:
                query = query.where(and_(*filters))
            
            # Order by created_at desc
            query = query.order_by(JobModel.created_at.desc())
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await db.execute(query)
            job_models = result.scalars().all()
            
            # Convert to Pydantic models
            jobs = [self._model_to_pydantic(job_model) for job_model in job_models]
            
            return JobListResponse(
                jobs=jobs,
                total=total,
                page=page,
                per_page=per_page
            )
            
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            raise
    
    async def get_job(self, db: AsyncSession, job_id: UUID) -> Optional[Job]:
        """Get specific job by ID"""
        try:
            query = select(JobModel).where(JobModel.id == job_id)
            result = await db.execute(query)
            job_model = result.scalar_one_or_none()
            
            if job_model:
                return self._model_to_pydantic(job_model)
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            raise
    
    async def search_jobs(
        self,
        db: AsyncSession,
        search_params: JobSearchParams
    ) -> dict:
        """Trigger job search with specified parameters"""
        try:
            # Get job discovery service
            discovery_service = await self.get_job_discovery_service()
            
            # Determine search strategy
            strategy = SearchStrategy.HYBRID
            if len(search_params.keywords) == 1:
                strategy = SearchStrategy.KEYWORD_BASED
            
            # Execute job discovery
            result = await discovery_service.discover_jobs(
                search_params=search_params,
                max_jobs=50,
                search_strategy=strategy
            )
            
            if result.success:
                # Save discovered jobs to database
                saved_jobs = []
                for job in result.jobs_found:
                    saved_job = await self._save_job(db, job)
                    if saved_job:
                        saved_jobs.append(saved_job)
                
                await db.commit()
                
                return {
                    "success": True,
                    "jobs_found": len(saved_jobs),
                    "total_processed": result.total_processed,
                    "duplicates_removed": result.duplicates_removed,
                    "filtered_out": result.filtered_out,
                    "search_duration": result.search_duration,
                    "search_strategy": result.search_strategy
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "search_duration": result.search_duration
                }
                
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            await db.rollback()
            raise
    
    async def update_job_status(
        self,
        db: AsyncSession,
        job_id: UUID,
        status: str
    ) -> bool:
        """Update job status"""
        try:
            # Validate status
            try:
                job_status = JobStatus(status)
            except ValueError:
                raise ValueError(f"Invalid job status: {status}")
            
            # Update job
            query = select(JobModel).where(JobModel.id == job_id)
            result = await db.execute(query)
            job_model = result.scalar_one_or_none()
            
            if not job_model:
                return False
            
            job_model.status = job_status
            job_model.updated_at = datetime.utcnow()
            
            await db.commit()
            
            # Broadcast job status update via WebSocket
            await websocket_service.broadcast_job_status_update(
                job_id=str(job_id),
                status=status,
                details={
                    "title": job_model.title,
                    "updated_at": job_model.updated_at.isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            await db.rollback()
            raise
    
    async def _save_job(self, db: AsyncSession, job: Job) -> Optional[JobModel]:
        """Save job to database, avoiding duplicates"""
        try:
            # Check for existing job by upwork_job_id or content_hash
            existing_query = select(JobModel).where(
                or_(
                    JobModel.upwork_job_id == job.upwork_job_id,
                    JobModel.content_hash == job.content_hash
                )
            )
            result = await db.execute(existing_query)
            existing_job = result.scalar_one_or_none()
            
            if existing_job:
                logger.debug(f"Job already exists: {job.title}")
                return existing_job
            
            # Create new job model
            job_model = JobModel(
                upwork_job_id=job.upwork_job_id,
                title=job.title,
                description=job.description,
                budget_min=job.budget_min,
                budget_max=job.budget_max,
                hourly_rate=job.hourly_rate,
                client_name=job.client_name,
                client_rating=job.client_rating,
                client_payment_verified=job.client_payment_verified,
                client_hire_rate=job.client_hire_rate,
                posted_date=job.posted_date,
                deadline=job.deadline,
                skills_required=job.skills_required,
                job_type=job.job_type,
                location=job.location,
                status=job.status,
                match_score=job.match_score,
                match_reasons=job.match_reasons,
                content_hash=job.content_hash,
                job_url=job.job_url
            )
            
            db.add(job_model)
            await db.flush()  # Get the ID without committing
            
            # Broadcast new job discovery via WebSocket
            await websocket_service.broadcast_job_discovered({
                "id": str(job_model.id),
                "title": job.title,
                "budget_max": job.budget_max,
                "hourly_rate": job.hourly_rate,
                "client_rating": job.client_rating,
                "match_score": job.match_score,
                "posted_date": job.posted_date.isoformat() if job.posted_date else None
            })
            
            logger.info(f"Saved new job: {job.title}")
            return job_model
            
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            return None
    
    def _model_to_pydantic(self, job_model: JobModel) -> Job:
        """Convert SQLAlchemy model to Pydantic model"""
        return Job(
            id=job_model.id,
            upwork_job_id=job_model.upwork_job_id,
            title=job_model.title,
            description=job_model.description,
            budget_min=job_model.budget_min,
            budget_max=job_model.budget_max,
            hourly_rate=job_model.hourly_rate,
            client_name=job_model.client_name,
            client_rating=job_model.client_rating,
            client_payment_verified=job_model.client_payment_verified,
            client_hire_rate=job_model.client_hire_rate,
            posted_date=job_model.posted_date,
            deadline=job_model.deadline,
            skills_required=job_model.skills_required or [],
            job_type=job_model.job_type,
            location=job_model.location,
            status=job_model.status,
            match_score=job_model.match_score,
            match_reasons=job_model.match_reasons or [],
            content_hash=job_model.content_hash,
            job_url=job_model.job_url,
            created_at=job_model.created_at,
            updated_at=job_model.updated_at
        )


# Global service instance
job_service = JobService()