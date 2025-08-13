"""
Workflow Service - Orchestrates end-to-end job discovery to proposal generation workflow
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import JobModel, ProposalModel, SystemConfigModel
from shared.models import Job, Proposal, JobSearchParams, ProposalGenerationRequest
from shared.utils import setup_logging
from .job_service import job_service
from .proposal_service import proposal_service
from .llm_proposal_service import llm_proposal_service
from .google_services import google_sheets_service

logger = setup_logging("workflow-service")


class WorkflowService:
    """Service for orchestrating automated workflows"""
    
    async def execute_discovery_to_proposal_workflow(
        self,
        db: AsyncSession,
        search_params: Optional[JobSearchParams] = None,
        max_jobs: int = 20,
        auto_generate_proposals: bool = True,
        quality_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Execute complete workflow from job discovery to proposal generation
        
        This is the main automation workflow that:
        1. Discovers new jobs using the job discovery service
        2. Filters jobs based on quality and criteria
        3. Automatically generates proposals for qualifying jobs
        4. Stores proposals in Google Docs
        5. Queues proposals for review/submission
        """
        workflow_start = datetime.utcnow()
        
        try:
            logger.info("Starting discovery-to-proposal workflow")
            
            # Step 1: Discover jobs
            discovery_result = await job_service.search_jobs(
                db=db,
                search_params=search_params or self._get_default_search_params()
            )
            
            if not discovery_result["success"]:
                raise Exception(f"Job discovery failed: {discovery_result.get('error')}")
            
            jobs_found = discovery_result["jobs_found"]
            logger.info(f"Discovered {jobs_found} new jobs")
            
            # Step 2: Get discovered jobs from database
            discovered_jobs = await self._get_recent_discovered_jobs(db, max_jobs)
            
            # Step 3: Filter jobs for proposal generation
            qualified_jobs = await self._filter_jobs_for_proposals(db, discovered_jobs, quality_threshold)
            logger.info(f"Found {len(qualified_jobs)} jobs qualifying for proposals")
            
            # Step 4: Generate proposals if enabled
            proposals_generated = []
            if auto_generate_proposals and qualified_jobs:
                proposals_generated = await self._batch_generate_proposals(
                    db, qualified_jobs, quality_threshold
                )
            
            # Step 5: Export results to Google Sheets
            export_result = await self._export_workflow_results(
                discovered_jobs, proposals_generated
            )
            
            workflow_duration = (datetime.utcnow() - workflow_start).total_seconds()
            
            # Step 6: Compile workflow results
            workflow_result = {
                "success": True,
                "workflow_duration": workflow_duration,
                "jobs_discovered": jobs_found,
                "jobs_qualified": len(qualified_jobs),
                "proposals_generated": len(proposals_generated),
                "discovery_stats": {
                    "total_processed": discovery_result["total_processed"],
                    "duplicates_removed": discovery_result["duplicates_removed"],
                    "filtered_out": discovery_result["filtered_out"]
                },
                "proposal_stats": {
                    "average_quality_score": self._calculate_average_quality(proposals_generated),
                    "proposals_above_threshold": len([p for p in proposals_generated if p.quality_score and p.quality_score >= quality_threshold])
                },
                "export_result": export_result,
                "next_steps": self._generate_next_steps_recommendations(qualified_jobs, proposals_generated)
            }
            
            logger.info(f"Workflow completed successfully in {workflow_duration:.2f}s")
            return workflow_result
            
        except Exception as e:
            workflow_duration = (datetime.utcnow() - workflow_start).total_seconds()
            logger.error(f"Workflow failed after {workflow_duration:.2f}s: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "workflow_duration": workflow_duration,
                "jobs_discovered": 0,
                "jobs_qualified": 0,
                "proposals_generated": 0
            }
    
    async def execute_proposal_optimization_workflow(
        self,
        db: AsyncSession,
        proposal_ids: List[UUID],
        auto_apply_optimizations: bool = False
    ) -> Dict[str, Any]:
        """
        Execute workflow to optimize existing proposals
        
        Analyzes and optimizes multiple proposals using AI suggestions
        """
        try:
            logger.info(f"Starting proposal optimization workflow for {len(proposal_ids)} proposals")
            
            optimization_results = []
            
            for proposal_id in proposal_ids:
                try:
                    # Get optimization suggestions
                    optimization = await proposal_service.optimize_proposal(db, proposal_id)
                    
                    # Auto-apply optimizations if enabled and improvement is significant
                    if (auto_apply_optimizations and 
                        optimization["estimated_improvement"] > 0.15):
                        
                        # Regenerate proposal with optimization suggestions
                        optimization_instructions = self._convert_suggestions_to_instructions(
                            optimization["suggestions"]
                        )
                        
                        optimized_proposal = await proposal_service.regenerate_proposal(
                            db=db,
                            proposal_id=proposal_id,
                            custom_instructions=optimization_instructions
                        )
                        
                        optimization["optimized"] = True
                        optimization["new_quality_score"] = float(optimized_proposal.quality_score or 0)
                    else:
                        optimization["optimized"] = False
                    
                    optimization["proposal_id"] = str(proposal_id)
                    optimization_results.append(optimization)
                    
                except Exception as e:
                    logger.warning(f"Failed to optimize proposal {proposal_id}: {e}")
                    optimization_results.append({
                        "proposal_id": str(proposal_id),
                        "error": str(e),
                        "optimized": False
                    })
            
            # Calculate summary statistics
            successful_optimizations = [r for r in optimization_results if r.get("optimized")]
            average_improvement = sum(r.get("estimated_improvement", 0) for r in successful_optimizations) / len(successful_optimizations) if successful_optimizations else 0
            
            return {
                "success": True,
                "proposals_processed": len(proposal_ids),
                "proposals_optimized": len(successful_optimizations),
                "average_improvement": average_improvement,
                "optimization_results": optimization_results
            }
            
        except Exception as e:
            logger.error(f"Proposal optimization workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "proposals_processed": len(proposal_ids),
                "proposals_optimized": 0
            }
    
    async def _get_recent_discovered_jobs(
        self,
        db: AsyncSession,
        limit: int
    ) -> List[JobModel]:
        """Get recently discovered jobs from database"""
        try:
            query = (
                select(JobModel)
                .where(JobModel.status == "discovered")
                .order_by(JobModel.created_at.desc())
                .limit(limit)
            )
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            return []
    
    async def _filter_jobs_for_proposals(
        self,
        db: AsyncSession,
        jobs: List[JobModel],
        quality_threshold: float
    ) -> List[JobModel]:
        """Filter jobs that qualify for proposal generation"""
        qualified_jobs = []
        
        for job in jobs:
            # Check if proposal already exists
            existing_proposal_query = select(ProposalModel).where(ProposalModel.job_id == job.id)
            existing_result = await db.execute(existing_proposal_query)
            existing_proposal = existing_result.scalar_one_or_none()
            
            if existing_proposal:
                continue  # Skip if proposal already exists
            
            # Check job quality criteria
            if (job.match_score and 
                float(job.match_score) >= quality_threshold and
                job.client_rating >= 4.0 and
                job.client_payment_verified):
                qualified_jobs.append(job)
        
        return qualified_jobs
    
    async def _batch_generate_proposals(
        self,
        db: AsyncSession,
        jobs: List[JobModel],
        quality_threshold: float
    ) -> List[Proposal]:
        """Generate proposals for multiple jobs in batch"""
        proposals = []
        
        # Process jobs in smaller batches to avoid overwhelming the LLM API
        batch_size = 5
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            
            # Generate proposals for this batch
            batch_tasks = []
            for job in batch:
                request = ProposalGenerationRequest(
                    job_id=job.id,
                    include_attachments=True
                )
                task = proposal_service.generate_proposal(db, request)
                batch_tasks.append(task)
            
            # Execute batch
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Proposal generation failed: {result}")
                    else:
                        proposals.append(result)
                
                # Add delay between batches to respect API rate limits
                if i + batch_size < len(jobs):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Batch proposal generation failed: {e}")
        
        logger.info(f"Generated {len(proposals)} proposals from {len(jobs)} jobs")
        return proposals
    
    async def _export_workflow_results(
        self,
        jobs: List[JobModel],
        proposals: List[Proposal]
    ) -> Dict[str, Any]:
        """Export workflow results to Google Sheets"""
        try:
            # Prepare jobs data for export
            jobs_data = []
            for job in jobs:
                jobs_data.append({
                    "id": str(job.id),
                    "title": job.title,
                    "client_name": job.client_name,
                    "hourly_rate": str(job.hourly_rate) if job.hourly_rate else "",
                    "client_rating": str(job.client_rating),
                    "status": job.status,
                    "match_score": str(job.match_score) if job.match_score else "",
                    "posted_date": job.posted_date.isoformat() if job.posted_date else "",
                    "job_url": job.job_url or ""
                })
            
            # Export to Google Sheets
            export_result = await google_sheets_service.export_jobs_data(jobs_data)
            
            return {
                "exported": True,
                "jobs_exported": len(jobs_data),
                "spreadsheet_url": export_result["spreadsheet_url"]
            }
            
        except Exception as e:
            logger.warning(f"Failed to export workflow results: {e}")
            return {
                "exported": False,
                "error": str(e)
            }
    
    def _get_default_search_params(self) -> JobSearchParams:
        """Get default search parameters for job discovery"""
        return JobSearchParams(
            keywords=[
                "Salesforce Agentforce",
                "Salesforce AI", 
                "Einstein AI",
                "Salesforce Developer"
            ],
            min_hourly_rate=50.0,
            min_client_rating=4.0,
            payment_verified_only=True
        )
    
    def _calculate_average_quality(self, proposals: List[Proposal]) -> float:
        """Calculate average quality score of proposals"""
        if not proposals:
            return 0.0
        
        quality_scores = [float(p.quality_score) for p in proposals if p.quality_score]
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    def _generate_next_steps_recommendations(
        self,
        qualified_jobs: List[JobModel],
        proposals: List[Proposal]
    ) -> List[str]:
        """Generate recommendations for next steps"""
        recommendations = []
        
        if not qualified_jobs:
            recommendations.append("No qualifying jobs found. Consider adjusting search criteria or quality thresholds.")
        
        if qualified_jobs and not proposals:
            recommendations.append("Qualifying jobs found but no proposals generated. Check proposal generation settings.")
        
        if proposals:
            high_quality_proposals = [p for p in proposals if p.quality_score and p.quality_score >= 0.8]
            if high_quality_proposals:
                recommendations.append(f"{len(high_quality_proposals)} high-quality proposals ready for review and submission.")
            
            low_quality_proposals = [p for p in proposals if p.quality_score and p.quality_score < 0.6]
            if low_quality_proposals:
                recommendations.append(f"{len(low_quality_proposals)} proposals need optimization before submission.")
        
        if len(qualified_jobs) > len(proposals):
            recommendations.append(f"{len(qualified_jobs) - len(proposals)} jobs still need proposals generated.")
        
        return recommendations
    
    def _convert_suggestions_to_instructions(self, suggestions: List[Dict[str, str]]) -> str:
        """Convert optimization suggestions to custom instructions"""
        instructions = []
        
        for suggestion in suggestions:
            if suggestion["priority"] == "high":
                instructions.append(f"Important: {suggestion['suggestion']}")
            else:
                instructions.append(suggestion["suggestion"])
        
        return " ".join(instructions)


# Global service instance
workflow_service = WorkflowService()