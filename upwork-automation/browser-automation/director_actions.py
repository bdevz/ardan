"""
Director Action Implementations for workflow step execution
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from shared.utils import setup_logging
from browserbase_client import BrowserbaseClient
from stagehand_controller import ArdanJobSearchController, ArdanApplicationController

logger = setup_logging("director-actions")


class DirectorActions:
    """Implementation of workflow step actions"""
    
    def __init__(self, browserbase_client: BrowserbaseClient, stagehand_controller):
        self.browserbase_client = browserbase_client
        self.stagehand_controller = stagehand_controller
    
    async def execute_step_action(
        self,
        step,
        session_id: Optional[str],
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific step action"""
        action = step.action
        parameters = step.parameters.copy()
        
        # Add context data
        parameters["input_data"] = input_data
        parameters["step_results"] = step_results
        
        try:
            if action == "create_session_pool":
                return await self._action_create_session_pool(parameters)
            elif action == "search_jobs":
                return await self._action_search_jobs(session_id, parameters)
            elif action == "submit_proposals":
                return await self._action_submit_proposals(session_id, parameters)
            elif action == "merge_job_results":
                return await self._action_merge_job_results(parameters, step_results)
            elif action == "validate_proposals":
                return await self._action_validate_proposals(parameters)
            elif action == "acquire_sessions":
                return await self._action_acquire_sessions(parameters)
            elif action == "verify_submissions":
                return await self._action_verify_submissions(session_id, parameters)
            elif action == "check_profile":
                return await self._action_check_profile(session_id, parameters)
            elif action == "update_availability":
                return await self._action_update_availability(session_id, parameters)
            elif action == "refresh_portfolio":
                return await self._action_refresh_portfolio(session_id, parameters)
            elif action == "update_skills":
                return await self._action_update_skills(session_id, parameters)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Step action failed: {action} - {e}")
            raise
    
    # Action implementations
    async def _action_create_session_pool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pool of browser sessions"""
        pool_size = parameters.get("pool_size", 3)
        session_type = parameters.get("session_type", "general")
        
        sessions = await self.browserbase_client.create_session_pool(pool_size=pool_size)
        
        return {
            "sessions_created": len(sessions),
            "session_ids": sessions,
            "session_type": session_type
        }
    
    async def _action_search_jobs(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search for jobs using Stagehand controller"""
        if not session_id:
            raise ValueError("Session ID required for job search")
        
        keywords = parameters.get("keywords", [])
        sort_order = parameters.get("sort", "newest")
        filters = parameters.get("filters", [])
        
        # Use specialized Ardan job search controller
        job_controller = ArdanJobSearchController()
        
        # Convert filters to dictionary format
        filter_dict = {}
        for filter_name in filters:
            if filter_name == "payment_verified":
                filter_dict["payment_verified"] = True
            elif filter_name == "high_rating":
                filter_dict["min_client_rating"] = 4.0
        
        result = await job_controller.search_jobs(session_id, keywords, filter_dict)
        
        return {
            "success": result.success,
            "jobs_found": len(result.data.get("jobs", [])) if result.success else 0,
            "jobs": result.data.get("jobs", []) if result.success else [],
            "keywords": keywords,
            "sort_order": sort_order,
            "error": result.error_message
        }
    
    async def _action_submit_proposals(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Submit proposals using Stagehand controller"""
        if not session_id:
            raise ValueError("Session ID required for proposal submission")
        
        batch_size = parameters.get("batch_size", 5)
        proposals = parameters.get("proposals", [])
        
        # Use specialized Ardan application controller
        app_controller = ArdanApplicationController()
        
        submitted = 0
        failed = 0
        results = []
        
        for proposal in proposals[:batch_size]:
            try:
                result = await app_controller.submit_application(
                    session_id,
                    proposal["job_url"],
                    proposal["content"],
                    proposal["bid_amount"],
                    proposal.get("attachments", [])
                )
                
                if result.success:
                    submitted += 1
                else:
                    failed += 1
                
                results.append({
                    "job_url": proposal["job_url"],
                    "success": result.success,
                    "error": result.error_message
                })
                
            except Exception as e:
                failed += 1
                results.append({
                    "job_url": proposal.get("job_url", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "submitted": submitted,
            "failed": failed,
            "total_processed": len(results),
            "results": results
        }
    
    async def _action_merge_job_results(
        self,
        parameters: Dict[str, Any],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge and deduplicate job results from multiple search steps"""
        all_jobs = []
        search_steps = ["search_agentforce", "search_ai_einstein", "search_developer"]
        
        for step_id in search_steps:
            if step_id in step_results:
                step_result = step_results[step_id]
                if step_result.get("success") and "jobs" in step_result:
                    all_jobs.extend(step_result["jobs"])
        
        # Deduplicate by job URL or ID
        seen_jobs = set()
        unique_jobs = []
        
        for job in all_jobs:
            job_identifier = job.get("job_url") or job.get("id") or job.get("title")
            if job_identifier and job_identifier not in seen_jobs:
                seen_jobs.add(job_identifier)
                unique_jobs.append(job)
        
        # Sort by relevance/match score if available
        unique_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return {
            "total_jobs_found": len(all_jobs),
            "unique_jobs": len(unique_jobs),
            "jobs": unique_jobs,
            "duplicates_removed": len(all_jobs) - len(unique_jobs)
        }
    
    async def _action_validate_proposals(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate proposal data before submission"""
        proposals = parameters.get("proposals", [])
        
        valid_proposals = []
        invalid_proposals = []
        
        for proposal in proposals:
            errors = []
            
            # Check required fields
            if not proposal.get("job_url"):
                errors.append("Missing job URL")
            if not proposal.get("content"):
                errors.append("Missing proposal content")
            if not proposal.get("bid_amount"):
                errors.append("Missing bid amount")
            
            # Validate content length
            content = proposal.get("content", "")
            if len(content) < 100:
                errors.append("Proposal content too short (minimum 100 characters)")
            if len(content) > 5000:
                errors.append("Proposal content too long (maximum 5000 characters)")
            
            # Validate bid amount
            try:
                bid_amount = float(proposal.get("bid_amount", 0))
                if bid_amount < 10:
                    errors.append("Bid amount too low (minimum $10/hour)")
                if bid_amount > 200:
                    errors.append("Bid amount too high (maximum $200/hour)")
            except (ValueError, TypeError):
                errors.append("Invalid bid amount format")
            
            if errors:
                invalid_proposals.append({
                    "proposal": proposal,
                    "errors": errors
                })
            else:
                valid_proposals.append(proposal)
        
        return {
            "valid_count": len(valid_proposals),
            "invalid_count": len(invalid_proposals),
            "valid_proposals": valid_proposals,
            "invalid_proposals": invalid_proposals
        }
    
    async def _action_acquire_sessions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Acquire additional browser sessions"""
        session_type = parameters.get("session_type", "general")
        count = parameters.get("count", 1)
        
        sessions = []
        for i in range(count):
            try:
                session_id = await self.browserbase_client.create_session({
                    "name": f"{session_type}_session_{i}"
                })
                sessions.append(session_id)
            except Exception as e:
                logger.error(f"Failed to acquire session {i}: {e}")
        
        return {
            "requested": count,
            "acquired": len(sessions),
            "session_ids": sessions
        }
    
    async def _action_verify_submissions(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that proposals were submitted successfully"""
        if not session_id:
            raise ValueError("Session ID required for verification")
        
        app_controller = ArdanApplicationController()
        verification_result = await app_controller.verify_submission(session_id)
        
        return {
            "verification_success": verification_result.success,
            "confirmation_data": verification_result.data,
            "error": verification_result.error_message
        }
    
    async def _action_check_profile(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check Ardan profile status"""
        if not session_id:
            raise ValueError("Session ID required for profile check")
        
        # Navigate to profile page and extract status
        nav_result = await self.stagehand_controller.intelligent_navigate(
            session_id,
            "Ardan profile page",
            context={"target": "profile_overview"}
        )
        
        if not nav_result.success:
            return {
                "success": False,
                "error": f"Failed to navigate to profile: {nav_result.error_message}"
            }
        
        # Extract profile information
        from stagehand_controller import ExtractionType
        
        profile_result = await self.stagehand_controller.extract_content(
            session_id,
            "Extract profile status including: availability, profile completeness, recent activity, earnings",
            ExtractionType.PAGE_CONTENT
        )
        
        return {
            "success": profile_result.success,
            "profile_data": profile_result.data,
            "error": profile_result.error_message
        }
    
    async def _action_update_availability(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update availability status on profile"""
        if not session_id:
            raise ValueError("Session ID required for availability update")
        
        status = parameters.get("status", "available")
        
        # Navigate to availability settings
        nav_result = await self.stagehand_controller.intelligent_navigate(
            session_id,
            "profile availability settings",
            context={"target": "availability_settings"}
        )
        
        if not nav_result.success:
            return {
                "success": False,
                "error": f"Failed to navigate to availability settings: {nav_result.error_message}"
            }
        
        # Update availability
        form_result = await self.stagehand_controller.interact_with_form(
            session_id,
            {"availability_status": status},
            submit=True
        )
        
        return {
            "success": form_result.success,
            "status_updated": status,
            "error": form_result.error_message
        }
    
    async def _action_refresh_portfolio(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh portfolio items"""
        if not session_id:
            raise ValueError("Session ID required for portfolio refresh")
        
        # Navigate to portfolio section
        nav_result = await self.stagehand_controller.intelligent_navigate(
            session_id,
            "portfolio section",
            context={"target": "portfolio_management"}
        )
        
        if not nav_result.success:
            return {
                "success": False,
                "error": f"Failed to navigate to portfolio: {nav_result.error_message}"
            }
        
        # Extract current portfolio items
        from stagehand_controller import ExtractionType
        
        portfolio_result = await self.stagehand_controller.extract_content(
            session_id,
            "Extract portfolio items including: titles, descriptions, technologies, last updated dates",
            ExtractionType.PAGE_CONTENT
        )
        
        return {
            "success": portfolio_result.success,
            "portfolio_items": portfolio_result.data,
            "error": portfolio_result.error_message
        }
    
    async def _action_update_skills(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update skills and certifications"""
        if not session_id:
            raise ValueError("Session ID required for skills update")
        
        # Navigate to skills section
        nav_result = await self.stagehand_controller.intelligent_navigate(
            session_id,
            "skills and certifications section",
            context={"target": "skills_management"}
        )
        
        if not nav_result.success:
            return {
                "success": False,
                "error": f"Failed to navigate to skills section: {nav_result.error_message}"
            }
        
        # Extract current skills
        from stagehand_controller import ExtractionType
        
        skills_result = await self.stagehand_controller.extract_content(
            session_id,
            "Extract current skills, certifications, and test scores",
            ExtractionType.PAGE_CONTENT
        )
        
        return {
            "success": skills_result.success,
            "skills_data": skills_result.data,
            "error": skills_result.error_message
        }