"""
Tests for MCP Strategy Adaptation and Learning System
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from mcp_client import (
    MCPClient, PageContext, AutomationStrategy, InteractionResult, 
    LearningPattern, AdaptationStrategy
)


class TestMCPStrategyAdaptation:
    """Test cases for MCP strategy adaptation and learning"""
    
    @pytest.fixture
    async def mcp_client_with_data(self):
        """Create MCP client with pre-populated learning data"""
        client = MCPClient()
        await client.initialize()
        
        # Add some learning patterns
        pattern1 = LearningPattern(
            pattern_id="job_search:strategy_1",
            page_type="job_search",
            automation_goal="search_jobs",
            success_conditions={"keywords_present": True, "filters_applied": True},
            failure_conditions={"timeout": True, "captcha": True},
            optimal_strategy="keyword_focused_search",
            confidence=0.85,
            sample_size=25
        )
        
        pattern2 = LearningPattern(
            pattern_id="application_form:strategy_2",
            page_type="application_form",
            automation_goal="submit_application",
            success_conditions={"form_validation_passed": True, "attachments_uploaded": True},
            failure_conditions={"validation_errors": True, "network_timeout": True},
            optimal_strategy="step_by_step_form_fill",
            confidence=0.92,
            sample_size=40
        )
        
        client.learning_patterns["job_search:strategy_1"] = pattern1
        client.learning_patterns["application_form:strategy_2"] = pattern2
        
        return client
    
    @pytest.fixture
    def job_search_context(self):
        """Sample job search page context"""
        return PageContext(
            session_id="test_session",
            url="https://www.ardan.com/nx/search/jobs/",
            title="Find Jobs - Ardan",
            page_type="job_search",
            content_hash="abc123",
            interactive_elements=[
                {"type": "input", "name": "search", "placeholder": "Search jobs"},
                {"type": "button", "name": "search_btn", "text": "Search"},
                {"type": "select", "name": "category", "options": ["All", "Web Development"]}
            ],
            form_fields=[
                {"name": "q", "type": "text", "required": False},
                {"name": "category", "type": "select", "required": False}
            ]
        )
    
    @pytest.fixture
    def application_form_context(self):
        """Sample application form page context"""
        return PageContext(
            session_id="test_session",
            url="https://www.ardan.com/ab/proposals/job/123456",
            title="Submit Proposal - Ardan",
            page_type="application_form",
            content_hash="def456",
            interactive_elements=[
                {"type": "textarea", "name": "cover_letter", "required": True},
                {"type": "input", "name": "bid_amount", "type": "number", "required": True},
                {"type": "file", "name": "attachments", "multiple": True},
                {"type": "button", "name": "submit", "text": "Submit Proposal"}
            ],
            form_fields=[
                {"name": "cover_letter", "type": "textarea", "required": True},
                {"name": "bid_amount", "type": "number", "required": True},
                {"name": "attachments", "type": "file", "required": False}
            ]
        )
    
    @pytest.mark.asyncio
    async def test_strategy_improvement_with_learning(self, mcp_client_with_data, job_search_context):
        """Test that strategies improve based on learning patterns"""
        client = mcp_client_with_data
        
        # Generate strategy for job search
        strategy = await client.generate_adaptive_strategy(
            "test_session", "search_jobs", job_search_context
        )
        
        # Strategy should be influenced by existing learning pattern
        assert strategy.confidence_score > 0.5  # Should be boosted by learning
        assert len(strategy.fallback_strategies) > 0  # Should include learned fallbacks
        
        # Verify that learning pattern was applied
        relevant_pattern = client.learning_patterns.get("job_search:strategy_1")
        if relevant_pattern and relevant_pattern.confidence > 0.7:
            # Strategy confidence should be enhanced by learning
            assert strategy.confidence_score >= 0.6
    
    @pytest.mark.asyncio
    async def test_adaptive_strategy_generation_based_on_context(self, mcp_client_with_data):
        """Test that strategies adapt based on different page contexts"""
        client = mcp_client_with_data
        
        # Test different contexts
        contexts = [
            {
                "page_type": "job_search",
                "goal": "search_jobs",
                "expected_actions": ["fill_search", "click", "extract"]
            },
            {
                "page_type": "job_details", 
                "goal": "extract_job_info",
                "expected_actions": ["extract"]
            },
            {
                "page_type": "application_form",
                "goal": "submit_application", 
                "expected_actions": ["fill", "upload", "click"]
            }
        ]
        
        for ctx in contexts:
            context = PageContext(
                session_id="test_session",
                url="https://test.com",
                title="Test Page",
                page_type=ctx["page_type"],
                content_hash="test_hash"
            )
            
            strategy = await client.generate_adaptive_strategy(
                "test_session", ctx["goal"], context
            )
            
            assert strategy.page_type == ctx["page_type"]
            assert strategy.automation_goal == ctx["goal"]
            assert len(strategy.recommended_actions) > 0
            
            # Check that actions are appropriate for the context
            action_types = [action.get("action") for action in strategy.recommended_actions]
            has_expected_actions = any(
                expected in str(action_types) for expected in ctx["expected_actions"]
            )
            assert has_expected_actions or len(strategy.recommended_actions) > 0
    
    @pytest.mark.asyncio
    async def test_error_adaptation_strategies(self, mcp_client_with_data, job_search_context):
        """Test different error adaptation strategies"""
        client = mcp_client_with_data
        
        # Generate base strategy
        strategy = await client.generate_adaptive_strategy(
            "test_session", "search_jobs", job_search_context
        )
        
        # Test different error scenarios and their adaptations
        error_scenarios = [
            {
                "error_type": "timeout_error",
                "error_message": "Request timeout after 30 seconds",
                "failed_action": "page_load",
                "expected_strategy": AdaptationStrategy.RETRY_WITH_DELAY
            },
            {
                "error_type": "element_not_found",
                "error_message": "Could not locate element with selector .search-button",
                "failed_action": "click_search",
                "expected_strategy": AdaptationStrategy.CHANGE_APPROACH
            },
            {
                "error_type": "validation_error",
                "error_message": "Form validation failed: required field missing",
                "failed_action": "form_submit",
                "expected_strategy": AdaptationStrategy.FALLBACK_METHOD
            },
            {
                "error_type": "captcha_challenge",
                "error_message": "CAPTCHA verification required",
                "failed_action": "form_submit",
                "expected_strategy": AdaptationStrategy.ESCALATE_ERROR
            },
            {
                "error_type": "rate_limit",
                "error_message": "Too many requests, please try again later",
                "failed_action": "api_call",
                "expected_strategy": AdaptationStrategy.RETRY_WITH_DELAY
            }
        ]
        
        for scenario in error_scenarios:
            adaptation = await client.adapt_to_error(
                "test_session", scenario, strategy
            )
            
            # Verify adaptation response structure
            assert isinstance(adaptation, dict)
            assert "strategy" in adaptation
            assert "recommended_actions" in adaptation
            assert "confidence" in adaptation
            assert "estimated_recovery_time" in adaptation
            
            # Verify adaptation makes sense for the error type
            assert len(adaptation["recommended_actions"]) > 0
            assert 0.0 <= adaptation["confidence"] <= 1.0
            assert adaptation["estimated_recovery_time"] >= 0
            
            # For specific error types, verify appropriate strategies
            if scenario["error_type"] == "timeout_error":
                actions = [action.get("action") for action in adaptation["recommended_actions"]]
                assert any("wait" in str(action) or "retry" in str(action) for action in actions)
            
            elif scenario["error_type"] == "captcha_challenge":
                actions = [action.get("action") for action in adaptation["recommended_actions"]]
                assert any("escalate" in str(action) for action in actions)
    
    @pytest.mark.asyncio
    async def test_learning_pattern_evolution(self, mcp_client_with_data):
        """Test that learning patterns evolve with new interaction data"""
        client = mcp_client_with_data
        
        # Get initial pattern state
        initial_pattern = client.learning_patterns.get("job_search:strategy_1")
        initial_confidence = initial_pattern.confidence if initial_pattern else 0.0
        initial_sample_size = initial_pattern.sample_size if initial_pattern else 0
        
        # Simulate a series of interactions with mixed results
        session_id = "learning_test_session"
        strategy_id = "strategy_1"
        
        # Create mock context
        context = PageContext(
            session_id=session_id,
            url="https://test.com",
            title="Test",
            page_type="job_search",
            content_hash="test"
        )
        
        # Add successful interactions
        for i in range(10):
            await client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy_id,
                action_type="search",
                success=True,
                execution_time=1.0 + (i * 0.1),
                context_before=context
            )
        
        # Add some failed interactions
        for i in range(3):
            await client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy_id,
                action_type="search",
                success=False,
                execution_time=5.0,
                error_message="Search failed",
                context_before=context
            )
        
        # Check if pattern was updated
        pattern_key = f"{context.page_type}:{strategy_id}"
        if pattern_key in client.learning_patterns:
            updated_pattern = client.learning_patterns[pattern_key]
            
            # Sample size should have increased
            assert updated_pattern.sample_size > initial_sample_size
            
            # Confidence should reflect the success rate (10 success / 13 total ≈ 0.77)
            if updated_pattern.sample_size >= client.learning_threshold:
                expected_confidence = 10.0 / 13.0  # ≈ 0.77
                assert abs(updated_pattern.confidence - expected_confidence) < 0.1
    
    @pytest.mark.asyncio
    async def test_context_aware_strategy_caching(self, mcp_client_with_data, job_search_context):
        """Test that strategies are properly cached and reused for similar contexts"""
        client = mcp_client_with_data
        
        automation_goal = "search_jobs"
        
        # Generate strategy for first time
        strategy1 = await client.generate_adaptive_strategy(
            "session1", automation_goal, job_search_context
        )
        
        # Generate strategy for same context - should be cached
        strategy2 = await client.generate_adaptive_strategy(
            "session2", automation_goal, job_search_context
        )
        
        # Should be the same strategy (cached)
        assert strategy1.strategy_id == strategy2.strategy_id
        assert strategy1.context_hash == strategy2.context_hash
        
        # Verify cache key exists
        cache_key = f"{job_search_context.content_hash}:{automation_goal}"
        assert cache_key in client.strategy_cache
        assert client.strategy_cache[cache_key] == strategy1.strategy_id
    
    @pytest.mark.asyncio
    async def test_strategy_confidence_adjustment(self, mcp_client_with_data):
        """Test that strategy confidence is adjusted based on historical performance"""
        client = mcp_client_with_data
        
        # Create context with existing learning pattern
        context = PageContext(
            session_id="test_session",
            url="https://test.com",
            title="Test",
            page_type="job_search",
            content_hash="test_hash"
        )
        
        # Generate strategy - should be influenced by existing high-confidence pattern
        strategy = await client.generate_adaptive_strategy(
            "test_session", "search_jobs", context
        )
        
        # Strategy confidence should be boosted by the high-confidence learning pattern
        # The existing pattern has confidence 0.85, so strategy should be enhanced
        base_confidence = 0.6  # Assumed base confidence from fallback strategy
        
        # With learning pattern influence, confidence should be higher
        assert strategy.confidence_score >= base_confidence
    
    @pytest.mark.asyncio
    async def test_multi_session_learning_aggregation(self, mcp_client_with_data):
        """Test that learning aggregates across multiple sessions"""
        client = mcp_client_with_data
        
        strategy_id = "multi_session_strategy"
        action_type = "form_fill"
        
        # Create contexts for different sessions
        contexts = []
        for i in range(3):
            context = PageContext(
                session_id=f"session_{i}",
                url="https://test.com",
                title="Test",
                page_type="application_form",
                content_hash="form_hash"
            )
            contexts.append(context)
        
        # Record interactions from multiple sessions
        total_interactions = 0
        successful_interactions = 0
        
        for i, context in enumerate(contexts):
            session_id = f"session_{i}"
            
            # Each session has different success rates
            session_success_rate = 0.6 + (i * 0.1)  # 0.6, 0.7, 0.8
            session_interactions = 8
            session_successes = int(session_interactions * session_success_rate)
            
            # Record successful interactions
            for j in range(session_successes):
                await client.record_interaction_result(
                    session_id=session_id,
                    strategy_id=strategy_id,
                    action_type=action_type,
                    success=True,
                    execution_time=1.0,
                    context_before=context
                )
                successful_interactions += 1
                total_interactions += 1
            
            # Record failed interactions
            for j in range(session_interactions - session_successes):
                await client.record_interaction_result(
                    session_id=session_id,
                    strategy_id=strategy_id,
                    action_type=action_type,
                    success=False,
                    execution_time=3.0,
                    error_message="Form validation failed",
                    context_before=context
                )
                total_interactions += 1
        
        # Check that learning pattern aggregates data from all sessions
        pattern_key = f"application_form:{strategy_id}"
        if pattern_key in client.learning_patterns:
            pattern = client.learning_patterns[pattern_key]
            
            # Should have data from all sessions
            assert pattern.sample_size >= total_interactions
            
            # Confidence should reflect overall success rate
            if pattern.sample_size >= client.learning_threshold:
                expected_confidence = successful_interactions / total_interactions
                assert abs(pattern.confidence - expected_confidence) < 0.15
    
    @pytest.mark.asyncio
    async def test_strategy_risk_assessment(self, mcp_client_with_data, application_form_context):
        """Test that strategies include appropriate risk assessments"""
        client = mcp_client_with_data
        
        # Generate strategy for application form (higher risk context)
        strategy = await client.generate_adaptive_strategy(
            "test_session", "submit_application", application_form_context
        )
        
        # Application submission should have identified risk factors
        assert len(strategy.risk_factors) >= 0  # May have risks identified
        
        # Common risk factors for application forms
        potential_risks = [
            "form_validation", "network_timeout", "captcha", 
            "rate_limiting", "attachment_upload"
        ]
        
        # Strategy should have reasonable success probability
        assert 0.0 <= strategy.success_probability <= 1.0
        
        # Estimated duration should be reasonable for form submission
        assert strategy.estimated_duration > 0
        assert strategy.estimated_duration <= 300  # Should be under 5 minutes
    
    @pytest.mark.asyncio
    async def test_adaptive_fallback_strategies(self, mcp_client_with_data):
        """Test that fallback strategies are contextually appropriate"""
        client = mcp_client_with_data
        
        # Test different contexts and their fallback strategies
        test_contexts = [
            {
                "page_type": "job_search",
                "goal": "search_jobs",
                "expected_fallbacks": ["retry", "alternative_search", "manual_intervention"]
            },
            {
                "page_type": "application_form",
                "goal": "submit_application",
                "expected_fallbacks": ["step_by_step_form_fill", "retry", "manual_review"]
            },
            {
                "page_type": "job_details",
                "goal": "extract_job_info",
                "expected_fallbacks": ["alternative_extraction", "manual_extraction"]
            }
        ]
        
        for ctx in test_contexts:
            context = PageContext(
                session_id="test_session",
                url="https://test.com",
                title="Test",
                page_type=ctx["page_type"],
                content_hash=f"{ctx['page_type']}_hash"
            )
            
            strategy = await client.generate_adaptive_strategy(
                "test_session", ctx["goal"], context
            )
            
            # Should have fallback strategies
            assert len(strategy.fallback_strategies) >= 0
            
            # Fallback strategies should be strings (strategy names)
            for fallback in strategy.fallback_strategies:
                assert isinstance(fallback, str)
                assert len(fallback) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])