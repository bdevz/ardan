"""
MCP-enhanced Director actions for intelligent workflow execution
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from mcp_integration import MCPIntegration, MCPEnhancedResult
from director_actions import DirectorActions
from shared.config import settings
from shared.utils import setup_logging, retry_async

logger = setup_logging("mcp-director-actions")


class MCPDirectorActions(DirectorActions):
    """Enhanced Director actions with MCP integration for intelligent automation"""
    
    def __init__(self, browserbase_client, stagehand_controller, mcp_integration: Optional[MCPIntegration] = None):
        super().__init__(browserbase_client, stagehand_controller)
        self.mcp_integration = mcp_integration or MCPIntegration(
            stagehand_controller=stagehand_controller,
            browserbase_client=browserbase_client
        )
        
        # MCP-specific state
        self.workflow_contexts: Dict[str, Dict[str, Any]] = {}
        self.adaptive_strategies: Dict[str, Any] = {}
    
    async def initialize(self):
        """Initialize MCP-enhanced Director actions"""
        logger.info("Initializing MCP-enhanced Director actions...")
        
        try:
            await super().initialize()
            await self.mcp_integration.initialize()
            
            logger.info("MCP-enhanced Director actions initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP-enhanced Director actions: {e}")
            raise
    
    async def execute_step_action(
        self,
        step,
        session_id: Optional[str],
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute step action with MCP enhancement"""
        try:
            # Store workflow context for MCP analysis
            workflow_context = {
                "step_id": step.id,
                "step_name": step.name,
                "action": step.action,
                "parameters": step.parameters,
                "input_data": input_data,
                "previous_results": step_results
            }
            
            if session_id:
                self.workflow_contexts[session_id] = workflow_context
            
            # Execute action with MCP enhancement
            if step.action == "search_jobs":
                return await self._mcp_enhanced_search_jobs(step, session_id, input_data, step_results)
            
            elif step.action == "extract_job_details":
                return await self._mcp_enhanced_extract_job_details(step, session_id, input_data, step_results)
            
            elif step.action == "submit_proposals":
                return await self._mcp_enhanced_submit_proposals(step, session_id, input_data, step_results)
            
            elif step.action == "validate_proposals":
                return await self._mcp_enhanced_validate_proposals(step, session_id, input_data, step_results)
            
            elif step.action == "merge_job_results":
                return await self._mcp_enhanced_merge_results(step, session_id, input_data, step_results)
            
            else:
                # Fallback to parent implementation with MCP context awareness
                return await self._execute_with_mcp_context(step, session_id, input_data, step_results)
        
        except Exception as e:
            logger.error(f"MCP-enhanced step execution failed: {step.action} - {e}")
            
            # Attempt error recovery with MCP
            if session_id:
                recovery_result = await self._attempt_mcp_error_recovery(
                    session_id, step, str(e), input_data, step_results
                )
                if recovery_result.get("recovery_successful"):
                    return recovery_result["result"]
            
            # Fallback to parent implementation
            return await super().execute_step_action(step, session_id, input_data, step_results)
    
    async def _mcp_enhanced_search_jobs(
        self,
        step,
        session_id: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced job search with MCP context analysis"""
        try:
            logger.info(f"Executing MCP-enhanced job search for session {session_id}")
            
            # Extract search parameters
            keywords = step.parameters.get("keywords", ["Salesforce Agentforce"])
            sort_order = step.parameters.get("sort", "newest")
            filters = step.parameters.get("filters", [])
            
            # Navigate to job search with MCP enhancement
            nav_result = await self.mcp_integration.enhanced_navigate(
                session_id=session_id,
                target_description="Ardan job search page",
                automation_goal="job_search",
                context_data={"keywords": keywords, "sort": sort_order}
            )
            
            if not nav_result.original_result.success:
                return {
                    "success": False,
                    "error": f"Navigation failed: {nav_result.original_result.error_message}",
                    "mcp_context": nav_result.mcp_context
                }
            
            # Perform search with context-aware form interaction
            search_data = {
                "search_query": " ".join(keywords),
                "sort_order": sort_order
            }
            
            # Add filters to search data
            for filter_name in filters:
                search_data[f"filter_{filter_name}"] = True
            
            form_result = await self.mcp_integration.enhanced_form_interaction(
                session_id=session_id,
                form_data=search_data,
                submit=True,
                automation_goal="perform_job_search"
            )
            
            if not form_result.original_result.success:
                return {
                    "success": False,
                    "error": f"Search form interaction failed: {form_result.original_result.error_message}",
                    "mcp_context": form_result.mcp_context
                }
            
            # Wait for results with dynamic content handling
            await asyncio.sleep(3)
            
            # Extract job listings with MCP enhancement
            extraction_result = await self.mcp_integration.enhanced_extract(
                session_id=session_id,
                extraction_prompt="""
                Extract all job listings from this search results page. For each job, extract:
                - title: Job title
                - client_name: Client name
                - budget: Budget range or hourly rate
                - description: Job description preview
                - posted_time: When the job was posted
                - proposals: Number of proposals submitted
                - client_rating: Client rating (stars)
                - payment_verified: Whether client payment is verified
                - job_url: Direct link to the job posting
                - skills_required: List of required skills mentioned
                """,
                extraction_type="job_listings",
                automation_goal="extract_job_search_results"
            )
            
            if not extraction_result.original_result.success:
                return {
                    "success": False,
                    "error": f"Job extraction failed: {extraction_result.original_result.error_message}",
                    "mcp_context": extraction_result.mcp_context
                }
            
            # Process and enhance extracted data with MCP insights
            jobs_data = extraction_result.original_result.data
            enhanced_jobs = await self._enhance_job_data_with_mcp(
                jobs_data, extraction_result.mcp_context, keywords
            )
            
            return {
                "success": True,
                "jobs_found": len(enhanced_jobs),
                "jobs_data": enhanced_jobs,
                "search_parameters": {
                    "keywords": keywords,
                    "sort": sort_order,
                    "filters": filters
                },
                "mcp_insights": {
                    "context": extraction_result.mcp_context,
                    "strategy_confidence": extraction_result.applied_strategy.confidence_score if extraction_result.applied_strategy else 0.0,
                    "extraction_confidence": extraction_result.original_result.confidence_score
                }
            }
            
        except Exception as e:
            logger.error(f"MCP-enhanced job search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_attempted": True
            }
    
    async def _mcp_enhanced_extract_job_details(
        self,
        step,
        session_id: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced job details extraction with MCP context analysis"""
        try:
            job_url = step.parameters.get("job_url")
            if not job_url:
                return {"success": False, "error": "No job URL provided"}
            
            logger.info(f"Extracting job details with MCP enhancement: {job_url}")
            
            # Navigate to job details page
            nav_result = await self.mcp_integration.enhanced_navigate(
                session_id=session_id,
                target_description=job_url,
                automation_goal="view_job_details"
            )
            
            if not nav_result.original_result.success:
                return {
                    "success": False,
                    "error": f"Failed to navigate to job details: {nav_result.original_result.error_message}"
                }
            
            # Extract comprehensive job details
            extraction_result = await self.mcp_integration.enhanced_extract(
                session_id=session_id,
                extraction_prompt="""
                Extract complete job information from this job details page:
                - title: Full job title
                - description: Complete job description
                - budget_type: "fixed" or "hourly"
                - budget_min: Minimum budget/rate
                - budget_max: Maximum budget/rate
                - client_info: {name, rating, hire_rate, payment_verified, location, member_since}
                - skills_required: List of all required skills
                - job_requirements: Specific requirements and qualifications
                - timeline: Project timeline or expected duration
                - application_deadline: Application deadline if specified
                - similar_jobs_count: Number of similar jobs posted by this client
                - job_category: Job category/type
                - experience_level: Required experience level
                - project_type: Type of project (ongoing, one-time, etc.)
                """,
                extraction_type="job_details",
                automation_goal="extract_comprehensive_job_info"
            )
            
            if not extraction_result.original_result.success:
                return {
                    "success": False,
                    "error": f"Job details extraction failed: {extraction_result.original_result.error_message}"
                }
            
            # Enhance job details with MCP analysis
            job_details = extraction_result.original_result.data
            enhanced_details = await self._analyze_job_fit_with_mcp(
                job_details, extraction_result.mcp_context
            )
            
            return {
                "success": True,
                "job_details": enhanced_details,
                "mcp_analysis": {
                    "page_context": extraction_result.mcp_context,
                    "extraction_confidence": extraction_result.original_result.confidence_score,
                    "fit_analysis": enhanced_details.get("mcp_fit_analysis", {})
                }
            }
            
        except Exception as e:
            logger.error(f"MCP-enhanced job details extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _mcp_enhanced_submit_proposals(
        self,
        step,
        session_id: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced proposal submission with MCP context analysis"""
        try:
            proposals_to_submit = step.parameters.get("proposals", [])
            batch_size = step.parameters.get("batch_size", 5)
            
            if not proposals_to_submit:
                return {"success": False, "error": "No proposals to submit"}
            
            logger.info(f"Submitting {len(proposals_to_submit)} proposals with MCP enhancement")
            
            submission_results = []
            
            for i, proposal in enumerate(proposals_to_submit[:batch_size]):
                try:
                    # Navigate to job application page
                    job_url = proposal.get("job_url")
                    nav_result = await self.mcp_integration.enhanced_navigate(
                        session_id=session_id,
                        target_description=job_url,
                        automation_goal="apply_to_job"
                    )
                    
                    if not nav_result.original_result.success:
                        submission_results.append({
                            "proposal_id": proposal.get("id"),
                            "success": False,
                            "error": f"Navigation failed: {nav_result.original_result.error_message}"
                        })
                        continue
                    
                    # Click apply button with MCP context awareness
                    stagehand = await self.stagehand_controller.get_stagehand(session_id)
                    await stagehand.act("click the apply button or submit proposal button")
                    
                    # Wait for application form
                    await asyncio.sleep(2)
                    
                    # Fill application form with MCP enhancement
                    form_data = {
                        "cover_letter": proposal.get("content", ""),
                        "bid_amount": str(proposal.get("bid_amount", 0)),
                        "attachments": proposal.get("attachments", [])
                    }
                    
                    form_result = await self.mcp_integration.enhanced_form_interaction(
                        session_id=session_id,
                        form_data=form_data,
                        submit=True,
                        automation_goal="submit_job_application"
                    )
                    
                    # Verify submission
                    verification_result = await self._verify_submission_with_mcp(session_id)
                    
                    submission_results.append({
                        "proposal_id": proposal.get("id"),
                        "success": form_result.original_result.success and verification_result.get("success", False),
                        "form_result": form_result.original_result.success,
                        "verification": verification_result,
                        "mcp_context": form_result.mcp_context
                    })
                    
                    # Add delay between submissions
                    if i < len(proposals_to_submit) - 1:
                        await asyncio.sleep(5)
                
                except Exception as e:
                    logger.error(f"Proposal submission failed: {e}")
                    submission_results.append({
                        "proposal_id": proposal.get("id"),
                        "success": False,
                        "error": str(e)
                    })
            
            successful_submissions = sum(1 for r in submission_results if r["success"])
            
            return {
                "success": successful_submissions > 0,
                "total_proposals": len(proposals_to_submit),
                "successful_submissions": successful_submissions,
                "failed_submissions": len(submission_results) - successful_submissions,
                "results": submission_results
            }
            
        except Exception as e:
            logger.error(f"MCP-enhanced proposal submission failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _mcp_enhanced_validate_proposals(
        self,
        step,
        session_id: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced proposal validation with MCP analysis"""
        try:
            proposals = input_data.get("proposals", []) if input_data else []
            
            if not proposals:
                return {"success": False, "error": "No proposals to validate"}
            
            logger.info(f"Validating {len(proposals)} proposals with MCP enhancement")
            
            validation_results = []
            
            for proposal in proposals:
                # Basic validation
                basic_validation = {
                    "has_content": bool(proposal.get("content")),
                    "has_bid_amount": bool(proposal.get("bid_amount")),
                    "has_job_url": bool(proposal.get("job_url")),
                    "content_length": len(proposal.get("content", "")),
                    "bid_amount_valid": self._validate_bid_amount(proposal.get("bid_amount"))
                }
                
                # MCP-enhanced validation using AI analysis
                mcp_validation = await self._validate_proposal_with_mcp(proposal)
                
                # Combine validations
                is_valid = (
                    basic_validation["has_content"] and
                    basic_validation["has_bid_amount"] and
                    basic_validation["has_job_url"] and
                    basic_validation["content_length"] >= 100 and
                    basic_validation["bid_amount_valid"] and
                    mcp_validation.get("quality_score", 0) >= 0.6
                )
                
                validation_results.append({
                    "proposal_id": proposal.get("id"),
                    "valid": is_valid,
                    "basic_validation": basic_validation,
                    "mcp_validation": mcp_validation,
                    "issues": self._identify_validation_issues(basic_validation, mcp_validation)
                })
            
            valid_proposals = [r for r in validation_results if r["valid"]]
            
            return {
                "success": True,
                "total_proposals": len(proposals),
                "valid_proposals": len(valid_proposals),
                "invalid_proposals": len(proposals) - len(valid_proposals),
                "validation_results": validation_results
            }
            
        except Exception as e:
            logger.error(f"MCP-enhanced proposal validation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _mcp_enhanced_merge_results(
        self,
        step,
        session_id: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced result merging with MCP deduplication and ranking"""
        try:
            # Collect job results from previous steps
            all_jobs = []
            
            for step_id, result in step_results.items():
                if isinstance(result, dict) and result.get("jobs_data"):
                    jobs_data = result["jobs_data"]
                    if isinstance(jobs_data, list):
                        all_jobs.extend(jobs_data)
            
            if not all_jobs:
                return {"success": False, "error": "No job results to merge"}
            
            logger.info(f"Merging {len(all_jobs)} job results with MCP enhancement")
            
            # MCP-enhanced deduplication
            deduplicated_jobs = await self._deduplicate_jobs_with_mcp(all_jobs)
            
            # MCP-enhanced ranking and scoring
            ranked_jobs = await self._rank_jobs_with_mcp(deduplicated_jobs)
            
            # Apply filtering based on MCP analysis
            filtered_jobs = await self._filter_jobs_with_mcp(ranked_jobs)
            
            return {
                "success": True,
                "original_count": len(all_jobs),
                "deduplicated_count": len(deduplicated_jobs),
                "final_count": len(filtered_jobs),
                "jobs": filtered_jobs,
                "mcp_analysis": {
                    "deduplication_ratio": len(deduplicated_jobs) / len(all_jobs) if all_jobs else 0,
                    "filter_ratio": len(filtered_jobs) / len(deduplicated_jobs) if deduplicated_jobs else 0,
                    "average_match_score": sum(job.get("match_score", 0) for job in filtered_jobs) / len(filtered_jobs) if filtered_jobs else 0
                }
            }
            
        except Exception as e:
            logger.error(f"MCP-enhanced result merging failed: {e}")
            return {"success": False, "error": str(e)}
    
    # Helper methods for MCP enhancement
    async def _enhance_job_data_with_mcp(
        self,
        jobs_data: List[Dict[str, Any]],
        context: Optional[Any],
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Enhance job data with MCP analysis"""
        enhanced_jobs = []
        
        for job in jobs_data:
            try:
                # Calculate match score based on keywords and context
                match_score = await self._calculate_job_match_score(job, keywords, context)
                
                # Add MCP enhancements
                job["match_score"] = match_score
                job["mcp_analysis"] = {
                    "keyword_matches": self._count_keyword_matches(job, keywords),
                    "context_relevance": 0.8,  # Placeholder
                    "extraction_confidence": 0.9  # Placeholder
                }
                
                enhanced_jobs.append(job)
                
            except Exception as e:
                logger.warning(f"Failed to enhance job data: {e}")
                enhanced_jobs.append(job)
        
        return enhanced_jobs
    
    async def _analyze_job_fit_with_mcp(
        self,
        job_details: Dict[str, Any],
        context: Optional[Any]
    ) -> Dict[str, Any]:
        """Analyze job fit using MCP"""
        try:
            # Basic fit analysis
            fit_score = 0.7  # Placeholder
            
            job_details["mcp_fit_analysis"] = {
                "overall_fit_score": fit_score,
                "skill_match": 0.8,
                "budget_match": 0.9,
                "client_quality": 0.7,
                "project_complexity": 0.6,
                "success_probability": fit_score * 0.9
            }
            
            return job_details
            
        except Exception as e:
            logger.warning(f"MCP job fit analysis failed: {e}")
            return job_details
    
    async def _verify_submission_with_mcp(self, session_id: str) -> Dict[str, Any]:
        """Verify proposal submission with MCP context analysis"""
        try:
            # Wait for confirmation
            await asyncio.sleep(3)
            
            # Extract confirmation with MCP
            verification_result = await self.mcp_integration.enhanced_extract(
                session_id=session_id,
                extraction_prompt="""
                Check if the job application was submitted successfully. Look for:
                - Success confirmation message
                - Application ID or reference number
                - Confirmation that proposal was sent
                - Any error messages or warnings
                
                Return:
                - success: true/false
                - confirmation_message: The confirmation text
                - application_id: Application reference if available
                - errors: Any error messages found
                """,
                extraction_type="confirmation",
                automation_goal="verify_application_submission"
            )
            
            return {
                "success": verification_result.original_result.success,
                "verification_data": verification_result.original_result.data,
                "mcp_context": verification_result.mcp_context
            }
            
        except Exception as e:
            logger.error(f"MCP submission verification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_proposal_with_mcp(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Validate proposal using MCP AI analysis"""
        try:
            # Mock MCP validation - in real implementation, this would use AI
            content = proposal.get("content", "")
            
            quality_score = min(len(content) / 500.0, 1.0)  # Simple length-based scoring
            
            return {
                "quality_score": quality_score,
                "readability_score": 0.8,
                "relevance_score": 0.7,
                "professionalism_score": 0.9,
                "suggestions": []
            }
            
        except Exception as e:
            logger.warning(f"MCP proposal validation failed: {e}")
            return {"quality_score": 0.5}
    
    def _validate_bid_amount(self, bid_amount: Any) -> bool:
        """Validate bid amount"""
        try:
            amount = float(bid_amount)
            return 10.0 <= amount <= 200.0  # Reasonable hourly rate range
        except (ValueError, TypeError):
            return False
    
    def _identify_validation_issues(
        self,
        basic_validation: Dict[str, Any],
        mcp_validation: Dict[str, Any]
    ) -> List[str]:
        """Identify validation issues"""
        issues = []
        
        if not basic_validation["has_content"]:
            issues.append("Missing proposal content")
        
        if not basic_validation["has_bid_amount"]:
            issues.append("Missing bid amount")
        
        if basic_validation["content_length"] < 100:
            issues.append("Proposal content too short")
        
        if not basic_validation["bid_amount_valid"]:
            issues.append("Invalid bid amount")
        
        if mcp_validation.get("quality_score", 0) < 0.6:
            issues.append("Low quality score from MCP analysis")
        
        return issues
    
    async def _deduplicate_jobs_with_mcp(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate jobs using MCP analysis"""
        # Simple deduplication by title and client
        seen = set()
        deduplicated = []
        
        for job in jobs:
            key = f"{job.get('title', '')}:{job.get('client_name', '')}"
            if key not in seen:
                seen.add(key)
                deduplicated.append(job)
        
        return deduplicated
    
    async def _rank_jobs_with_mcp(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank jobs using MCP analysis"""
        # Sort by match score (highest first)
        return sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)
    
    async def _filter_jobs_with_mcp(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter jobs using MCP analysis"""
        # Filter by minimum match score
        return [job for job in jobs if job.get("match_score", 0) >= 0.5]
    
    async def _calculate_job_match_score(
        self,
        job: Dict[str, Any],
        keywords: List[str],
        context: Optional[Any]
    ) -> float:
        """Calculate job match score"""
        score = 0.0
        
        # Keyword matching
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()
        
        keyword_matches = 0
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in description:
                keyword_matches += 1
        
        score += (keyword_matches / len(keywords)) * 0.4
        
        # Budget scoring
        budget = job.get("budget", "")
        if "$50" in str(budget) or "50" in str(budget):
            score += 0.3
        
        # Client rating
        client_rating = job.get("client_rating", 0)
        if isinstance(client_rating, (int, float)) and client_rating >= 4.0:
            score += 0.3
        
        return min(score, 1.0)
    
    def _count_keyword_matches(self, job: Dict[str, Any], keywords: List[str]) -> int:
        """Count keyword matches in job"""
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()
        
        matches = 0
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in description:
                matches += 1
        
        return matches
    
    async def _execute_with_mcp_context(
        self,
        step,
        session_id: Optional[str],
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute step with MCP context awareness"""
        try:
            # Get enhanced session state if available
            if session_id:
                session_state = await self.mcp_integration.get_enhanced_session_state(session_id)
                logger.debug(f"Executing step with MCP context: {step.action}")
            
            # Execute parent implementation
            result = await super().execute_step_action(step, session_id, input_data, step_results)
            
            # Enhance result with MCP insights if available
            if session_id and isinstance(result, dict):
                result["mcp_enhanced"] = True
                result["session_context"] = session_state.get("current_strategy") if session_id else None
            
            return result
            
        except Exception as e:
            logger.error(f"MCP context execution failed: {e}")
            return await super().execute_step_action(step, session_id, input_data, step_results)
    
    async def _attempt_mcp_error_recovery(
        self,
        session_id: str,
        step,
        error_message: str,
        input_data: Optional[Dict[str, Any]],
        step_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt error recovery using MCP"""
        try:
            error_context = {
                "error_type": "step_execution_error",
                "error_message": error_message,
                "failed_action": step.action,
                "step_parameters": step.parameters
            }
            
            recovery_result = await self.mcp_integration.context_aware_error_recovery(
                session_id, error_context
            )
            
            if recovery_result.get("recovery_successful"):
                # Retry step execution after recovery
                retry_result = await super().execute_step_action(step, session_id, input_data, step_results)
                return {
                    "recovery_successful": True,
                    "result": retry_result,
                    "recovery_details": recovery_result
                }
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"MCP error recovery failed: {e}")
            return {"recovery_successful": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up MCP Director actions"""
        logger.info("Cleaning up MCP Director actions...")
        
        try:
            await self.mcp_integration.cleanup()
            await super().cleanup()
            
            # Clear MCP-specific state
            self.workflow_contexts.clear()
            self.adaptive_strategies.clear()
            
            logger.info("MCP Director actions cleanup complete")
            
        except Exception as e:
            logger.error(f"MCP Director actions cleanup failed: {e}")