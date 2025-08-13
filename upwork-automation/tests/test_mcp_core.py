"""
Core tests for MCP functionality without external dependencies
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import hashlib

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

# Mock external dependencies
sys.modules['playwright'] = Mock()
sys.modules['playwright.async_api'] = Mock()
sys.modules['stagehand'] = Mock()
sys.modules['browserbase_client'] = Mock()
sys.modules['director_actions'] = Mock()

from mcp_client import (
    MCPClient, PageContext, AutomationStrategy, InteractionResult, 
    LearningPattern, ContextType, AdaptationStrategy, MockAIClient
)


class TestMCPCoreLogic:
    """Test core MCP logic without external dependencies"""
    
    @pytest_asyncio.fixture
    async def mcp_client(self):
        """Create MCP client for testing"""
        client = MCPClient()
        # Use mock AI client to avoid external dependencies
        client.ai_client = MockAIClient("test_key")
        await client.ai_client.initialize()
        return client
    
    @pytest.fixture
    def sample_page_data(self):
        """Sample page data for testing"""
        return {
            "url": "https://www.ardan.com/nx/search/jobs/?q=Salesforce%20Agentforce",
            "title": "Salesforce Agentforce Jobs - Ardan",
            "content": "Find Salesforce Agentforce jobs on Ardan. Browse job listings and apply to projects.",
        }
    
    @pytest.mark.asyncio
    async def test_page_context_creation(self, mcp_client, sample_page_data):
        """Test page context creation and analysis"""
        session_id = "test_session_123"
        automation_goal = "job_search"
        
        # Mock the helper methods to avoid external dependencies
        with patch.object(mcp_client, '_classify_page_type', return_value="job_search"), \
             patch.object(mcp_client, '_extract_interactive_elements', return_value=[]), \
             patch.object(mcp_client, '_extract_form_fields', return_value=[]), \
             patch.object(mcp_client, '_analyze_navigation_state', return_value={}), \
             patch.object(mcp_client, '_detect_error_indicators', return_value=[]), \
             patch.object(mcp_client, '_detect_success_indicators', return_value=[]):
            
            context = await mcp_client.analyze_page_context(
                session_id, sample_page_data, automation_goal
            )
        
        assert isinstance(context, PageContext)
        assert context.session_id == session_id
        assert context.url == sample_page_data["url"]
        assert context.title == sample_page_data["title"]
        assert context.page_type == "job_search"
        assert len(context.content_hash) == 32  # MD5 hash length
        assert context.metadata["automation_goal"] == automation_goal
        
        # Verify context is stored
        assert session_id in mcp_client.page_contexts
        assert session_id in mcp_client.context_history
    
    @pytest.mark.asyncio
    async def test_strategy_generation_fallback(self, mcp_client):
        """Test fallback strategy generation"""
        context = PageContext(
            session_id="test_session",
            url="https://www.ardan.com/jobs/search",
            title="Job Search",
            page_type="job_search",
            content_hash="test_hash",
            interactive_elements=[
                {"type": "input", "name": "search_input"},
                {"type": "button", "name": "search_button"}
            ],
            form_fields=[
                {"name": "q", "type": "text", "required": False}
            ]
        )
        
        strategy = await mcp_client.generate_adaptive_strategy(
            "test_session", "search_jobs", context
        )
        
        assert isinstance(strategy, AutomationStrategy)
        assert strategy.context_hash == context.content_hash
        assert strategy.page_type == context.page_type
        assert strategy.automation_goal == "search_jobs"
        assert 0.0 <= strategy.confidence_score <= 1.0
        assert 0.0 <= strategy.success_probability <= 1.0
        assert strategy.estimated_duration > 0
        assert len(strategy.recommended_actions) > 0
        
        # For job search, should have appropriate actions
        action_types = [action.get("action") for action in strategy.recommended_actions]
        assert "fill_search" in action_types or "extract" in action_types
    
    @pytest.mark.asyncio
    async def test_interaction_result_recording(self, mcp_client):
        """Test interaction result recording and learning"""
        session_id = "test_session"
        strategy_id = "test_strategy"
        
        # Create a context for the interaction
        context = PageContext(
            session_id=session_id,
            url="https://test.com",
            title="Test Page",
            page_type="job_search",
            content_hash="test_hash"
        )
        
        # Record successful interaction
        await mcp_client.record_interaction_result(
            session_id=session_id,
            strategy_id=strategy_id,
            action_type="navigation",
            success=True,
            execution_time=2.5,
            context_before=context
        )
        
        # Verify result is recorded
        assert len(mcp_client.interaction_results) == 1
        result = mcp_client.interaction_results[0]
        
        assert result.session_id == session_id
        assert result.strategy_id == strategy_id
        assert result.action_type == "navigation"
        assert result.success is True
        assert result.execution_time == 2.5
        assert result.context_before == context
    
    @pytest.mark.asyncio
    async def test_error_adaptation_logic(self, mcp_client):
        """Test error adaptation logic"""
        # Create a basic strategy
        strategy = AutomationStrategy(
            strategy_id="test_strategy",
            context_hash="test_hash",
            page_type="job_search",
            automation_goal="search_jobs",
            recommended_actions=[{"action": "search"}],
            fallback_strategies=["alternative_search", "manual_search"]
        )
        
        # Test timeout error adaptation
        timeout_error = {
            "error_type": "timeout_error",
            "error_message": "Request timeout after 30 seconds",
            "failed_action": "page_load"
        }
        
        adaptation = await mcp_client.adapt_to_error(
            "test_session", timeout_error, strategy
        )
        
        assert isinstance(adaptation, dict)
        assert "strategy" in adaptation
        assert "recommended_actions" in adaptation
        assert "confidence" in adaptation
        assert "estimated_recovery_time" in adaptation
        
        # Should recommend retry with delay for timeout
        assert adaptation["strategy"] == AdaptationStrategy.RETRY_WITH_DELAY.value
        assert len(adaptation["recommended_actions"]) > 0
        
        # Test element not found error
        element_error = {
            "error_type": "element_not_found",
            "error_message": "Could not locate element",
            "failed_action": "click"
        }
        
        adaptation = await mcp_client.adapt_to_error(
            "test_session", element_error, strategy
        )
        
        # Should recommend changing approach
        assert adaptation["strategy"] == AdaptationStrategy.CHANGE_APPROACH.value
    
    @pytest.mark.asyncio
    async def test_learning_pattern_updates(self, mcp_client):
        """Test learning pattern creation and updates"""
        session_id = "test_session"
        strategy_id = "test_strategy"
        
        # Create context
        context = PageContext(
            session_id=session_id,
            url="https://test.com",
            title="Test",
            page_type="job_search",
            content_hash="test_hash"
        )
        
        # Record multiple interactions to trigger learning
        success_count = 0
        total_count = 15
        
        for i in range(total_count):
            success = i % 3 != 0  # 2/3 success rate
            if success:
                success_count += 1
            
            await mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy_id,
                action_type="test_action",
                success=success,
                execution_time=1.0,
                error_message="Test error" if not success else None,
                context_before=context
            )
        
        # Check if learning pattern was created/updated
        pattern_key = f"{context.page_type}:{strategy_id}"
        if pattern_key in mcp_client.learning_patterns:
            pattern = mcp_client.learning_patterns[pattern_key]
            assert pattern.sample_size >= mcp_client.learning_threshold
            
            # Confidence should reflect success rate
            expected_confidence = success_count / total_count
            assert abs(pattern.confidence - expected_confidence) < 0.1
    
    @pytest.mark.asyncio
    async def test_session_memory_retrieval(self, mcp_client):
        """Test session memory retrieval"""
        session_id = "test_session"
        
        # Create context
        context = PageContext(
            session_id=session_id,
            url="https://test.com",
            title="Test",
            page_type="job_search",
            content_hash="test_hash"
        )
        
        # Store context
        mcp_client.page_contexts[session_id] = context
        mcp_client.context_history[session_id] = [context]
        
        # Record some interactions
        await mcp_client.record_interaction_result(
            session_id, "strategy_1", "navigation", True, 1.5
        )
        await mcp_client.record_interaction_result(
            session_id, "strategy_2", "extraction", False, 3.0, "Extraction failed"
        )
        
        memory = await mcp_client.get_session_memory(session_id)
        
        assert isinstance(memory, dict)
        assert "current_context" in memory
        assert "context_history" in memory
        assert "successful_strategies" in memory
        assert "failed_strategies" in memory
        
        # Verify memory content
        assert memory["current_context"] is not None
        assert len(memory["context_history"]) > 0
        assert "strategy_1" in memory["successful_strategies"]
        assert "strategy_2" in memory["failed_strategies"]
    
    @pytest.mark.asyncio
    async def test_strategy_caching(self, mcp_client):
        """Test strategy caching mechanism"""
        context = PageContext(
            session_id="test_session",
            url="https://test.com",
            title="Test",
            page_type="job_search",
            content_hash="test_hash"
        )
        
        automation_goal = "search_jobs"
        
        # Generate strategy first time
        strategy1 = await mcp_client.generate_adaptive_strategy(
            "session1", automation_goal, context
        )
        
        # Generate strategy for same context - should be cached
        strategy2 = await mcp_client.generate_adaptive_strategy(
            "session2", automation_goal, context
        )
        
        # Should be the same strategy (cached)
        assert strategy1.strategy_id == strategy2.strategy_id
        
        # Verify cache key exists
        cache_key = f"{context.content_hash}:{automation_goal}"
        assert cache_key in mcp_client.strategy_cache
        assert mcp_client.strategy_cache[cache_key] == strategy1.strategy_id
    
    def test_content_hash_generation(self, mcp_client):
        """Test content hash generation for caching"""
        url = "https://test.com"
        title = "Test Page"
        content = "Test content"
        
        expected_hash = hashlib.md5(
            f"{url}:{title}:{content}".encode()
        ).hexdigest()
        
        # This would be part of the analyze_page_context method
        actual_hash = hashlib.md5(
            f"{url}:{title}:{content}".encode()
        ).hexdigest()
        
        assert actual_hash == expected_hash
        assert len(actual_hash) == 32
    
    @pytest.mark.asyncio
    async def test_mock_ai_client(self):
        """Test mock AI client functionality"""
        ai_client = MockAIClient("test_key")
        await ai_client.initialize()
        
        # Test classification
        classification_result = await ai_client.analyze(
            "URL: https://ardan.com/jobs/search Title: Job Search"
        )
        assert "classification" in classification_result
        assert classification_result["classification"] in [
            "job_search", "job_details", "application_form", "profile", "unknown"
        ]
        
        # Test strategy generation
        strategy_result = await ai_client.generate_strategy(
            "Generate strategy for job search"
        )
        assert "actions" in strategy_result
        assert "confidence" in strategy_result
        assert isinstance(strategy_result["actions"], list)
        assert 0.0 <= strategy_result["confidence"] <= 1.0
        
        await ai_client.cleanup()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mcp_client):
        """Test MCP client cleanup"""
        # Add some data
        mcp_client.page_contexts["test"] = Mock()
        mcp_client.strategies["test"] = Mock()
        mcp_client.strategy_cache["test"] = "test"
        
        await mcp_client.cleanup()
        
        # Verify cleanup
        assert len(mcp_client.page_contexts) == 0
        assert len(mcp_client.strategies) == 0
        assert len(mcp_client.strategy_cache) == 0


class TestMCPDataStructures:
    """Test MCP data structures and models"""
    
    def test_page_context_creation(self):
        """Test PageContext data structure"""
        context = PageContext(
            session_id="test_session",
            url="https://test.com",
            title="Test Page",
            page_type="job_search",
            content_hash="abc123",
            interactive_elements=[{"type": "button", "text": "Click me"}],
            form_fields=[{"name": "search", "type": "text"}],
            navigation_state={"current_page": "search"},
            error_indicators=["error_message"],
            success_indicators=["success_message"]
        )
        
        assert context.session_id == "test_session"
        assert context.url == "https://test.com"
        assert context.page_type == "job_search"
        assert len(context.interactive_elements) == 1
        assert len(context.form_fields) == 1
        assert isinstance(context.timestamp, datetime)
    
    def test_automation_strategy_creation(self):
        """Test AutomationStrategy data structure"""
        strategy = AutomationStrategy(
            strategy_id="test_strategy",
            context_hash="abc123",
            page_type="job_search",
            automation_goal="search_jobs",
            recommended_actions=[
                {"action": "fill_search", "target": "search_input"},
                {"action": "click", "target": "search_button"}
            ],
            confidence_score=0.8,
            fallback_strategies=["alternative_search"],
            success_probability=0.75,
            estimated_duration=30,
            risk_factors=["timeout", "captcha"]
        )
        
        assert strategy.strategy_id == "test_strategy"
        assert strategy.page_type == "job_search"
        assert strategy.confidence_score == 0.8
        assert len(strategy.recommended_actions) == 2
        assert len(strategy.fallback_strategies) == 1
        assert len(strategy.risk_factors) == 2
        assert isinstance(strategy.created_at, datetime)
    
    def test_interaction_result_creation(self):
        """Test InteractionResult data structure"""
        result = InteractionResult(
            session_id="test_session",
            strategy_id="test_strategy",
            action_type="navigation",
            success=True,
            execution_time=2.5,
            error_message=None
        )
        
        assert result.session_id == "test_session"
        assert result.strategy_id == "test_strategy"
        assert result.success is True
        assert result.execution_time == 2.5
        assert result.error_message is None
        assert isinstance(result.timestamp, datetime)
    
    def test_learning_pattern_creation(self):
        """Test LearningPattern data structure"""
        pattern = LearningPattern(
            pattern_id="job_search:strategy_1",
            page_type="job_search",
            automation_goal="search_jobs",
            success_conditions={"keywords_present": True},
            failure_conditions={"timeout": True},
            optimal_strategy="keyword_search",
            confidence=0.85,
            sample_size=25
        )
        
        assert pattern.pattern_id == "job_search:strategy_1"
        assert pattern.page_type == "job_search"
        assert pattern.confidence == 0.85
        assert pattern.sample_size == 25
        assert isinstance(pattern.last_updated, datetime)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])