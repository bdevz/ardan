"""
MCP (Model Context Protocol) Client for AI agent integration with browser contexts
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from shared.config import settings
from shared.utils import setup_logging, retry_async
from shared.models import BrowserSession

logger = setup_logging("mcp-client")


class ContextType(Enum):
    """Types of browser context"""
    PAGE_STATE = "page_state"
    NAVIGATION = "navigation"
    INTERACTION = "interaction"
    EXTRACTION = "extraction"
    ERROR = "error"
    STRATEGY = "strategy"


class AdaptationStrategy(Enum):
    """Adaptation strategies for different scenarios"""
    RETRY_WITH_DELAY = "retry_with_delay"
    CHANGE_APPROACH = "change_approach"
    FALLBACK_METHOD = "fallback_method"
    ESCALATE_ERROR = "escalate_error"
    LEARN_AND_ADAPT = "learn_and_adapt"


@dataclass
class PageContext:
    """Comprehensive page context information"""
    session_id: str
    url: str
    title: str
    page_type: str  # 'job_search', 'job_details', 'application_form', 'profile', 'unknown'
    content_hash: str
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)
    form_fields: List[Dict[str, Any]] = field(default_factory=list)
    navigation_state: Dict[str, Any] = field(default_factory=dict)
    error_indicators: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationStrategy:
    """Strategy for automation based on context analysis"""
    strategy_id: str
    context_hash: str
    page_type: str
    automation_goal: str
    recommended_actions: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    fallback_strategies: List[str] = field(default_factory=list)
    success_probability: float = 0.0
    estimated_duration: int = 0  # seconds
    risk_factors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InteractionResult:
    """Result of an automation interaction"""
    session_id: str
    strategy_id: str
    action_type: str
    success: bool
    execution_time: float
    error_message: Optional[str] = None
    context_before: Optional[PageContext] = None
    context_after: Optional[PageContext] = None
    adaptation_applied: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningPattern:
    """Pattern learned from interaction results"""
    pattern_id: str
    page_type: str
    automation_goal: str
    success_conditions: Dict[str, Any]
    failure_conditions: Dict[str, Any]
    optimal_strategy: str
    confidence: float
    sample_size: int
    last_updated: datetime = field(default_factory=datetime.utcnow)


class MCPClient:
    """Model Context Protocol client for AI agent integration with browser contexts"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.api_key = openai_api_key or settings.openai_api_key
        
        # Context storage
        self.page_contexts: Dict[str, PageContext] = {}
        self.context_history: Dict[str, List[PageContext]] = {}
        
        # Strategy management
        self.strategies: Dict[str, AutomationStrategy] = {}
        self.strategy_cache: Dict[str, str] = {}  # context_hash -> strategy_id
        
        # Learning system
        self.interaction_results: List[InteractionResult] = []
        self.learning_patterns: Dict[str, LearningPattern] = {}
        
        # Configuration
        self.max_context_history = 50
        self.max_interaction_results = 1000
        self.learning_threshold = 10  # minimum samples for pattern recognition
        
        # AI client (placeholder for actual OpenAI client)
        self.ai_client = None
        
    async def initialize(self):
        """Initialize the MCP client"""
        logger.info("Initializing MCP client...")
        
        try:
            # Initialize AI client
            if self.api_key:
                # In a real implementation, this would initialize OpenAI client
                # For now, we'll use a mock implementation
                self.ai_client = MockAIClient(self.api_key)
                await self.ai_client.initialize()
            
            # Load existing learning patterns
            await self._load_learning_patterns()
            
            logger.info("MCP client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
            raise
    
    async def analyze_page_context(
        self,
        session_id: str,
        page_data: Dict[str, Any],
        automation_goal: Optional[str] = None
    ) -> PageContext:
        """Analyze current browser page context for AI understanding"""
        try:
            # Extract basic page information
            url = page_data.get("url", "")
            title = page_data.get("title", "")
            content = page_data.get("content", "")
            
            # Generate content hash for caching
            content_hash = hashlib.md5(
                f"{url}:{title}:{content}".encode()
            ).hexdigest()
            
            # Determine page type using AI analysis
            page_type = await self._classify_page_type(url, title, content)
            
            # Extract interactive elements
            interactive_elements = await self._extract_interactive_elements(page_data)
            
            # Extract form fields
            form_fields = await self._extract_form_fields(page_data)
            
            # Analyze navigation state
            navigation_state = await self._analyze_navigation_state(page_data)
            
            # Detect error and success indicators
            error_indicators = await self._detect_error_indicators(page_data)
            success_indicators = await self._detect_success_indicators(page_data)
            
            # Create page context
            context = PageContext(
                session_id=session_id,
                url=url,
                title=title,
                page_type=page_type,
                content_hash=content_hash,
                interactive_elements=interactive_elements,
                form_fields=form_fields,
                navigation_state=navigation_state,
                error_indicators=error_indicators,
                success_indicators=success_indicators,
                metadata={
                    "automation_goal": automation_goal,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Store context
            self.page_contexts[session_id] = context
            
            # Add to history
            if session_id not in self.context_history:
                self.context_history[session_id] = []
            
            self.context_history[session_id].append(context)
            
            # Maintain history size limit
            if len(self.context_history[session_id]) > self.max_context_history:
                self.context_history[session_id].pop(0)
            
            logger.info(f"Analyzed page context for session {session_id}: {page_type}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to analyze page context for session {session_id}: {e}")
            raise
    
    async def generate_adaptive_strategy(
        self,
        session_id: str,
        automation_goal: str,
        context: Optional[PageContext] = None
    ) -> AutomationStrategy:
        """Generate adaptive automation strategy based on page context and goals"""
        try:
            # Get current context if not provided
            if context is None:
                context = self.page_contexts.get(session_id)
                if not context:
                    raise ValueError(f"No context available for session {session_id}")
            
            # Check strategy cache
            cache_key = f"{context.content_hash}:{automation_goal}"
            if cache_key in self.strategy_cache:
                strategy_id = self.strategy_cache[cache_key]
                if strategy_id in self.strategies:
                    logger.debug(f"Using cached strategy: {strategy_id}")
                    return self.strategies[strategy_id]
            
            # Generate new strategy using AI analysis
            strategy = await self._generate_strategy_with_ai(context, automation_goal)
            
            # Apply learning patterns to improve strategy
            strategy = await self._apply_learning_patterns(strategy, context)
            
            # Store strategy
            self.strategies[strategy.strategy_id] = strategy
            self.strategy_cache[cache_key] = strategy.strategy_id
            
            logger.info(f"Generated adaptive strategy: {strategy.strategy_id} for goal: {automation_goal}")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to generate adaptive strategy for session {session_id}: {e}")
            raise
    
    async def record_interaction_result(
        self,
        session_id: str,
        strategy_id: str,
        action_type: str,
        success: bool,
        execution_time: float,
        error_message: Optional[str] = None,
        context_before: Optional[PageContext] = None,
        context_after: Optional[PageContext] = None
    ):
        """Record the result of an automation interaction for learning"""
        try:
            result = InteractionResult(
                session_id=session_id,
                strategy_id=strategy_id,
                action_type=action_type,
                success=success,
                execution_time=execution_time,
                error_message=error_message,
                context_before=context_before,
                context_after=context_after
            )
            
            self.interaction_results.append(result)
            
            # Maintain results size limit
            if len(self.interaction_results) > self.max_interaction_results:
                self.interaction_results.pop(0)
            
            # Update learning patterns
            await self._update_learning_patterns(result)
            
            logger.debug(f"Recorded interaction result: {action_type} - {'success' if success else 'failure'}")
            
        except Exception as e:
            logger.error(f"Failed to record interaction result: {e}")
    
    async def adapt_to_error(
        self,
        session_id: str,
        error_context: Dict[str, Any],
        current_strategy: AutomationStrategy
    ) -> Dict[str, Any]:
        """Provide context-aware error recovery and adaptation mechanisms"""
        try:
            # Analyze error context
            error_type = error_context.get("error_type", "unknown")
            error_message = error_context.get("error_message", "")
            failed_action = error_context.get("failed_action", "")
            
            # Get current page context
            current_context = self.page_contexts.get(session_id)
            
            # Determine adaptation strategy
            adaptation_strategy = await self._determine_adaptation_strategy(
                error_type, error_message, failed_action, current_context, current_strategy
            )
            
            # Generate adaptation recommendations
            adaptation = {
                "strategy": adaptation_strategy.value,
                "recommended_actions": [],
                "confidence": 0.0,
                "estimated_recovery_time": 0
            }
            
            if adaptation_strategy == AdaptationStrategy.RETRY_WITH_DELAY:
                adaptation.update({
                    "recommended_actions": [
                        {"action": "wait", "duration": 3},
                        {"action": "retry_last_action", "parameters": {}}
                    ],
                    "confidence": 0.7,
                    "estimated_recovery_time": 5
                })
            
            elif adaptation_strategy == AdaptationStrategy.CHANGE_APPROACH:
                # Use AI to suggest alternative approach
                alternative_actions = await self._generate_alternative_actions(
                    current_context, current_strategy.automation_goal, error_context
                )
                adaptation.update({
                    "recommended_actions": alternative_actions,
                    "confidence": 0.6,
                    "estimated_recovery_time": 10
                })
            
            elif adaptation_strategy == AdaptationStrategy.FALLBACK_METHOD:
                # Use predefined fallback strategies
                fallback_actions = await self._get_fallback_actions(
                    current_strategy, error_context
                )
                adaptation.update({
                    "recommended_actions": fallback_actions,
                    "confidence": 0.8,
                    "estimated_recovery_time": 15
                })
            
            elif adaptation_strategy == AdaptationStrategy.LEARN_AND_ADAPT:
                # Apply learning from similar past errors
                learned_solution = await self._apply_learned_error_recovery(
                    error_type, current_context
                )
                adaptation.update(learned_solution)
            
            else:  # ESCALATE_ERROR
                adaptation.update({
                    "recommended_actions": [
                        {"action": "escalate_to_human", "reason": "Unrecoverable error"}
                    ],
                    "confidence": 0.9,
                    "estimated_recovery_time": 0
                })
            
            logger.info(f"Generated error adaptation: {adaptation_strategy.value}")
            return adaptation
            
        except Exception as e:
            logger.error(f"Failed to adapt to error for session {session_id}: {e}")
            return {
                "strategy": AdaptationStrategy.ESCALATE_ERROR.value,
                "recommended_actions": [
                    {"action": "escalate_to_human", "reason": f"Adaptation failed: {str(e)}"}
                ],
                "confidence": 1.0,
                "estimated_recovery_time": 0
            }
    
    async def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session memory for context-aware operations"""
        try:
            memory = {
                "current_context": None,
                "context_history": [],
                "successful_strategies": [],
                "failed_strategies": [],
                "learned_patterns": [],
                "session_metadata": {}
            }
            
            # Current context
            if session_id in self.page_contexts:
                memory["current_context"] = self._context_to_dict(self.page_contexts[session_id])
            
            # Context history
            if session_id in self.context_history:
                memory["context_history"] = [
                    self._context_to_dict(ctx) for ctx in self.context_history[session_id][-10:]
                ]
            
            # Strategy performance for this session
            session_results = [
                r for r in self.interaction_results if r.session_id == session_id
            ]
            
            successful_strategies = {}
            failed_strategies = {}
            
            for result in session_results:
                if result.success:
                    if result.strategy_id not in successful_strategies:
                        successful_strategies[result.strategy_id] = 0
                    successful_strategies[result.strategy_id] += 1
                else:
                    if result.strategy_id not in failed_strategies:
                        failed_strategies[result.strategy_id] = 0
                    failed_strategies[result.strategy_id] += 1
            
            memory["successful_strategies"] = successful_strategies
            memory["failed_strategies"] = failed_strategies
            
            # Relevant learned patterns
            current_context = self.page_contexts.get(session_id)
            if current_context:
                relevant_patterns = [
                    pattern for pattern in self.learning_patterns.values()
                    if pattern.page_type == current_context.page_type
                ]
                memory["learned_patterns"] = [
                    self._pattern_to_dict(pattern) for pattern in relevant_patterns[:5]
                ]
            
            return memory
            
        except Exception as e:
            logger.error(f"Failed to get session memory for {session_id}: {e}")
            return {}
    
    # Private helper methods
    async def _classify_page_type(self, url: str, title: str, content: str) -> str:
        """Classify the type of page using AI analysis"""
        try:
            if not self.ai_client:
                # Fallback to simple URL-based classification
                if "job" in url.lower() and "search" in url.lower():
                    return "job_search"
                elif "job" in url.lower():
                    return "job_details"
                elif "apply" in url.lower() or "proposal" in url.lower():
                    return "application_form"
                elif "profile" in url.lower():
                    return "profile"
                else:
                    return "unknown"
            
            # Use AI for more sophisticated classification
            classification_prompt = f"""
            Analyze this web page and classify its type:
            URL: {url}
            Title: {title}
            Content preview: {content[:500]}...
            
            Classify as one of: job_search, job_details, application_form, profile, login, error, unknown
            """
            
            result = await self.ai_client.analyze(classification_prompt)
            return result.get("classification", "unknown")
            
        except Exception as e:
            logger.warning(f"Page classification failed, using fallback: {e}")
            return "unknown"
    
    async def _extract_interactive_elements(self, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract interactive elements from page data"""
        # This would typically use the browser automation tools
        # For now, return mock data
        return [
            {"type": "button", "text": "Apply Now", "selector": ".apply-button"},
            {"type": "link", "text": "View Details", "selector": ".job-link"},
            {"type": "input", "placeholder": "Search jobs", "selector": "#search-input"}
        ]
    
    async def _extract_form_fields(self, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract form fields from page data"""
        # Mock implementation
        return [
            {"name": "cover_letter", "type": "textarea", "required": True},
            {"name": "bid_amount", "type": "number", "required": True},
            {"name": "attachments", "type": "file", "required": False}
        ]
    
    async def _analyze_navigation_state(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current navigation state"""
        return {
            "breadcrumbs": ["Home", "Jobs", "Search Results"],
            "current_step": "job_search",
            "available_actions": ["search", "filter", "apply"]
        }
    
    async def _detect_error_indicators(self, page_data: Dict[str, Any]) -> List[str]:
        """Detect error indicators on the page"""
        # Mock implementation - would analyze page content for error messages
        return []
    
    async def _detect_success_indicators(self, page_data: Dict[str, Any]) -> List[str]:
        """Detect success indicators on the page"""
        # Mock implementation
        return []
    
    async def _generate_strategy_with_ai(
        self,
        context: PageContext,
        automation_goal: str
    ) -> AutomationStrategy:
        """Generate automation strategy using AI analysis"""
        strategy_id = str(uuid.uuid4())
        
        if not self.ai_client:
            # Fallback to rule-based strategy generation
            return self._generate_fallback_strategy(strategy_id, context, automation_goal)
        
        try:
            strategy_prompt = f"""
            Generate an automation strategy for this context:
            Page Type: {context.page_type}
            URL: {context.url}
            Goal: {automation_goal}
            Interactive Elements: {context.interactive_elements}
            Form Fields: {context.form_fields}
            
            Provide a step-by-step automation strategy with confidence scores.
            """
            
            ai_result = await self.ai_client.generate_strategy(strategy_prompt)
            
            return AutomationStrategy(
                strategy_id=strategy_id,
                context_hash=context.content_hash,
                page_type=context.page_type,
                automation_goal=automation_goal,
                recommended_actions=ai_result.get("actions", []),
                confidence_score=ai_result.get("confidence", 0.5),
                fallback_strategies=ai_result.get("fallbacks", []),
                success_probability=ai_result.get("success_probability", 0.5),
                estimated_duration=ai_result.get("duration", 30),
                risk_factors=ai_result.get("risks", [])
            )
            
        except Exception as e:
            logger.warning(f"AI strategy generation failed, using fallback: {e}")
            return self._generate_fallback_strategy(strategy_id, context, automation_goal)
    
    def _generate_fallback_strategy(
        self,
        strategy_id: str,
        context: PageContext,
        automation_goal: str
    ) -> AutomationStrategy:
        """Generate fallback strategy using rule-based approach"""
        actions = []
        confidence = 0.6
        
        if context.page_type == "job_search" and automation_goal == "search_jobs":
            actions = [
                {"action": "fill_search", "target": "search_input", "value": "Salesforce Agentforce"},
                {"action": "click", "target": "search_button"},
                {"action": "wait", "duration": 3},
                {"action": "extract", "target": "job_listings"}
            ]
            confidence = 0.8
        
        elif context.page_type == "job_details" and automation_goal == "extract_job_info":
            actions = [
                {"action": "extract", "target": "job_title"},
                {"action": "extract", "target": "job_description"},
                {"action": "extract", "target": "client_info"},
                {"action": "extract", "target": "requirements"}
            ]
            confidence = 0.9
        
        elif context.page_type == "application_form" and automation_goal == "submit_application":
            actions = [
                {"action": "fill", "target": "cover_letter", "value": "proposal_content"},
                {"action": "fill", "target": "bid_amount", "value": "hourly_rate"},
                {"action": "upload", "target": "attachments", "value": "files"},
                {"action": "click", "target": "submit_button"}
            ]
            confidence = 0.7
        
        return AutomationStrategy(
            strategy_id=strategy_id,
            context_hash=context.content_hash,
            page_type=context.page_type,
            automation_goal=automation_goal,
            recommended_actions=actions,
            confidence_score=confidence,
            success_probability=confidence,
            estimated_duration=len(actions) * 5
        )
    
    async def _apply_learning_patterns(
        self,
        strategy: AutomationStrategy,
        context: PageContext
    ) -> AutomationStrategy:
        """Apply learned patterns to improve strategy"""
        # Find relevant patterns
        relevant_patterns = [
            pattern for pattern in self.learning_patterns.values()
            if (pattern.page_type == context.page_type and 
                pattern.automation_goal == strategy.automation_goal and
                pattern.confidence > 0.7)
        ]
        
        if relevant_patterns:
            # Use the best pattern to adjust strategy
            best_pattern = max(relevant_patterns, key=lambda p: p.confidence)
            
            # Adjust confidence based on learned success rate
            strategy.confidence_score = min(
                strategy.confidence_score * (1 + best_pattern.confidence * 0.2),
                1.0
            )
            
            # Add learned optimizations
            if best_pattern.optimal_strategy:
                strategy.fallback_strategies.insert(0, best_pattern.optimal_strategy)
        
        return strategy
    
    async def _update_learning_patterns(self, result: InteractionResult):
        """Update learning patterns based on interaction results"""
        if not result.context_before:
            return
        
        pattern_key = f"{result.context_before.page_type}:{result.strategy_id}"
        
        if pattern_key not in self.learning_patterns:
            self.learning_patterns[pattern_key] = LearningPattern(
                pattern_id=pattern_key,
                page_type=result.context_before.page_type,
                automation_goal="",  # Would be extracted from strategy
                success_conditions={},
                failure_conditions={},
                optimal_strategy="",
                confidence=0.0,
                sample_size=0
            )
        
        pattern = self.learning_patterns[pattern_key]
        pattern.sample_size += 1
        
        # Update success/failure conditions
        if result.success:
            # Add to success conditions
            pass
        else:
            # Add to failure conditions
            if result.error_message:
                if "failure_errors" not in pattern.failure_conditions:
                    pattern.failure_conditions["failure_errors"] = []
                pattern.failure_conditions["failure_errors"].append(result.error_message)
        
        # Update confidence based on success rate
        recent_results = [
            r for r in self.interaction_results[-50:]  # Last 50 results
            if r.strategy_id == result.strategy_id
        ]
        
        if len(recent_results) >= self.learning_threshold:
            success_rate = sum(1 for r in recent_results if r.success) / len(recent_results)
            pattern.confidence = success_rate
        
        pattern.last_updated = datetime.utcnow()
    
    async def _determine_adaptation_strategy(
        self,
        error_type: str,
        error_message: str,
        failed_action: str,
        context: Optional[PageContext],
        strategy: AutomationStrategy
    ) -> AdaptationStrategy:
        """Determine the best adaptation strategy for an error"""
        
        # Simple rule-based adaptation logic
        if "timeout" in error_message.lower():
            return AdaptationStrategy.RETRY_WITH_DELAY
        
        elif "element not found" in error_message.lower():
            return AdaptationStrategy.CHANGE_APPROACH
        
        elif "captcha" in error_message.lower():
            return AdaptationStrategy.ESCALATE_ERROR
        
        elif strategy.fallback_strategies:
            return AdaptationStrategy.FALLBACK_METHOD
        
        else:
            return AdaptationStrategy.LEARN_AND_ADAPT
    
    async def _generate_alternative_actions(
        self,
        context: Optional[PageContext],
        automation_goal: str,
        error_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alternative actions using AI"""
        # Mock implementation
        return [
            {"action": "wait", "duration": 2},
            {"action": "scroll", "direction": "down"},
            {"action": "retry_with_different_selector", "selector": "alternative_selector"}
        ]
    
    async def _get_fallback_actions(
        self,
        strategy: AutomationStrategy,
        error_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get fallback actions from strategy"""
        # Use predefined fallback strategies
        return [
            {"action": "use_fallback_method", "method": strategy.fallback_strategies[0]}
        ] if strategy.fallback_strategies else []
    
    async def _apply_learned_error_recovery(
        self,
        error_type: str,
        context: Optional[PageContext]
    ) -> Dict[str, Any]:
        """Apply learned error recovery patterns"""
        # Find similar past errors and their successful recoveries
        similar_errors = [
            r for r in self.interaction_results
            if (r.error_message and error_type in r.error_message and
                r.adaptation_applied and "success" in r.adaptation_applied)
        ]
        
        if similar_errors:
            # Use the most recent successful recovery
            recent_success = max(similar_errors, key=lambda r: r.timestamp)
            return {
                "recommended_actions": [
                    {"action": "apply_learned_recovery", "method": recent_success.adaptation_applied}
                ],
                "confidence": 0.8,
                "estimated_recovery_time": 10
            }
        
        return {
            "recommended_actions": [
                {"action": "escalate_to_human", "reason": "No learned recovery available"}
            ],
            "confidence": 0.5,
            "estimated_recovery_time": 0
        }
    
    async def _load_learning_patterns(self):
        """Load existing learning patterns from storage"""
        # In a real implementation, this would load from database
        logger.info("Loading learning patterns...")
    
    def _context_to_dict(self, context: PageContext) -> Dict[str, Any]:
        """Convert PageContext to dictionary"""
        return {
            "session_id": context.session_id,
            "url": context.url,
            "title": context.title,
            "page_type": context.page_type,
            "content_hash": context.content_hash,
            "interactive_elements": context.interactive_elements,
            "form_fields": context.form_fields,
            "navigation_state": context.navigation_state,
            "error_indicators": context.error_indicators,
            "success_indicators": context.success_indicators,
            "timestamp": context.timestamp.isoformat(),
            "metadata": context.metadata
        }
    
    def _pattern_to_dict(self, pattern: LearningPattern) -> Dict[str, Any]:
        """Convert LearningPattern to dictionary"""
        return {
            "pattern_id": pattern.pattern_id,
            "page_type": pattern.page_type,
            "automation_goal": pattern.automation_goal,
            "success_conditions": pattern.success_conditions,
            "failure_conditions": pattern.failure_conditions,
            "optimal_strategy": pattern.optimal_strategy,
            "confidence": pattern.confidence,
            "sample_size": pattern.sample_size,
            "last_updated": pattern.last_updated.isoformat()
        }
    
    async def cleanup(self):
        """Clean up MCP client resources"""
        logger.info("Cleaning up MCP client...")
        
        if self.ai_client:
            await self.ai_client.cleanup()
        
        # Clear caches
        self.page_contexts.clear()
        self.strategies.clear()
        self.strategy_cache.clear()
        
        logger.info("MCP client cleanup complete")


class MockAIClient:
    """Mock AI client for testing and development"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def initialize(self):
        """Initialize mock AI client"""
        pass
    
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """Mock AI analysis"""
        # Simple keyword-based classification
        prompt_lower = prompt.lower()
        
        if "job" in prompt_lower and "search" in prompt_lower:
            return {"classification": "job_search"}
        elif "job" in prompt_lower and "details" in prompt_lower:
            return {"classification": "job_details"}
        elif "apply" in prompt_lower or "proposal" in prompt_lower:
            return {"classification": "application_form"}
        elif "profile" in prompt_lower:
            return {"classification": "profile"}
        else:
            return {"classification": "unknown"}
    
    async def generate_strategy(self, prompt: str) -> Dict[str, Any]:
        """Mock strategy generation"""
        return {
            "actions": [
                {"action": "analyze_page", "confidence": 0.9},
                {"action": "execute_goal", "confidence": 0.8}
            ],
            "confidence": 0.8,
            "success_probability": 0.75,
            "duration": 30,
            "risks": ["page_change", "network_timeout"],
            "fallbacks": ["retry", "manual_intervention"]
        }
    
    async def cleanup(self):
        """Clean up mock AI client"""
        pass