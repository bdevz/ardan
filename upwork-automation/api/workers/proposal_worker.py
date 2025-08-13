"""
Proposal Generation Worker for background job processing
"""
import logging
from typing import Dict, Any
from uuid import UUID

from workers.base_worker import BaseWorker
from services.proposal_service import proposal_service
from services.job_service import job_service
from services.google_services import google_services

logger = logging.getLogger(__name__)


class ProposalWorker(BaseWorker):
    """Worker for processing proposal generation tasks"""
    
    def __init__(self, concurrency: int = 3):
        super().__init__(
            worker_name="proposal_generation",
            task_types=["generate_proposal", "batch_generate_proposals", "update_proposal"],
            concurrency=concurrency
        )
    
    async def process_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process proposal generation tasks"""
        logger.info(f"Processing {task_type} task {task_id}")
        
        if task_type == "generate_proposal":
            return await self._process_generate_proposal(task_data)
        elif task_type == "batch_generate_proposals":
            return await self._process_batch_generate_proposals(task_data)
        elif task_type == "update_proposal":
            return await self._process_update_proposal(task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _process_generate_proposal(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process single proposal generation"""
        job_id = UUID(task_data["job_id"])
        custom_instructions = task_data.get("custom_instructions")
        include_attachments = task_data.get("include_attachments", True)
        
        try:
            # Get job details
            job = await job_service.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Generate proposal content using LLM
            proposal_content = await proposal_service.generate_proposal_content(
                job=job,
                custom_instructions=custom_instructions
            )
            
            # Calculate optimal bid amount
            bid_amount = await proposal_service.calculate_bid_amount(job)
            
            # Select relevant attachments
            attachments = []
            if include_attachments:
                attachments = await google_services.select_relevant_attachments(
                    job_description=job.description,
                    required_skills=job.skills_required
                )
            
            # Create Google Doc for proposal
            doc_result = await google_services.create_proposal_document(
                job_title=job.title,
                proposal_content=proposal_content
            )
            
            # Create proposal record
            proposal = await proposal_service.create_proposal(
                job_id=job_id,
                content=proposal_content,
                bid_amount=bid_amount,
                attachments=[att["id"] for att in attachments],
                google_doc_url=doc_result["document_url"],
                google_doc_id=doc_result["document_id"]
            )
            
            # Update job status
            await job_service.update_job_status(job_id, "queued")
            
            return {
                "proposal_id": str(proposal.id),
                "job_id": str(job_id),
                "bid_amount": float(bid_amount),
                "attachments_count": len(attachments),
                "google_doc_url": doc_result["document_url"],
                "content_length": len(proposal_content)
            }
            
        except Exception as e:
            logger.error(f"Proposal generation failed for job {job_id}: {str(e)}")
            raise
    
    async def _process_batch_generate_proposals(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process batch proposal generation"""
        job_ids = [UUID(job_id) for job_id in task_data["job_ids"]]
        custom_instructions = task_data.get("custom_instructions")
        include_attachments = task_data.get("include_attachments", True)
        
        results = {
            "successful": [],
            "failed": [],
            "total_processed": 0
        }
        
        for job_id in job_ids:
            try:
                result = await self._process_generate_proposal({
                    "job_id": str(job_id),
                    "custom_instructions": custom_instructions,
                    "include_attachments": include_attachments
                })
                results["successful"].append({
                    "job_id": str(job_id),
                    "proposal_id": result["proposal_id"]
                })
            except Exception as e:
                logger.error(f"Failed to generate proposal for job {job_id}: {str(e)}")
                results["failed"].append({
                    "job_id": str(job_id),
                    "error": str(e)
                })
            
            results["total_processed"] += 1
        
        return results
    
    async def _process_update_proposal(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process proposal update"""
        proposal_id = UUID(task_data["proposal_id"])
        updates = task_data.get("updates", {})
        
        try:
            # Get existing proposal
            proposal = await proposal_service.get_proposal(proposal_id)
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            # Update proposal content if provided
            if "content" in updates:
                # Update Google Doc
                if proposal.google_doc_id:
                    await google_services.update_document_content(
                        document_id=proposal.google_doc_id,
                        content=updates["content"]
                    )
            
            # Update proposal record
            updated_proposal = await proposal_service.update_proposal(
                proposal_id=proposal_id,
                **updates
            )
            
            return {
                "proposal_id": str(proposal_id),
                "updated_fields": list(updates.keys()),
                "status": updated_proposal.status
            }
            
        except Exception as e:
            logger.error(f"Proposal update failed for {proposal_id}: {str(e)}")
            raise


# Create worker instance
proposal_worker = ProposalWorker()