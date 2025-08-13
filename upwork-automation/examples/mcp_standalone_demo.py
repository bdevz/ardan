"""
Standalone MCP (Model Context Protocol) Demo

This demo shows the core MCP functionality without external dependencies.
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


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
    page_type: str
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
    estimated_duration: int = 0
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


class SimpleMCPClient:
    """Simplified MCP client for demonstration"""
    
    def __init__(self):
        self.page_contexts: Dict[str, PageContext] = {}
        self.context_history: Dict[str, List[PageContext]] = {}
        self.strategies: Dict[str, AutomationStrategy] = {}
        self.strategy_cache: Dict[str, str] = {}
        self.interaction_results: List[InteractionResult] = []
        self.learning_patterns: Dict[str, LearningPattern] = {}
        self.learning_threshold = 10
    
    async def analyze_page_context(
        self,
        session_id: str,
        page_data: Dict[str, Any],
        automation_goal: Optional[str] = None
    ) -> PageContext:
        """Analyze current browser page context"""
        url = page_data.get("url", "")
        title = page_data.get("title", "")
        content = page_data.get("content", "")
        
        # Generate content hash
        content_hash = hashlib.md5(f"{url}:{title}:{content}".encode()).hexdigest()
        
        # Simple page type classification
        page_type = self._classify_page_type(url, title, content)
        
        # Create context
        context = PageContext(
            session_id=session_id,
            url=url,
            title=title,
            page_type=page_type,
            content_hash=content_hash,
            interactive_elements=self._extract_mock_elements(page_type),
            form_fields=self._extract_mock_form_fields(page_type),
            metadata={"automation_goal": automation_goal}
        )
        
        # Store context
        self.page_contexts[session_id] = context
        
        if session_id not in self.context_history:
            self.context_history[session_id] = []
        self.context_history[session_id].append(context)
        
        return context
    
    async def generate_adaptive_strategy(
        self,
        session_id: str,
        automation_goal: str,
        context: Optional[PageContext] = None
    ) -> AutomationStrategy:
        """Generate adaptive automation strategy"""
        if context is None:
            context = self.page_contexts.get(session_id)
            if not context:
                raise ValueError(f"No context available for session {session_id}")
        
        # Check cache
        cache_key = f"{context.content_hash}:{automation_goal}"
        if cache_key in self.strategy_cache:
            strategy_id = self.strategy_cache[cache_key]
            if strategy_id in self.strategies:
                return self.strategies[strategy_id]
        
        # Generate new strategy
        strategy = self._generate_strategy(context, automation_goal)
        
        # Apply learning patterns
        strategy = self._apply_learning_patterns(strategy, context)
        
        # Store strategy
        self.strategies[strategy.strategy_id] = strategy
        self.strategy_cache[cache_key] = strategy.strategy_id
        
        return strategy
    
    async def record_interaction_result(
        self,
        session_id: str,
        strategy_id: str,
        action_type: str,
        success: bool,
        execution_time: float,
        error_message: Optional[str] = None,
        context_before: Optional[PageContext] = None
    ):
        """Record interaction result for learning"""
        result = InteractionResult(
            session_id=session_id,
            strategy_id=strategy_id,
            action_type=action_type,
            success=success,
            execution_time=execution_time,
            error_message=error_message,
            context_before=context_before
        )
        
        self.interaction_results.append(result)
        
        # Update learning patterns
        if context_before:
            await self._update_learning_patterns(result)
    
    async def adapt_to_error(
        self,
        session_id: str,
        error_context: Dict[str, Any],
        current_strategy: AutomationStrategy
    ) -> Dict[str, Any]:
        """Provide error adaptation recommendations"""
        error_type = error_context.get("error_type", "unknown")
        error_message = error_context.get("error_message", "")
        
        # Determine adaptation strategy
        if "timeout" in error_message.lower():
            strategy = AdaptationStrategy.RETRY_WITH_DELAY
            actions = [
                {"action": "wait", "duration": 3},
                {"action": "retry_last_action"}
            ]
            confidence = 0.7
            recovery_time = 5
        
        elif "element not found" in error_message.lower():
            strategy = AdaptationStrategy.CHANGE_APPROACH
            actions = [
                {"action": "scroll_page"},
                {"action": "try_alternative_selector"},
                {"action": "wait_for_element"}
            ]
            confidence = 0.6
            recovery_time = 10
        
        elif "captcha" in error_message.lower():
            strategy = AdaptationStrategy.ESCALATE_ERROR
            actions = [
                {"action": "escalate_to_human", "reason": "CAPTCHA challenge"}
            ]
            confidence = 0.9
            recovery_time = 0
        
        elif current_strategy.fallback_strategies:
            strategy = AdaptationStrategy.FALLBACK_METHOD
            actions = [
                {"action": "use_fallback", "method": current_strategy.fallback_strategies[0]}
            ]
            confidence = 0.8
            recovery_time = 15
        
        else:
            strategy = AdaptationStrategy.LEARN_AND_ADAPT
            actions = [
                {"action": "analyze_error"},
                {"action": "try_learned_solution"}
            ]
            confidence = 0.5
            recovery_time = 20
        
        return {
            "strategy": strategy.value,
            "recommended_actions": actions,
            "confidence": confidence,
            "estimated_recovery_time": recovery_time
        }
    
    async def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """Get session memory"""
        memory = {
            "current_context": None,
            "context_history": [],
            "successful_strategies": {},
            "failed_strategies": {},
            "learned_patterns": []
        }
        
        # Current context
        if session_id in self.page_contexts:
            context = self.page_contexts[session_id]
            memory["current_context"] = {
                "page_type": context.page_type,
                "url": context.url,
                "content_hash": context.content_hash
            }
        
        # Context history
        if session_id in self.context_history:
            memory["context_history"] = [
                {"page_type": ctx.page_type, "url": ctx.url}
                for ctx in self.context_history[session_id][-5:]  # Last 5
            ]
        
        # Strategy performance
        session_results = [r for r in self.interaction_results if r.session_id == session_id]
        
        for result in session_results:
            if result.success:
                if result.strategy_id not in memory["successful_strategies"]:
                    memory["successful_strategies"][result.strategy_id] = 0
                memory["successful_strategies"][result.strategy_id] += 1
            else:
                if result.strategy_id not in memory["failed_strategies"]:
                    memory["failed_strategies"][result.strategy_id] = 0
                memory["failed_strategies"][result.strategy_id] += 1
        
        return memory
    
    def _classify_page_type(self, url: str, title: str, content: str) -> str:
        """Simple page type classification"""
        url_lower = url.lower()
        title_lower = title.lower()
        content_lower = content.lower()
        
        if "search" in url_lower or "search" in title_lower:
            return "job_search"
        elif "jobs/" in url_lower and "~" in url_lower:
            return "job_details"
        elif "proposal" in url_lower or "apply" in title_lower:
            return "application_form"
        elif "profile" in url_lower:
            return "profile"
        else:
            return "unknown"
    
    def _extract_mock_elements(self, page_type: str) -> List[Dict[str, Any]]:
        """Extract mock interactive elements based on page type"""
        if page_type == "job_search":
            return [
                {"type": "input", "name": "search", "placeholder": "Search jobs"},
                {"type": "button", "name": "search_btn", "text": "Search"},
                {"type": "select", "name": "category", "options": ["All", "Development"]}
            ]
        elif page_type == "job_details":
            return [
                {"type": "button", "name": "apply_btn", "text": "Apply Now"},
                {"type": "link", "name": "client_profile", "text": "View Client Profile"}
            ]
        elif page_type == "application_form":
            return [
                {"type": "textarea", "name": "cover_letter", "required": True},
                {"type": "input", "name": "bid_amount", "type": "number"},
                {"type": "file", "name": "attachments"},
                {"type": "button", "name": "submit", "text": "Submit Proposal"}
            ]
        else:
            return []
    
    def _extract_mock_form_fields(self, page_type: str) -> List[Dict[str, Any]]:
        """Extract mock form fields based on page type"""
        if page_type == "job_search":
            return [
                {"name": "q", "type": "text", "required": False},
                {"name": "category", "type": "select", "required": False}
            ]
        elif page_type == "application_form":
            return [
                {"name": "cover_letter", "type": "textarea", "required": True},
                {"name": "bid_amount", "type": "number", "required": True},
                {"name": "attachments", "type": "file", "required": False}
            ]
        else:
            return []
    
    def _generate_strategy(self, context: PageContext, automation_goal: str) -> AutomationStrategy:
        """Generate strategy based on context"""
        strategy_id = str(uuid.uuid4())
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
            estimated_duration=len(actions) * 5,
            fallback_strategies=["manual_intervention", "retry_with_delay"],
            risk_factors=["timeout", "element_change"] if len(actions) > 2 else []
        )
    
    def _apply_learning_patterns(self, strategy: AutomationStrategy, context: PageContext) -> AutomationStrategy:
        """Apply learning patterns to improve strategy"""
        relevant_patterns = [
            pattern for pattern in self.learning_patterns.values()
            if (pattern.page_type == context.page_type and 
                pattern.automation_goal == strategy.automation_goal and
                pattern.confidence > 0.7)
        ]
        
        if relevant_patterns:
            best_pattern = max(relevant_patterns, key=lambda p: p.confidence)
            # Boost confidence based on learning
            strategy.confidence_score = min(
                strategy.confidence_score * (1 + best_pattern.confidence * 0.2),
                1.0
            )
        
        return strategy
    
    async def _update_learning_patterns(self, result: InteractionResult):
        """Update learning patterns based on results"""
        if not result.context_before:
            return
        
        pattern_key = f"{result.context_before.page_type}:{result.strategy_id}"
        
        if pattern_key not in self.learning_patterns:
            self.learning_patterns[pattern_key] = LearningPattern(
                pattern_id=pattern_key,
                page_type=result.context_before.page_type,
                automation_goal="",
                success_conditions={},
                failure_conditions={},
                optimal_strategy="",
                confidence=0.0,
                sample_size=0
            )
        
        pattern = self.learning_patterns[pattern_key]
        pattern.sample_size += 1
        
        # Update confidence based on recent results
        recent_results = [
            r for r in self.interaction_results[-20:]  # Last 20 results
            if r.strategy_id == result.strategy_id
        ]
        
        if len(recent_results) >= self.learning_threshold:
            success_rate = sum(1 for r in recent_results if r.success) / len(recent_results)
            pattern.confidence = success_rate
        
        pattern.last_updated = datetime.utcnow()


async def demo_mcp_functionality():
    """Demonstrate MCP functionality"""
    print("MCP (Model Context Protocol) Standalone Demo")
    print("=" * 50)
    
    # Initialize MCP client
    mcp = SimpleMCPClient()
    
    # Demo 1: Context Analysis
    print("\n1. Page Context Analysis")
    print("-" * 30)
    
    pages = [
        {
            "name": "Job Search",
            "data": {
                "url": "https://www.ardan.com/nx/search/jobs/?q=Salesforce",
                "title": "Salesforce Jobs - Ardan",
                "content": "Find Salesforce jobs on Ardan"
            },
            "goal": "search_jobs"
        },
        {
            "name": "Job Details",
            "data": {
                "url": "https://www.ardan.com/jobs/~123456",
                "title": "Salesforce Developer Needed",
                "content": "We need a Salesforce developer for our project"
            },
            "goal": "extract_job_info"
        },
        {
            "name": "Application Form",
            "data": {
                "url": "https://www.ardan.com/ab/proposals/job/123456",
                "title": "Submit Proposal",
                "content": "Submit your proposal for this job"
            },
            "goal": "submit_application"
        }
    ]
    
    for page in pages:
        session_id = f"demo_{page['name'].lower().replace(' ', '_')}"
        
        context = await mcp.analyze_page_context(
            session_id, page["data"], page["goal"]
        )
        
        strategy = await mcp.generate_adaptive_strategy(
            session_id, page["goal"], context
        )
        
        print(f"\n{page['name']}:")
        print(f"  Page Type: {context.page_type}")
        print(f"  Strategy Confidence: {strategy.confidence_score:.2f}")
        print(f"  Actions: {len(strategy.recommended_actions)}")
        print(f"  Estimated Duration: {strategy.estimated_duration}s")
    
    # Demo 2: Learning System
    print("\n\n2. Learning System")
    print("-" * 30)
    
    session_id = "learning_demo"
    context = await mcp.analyze_page_context(
        session_id,
        {
            "url": "https://www.ardan.com/jobs/search",
            "title": "Job Search",
            "content": "Search for jobs"
        },
        "search_jobs"
    )
    
    strategy = await mcp.generate_adaptive_strategy(session_id, "search_jobs", context)
    
    print(f"Initial Strategy Confidence: {strategy.confidence_score:.2f}")
    
    # Simulate interactions
    print("\nSimulating 15 interactions...")
    success_count = 0
    
    for i in range(15):
        success = i % 4 != 0  # 75% success rate
        if success:
            success_count += 1
        
        await mcp.record_interaction_result(
            session_id=session_id,
            strategy_id=strategy.strategy_id,
            action_type="search",
            success=success,
            execution_time=1.0 + (i * 0.1),
            error_message="Search failed" if not success else None,
            context_before=context
        )
    
    print(f"Interactions completed: {success_count}/15 successful ({success_count/15:.1%})")
    
    # Check learning patterns
    pattern_key = f"{context.page_type}:{strategy.strategy_id}"
    if pattern_key in mcp.learning_patterns:
        pattern = mcp.learning_patterns[pattern_key]
        print(f"Learning Pattern Created:")
        print(f"  Sample Size: {pattern.sample_size}")
        print(f"  Confidence: {pattern.confidence:.2f}")
    
    # Demo 3: Error Adaptation
    print("\n\n3. Error Adaptation")
    print("-" * 30)
    
    error_scenarios = [
        {
            "name": "Timeout Error",
            "context": {
                "error_type": "timeout",
                "error_message": "Request timeout after 30 seconds",
                "failed_action": "page_load"
            }
        },
        {
            "name": "Element Not Found",
            "context": {
                "error_type": "element_error",
                "error_message": "Element not found on page",
                "failed_action": "click_button"
            }
        },
        {
            "name": "CAPTCHA Challenge",
            "context": {
                "error_type": "captcha",
                "error_message": "CAPTCHA verification required",
                "failed_action": "form_submit"
            }
        }
    ]
    
    for scenario in error_scenarios:
        adaptation = await mcp.adapt_to_error(
            "error_demo", scenario["context"], strategy
        )
        
        print(f"\n{scenario['name']}:")
        print(f"  Strategy: {adaptation['strategy']}")
        print(f"  Confidence: {adaptation['confidence']:.2f}")
        print(f"  Recovery Time: {adaptation['estimated_recovery_time']}s")
        print(f"  Actions: {len(adaptation['recommended_actions'])}")
    
    # Demo 4: Session Memory
    print("\n\n4. Session Memory")
    print("-" * 30)
    
    memory = await mcp.get_session_memory(session_id)
    
    print(f"Current Context: {memory['current_context']['page_type'] if memory['current_context'] else 'None'}")
    print(f"Context History: {len(memory['context_history'])} pages")
    print(f"Successful Strategies: {len(memory['successful_strategies'])}")
    print(f"Failed Strategies: {len(memory['failed_strategies'])}")
    
    if memory['successful_strategies']:
        for strategy_id, count in memory['successful_strategies'].items():
            print(f"  Strategy {strategy_id[:8]}...: {count} successes")
    
    print("\n" + "=" * 50)
    print("MCP Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("✓ Page context analysis and classification")
    print("✓ Adaptive strategy generation with confidence scoring")
    print("✓ Learning system that improves over time")
    print("✓ Error adaptation with multiple recovery strategies")
    print("✓ Session memory tracking across interactions")


if __name__ == "__main__":
    asyncio.run(demo_mcp_functionality())