"""
Job Discovery Worker for background job processing
"""
import logging
from typing import Dict, Any

from workers.base_worker import BaseWorker
from services.job_service import job_service
from services.browser_service import browser_service

logger = logging.getLogger(__name__)


class JobDiscoveryWorker(BaseWorker):
    """Worker for processing job discovery tasks"""
    
    def __init__(self, concurrency: int = 2):
        super().__init__(
            worker_name="job_discovery",
            task_types=["job_discovery", "job_search", "job_filtering"],
            concurrency=concurrency
        )
    
    async def process_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process job discovery tasks"""
        logger.info(f"Processing {task_type} task {task_id}")
        
        if task_type == "job_discovery":
            return await self._process_job_discovery(task_data)
        elif task_type == "job_search":
            return await self._process_job_search(task_data)
        elif task_type == "job_filtering":
            return await self._process_job_filtering(task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _process_job_discovery(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process full job discovery workflow"""
        search_params = task_data.get("search_params", {})
        session_pool_size = task_data.get("session_pool_size", 3)
        
        try:
            # Create browser session pool
            sessions = await browser_service.create_session_pool(session_pool_size)
            
            # Execute job search across multiple sessions
            all_jobs = []
            search_strategies = [
                {
                    "keywords": ["Salesforce Agentforce"],
                    "sort": "newest",
                    "filters": {"payment_verified": True, "min_rating": 4.0}
                },
                {
                    "keywords": ["Salesforce AI", "Einstein"],
                    "sort": "best_match",
                    "filters": {"payment_verified": True, "min_hourly_rate": 50}
                },
                {
                    "keywords": ["Salesforce Developer"],
                    "sort": "newest",
                    "filters": {"payment_verified": True, "min_rating": 4.0, "min_hourly_rate": 50}
                }
            ]
            
            # Execute searches in parallel
            for i, strategy in enumerate(search_strategies[:len(sessions)]):
                session_id = sessions[i]
                jobs = await self._execute_search_strategy(session_id, strategy)
                all_jobs.extend(jobs)
            
            # Filter and rank jobs
            filtered_jobs = await job_service.filter_and_rank_jobs(all_jobs)
            
            # Store jobs in database
            stored_jobs = []
            for job_data in filtered_jobs:
                job = await job_service.create_job(job_data)
                stored_jobs.append(str(job.id))
            
            return {
                "total_jobs_found": len(all_jobs),
                "filtered_jobs": len(filtered_jobs),
                "stored_jobs": stored_jobs,
                "search_strategies_used": len(search_strategies)
            }
            
        except Exception as e:
            logger.error(f"Job discovery failed: {str(e)}")
            raise
    
    async def _execute_search_strategy(self, session_id: str, strategy: Dict[str, Any]) -> list:
        """Execute a specific search strategy"""
        try:
            # Use browser service to search for jobs
            search_results = await browser_service.search_jobs(
                session_id=session_id,
                keywords=strategy["keywords"],
                sort_by=strategy.get("sort", "newest"),
                filters=strategy.get("filters", {})
            )
            
            # Extract detailed job information
            detailed_jobs = []
            for job_preview in search_results:
                try:
                    job_details = await browser_service.extract_job_details(
                        session_id=session_id,
                        job_url=job_preview["url"]
                    )
                    detailed_jobs.append(job_details)
                except Exception as e:
                    logger.warning(f"Failed to extract details for job {job_preview.get('id', 'unknown')}: {str(e)}")
                    continue
            
            return detailed_jobs
            
        except Exception as e:
            logger.error(f"Search strategy failed: {str(e)}")
            return []
    
    async def _process_job_search(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process simple job search task"""
        keywords = task_data.get("keywords", [])
        filters = task_data.get("filters", {})
        
        try:
            # Get or create browser session
            session_id = await browser_service.get_session("job_discovery")
            
            # Execute search
            search_results = await browser_service.search_jobs(
                session_id=session_id,
                keywords=keywords,
                filters=filters
            )
            
            return {
                "jobs_found": len(search_results),
                "search_keywords": keywords,
                "filters_applied": filters
            }
            
        except Exception as e:
            logger.error(f"Job search failed: {str(e)}")
            raise
    
    async def _process_job_filtering(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process job filtering task"""
        job_ids = task_data.get("job_ids", [])
        filter_criteria = task_data.get("filter_criteria", {})
        
        try:
            # Get jobs from database
            jobs = await job_service.get_jobs_by_ids(job_ids)
            
            # Apply filtering
            filtered_jobs = await job_service.apply_filters(jobs, filter_criteria)
            
            # Update job statuses
            for job in filtered_jobs:
                await job_service.update_job_status(job.id, "filtered")
            
            return {
                "total_jobs": len(jobs),
                "filtered_jobs": len(filtered_jobs),
                "filter_criteria": filter_criteria
            }
            
        except Exception as e:
            logger.error(f"Job filtering failed: {str(e)}")
            raise


# Create worker instance
job_discovery_worker = JobDiscoveryWorker()