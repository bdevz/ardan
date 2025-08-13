"""
Core Job Discovery Service for automated Upwork job search and extraction
"""
import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from shared.models import Job, JobStatus, JobType, JobSearchParams
from shared.config import settings
from shared.utils import setup_logging, retry_async
from stagehand_controller import StagehandController, ExtractionResult, ExtractionType
from mcp_client import MCPClient
from director import DirectorOrchestrator
from browserbase_client import BrowserbaseClient

logger = setup_logging("job-discovery-service")


class SearchStrategy(Enum):
    """Job search strategies"""
    KEYWORD_BASED = "keyword_based"
    CATEGORY_BASED = "category_based"
    CLIENT_BASED = "client_based"
    HYBRID = "hybrid"


class FilterCriteria(Enum):
    """Job filtering criteria"""
    HOURLY_RATE = "hourly_rate"
    CLIENT_RATING = "client_rating"
    PAYMENT_VERIFIED = "payment_verified"
    HIRE_RATE = "hire_rate"
    SKILLS_MATCH = "skills_match"
    DESCRIPTION_RELEVANCE = "description_relevance"


@dataclass
class JobDiscoveryResult:
    """Result of job discovery operation"""
    jobs_found: List[Job]
    total_processed: int
    duplicates_removed: int
    filtered_out: int
    search_duration: float
    search_strategy: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class DeduplicationResult:
    """Result of job deduplication"""
    original_count: int
    deduplicated_count: int
    duplicates_found: int
    duplicate_pairs: List[Tuple[str, str]]


class JobDiscoveryService:
    """Core service for automated job discovery using AI-powered browser automation"""
    
    def __init__(
        self,
        browserbase_client: Optional[BrowserbaseClient] = None,
        stagehand_controller: Optional[StagehandController] = None,
        mcp_client: Optional[MCPClient] = None,
        director: Optional[DirectorOrchestrator] = None
    ):
        # Initialize components
        self.browserbase_client = browserbase_client or BrowserbaseClient()
        self.stagehand_controller = stagehand_controller or UpworkJobSearchController()
        self.mcp_client = mcp_client or MCPClient()
        self.director = director or DirectorOrchestrator()
        
        # Job storage and caching
        self.discovered_jobs: Dict[str, Job] = {}
        self.job_content_hashes: Set[str] = set()
        self.upwork_job_ids: Set[str] = set()
        
        # Search configuration
        self.default_keywords = [
            "Salesforce Agentforce",
            "Salesforce AI", 
            "Einstein AI",
            "Salesforce Developer",
            "Agentforce Developer"
        ]
        
        # Filtering and ranking configuration
        self.min_hourly_rate = Decimal("50.0")
        self.min_client_rating = Decimal("4.0")
        self.min_hire_rate = Decimal("0.5")
        
        # Historical success tracking for ranking
        self.success_patterns: Dict[str, float] = {}
        self.keyword_performance: Dict[str, float] = {}
        
    async def initialize(self):
        """Initialize the job discovery service"""
        logger.info("Initializing Job Discovery Service...")
        
        try:
            # Initialize MCP client for AI-powered filtering
            await self.mcp_client.initialize()
            
            # Load historical success patterns
            await self._load_success_patterns()
            
            logger.info("Job Discovery Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Job Discovery Service: {e}")
            raise
    
    @retry_async(max_retries=3, delay=5.0)
    async def discover_jobs(
        self,
        search_params: Optional[JobSearchParams] = None,
        max_jobs: int = 50,
        search_strategy: SearchStrategy = SearchStrategy.HYBRID
    ) -> JobDiscoveryResult:
        """
        Main job discovery method using intelligent browser automation
        
        Args:
            search_params: Search parameters and filters
            max_jobs: Maximum number of jobs to discover
            search_strategy: Strategy to use for job search
            
        Returns:
            JobDiscoveryResult with discovered jobs and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting job discovery with strategy: {search_strategy.value}")
            
            # Use default search params if none provided
            if search_params is None:
                search_params = JobSearchParams(
                    keywords=self.default_keywords,
                    min_hourly_rate=self.min_hourly_rate,
                    min_client_rating=self.min_client_rating,
                    payment_verified_only=True
                )
            
            # Create browser session pool for parallel searching
            session_pool = await self._create_search_session_pool(size=3)
            
            # Execute search based on strategy
            raw_jobs = []
            if search_strategy == SearchStrategy.KEYWORD_BASED:
                raw_jobs = await self._keyword_based_search(session_pool, search_params, max_jobs)
            elif search_strategy == SearchStrategy.CATEGORY_BASED:
                raw_jobs = await self._category_based_search(session_pool, search_params, max_jobs)
            elif search_strategy == SearchStrategy.CLIENT_BASED:
                raw_jobs = await self._client_based_search(session_pool, search_params, max_jobs)
            else:  # HYBRID
                raw_jobs = await self._hybrid_search(session_pool, search_params, max_jobs)
            
            total_processed = len(raw_jobs)
            logger.info(f"Found {total_processed} raw jobs from search")
            
            # Deduplicate jobs
            dedup_result = await self._deduplicate_jobs(raw_jobs)
            deduplicated_jobs = dedup_result.deduplicated_count
            
            # Apply AI-powered filtering
            filtered_jobs = await self._ai_powered_filtering(
                [job for job in raw_jobs if job.id not in [dup[1] for dup in dedup_result.duplicate_pairs]]
            )
            
            filtered_out = deduplicated_jobs - len(filtered_jobs)
            
            # Rank and score jobs
            ranked_jobs = await self._rank_and_score_jobs(filtered_jobs)
            
            # Clean up browser sessions
            await self._cleanup_session_pool(session_pool)
            
            search_duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"Job discovery completed: {len(ranked_jobs)} jobs found, "
                f"{dedup_result.duplicates_found} duplicates removed, "
                f"{filtered_out} filtered out in {search_duration:.2f}s"
            )
            
            return JobDiscoveryResult(
                jobs_found=ranked_jobs,
                total_processed=total_processed,
                duplicates_removed=dedup_result.duplicates_found,
                filtered_out=filtered_out,
                search_duration=search_duration,
                search_strategy=search_strategy.value,
                success=True
            )
            
        except Exception as e:
            search_duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Job discovery failed: {e}")
            
            return JobDiscoveryResult(
                jobs_found=[],
                total_processed=0,
                duplicates_removed=0,
                filtered_out=0,
                search_duration=search_duration,
                search_strategy=search_strategy.value,
                success=False,
                error_message=str(e)
            )
    
    async def extract_job_details(
        self,
        job_url: str,
        session_id: Optional[str] = None
    ) -> Optional[Job]:
        """
        Extract comprehensive job details from a specific job posting
        
        Args:
            job_url: URL of the job posting
            session_id: Optional browser session ID to use
            
        Returns:
            Job object with detailed information or None if extraction fails
        """
        try:
            # Create or use existing session
            if session_id is None:
                session_info = await self.browserbase_client.create_session({
                    "projectId": "upwork-automation",
                    "stealth": True,
                    "keepAlive": True
                })
                session_id = session_info.id
                cleanup_session = True
            else:
                cleanup_session = False
            
            # Extract job details using Stagehand
            extraction_result = await self.stagehand_controller.extract_job_details(
                session_id, job_url
            )
            
            if not extraction_result.success:
                logger.warning(f"Failed to extract job details from {job_url}: {extraction_result.error_message}")
                return None
            
            # Convert extracted data to Job model
            job_data = extraction_result.data
            job = await self._convert_to_job_model(job_data, job_url)
            
            # Generate content hash for deduplication
            job.content_hash = self._generate_content_hash(job)
            
            # Clean up session if we created it
            if cleanup_session:
                await self.browserbase_client.end_session(session_id)
            
            logger.info(f"Successfully extracted job details: {job.title}")
            return job
            
        except Exception as e:
            logger.error(f"Failed to extract job details from {job_url}: {e}")
            return None
    
    async def _create_search_session_pool(self, size: int = 3) -> List[str]:
        """Create a pool of browser sessions for parallel job searching"""
        try:
            sessions = []
            for i in range(size):
                session_info = await self.browserbase_client.create_session({
                    "projectId": "upwork-automation",
                    "stealth": True,
                    "keepAlive": True,
                    "proxies": True
                })
                sessions.append(session_info.id)
                
                # Initialize Stagehand for each session
                await self.stagehand_controller.initialize_stagehand(session_info.id)
            
            logger.info(f"Created session pool with {len(sessions)} sessions")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to create session pool: {e}")
            raise
    
    async def _cleanup_session_pool(self, session_ids: List[str]):
        """Clean up browser session pool"""
        for session_id in session_ids:
            try:
                await self.stagehand_controller.cleanup_session(session_id)
                await self.browserbase_client.end_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup session {session_id}: {e}")
    
    async def _keyword_based_search(
        self,
        session_pool: List[str],
        search_params: JobSearchParams,
        max_jobs: int
    ) -> List[Job]:
        """Execute keyword-based job search across multiple sessions"""
        jobs = []
        
        # Distribute keywords across sessions
        keywords_per_session = len(search_params.keywords) // len(session_pool) + 1
        
        search_tasks = []
        for i, session_id in enumerate(session_pool):
            start_idx = i * keywords_per_session
            end_idx = min((i + 1) * keywords_per_session, len(search_params.keywords))
            session_keywords = search_params.keywords[start_idx:end_idx]
            
            if session_keywords:
                task = self._search_with_keywords(session_id, session_keywords, search_params)
                search_tasks.append(task)
        
        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Search task failed: {result}")
                continue
            
            if isinstance(result, list):
                jobs.extend(result)
                
                # Stop if we've reached max jobs
                if len(jobs) >= max_jobs:
                    break
        
        return jobs[:max_jobs]
    
    async def _search_with_keywords(
        self,
        session_id: str,
        keywords: List[str],
        search_params: JobSearchParams
    ) -> List[Job]:
        """Search for jobs using specific keywords in a browser session"""
        jobs = []
        
        try:
            # Navigate to Upwork job search
            nav_result = await self.stagehand_controller.intelligent_navigate(
                session_id,
                "https://www.upwork.com/nx/search/jobs/",
                context={"search_type": "job_search"}
            )
            
            if not nav_result.success:
                logger.error(f"Failed to navigate to job search: {nav_result.error_message}")
                return jobs
            
            # Perform search for each keyword combination
            for keyword in keywords:
                try:
                    # Use Stagehand for intelligent job search
                    search_result = await self.stagehand_controller.search_jobs(
                        session_id,
                        [keyword],
                        filters={
                            "min_hourly_rate": float(search_params.min_hourly_rate or 0),
                            "min_client_rating": float(search_params.min_client_rating or 0),
                            "payment_verified": search_params.payment_verified_only
                        }
                    )
                    
                    if search_result.success:
                        # Convert search results to Job objects
                        keyword_jobs = await self._convert_search_results_to_jobs(
                            search_result.data, keyword
                        )
                        jobs.extend(keyword_jobs)
                        
                        logger.info(f"Found {len(keyword_jobs)} jobs for keyword: {keyword}")
                    
                    # Add delay between searches to avoid rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Search failed for keyword '{keyword}': {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Session search failed for session {session_id}: {e}")
        
        return jobs
    
    async def _hybrid_search(
        self,
        session_pool: List[str],
        search_params: JobSearchParams,
        max_jobs: int
    ) -> List[Job]:
        """Execute hybrid search combining multiple strategies"""
        all_jobs = []
        
        # Allocate sessions to different strategies
        keyword_sessions = session_pool[:2] if len(session_pool) >= 2 else session_pool
        category_sessions = session_pool[2:] if len(session_pool) > 2 else []
        
        search_tasks = []
        
        # Keyword-based search
        if keyword_sessions:
            task = self._keyword_based_search(keyword_sessions, search_params, max_jobs // 2)
            search_tasks.append(task)
        
        # Category-based search (if we have extra sessions)
        if category_sessions:
            task = self._category_based_search(category_sessions, search_params, max_jobs // 2)
            search_tasks.append(task)
        
        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Hybrid search task failed: {result}")
                continue
            
            if isinstance(result, list):
                all_jobs.extend(result)
        
        return all_jobs[:max_jobs]
    
    async def _category_based_search(
        self,
        session_pool: List[str],
        search_params: JobSearchParams,
        max_jobs: int
    ) -> List[Job]:
        """Execute category-based job search"""
        # Placeholder for category-based search
        # Would implement navigation to specific Ardan categories
        return []
    
    async def _client_based_search(
        self,
        session_pool: List[str],
        search_params: JobSearchParams,
        max_jobs: int
    ) -> List[Job]:
        """Execute client-based job search targeting high-quality clients"""
        # Placeholder for client-based search
        # Would implement search focusing on clients with high ratings and hire rates
        return []
    
    async def _convert_search_results_to_jobs(
        self,
        search_data: Dict[str, Any],
        search_keyword: str
    ) -> List[Job]:
        """Convert raw search results to Job model objects"""
        jobs = []
        
        try:
            job_listings = search_data.get("jobs", [])
            
            for job_data in job_listings:
                try:
                    job = await self._convert_to_job_model(job_data, search_keyword=search_keyword)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Failed to convert job data: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Failed to convert search results: {e}")
        
        return jobs
    
    async def _convert_to_job_model(
        self,
        job_data: Dict[str, Any],
        job_url: Optional[str] = None,
        search_keyword: Optional[str] = None
    ) -> Optional[Job]:
        """Convert raw job data to Job model"""
        try:
            # Extract basic job information
            title = job_data.get("title", "")
            description = job_data.get("description", "")
            
            if not title or not description:
                return None
            
            # Parse budget information
            budget_min = None
            budget_max = None
            hourly_rate = None
            job_type = JobType.HOURLY
            
            if "budget" in job_data:
                budget_str = str(job_data["budget"])
                if "$" in budget_str:
                    # Parse budget range or hourly rate
                    if "/hr" in budget_str.lower():
                        job_type = JobType.HOURLY
                        # Extract hourly rate
                        import re
                        rate_match = re.search(r'\$(\d+(?:\.\d+)?)', budget_str)
                        if rate_match:
                            hourly_rate = Decimal(rate_match.group(1))
                    else:
                        job_type = JobType.FIXED
                        # Extract budget range
                        import re
                        amounts = re.findall(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', budget_str)
                        if len(amounts) >= 2:
                            budget_min = Decimal(amounts[0].replace(",", ""))
                            budget_max = Decimal(amounts[1].replace(",", ""))
                        elif len(amounts) == 1:
                            budget_min = budget_max = Decimal(amounts[0].replace(",", ""))
            
            # Parse client information
            client_name = job_data.get("client_name", "")
            client_rating = Decimal(str(job_data.get("client_rating", "0")))
            client_payment_verified = job_data.get("payment_verified", False)
            client_hire_rate = Decimal(str(job_data.get("hire_rate", "0")))
            
            # Parse skills
            skills_required = job_data.get("skills", [])
            if isinstance(skills_required, str):
                skills_required = [s.strip() for s in skills_required.split(",")]
            
            # Parse dates
            posted_date = None
            if "posted_time" in job_data:
                try:
                    posted_date = datetime.fromisoformat(job_data["posted_time"])
                except:
                    # Handle relative dates like "2 hours ago"
                    posted_date = datetime.utcnow()  # Fallback to current time
            
            # Create Job object
            job = Job(
                id=uuid.uuid4(),
                upwork_job_id=job_data.get("job_id"),
                title=title,
                description=description,
                budget_min=budget_min,
                budget_max=budget_max,
                hourly_rate=hourly_rate,
                client_name=client_name,
                client_rating=client_rating,
                client_payment_verified=client_payment_verified,
                client_hire_rate=client_hire_rate,
                posted_date=posted_date,
                skills_required=skills_required,
                job_type=job_type,
                job_url=job_url or job_data.get("job_url", ""),
                status=JobStatus.DISCOVERED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Generate content hash for deduplication
            job.content_hash = self._generate_content_hash(job)
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to convert job data to model: {e}")
            return None
    
    def _generate_content_hash(self, job: Job) -> str:
        """Generate content hash for job deduplication"""
        # Create hash from key job attributes
        content_string = f"{job.title}:{job.client_name}:{job.description[:200]}"
        return hashlib.md5(content_string.encode()).hexdigest()
    
    async def _deduplicate_jobs(self, jobs: List[Job]) -> DeduplicationResult:
        """Remove duplicate jobs using ID and content hash checking"""
        original_count = len(jobs)
        seen_hashes = set()
        seen_upwork_ids = set()
        deduplicated_jobs = []
        duplicate_pairs = []
        
        for job in jobs:
            is_duplicate = False
            duplicate_reason = ""
            
            # Check Upwork job ID
            if job.upwork_job_id and job.upwork_job_id in seen_upwork_ids:
                is_duplicate = True
                duplicate_reason = f"Duplicate Upwork ID: {job.upwork_job_id}"
            
            # Check content hash
            elif job.content_hash and job.content_hash in seen_hashes:
                is_duplicate = True
                duplicate_reason = f"Duplicate content hash: {job.content_hash}"
            
            if is_duplicate:
                duplicate_pairs.append((str(job.id), duplicate_reason))
                logger.debug(f"Removing duplicate job: {job.title} - {duplicate_reason}")
            else:
                deduplicated_jobs.append(job)
                if job.upwork_job_id:
                    seen_upwork_ids.add(job.upwork_job_id)
                if job.content_hash:
                    seen_hashes.add(job.content_hash)
        
        duplicates_found = original_count - len(deduplicated_jobs)
        
        logger.info(f"Deduplication: {original_count} -> {len(deduplicated_jobs)} jobs ({duplicates_found} duplicates removed)")
        
        return DeduplicationResult(
            original_count=original_count,
            deduplicated_count=len(deduplicated_jobs),
            duplicates_found=duplicates_found,
            duplicate_pairs=duplicate_pairs
        )
    
    async def _ai_powered_filtering(self, jobs: List[Job]) -> List[Job]:
        """Apply AI-powered job filtering using MCP for context-aware decisions"""
        filtered_jobs = []
        
        try:
            for job in jobs:
                # Basic criteria filtering first
                if not self._meets_basic_criteria(job):
                    continue
                
                # AI-powered relevance analysis using MCP
                try:
                    relevance_analysis = await self._analyze_job_relevance(job)
                    
                    if relevance_analysis["relevant"] and relevance_analysis["confidence"] > 0.6:
                        job.match_score = Decimal(str(relevance_analysis["confidence"]))
                        job.match_reasons = relevance_analysis.get("reasons", [])
                        filtered_jobs.append(job)
                        
                except Exception as e:
                    logger.warning(f"AI filtering failed for job {job.title}: {e}")
                    # Fall back to basic filtering
                    if self._meets_basic_criteria(job):
                        job.match_score = Decimal("0.5")  # Default score
                        filtered_jobs.append(job)
        
        except Exception as e:
            logger.error(f"AI-powered filtering failed: {e}")
            # Fallback to basic filtering
            filtered_jobs = [job for job in jobs if self._meets_basic_criteria(job)]
        
        logger.info(f"AI filtering: {len(jobs)} -> {len(filtered_jobs)} jobs")
        return filtered_jobs
    
    def _meets_basic_criteria(self, job: Job) -> bool:
        """Check if job meets basic filtering criteria"""
        # Hourly rate check
        if job.hourly_rate and job.hourly_rate < self.min_hourly_rate:
            return False
        
        # Client rating check
        if job.client_rating < self.min_client_rating:
            return False
        
        # Client hire rate check
        if job.client_hire_rate < self.min_hire_rate:
            return False
        
        # Payment verification check
        if not job.client_payment_verified:
            return False
        
        # Keyword relevance check
        title_lower = job.title.lower()
        description_lower = job.description.lower()
        
        salesforce_keywords = ["salesforce", "agentforce", "einstein", "crm"]
        has_salesforce_keyword = any(keyword in title_lower or keyword in description_lower 
                                   for keyword in salesforce_keywords)
        
        if not has_salesforce_keyword:
            return False
        
        return True
    
    async def _analyze_job_relevance(self, job: Job) -> Dict[str, Any]:
        """Analyze job relevance using MCP AI agent"""
        try:
            # Prepare job context for AI analysis
            job_context = {
                "title": job.title,
                "description": job.description,
                "skills_required": job.skills_required,
                "client_rating": float(job.client_rating),
                "hourly_rate": float(job.hourly_rate) if job.hourly_rate else None,
                "client_hire_rate": float(job.client_hire_rate)
            }
            
            # Use MCP client for AI-powered analysis
            analysis_prompt = f"""
            Analyze this Ardan job for relevance to a Salesforce Agentforce Developer:
            
            Job: {job_context}
            
            Profile: Salesforce Agentforce Developer specializing in AI-powered customer service solutions
            
            Determine:
            1. Is this job relevant? (true/false)
            2. Confidence score (0.0 to 1.0)
            3. Reasons for the decision
            4. Match quality assessment
            
            Consider:
            - Salesforce/Agentforce keywords
            - AI/Einstein mentions
            - Technical requirements alignment
            - Client quality indicators
            - Project scope and complexity
            """
            
            # This would use the MCP client's AI analysis capabilities
            # For now, we'll implement a rule-based fallback
            return await self._fallback_relevance_analysis(job)
            
        except Exception as e:
            logger.warning(f"MCP relevance analysis failed: {e}")
            return await self._fallback_relevance_analysis(job)
    
    async def _fallback_relevance_analysis(self, job: Job) -> Dict[str, Any]:
        """Fallback relevance analysis using rule-based approach"""
        title_lower = job.title.lower()
        description_lower = job.description.lower()
        
        # Scoring factors
        score = 0.0
        reasons = []
        
        # Salesforce keywords (high value)
        salesforce_keywords = ["salesforce", "agentforce", "einstein", "service cloud", "sales cloud"]
        for keyword in salesforce_keywords:
            if keyword in title_lower:
                score += 0.3
                reasons.append(f"Title contains '{keyword}'")
            elif keyword in description_lower:
                score += 0.2
                reasons.append(f"Description mentions '{keyword}'")
        
        # AI/Automation keywords (medium value)
        ai_keywords = ["ai", "artificial intelligence", "automation", "chatbot", "machine learning"]
        for keyword in ai_keywords:
            if keyword in title_lower or keyword in description_lower:
                score += 0.1
                reasons.append(f"Contains AI/automation keyword: '{keyword}'")
        
        # Technical skills alignment
        relevant_skills = ["apex", "lightning", "visualforce", "soql", "rest api", "integration"]
        skill_matches = [skill for skill in job.skills_required 
                        if any(relevant in skill.lower() for relevant in relevant_skills)]
        
        if skill_matches:
            score += len(skill_matches) * 0.05
            reasons.append(f"Relevant skills: {', '.join(skill_matches)}")
        
        # Client quality bonus
        if job.client_rating >= Decimal("4.5"):
            score += 0.1
            reasons.append("High client rating")
        
        if job.client_hire_rate >= Decimal("0.8"):
            score += 0.1
            reasons.append("High client hire rate")
        
        # Hourly rate consideration
        if job.hourly_rate and job.hourly_rate >= Decimal("75"):
            score += 0.1
            reasons.append("High hourly rate")
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return {
            "relevant": score >= 0.6,
            "confidence": score,
            "reasons": reasons,
            "match_quality": "high" if score >= 0.8 else "medium" if score >= 0.6 else "low"
        }
    
    async def _rank_and_score_jobs(self, jobs: List[Job]) -> List[Job]:
        """Rank and score jobs based on match criteria and historical success"""
        try:
            # Calculate comprehensive scores for each job
            for job in jobs:
                if job.match_score is None:
                    job.match_score = Decimal("0.5")  # Default score
                
                # Apply historical success patterns
                historical_bonus = await self._get_historical_success_bonus(job)
                job.match_score = min(job.match_score + Decimal(str(historical_bonus)), Decimal("1.0"))
            
            # Sort jobs by match score (descending)
            ranked_jobs = sorted(jobs, key=lambda j: j.match_score, reverse=True)
            
            logger.info(f"Ranked {len(ranked_jobs)} jobs by match score")
            return ranked_jobs
            
        except Exception as e:
            logger.error(f"Job ranking failed: {e}")
            return jobs
    
    async def _get_historical_success_bonus(self, job: Job) -> float:
        """Calculate bonus score based on historical success patterns"""
        bonus = 0.0
        
        try:
            # Client success pattern
            client_key = f"client:{job.client_name}"
            if client_key in self.success_patterns:
                bonus += self.success_patterns[client_key] * 0.1
            
            # Keyword success pattern
            for keyword in self.default_keywords:
                if keyword.lower() in job.title.lower() or keyword.lower() in job.description.lower():
                    keyword_key = f"keyword:{keyword}"
                    if keyword_key in self.success_patterns:
                        bonus += self.success_patterns[keyword_key] * 0.05
            
            # Hourly rate range success pattern
            if job.hourly_rate:
                rate_range = f"rate:{int(job.hourly_rate // 25) * 25}"  # Group by $25 ranges
                if rate_range in self.success_patterns:
                    bonus += self.success_patterns[rate_range] * 0.05
        
        except Exception as e:
            logger.warning(f"Failed to calculate historical bonus: {e}")
        
        return min(bonus, 0.3)  # Cap bonus at 0.3
    
    async def _load_success_patterns(self):
        """Load historical success patterns for ranking"""
        try:
            # This would typically load from a database or file
            # For now, initialize with default patterns
            self.success_patterns = {
                "keyword:Salesforce Agentforce": 0.8,
                "keyword:Einstein AI": 0.7,
                "keyword:Salesforce AI": 0.75,
                "rate:75": 0.6,
                "rate:100": 0.8
            }
            
            logger.info("Loaded historical success patterns")
            
        except Exception as e:
            logger.warning(f"Failed to load success patterns: {e}")
            self.success_patterns = {}
    
    async def update_success_pattern(self, pattern_key: str, success_rate: float):
        """Update success pattern based on application results"""
        try:
            self.success_patterns[pattern_key] = success_rate
            logger.debug(f"Updated success pattern: {pattern_key} = {success_rate}")
        except Exception as e:
            logger.error(f"Failed to update success pattern: {e}")
    
    async def get_discovery_stats(self) -> Dict[str, Any]:
        """Get job discovery statistics"""
        return {
            "total_jobs_discovered": len(self.discovered_jobs),
            "unique_content_hashes": len(self.job_content_hashes),
            "unique_upwork_ids": len(self.upwork_job_ids),
            "success_patterns_count": len(self.success_patterns),
            "last_discovery": datetime.utcnow().isoformat()
        }
    
    async def shutdown(self):
        """Shutdown the job discovery service"""
        logger.info("Shutting down Job Discovery Service...")
        
        try:
            # Cleanup Stagehand controller
            await self.stagehand_controller.shutdown()
            
            # Save success patterns
            await self._save_success_patterns()
            
            logger.info("Job Discovery Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def _save_success_patterns(self):
        """Save success patterns for future use"""
        try:
            # This would typically save to a database or file
            logger.info("Success patterns saved")
        except Exception as e:
            logger.warning(f"Failed to save success patterns: {e}")


class UpworkJobSearchController(StagehandController):
    """Specialized Stagehand controller for Upwork job search operations"""
    
    async def search_jobs(
        self,
        session_id: str,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Search for jobs using Stagehand AI automation"""
        try:
            stagehand = await self.get_stagehand(session_id)
            page = stagehand.page
            
            # Construct search query
            search_query = " OR ".join(keywords)
            
            # Use Stagehand to perform intelligent job search
            await stagehand.act(page, f"search for jobs with query: {search_query}")
            
            # Apply filters if provided
            if filters:
                if filters.get("min_hourly_rate"):
                    await stagehand.act(page, f"set minimum hourly rate filter to ${filters['min_hourly_rate']}")
                
                if filters.get("min_client_rating"):
                    await stagehand.act(page, f"set minimum client rating filter to {filters['min_client_rating']} stars")
                
                if filters.get("payment_verified"):
                    await stagehand.act(page, "enable payment verified filter")
            
            # Wait for results to load
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # Extract job listings using Stagehand
            jobs_data = await stagehand.extract(
                page,
                "extract all job listings with: title, client name, budget/hourly rate, "
                "client rating, payment verified status, job description preview, posted time, "
                "number of proposals, hire rate, job URL, job ID"
            )
            
            return ExtractionResult(
                success=True,
                data={"jobs": jobs_data},
                extraction_type=ExtractionType.JOB_LISTINGS,
                confidence_score=0.9
            )
            
        except Exception as e:
            logger.error(f"Job search failed for session {session_id}: {e}")
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=ExtractionType.JOB_LISTINGS,
                error_message=str(e)
            )
    
    async def extract_job_details(
        self,
        session_id: str,
        job_url: str
    ) -> ExtractionResult:
        """Extract detailed job information from job posting page"""
        try:
            stagehand = await self.get_stagehand(session_id)
            page = stagehand.page
            
            # Navigate to job details page
            await stagehand.act(page, f"navigate to job details page: {job_url}")
            await page.wait_for_load_state("networkidle", timeout=15000)
            
            # Extract comprehensive job details
            job_details = await stagehand.extract(
                page,
                "extract complete job information including: "
                "full job title, complete job description, client name and info, "
                "budget details (min/max or hourly rate), required skills, "
                "client rating, payment verification status, client hire rate, "
                "job posting date, application deadline, location requirements, "
                "number of proposals submitted, client's hiring history, "
                "similar jobs posted by client, job category, experience level required"
            )
            
            return ExtractionResult(
                success=True,
                data=job_details,
                extraction_type=ExtractionType.JOB_DETAILS,
                confidence_score=0.95
            )
            
        except Exception as e:
            logger.error(f"Job detail extraction failed for {job_url}: {e}")
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=ExtractionType.JOB_DETAILS,
                error_message=str(e)
            )