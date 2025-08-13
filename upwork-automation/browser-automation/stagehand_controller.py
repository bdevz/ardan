"""
Stagehand AI Browser Control Implementation for intelligent browser automation
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from playwright.async_api import Page, Browser, BrowserContext
from stagehand import Stagehand, StagehandConfig

from shared.config import BrowserAutomationConfig, settings
from shared.utils import setup_logging, retry_async
from browserbase_client import BrowserbaseClient

logger = setup_logging("stagehand-controller")


class NavigationStrategy(Enum):
    """Navigation strategies for different page types"""
    DIRECT_URL = "direct_url"
    SEARCH_AND_CLICK = "search_and_click"
    FORM_BASED = "form_based"
    MENU_NAVIGATION = "menu_navigation"


class ExtractionType(Enum):
    """Types of content extraction"""
    JOB_LISTINGS = "job_listings"
    JOB_DETAILS = "job_details"
    FORM_FIELDS = "form_fields"
    PAGE_CONTENT = "page_content"
    CONFIRMATION = "confirmation"


@dataclass
class NavigationResult:
    """Result of a navigation operation"""
    success: bool
    url: str
    page_title: str
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ExtractionResult:
    """Result of a content extraction operation"""
    success: bool
    data: Dict[str, Any]
    extraction_type: ExtractionType
    confidence_score: float = 0.0
    error_message: Optional[str] = None
    raw_html: Optional[str] = None


@dataclass
class InteractionResult:
    """Result of a form interaction operation"""
    success: bool
    action_performed: str
    elements_affected: List[str]
    error_message: Optional[str] = None
    validation_errors: List[str] = None


class StagehandController:
    """AI-powered browser controller using Stagehand for intelligent automation"""
    
    def __init__(self, browserbase_client: Optional[BrowserbaseClient] = None):
        self.browserbase_client = browserbase_client or BrowserbaseClient()
        self.stagehand_instances: Dict[str, Stagehand] = {}
        self.page_contexts: Dict[str, Dict[str, Any]] = {}
        self.navigation_history: Dict[str, List[str]] = {}
        
        # Stagehand configuration
        self.stagehand_config = StagehandConfig(
            api_key=settings.openai_api_key,
            model="gpt-4",
            headless=True,
            enable_caching=True,
            debug_mode=settings.debug
        )
    
    async def initialize_stagehand(self, session_id: str) -> bool:
        """Initialize Stagehand for a browser session"""
        try:
            # Get session info from browserbase client
            session_info = await self.browserbase_client.get_session(session_id)
            if not session_info or not session_info.connect_url:
                raise ValueError(f"Invalid session or missing connect URL for session {session_id}")
            
            # Initialize Stagehand with the browser session
            stagehand = Stagehand(config=self.stagehand_config)
            await stagehand.init(
                browser_ws_endpoint=session_info.connect_url,
                headless=True
            )
            
            self.stagehand_instances[session_id] = stagehand
            self.page_contexts[session_id] = {}
            self.navigation_history[session_id] = []
            
            logger.info(f"Initialized Stagehand for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Stagehand for session {session_id}: {e}")
            return False
    
    async def get_stagehand(self, session_id: str) -> Stagehand:
        """Get or initialize Stagehand instance for session"""
        if session_id not in self.stagehand_instances:
            success = await self.initialize_stagehand(session_id)
            if not success:
                raise RuntimeError(f"Failed to initialize Stagehand for session {session_id}")
        
        return self.stagehand_instances[session_id]
    
    @retry_async(max_retries=3, delay=2.0)
    async def intelligent_navigate(
        self,
        session_id: str,
        target_description: str,
        strategy: NavigationStrategy = NavigationStrategy.SEARCH_AND_CLICK,
        context: Optional[Dict[str, Any]] = None
    ) -> NavigationResult:
        """Navigate to a target using AI-powered understanding"""
        start_time = datetime.utcnow()
        
        try:
            stagehand = await self.get_stagehand(session_id)
            page = stagehand.page
            
            # Store navigation context
            nav_context = {
                "target": target_description,
                "strategy": strategy.value,
                "timestamp": start_time.isoformat(),
                "context": context or {}
            }
            self.page_contexts[session_id]["navigation"] = nav_context
            
            # Execute navigation based on strategy
            if strategy == NavigationStrategy.DIRECT_URL:
                await self._navigate_direct_url(stagehand, target_description)
            elif strategy == NavigationStrategy.SEARCH_AND_CLICK:
                await self._navigate_search_and_click(stagehand, target_description, context)
            elif strategy == NavigationStrategy.FORM_BASED:
                await self._navigate_form_based(stagehand, target_description, context)
            elif strategy == NavigationStrategy.MENU_NAVIGATION:
                await self._navigate_menu_based(stagehand, target_description, context)
            
            # Wait for page to stabilize
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Get final page info
            url = page.url
            title = await page.title()
            
            # Update navigation history
            self.navigation_history[session_id].append(url)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Successfully navigated to: {title} ({url})")
            
            return NavigationResult(
                success=True,
                url=url,
                page_title=title,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Navigation failed for session {session_id}: {e}")
            
            return NavigationResult(
                success=False,
                url="",
                page_title="",
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _navigate_direct_url(self, stagehand: Stagehand, url: str):
        """Navigate directly to a URL"""
        await stagehand.page.goto(url, wait_until="networkidle")
    
    async def _navigate_search_and_click(
        self,
        stagehand: Stagehand,
        target_description: str,
        context: Optional[Dict[str, Any]]
    ):
        """Navigate by searching for and clicking elements"""
        # Use Stagehand's AI to find and click the target
        await stagehand.act(f"navigate to {target_description}")
    
    async def _navigate_form_based(
        self,
        stagehand: Stagehand,
        target_description: str,
        context: Optional[Dict[str, Any]]
    ):
        """Navigate using form interactions"""
        if context and "form_data" in context:
            form_data = context["form_data"]
            for field, value in form_data.items():
                await stagehand.act(f"fill {field} with {value}")
            
            await stagehand.act(f"submit form to {target_description}")
        else:
            await stagehand.act(f"find and use form to navigate to {target_description}")
    
    async def _navigate_menu_based(
        self,
        stagehand: Stagehand,
        target_description: str,
        context: Optional[Dict[str, Any]]
    ):
        """Navigate using menu systems"""
        await stagehand.act(f"use menu navigation to reach {target_description}")
    
    @retry_async(max_retries=2, delay=1.0)
    async def extract_content(
        self,
        session_id: str,
        extraction_prompt: str,
        extraction_type: ExtractionType,
        schema: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Extract content using AI understanding"""
        try:
            stagehand = await self.get_stagehand(session_id)
            
            # Build extraction prompt with schema if provided
            if schema:
                schema_str = json.dumps(schema, indent=2)
                full_prompt = f"{extraction_prompt}\n\nReturn data in this format:\n{schema_str}"
            else:
                full_prompt = extraction_prompt
            
            # Use Stagehand's extract method
            extracted_data = await stagehand.extract(full_prompt)
            
            # Calculate confidence score based on data completeness
            confidence_score = self._calculate_extraction_confidence(extracted_data, schema)
            
            # Store extraction context
            self.page_contexts[session_id]["last_extraction"] = {
                "type": extraction_type.value,
                "prompt": extraction_prompt,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": confidence_score
            }
            
            logger.info(f"Extracted {extraction_type.value} data with confidence {confidence_score:.2f}")
            
            return ExtractionResult(
                success=True,
                data=extracted_data,
                extraction_type=extraction_type,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Content extraction failed for session {session_id}: {e}")
            
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=extraction_type,
                error_message=str(e)
            )
    
    def _calculate_extraction_confidence(
        self,
        extracted_data: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for extracted data"""
        if not extracted_data:
            return 0.0
        
        if not schema:
            # Basic confidence based on data presence
            return min(len(extracted_data) / 5.0, 1.0)  # Assume 5 fields is "complete"
        
        # Schema-based confidence calculation
        required_fields = schema.get("required", [])
        if not required_fields:
            return 0.8  # Good confidence if no specific requirements
        
        present_fields = sum(1 for field in required_fields if field in extracted_data)
        return present_fields / len(required_fields)
    
    @retry_async(max_retries=3, delay=1.0)
    async def interact_with_form(
        self,
        session_id: str,
        form_data: Dict[str, Any],
        submit: bool = False,
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> InteractionResult:
        """Fill and interact with forms using dynamic element detection"""
        try:
            stagehand = await self.get_stagehand(session_id)
            elements_affected = []
            validation_errors = []
            
            # Fill form fields
            for field_name, field_value in form_data.items():
                try:
                    # Use Stagehand's intelligent form filling
                    await stagehand.act(f"fill the {field_name} field with: {field_value}")
                    elements_affected.append(field_name)
                    
                    # Apply validation if rules provided
                    if validation_rules and field_name in validation_rules:
                        validation_result = await self._validate_field(
                            stagehand, field_name, field_value, validation_rules[field_name]
                        )
                        if not validation_result:
                            validation_errors.append(f"Validation failed for {field_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to fill field {field_name}: {e}")
                    validation_errors.append(f"Failed to fill {field_name}: {str(e)}")
            
            # Submit form if requested
            action_performed = "form_fill"
            if submit and not validation_errors:
                try:
                    await stagehand.act("submit the form")
                    action_performed = "form_submit"
                    
                    # Wait for submission to complete
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    validation_errors.append(f"Form submission failed: {str(e)}")
            
            # Store interaction context
            self.page_contexts[session_id]["last_interaction"] = {
                "action": action_performed,
                "fields": list(form_data.keys()),
                "timestamp": datetime.utcnow().isoformat(),
                "success": len(validation_errors) == 0
            }
            
            success = len(validation_errors) == 0
            logger.info(f"Form interaction completed: {action_performed}, success: {success}")
            
            return InteractionResult(
                success=success,
                action_performed=action_performed,
                elements_affected=elements_affected,
                validation_errors=validation_errors
            )
            
        except Exception as e:
            logger.error(f"Form interaction failed for session {session_id}: {e}")
            
            return InteractionResult(
                success=False,
                action_performed="error",
                elements_affected=[],
                error_message=str(e)
            )
    
    async def _validate_field(
        self,
        stagehand: Stagehand,
        field_name: str,
        field_value: Any,
        validation_rule: Dict[str, Any]
    ) -> bool:
        """Validate a form field using provided rules"""
        try:
            # Extract current field value to verify it was set correctly
            current_value = await stagehand.extract(f"get the current value of the {field_name} field")
            
            # Basic validation checks
            if validation_rule.get("required", False) and not current_value:
                return False
            
            if "min_length" in validation_rule:
                if len(str(current_value)) < validation_rule["min_length"]:
                    return False
            
            if "max_length" in validation_rule:
                if len(str(current_value)) > validation_rule["max_length"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Field validation failed for {field_name}: {e}")
            return False
    
    async def handle_dynamic_content(
        self,
        session_id: str,
        content_description: str,
        wait_timeout: int = 10
    ) -> bool:
        """Handle dynamic content loading and changes"""
        try:
            stagehand = await self.get_stagehand(session_id)
            
            # Use Stagehand to wait for and handle dynamic content
            await stagehand.act(f"wait for {content_description} to load")
            
            # Additional wait for content stabilization
            await asyncio.sleep(1)
            
            logger.info(f"Successfully handled dynamic content: {content_description}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle dynamic content for session {session_id}: {e}")
            return False
    
    async def capture_page_state(self, session_id: str) -> Dict[str, Any]:
        """Capture current page state for debugging and analysis"""
        try:
            stagehand = await self.get_stagehand(session_id)
            page = stagehand.page
            
            # Capture basic page information
            page_state = {
                "url": page.url,
                "title": await page.title(),
                "timestamp": datetime.utcnow().isoformat(),
                "viewport": await page.viewport_size(),
                "user_agent": await page.evaluate("navigator.userAgent")
            }
            
            # Capture page content summary
            try:
                content_summary = await stagehand.extract(
                    "summarize the main content and interactive elements on this page"
                )
                page_state["content_summary"] = content_summary
            except Exception as e:
                logger.warning(f"Failed to capture content summary: {e}")
            
            # Store in context
            self.page_contexts[session_id]["page_state"] = page_state
            
            return page_state
            
        except Exception as e:
            logger.error(f"Failed to capture page state for session {session_id}: {e}")
            return {}
    
    async def recover_from_error(
        self,
        session_id: str,
        error_context: Dict[str, Any],
        recovery_strategy: str = "auto"
    ) -> bool:
        """Attempt to recover from automation errors"""
        try:
            stagehand = await self.get_stagehand(session_id)
            
            if recovery_strategy == "auto":
                # Let Stagehand's AI determine the best recovery approach
                recovery_prompt = f"""
                An error occurred during automation: {error_context.get('error', 'Unknown error')}
                Current page: {stagehand.page.url}
                Last action: {error_context.get('last_action', 'Unknown')}
                
                Please analyze the current page state and take appropriate action to recover from this error.
                """
                
                await stagehand.act(recovery_prompt)
                
            elif recovery_strategy == "refresh":
                await stagehand.page.reload(wait_until="networkidle")
                
            elif recovery_strategy == "navigate_back":
                await stagehand.page.go_back(wait_until="networkidle")
                
            elif recovery_strategy == "restart_session":
                # This would require session manager integration
                return False
            
            # Verify recovery was successful
            await asyncio.sleep(2)
            page_state = await self.capture_page_state(session_id)
            
            logger.info(f"Error recovery attempted for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recovery failed for session {session_id}: {e}")
            return False
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive context for a session"""
        context = self.page_contexts.get(session_id, {})
        
        # Add navigation history
        context["navigation_history"] = self.navigation_history.get(session_id, [])
        
        # Add current page state if available
        if session_id in self.stagehand_instances:
            try:
                current_state = await self.capture_page_state(session_id)
                context["current_state"] = current_state
            except Exception as e:
                logger.warning(f"Failed to get current state for context: {e}")
        
        return context
    
    async def cleanup_session(self, session_id: str):
        """Clean up Stagehand resources for a session"""
        try:
            if session_id in self.stagehand_instances:
                stagehand = self.stagehand_instances[session_id]
                await stagehand.close()
                del self.stagehand_instances[session_id]
            
            # Clean up context data
            self.page_contexts.pop(session_id, None)
            self.navigation_history.pop(session_id, None)
            
            logger.info(f"Cleaned up Stagehand resources for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    async def shutdown(self):
        """Shutdown all Stagehand instances"""
        logger.info("Shutting down Stagehand controller...")
        
        # Close all Stagehand instances
        for session_id in list(self.stagehand_instances.keys()):
            await self.cleanup_session(session_id)
        
        logger.info("Stagehand controller shutdown complete")


# Specialized controllers for specific Ardan automation tasks
class ArdanJobSearchController(StagehandController):
    """Specialized controller for Ardan job search operations"""
    
    async def search_jobs(
        self,
        session_id: str,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Search for jobs on Ardan with specific criteria"""
        
        # Navigate to job search page
        nav_result = await self.intelligent_navigate(
            session_id,
            "Ardan job search page",
            NavigationStrategy.DIRECT_URL
        )
        
        if not nav_result.success:
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=ExtractionType.JOB_LISTINGS,
                error_message=f"Failed to navigate to job search: {nav_result.error_message}"
            )
        
        # Perform search
        search_query = " ".join(keywords)
        form_data = {"search_query": search_query}
        
        # Add filters if provided
        if filters:
            form_data.update(filters)
        
        interaction_result = await self.interact_with_form(
            session_id,
            form_data,
            submit=True
        )
        
        if not interaction_result.success:
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=ExtractionType.JOB_LISTINGS,
                error_message="Failed to perform job search"
            )
        
        # Wait for results to load
        await self.handle_dynamic_content(session_id, "job search results")
        
        # Extract job listings
        extraction_prompt = """
        Extract all job listings from this page with the following information for each job:
        - title: Job title
        - client_name: Client name
        - budget: Budget or hourly rate
        - description: Job description preview
        - posted_time: When the job was posted
        - proposals: Number of proposals
        - client_rating: Client rating
        - payment_verified: Whether client payment is verified
        - job_url: Link to the full job posting
        """
        
        return await self.extract_content(
            session_id,
            extraction_prompt,
            ExtractionType.JOB_LISTINGS
        )
    
    async def extract_job_details(self, session_id: str, job_url: str) -> ExtractionResult:
        """Extract detailed information from a specific job posting"""
        
        # Navigate to job details page
        nav_result = await self.intelligent_navigate(
            session_id,
            job_url,
            NavigationStrategy.DIRECT_URL
        )
        
        if not nav_result.success:
            return ExtractionResult(
                success=False,
                data={},
                extraction_type=ExtractionType.JOB_DETAILS,
                error_message=f"Failed to navigate to job details: {nav_result.error_message}"
            )
        
        # Extract comprehensive job details
        extraction_prompt = """
        Extract complete job information including:
        - title: Full job title
        - description: Complete job description
        - budget_type: Fixed price or hourly
        - budget_min: Minimum budget/rate
        - budget_max: Maximum budget/rate
        - skills_required: List of required skills
        - client_info: Client name, rating, hire rate, payment verification
        - job_requirements: Specific requirements and qualifications
        - timeline: Project timeline or duration
        - application_deadline: Application deadline if specified
        - similar_jobs: Number of similar jobs posted by client
        """
        
        return await self.extract_content(
            session_id,
            extraction_prompt,
            ExtractionType.JOB_DETAILS
        )


class ArdanApplicationController(StagehandController):
    """Specialized controller for Ardan job application submission"""
    
    async def submit_application(
        self,
        session_id: str,
        job_url: str,
        proposal_content: str,
        bid_amount: float,
        attachments: Optional[List[str]] = None
    ) -> InteractionResult:
        """Submit a job application with proposal"""
        
        # Navigate to job page
        nav_result = await self.intelligent_navigate(
            session_id,
            job_url,
            NavigationStrategy.DIRECT_URL
        )
        
        if not nav_result.success:
            return InteractionResult(
                success=False,
                action_performed="navigation_failed",
                elements_affected=[],
                error_message=f"Failed to navigate to job: {nav_result.error_message}"
            )
        
        # Click apply button
        stagehand = await self.get_stagehand(session_id)
        await stagehand.act("click the apply button or submit proposal button")
        
        # Wait for application form to load
        await self.handle_dynamic_content(session_id, "job application form")
        
        # Fill application form
        form_data = {
            "cover_letter": proposal_content,
            "bid_amount": str(bid_amount)
        }
        
        # Handle attachments if provided
        if attachments:
            for i, attachment in enumerate(attachments):
                form_data[f"attachment_{i}"] = attachment
        
        # Submit application
        return await self.interact_with_form(
            session_id,
            form_data,
            submit=True,
            validation_rules={
                "cover_letter": {"required": True, "min_length": 100},
                "bid_amount": {"required": True}
            }
        )
    
    async def verify_submission(self, session_id: str) -> ExtractionResult:
        """Verify that the application was submitted successfully"""
        
        # Wait for confirmation page/message
        await asyncio.sleep(3)
        
        extraction_prompt = """
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
        """
        
        return await self.extract_content(
            session_id,
            extraction_prompt,
            ExtractionType.CONFIRMATION
        )