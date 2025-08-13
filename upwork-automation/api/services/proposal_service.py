"""
Enhanced Proposal service - business logic for AI-powered proposal generation and management
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ProposalModel, JobModel
from shared.models import Proposal, ProposalGenerationRequest, ProposalStatus
from shared.utils import setup_logging
from .llm_proposal_service import llm_proposal_service
from .google_services import google_docs_service, google_drive_service
from .websocket_service import websocket_service

logger = setup_logging("proposal-service")


class ProposalService:
    """Service for proposal-related operations"""
    
    async def generate_proposal(
        self,
        db: AsyncSession,
        request: ProposalGenerationRequest
    ) -> Proposal:
        """Generate AI-powered proposal for a job"""
        try:
            # Get job details
            job_query = select(JobModel).where(JobModel.id == request.job_id)
            job_result = await db.execute(job_query)
            job_model = job_result.scalar_one_or_none()
            
            if not job_model:
                raise ValueError("Job not found")
            
            # Convert to shared Job model for LLM service
            job = self._db_model_to_shared_model(job_model)
            
            # Generate proposal using LLM service
            llm_result = await llm_proposal_service.generate_proposal(
                job=job,
                custom_instructions=request.custom_instructions,
                template_style="professional"
            )
            
            # Create Google Doc for the proposal
            google_doc_result = await google_docs_service.create_proposal_document(
                title=job.title,
                content=llm_result["content"],
                job_id=request.job_id
            )
            
            # Select relevant attachments from Google Drive
            attachments = []
            if request.include_attachments:
                job_requirements = job.skills_required or []
                drive_attachments = await google_drive_service.select_relevant_attachments(
                    job_requirements=job_requirements,
                    max_attachments=3
                )
                attachments = [att["id"] for att in drive_attachments]
            
            # Create proposal model
            proposal_model = ProposalModel(
                job_id=request.job_id,
                content=llm_result["content"],
                bid_amount=llm_result["bid_amount"],
                attachments=attachments,
                google_doc_url=google_doc_result["document_url"],
                google_doc_id=google_doc_result["document_id"],
                generated_at=llm_result["generated_at"],
                status=ProposalStatus.DRAFT,
                quality_score=llm_result["quality_score"]
            )
            
            db.add(proposal_model)
            await db.commit()
            
            # Broadcast proposal generation via WebSocket
            await websocket_service.broadcast_proposal_generated({
                "id": str(proposal_model.id),
                "job_id": str(request.job_id),
                "job_title": job_model.title,
                "bid_amount": float(proposal_model.bid_amount) if proposal_model.bid_amount else None,
                "generated_at": proposal_model.generated_at.isoformat()
            })
            
            logger.info(f"Generated AI proposal for job: {job_model.title} (Quality: {llm_result['quality_score']})")
            
            return self._model_to_pydantic(proposal_model)
            
        except Exception as e:
            logger.error(f"Error generating AI proposal: {e}")
            await db.rollback()
            raise
    
    async def get_proposal(self, db: AsyncSession, proposal_id: UUID) -> Optional[Proposal]:
        """Get specific proposal by ID"""
        try:
            query = select(ProposalModel).where(ProposalModel.id == proposal_id)
            result = await db.execute(query)
            proposal_model = result.scalar_one_or_none()
            
            if proposal_model:
                return self._model_to_pydantic(proposal_model)
            return None
            
        except Exception as e:
            logger.error(f"Error getting proposal {proposal_id}: {e}")
            raise
    
    async def update_proposal(
        self,
        db: AsyncSession,
        proposal_id: UUID,
        proposal_data: dict
    ) -> bool:
        """Update proposal content and sync with Google Doc"""
        try:
            query = select(ProposalModel).where(ProposalModel.id == proposal_id)
            result = await db.execute(query)
            proposal_model = result.scalar_one_or_none()
            
            if not proposal_model:
                return False
            
            # Update allowed fields
            content_updated = False
            if "content" in proposal_data:
                proposal_model.content = proposal_data["content"]
                content_updated = True
                
            if "bid_amount" in proposal_data:
                proposal_model.bid_amount = Decimal(str(proposal_data["bid_amount"]))
                
            if "attachments" in proposal_data:
                proposal_model.attachments = proposal_data["attachments"]
            
            proposal_model.updated_at = datetime.utcnow()
            
            # Update Google Doc if content changed
            if content_updated and proposal_model.google_doc_id:
                await google_docs_service.update_proposal_document(
                    document_id=proposal_model.google_doc_id,
                    content=proposal_model.content
                )
            
            await db.commit()
            logger.info(f"Updated proposal {proposal_id} and synced with Google Doc")
            return True
            
        except Exception as e:
            logger.error(f"Error updating proposal: {e}")
            await db.rollback()
            raise
    
    async def regenerate_proposal(
        self,
        db: AsyncSession,
        proposal_id: UUID,
        custom_instructions: Optional[str] = None
    ) -> Proposal:
        """Regenerate proposal using LLM with new instructions"""
        try:
            # Get existing proposal
            proposal_query = select(ProposalModel).where(ProposalModel.id == proposal_id)
            proposal_result = await db.execute(proposal_query)
            proposal_model = proposal_result.scalar_one_or_none()
            
            if not proposal_model:
                raise ValueError("Proposal not found")
            
            # Get job details
            job_query = select(JobModel).where(JobModel.id == proposal_model.job_id)
            job_result = await db.execute(job_query)
            job_model = job_result.scalar_one_or_none()
            
            if not job_model:
                raise ValueError("Associated job not found")
            
            # Convert to shared Job model
            job = self._db_model_to_shared_model(job_model)
            
            # Regenerate using LLM service
            llm_result = await llm_proposal_service.generate_proposal(
                job=job,
                custom_instructions=custom_instructions,
                template_style="professional"
            )
            
            # Update proposal
            proposal_model.content = llm_result["content"]
            proposal_model.bid_amount = llm_result["bid_amount"]
            proposal_model.quality_score = llm_result["quality_score"]
            proposal_model.generated_at = llm_result["generated_at"]
            proposal_model.updated_at = datetime.utcnow()
            
            # Update Google Doc
            if proposal_model.google_doc_id:
                await google_docs_service.update_proposal_document(
                    document_id=proposal_model.google_doc_id,
                    content=llm_result["content"]
                )
            
            await db.commit()
            
            logger.info(f"Regenerated proposal {proposal_id} with quality score: {llm_result['quality_score']}")
            
            return self._model_to_pydantic(proposal_model)
            
        except Exception as e:
            logger.error(f"Error regenerating proposal: {e}")
            await db.rollback()
            raise
    
    async def optimize_proposal(
        self,
        db: AsyncSession,
        proposal_id: UUID
    ) -> Dict[str, Any]:
        """Analyze and provide optimization suggestions for a proposal"""
        try:
            # Get proposal and job
            proposal_query = select(ProposalModel).where(ProposalModel.id == proposal_id)
            proposal_result = await db.execute(proposal_query)
            proposal_model = proposal_result.scalar_one_or_none()
            
            if not proposal_model:
                raise ValueError("Proposal not found")
            
            job_query = select(JobModel).where(JobModel.id == proposal_model.job_id)
            job_result = await db.execute(job_query)
            job_model = job_result.scalar_one_or_none()
            
            if not job_model:
                raise ValueError("Associated job not found")
            
            # Analyze proposal for optimization opportunities
            suggestions = await self._analyze_proposal_for_optimization(
                proposal_model.content,
                job_model
            )
            
            return {
                "current_quality_score": float(proposal_model.quality_score or 0),
                "suggestions": suggestions,
                "estimated_improvement": self._estimate_improvement_potential(suggestions),
                "analysis_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error optimizing proposal: {e}")
            raise
    
    async def _analyze_proposal_for_optimization(
        self,
        content: str,
        job_model: JobModel
    ) -> List[Dict[str, str]]:
        """Analyze proposal content for optimization opportunities"""
        suggestions = []
        
        # Check length
        word_count = len(content.split())
        if word_count < 150:
            suggestions.append({
                "type": "length",
                "issue": "Proposal is too short",
                "suggestion": "Add more specific details about your experience and approach",
                "priority": "high"
            })
        elif word_count > 400:
            suggestions.append({
                "type": "length", 
                "issue": "Proposal is too long",
                "suggestion": "Condense content to focus on most relevant points",
                "priority": "medium"
            })
        
        # Check for personalization
        if not job_model.client_name or job_model.client_name.lower() not in content.lower():
            suggestions.append({
                "type": "personalization",
                "issue": "Missing client name personalization",
                "suggestion": "Address the client by name to show attention to detail",
                "priority": "high"
            })
        
        # Check for metrics
        import re
        if not re.search(r'\d+%|\d+\+|\d+ years', content):
            suggestions.append({
                "type": "metrics",
                "issue": "No quantifiable achievements mentioned",
                "suggestion": "Include specific metrics and results from past projects",
                "priority": "high"
            })
        
        # Check for call to action
        cta_phrases = ['call', 'discuss', 'schedule', 'contact', 'chat']
        if not any(phrase in content.lower() for phrase in cta_phrases):
            suggestions.append({
                "type": "call_to_action",
                "issue": "Weak or missing call to action",
                "suggestion": "End with a clear invitation to discuss the project",
                "priority": "medium"
            })
        
        return suggestions
    
    def _estimate_improvement_potential(self, suggestions: List[Dict[str, str]]) -> float:
        """Estimate potential quality score improvement"""
        high_priority_count = sum(1 for s in suggestions if s["priority"] == "high")
        medium_priority_count = sum(1 for s in suggestions if s["priority"] == "medium")
        
        # Estimate improvement based on suggestion priorities
        potential_improvement = (high_priority_count * 0.15) + (medium_priority_count * 0.08)
        return min(potential_improvement, 0.3)  # Cap at 30% improvement
    
    def _db_model_to_shared_model(self, job_model: JobModel):
        """Convert database model to shared model for LLM service"""
        from shared.models import Job
        
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
    
    def _model_to_pydantic(self, proposal_model: ProposalModel) -> Proposal:
        """Convert SQLAlchemy model to Pydantic model"""
        return Proposal(
            id=proposal_model.id,
            job_id=proposal_model.job_id,
            content=proposal_model.content,
            bid_amount=proposal_model.bid_amount,
            attachments=proposal_model.attachments or [],
            google_doc_url=proposal_model.google_doc_url,
            google_doc_id=proposal_model.google_doc_id,
            generated_at=proposal_model.generated_at,
            submitted_at=proposal_model.submitted_at,
            status=proposal_model.status,
            quality_score=proposal_model.quality_score,
            created_at=proposal_model.created_at,
            updated_at=proposal_model.updated_at
        )


# Global service instance
proposal_service = ProposalService()