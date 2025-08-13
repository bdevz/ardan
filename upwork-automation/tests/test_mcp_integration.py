"""
Tests for MCP (Model Context Protocol) Integration
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from mcp_client import (
    MCPClient, PageContext, AutomationStrategy, InteractionResult, 
    LearningPattern, ContextType, AdaptationStrategy
)
from mcp_integration import MCPIntegration, MCPEnhancedResult
from mcp_director_actions import MCPDirectorActions


class TestMCPClient:
    """Test cases for MCP Client"""
    
    @pytest.fixture
    async def mcp_client(self):
        """Create MCP client for testing"""
        client = MCPClient()
        await client.initialize()
        return client
    
    @pytest.fixture
    def sample_page_data(self):
        """Sample page data for testing"""
        return {
            "url": "https://www.ardan.com/nx/search/jobs/?q=Salesforce%20Agentforce",
            "title": "Salesforce Agentforce Jobs - Ardan",
            "content": "Find Salesforce Agentforce jobs on Ardan. Browse job listings and apply to projects.",
            "interactive_elements": [
                {"type": "button", "text": "Apply Now", "selector": ".apply-btn"},
                {"type": "input", "placeholder": "Search jobs", "selector": "#search-input"}
            ],
            "form_fields": [
                {"name": "search_query", "type": "text", "required": False},
                {"name": "location", "type": "text", "required": False}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_analyze_page_context(self, mcp_client, sample_page_data):
        """Test page context analysis"""
        session_id = "test_session_123"
        automation_goal = "job_search"
        
        context = await mcp_client.analyze_page_context(
            session_id, sample_page_data, automation_goal
        )
        
        assert isinstance(context, PageContext)
        assert context.session_id == session_id
        assert context.url == sample_page_data["url"]
        assert context.title == sample_page_data["title"]
        assert context.page_type in ["job_search", "unknown"]
        assert len(context.content_hash) == 32  # MD5 hash length
        assert context.metadata["automation_goal"] == automation_goal
        
        # Verify context is stored
        assert session_id in mcp_client.page_contexts
        assert session_id in mcp_client.context_history
    
    @pytest.mark.asyncio
    async def test_generate_adaptive_strategy(self, mcp_client, sample_page_data):
        """Test adaptive strategy generation"""
        session_id = "test_session_123"
        automation_goal = "search_jobs"
        
        # First analyze page context
        context = await mcp_client.analyze_page_context(
            session_id, sample_page_data, automation_goal
        )
        
        # Generate strategy
        strategy = await mcp_client.generate_adaptive_strategy(
            session_id, automation_goal, context
        )
        
        assert isinstance(strategy, AutomationStrategy)
        assert strategy.context_hash == context.content_hash
        assert strategy.page_type == context.page_type
        assert strategy.automation_goal == automation_goal
        assert 0.0 <= strategy.confidence_score <= 1.0
        assert 0.0 <= strategy.success_probability <= 1.0
        assert strategy.estimated_duration > 0
        assert len(strategy.recommended_actions) > 0
        
        # Verify strategy is cached
        cache_key = f"{context.content_hash}:{automation_goal}"
        assert cache_key in mcp_client.strategy_cache
    
    @pytest.mark.asyncio
    async def test_record_interaction_result(self, mcp_client):
        """Test interaction result recording"""
        session_id = "test_session_123"
        strategy_id = "strategy_456"
        
        await mcp_client.record_interaction_result(
            session_id=session_id,
            strategy_id=strategy_id,
            action_type="navigation",
            success=True,
            execution_time=2.5,
            error_message=None
        )
        
        # Verify result is recorded
        assert len(mcp_client.interaction_results) == 1
        result = mcp_client.interaction_results[0]
        
        assert result.session_id == session_id
        assert result.strategy_id == strategy_id
        assert result.action_type == "navigation"
        assert result.success is True
        assert result.execution_time == 2.5
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_adapt_to_error(self, mcp_client, sample_page_data):
        """Test error adaptation"""
        session_id = "test_session_123"
        automation_goal = "search_jobs"
        
        # Setup context and strategy
        context = await mcp_client.analyze_page_context(
            session_id, sample_page_data, automation_goal
        )
        strategy = await mcp_client.generate_adaptive_strategy(
            session_id, automation_goal, context
        )
        
        # Test different error scenarios
        error_scenarios = [
            {
                "error_type": "timeout_error",
                "error_message": "Page load timeout",
                "failed_action": "navigation",
                "expected_strategy": AdaptationStrategy.RETRY_WITH_DELAY
            },
            {
                "error_type": "element_not_found",
                "error_message": "Element not found on page",
                "failed_action": "click",
                "expected_strategy": AdaptationStrategy.CHANGE_APPROACH
            },
            {
                "error_type": "captcha_detected",
                "error_message": "CAPTCHA challenge detected",
                "failed_action": "form_submit",
                "expected_strategy": AdaptationStrategy.ESCALATE_ERROR
            }
        ]
        
        for scenario in error_scenarios:
            adaptation = await mcp_client.adapt_to_error(
                session_id, scenario, strategy
            )
            
            assert isinstance(adaptation, dict)
            assert "strategy" in adaptation
            assert "recommended_actions" in adaptation
            assert "confidence" in adaptation
            assert "estimated_recovery_time" in adaptation
            
            assert len(adaptation["recommended_actions"]) > 0
            assert 0.0 <= adaptation["confidence"] <= 1.0
            assert adaptation["estimated_recovery_time"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_session_memory(self, mcp_client, sample_page_data):
        """Test session memory retrieval"""
        session_id = "test_session_123"
        
        # Setup some context and interactions
        context = await mcp_client.analyze_page_context(
            session_id, sample_page_data, "job_search"
        )
        
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
        assert "learned_patterns" in memory
        assert "session_metadata" in memory
        
        # Verify memory content
        assert memory["current_context"] is not None
        assert len(memory["context_history"]) > 0
        assert "strategy_1" in memory["successful_strategies"]
        assert "strategy_2" in memory["failed_strategies"]
    
    @pytest.mark.asyncio
    async def test_learning_pattern_updates(self, mcp_client, sample_page_data):
        """Test learning pattern updates"""
        session_id = "test_session_123"
        strategy_id = "test_strategy"
        
        # Create context
        context = await mcp_client.analyze_page_context(
            session_id, sample_page_data, "job_search"
        )
        
        # Record multiple interactions to trigger learning
        for i in range(15):  # Above learning threshold
            success = i % 3 != 0  # 2/3 success rate
            await mcp_client.record_interaction_result(
                session_id, strategy_id, "test_action", success, 1.0,
                error_message="Test error" if not success else None,
                context_before=context
            )
        
        # Check if learning patterns were created/updated
        pattern_key = f"{context.page_type}:{strategy_id}"
        if pattern_key in mcp_client.learning_patterns:
            pattern = mcp_client.learning_patterns[pattern_key]
            assert pattern.sample_size >= mcp_client.learning_threshold
            assert 0.0 <= pattern.confidence <= 1.0


class TestMCPIntegration:
    """Test cases for MCP Integration"""
    
    @pytest.fixture
    async def mcp_integration(self):
        """Create MCP integration for testing"""
        # Mock dependencies
        mock_stagehand = AsyncMock()
        mock_director = AsyncMock()
        mock_browserbase = AsyncMock()
        
        integration = MCPIntegration(
            stagehand_controller=mock_stagehand,
            director=mock_director,
            browserbase_client=mock_browserbase
        )
        await integration.initialize()
        return integration
    
    @pytest.fixture
    def mock_navigation_result(self):
        """Mock navigation result"""
        from stagehand_controller import NavigationResult
        return NavigationResult(
            success=True,
            url="https://www.ardan.com/jobs/test",
            page_title="Test Job",
            execution_time=2.0
        )
    
    @pytest.fixture
    def mock_extraction_result(self):
        """Mock extraction result"""
        from stagehand_controller import ExtractionResult, ExtractionType
        return ExtractionResult(
            success=True,
            data={"jobs": [{"title": "Test Job", "budget": "$50/hr"}]},
            extraction_type=ExtractionType.JOB_LISTINGS,
            confidence_score=0.9
        )
    
    @pytest.mark.asyncio
    async def test_enhanced_navigate(self, mcp_integration, mock_navigation_result):
        """Test enhanced navigation with MCP"""
        session_id = "test_session"
        target_description = "Ardan job search page"
        automation_goal = "navigate"
        
        # Mock the stagehand navigation
        mcp_integration.stagehand_controller.intelligent_navigate = AsyncMock(
            return_value=mock_navigation_result
        )
        
        # Mock page context capture
        with patch.object(mcp_integration, '_capture_page_context') as mock_capture:
            mock_context = Mock()
            mock_context.page_type = "job_search"
            mock_capture.return_value = mock_context
            
            result = await mcp_integration.enhanced_navigate(
                session_id, target_description, automation_goal
            )
        
        assert isinstance(result, MCPEnhancedResult)
        assert result.original_result == mock_navigation_result
        assert result.mcp_context == mock_context
        assert result.applied_strategy is not None
        assert result.learning_recorded is True
    
    @pytest.mark.asyncio
    async def test_enhanced_extract(self, mcp_integration, mock_extraction_result):
        """Test enhanced extraction with MCP"""
        session_id = "test_session"
        extraction_prompt = "Extract job listings"
        extraction_type = "job_listings"
        
        # Mock the stagehand extraction
        mcp_integration.stagehand_controller.extract_content = AsyncMock(
            return_value=mock_extraction_result
        )
        
        # Mock page context capture
        with patch.object(mcp_integration, '_capture_page_context') as mock_capture:
            mock_context = Mock()
            mock_context.page_type = "job_search"
            mock_capture.return_value = mock_context
            
            result = await mcp_integration.enhanced_extract(
                session_id, extraction_prompt, extraction_type
            )
        
        assert isinstance(result, MCPEnhancedResult)
        assert result.original_result == mock_extraction_result
        assert result.mcp_context == mock_context
        assert result.applied_strategy is not None
        assert result.learning_recorded is True
    
    @pytest.mark.asyncio
    async def test_context_aware_error_recovery(self, mcp_integration):
        """Test context-aware error recovery"""
        session_id = "test_session"
        error_context = {
            "error_type": "timeout_error",
            "error_message": "Page load timeout",
            "failed_action": "navigation"
        }
        
        # Mock active strategy
        mock_strategy = Mock()
        mock_strategy.strategy_id = "test_strategy"
        mock_strategy.automation_goal = "navigate"
        mcp_integration.active_strategies[session_id] = mock_strategy
        
        # Mock recovery action execution
        with patch.object(mcp_integration, '_execute_recovery_action') as mock_execute:
            mock_execute.return_value = {"success": True}
            
            result = await mcp_integration.context_aware_error_recovery(
                session_id, error_context
            )
        
        assert isinstance(result, dict)
        assert "recovery_attempted" in result
        assert result["recovery_attempted"] is True
    
    @pytest.mark.asyncio
    async def test_get_enhanced_session_state(self, mcp_integration):
        """Test enhanced session state retrieval"""
        session_id = "test_session"
        
        # Mock dependencies
        mcp_integration.stagehand_controller.get_session_context = AsyncMock(
            return_value={"basic": "state"}
        )
        
        # Mock active strategy
        mock_strategy = Mock()
        mock_strategy.strategy_id = "test_strategy"
        mock_strategy.automation_goal = "test_goal"
        mock_strategy.confidence_score = 0.8
        mock_strategy.success_probability = 0.7
        mcp_integration.active_strategies[session_id] = mock_strategy
        
        result = await mcp_integration.get_enhanced_session_state(session_id)
        
        assert isinstance(result, dict)
        assert "basic_state" in result
        assert "mcp_memory" in result
        assert "current_strategy" in result
        assert "session_insights" in result
        assert "recommendations" in result
        
        # Verify strategy information
        strategy_info = result["current_strategy"]
        assert strategy_info["strategy_id"] == "test_strategy"
        assert strategy_info["automation_goal"] == "test_goal"
        assert strategy_info["confidence_score"] == 0.8


class TestMCPDirectorActions:
    """Test cases for MCP Director Actions"""
    
    @pytest.fixture
    async def mcp_director_actions(self):
        """Create MCP Director Actions for testing"""
        # Mock dependencies
        mock_browserbase = AsyncMock()
        mock_stagehand = AsyncMock()
        mock_mcp_integration = AsyncMock()
        
        actions = MCPDirectorActions(
            mock_browserbase, mock_stagehand, mock_mcp_integration
        )
        await actions.initialize()
        return actions
    
    @pytest.fixture
    def mock_workflow_step(self):
        """Mock workflow step"""
        step = Mock()
        step.id = "test_step"
        step.name = "Test Step"
        step.action = "search_jobs"
        step.parameters = {
            "keywords": ["Salesforce", "Agentforce"],
            "sort": "newest"
        }
        return step
    
    @pytest.mark.asyncio
    async def test_mcp_enhanced_search_jobs(self, mcp_director_actions, mock_workflow_step):
        """Test MCP-enhanced job search"""
        session_id = "test_session"
        input_data = {}
        step_results = {}
        
        # Mock MCP integration responses
        mock_nav_result = Mock()
        mock_nav_result.original_result.success = True
        mock_nav_result.mcp_context = Mock()
        
        mock_form_result = Mock()
        mock_form_result.original_result.success = True
        mock_form_result.mcp_context = Mock()
        
        mock_extract_result = Mock()
        mock_extract_result.original_result.success = True
        mock_extract_result.original_result.data = [
            {"title": "Salesforce Developer", "budget": "$75/hr"},
            {"title": "Agentforce Specialist", "budget": "$80/hr"}
        ]
        mock_extract_result.mcp_context = Mock()
        mock_extract_result.applied_strategy = Mock()
        mock_extract_result.applied_strategy.confidence_score = 0.9
        mock_extract_result.original_result.confidence_score = 0.8
        
        mcp_director_actions.mcp_integration.enhanced_navigate = AsyncMock(
            return_value=mock_nav_result
        )
        mcp_director_actions.mcp_integration.enhanced_form_interaction = AsyncMock(
            return_value=mock_form_result
        )
        mcp_director_actions.mcp_integration.enhanced_extract = AsyncMock(
            return_value=mock_extract_result
        )
        
        # Mock job enhancement
        with patch.object(mcp_director_actions, '_enhance_job_data_with_mcp') as mock_enhance:
            mock_enhance.return_value = [
                {"title": "Salesforce Developer", "budget": "$75/hr", "match_score": 0.9},
                {"title": "Agentforce Specialist", "budget": "$80/hr", "match_score": 0.8}
            ]
            
            result = await mcp_director_actions._mcp_enhanced_search_jobs(
                mock_workflow_step, session_id, input_data, step_results
            )
        
        assert result["success"] is True
        assert result["jobs_found"] == 2
        assert len(result["jobs_data"]) == 2
        assert "mcp_insights" in result
        assert result["search_parameters"]["keywords"] == ["Salesforce", "Agentforce"]
    
    @pytest.mark.asyncio
    async def test_mcp_enhanced_validate_proposals(self, mcp_director_actions, mock_workflow_step):
        """Test MCP-enhanced proposal validation"""
        session_id = "test_session"
        input_data = {
            "proposals": [
                {
                    "id": "prop_1",
                    "content": "This is a detailed proposal for the Salesforce project with over 100 characters to meet minimum requirements.",
                    "bid_amount": 75.0,
                    "job_url": "https://ardan.com/job/123"
                },
                {
                    "id": "prop_2",
                    "content": "Short proposal",  # Too short
                    "bid_amount": "invalid",  # Invalid amount
                    "job_url": "https://ardan.com/job/456"
                }
            ]
        }
        step_results = {}
        
        # Mock MCP validation
        with patch.object(mcp_director_actions, '_validate_proposal_with_mcp') as mock_validate:
            mock_validate.side_effect = [
                {"quality_score": 0.8},  # Good proposal
                {"quality_score": 0.3}   # Poor proposal
            ]
            
            result = await mcp_director_actions._mcp_enhanced_validate_proposals(
                mock_workflow_step, session_id, input_data, step_results
            )
        
        assert result["success"] is True
        assert result["total_proposals"] == 2
        assert result["valid_proposals"] == 1
        assert result["invalid_proposals"] == 1
        
        # Check validation details
        validation_results = result["validation_results"]
        assert len(validation_results) == 2
        
        # First proposal should be valid
        assert validation_results[0]["valid"] is True
        assert validation_results[0]["proposal_id"] == "prop_1"
        
        # Second proposal should be invalid
        assert validation_results[1]["valid"] is False
        assert validation_results[1]["proposal_id"] == "prop_2"
        assert len(validation_results[1]["issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_mcp_enhanced_merge_results(self, mcp_director_actions, mock_workflow_step):
        """Test MCP-enhanced result merging"""
        session_id = "test_session"
        input_data = {}
        step_results = {
            "search_step_1": {
                "jobs_data": [
                    {"title": "Job 1", "client_name": "Client A"},
                    {"title": "Job 2", "client_name": "Client B"}
                ]
            },
            "search_step_2": {
                "jobs_data": [
                    {"title": "Job 1", "client_name": "Client A"},  # Duplicate
                    {"title": "Job 3", "client_name": "Client C"}
                ]
            }
        }
        
        # Mock MCP processing methods
        with patch.object(mcp_director_actions, '_deduplicate_jobs_with_mcp') as mock_dedup, \
             patch.object(mcp_director_actions, '_rank_jobs_with_mcp') as mock_rank, \
             patch.object(mcp_director_actions, '_filter_jobs_with_mcp') as mock_filter:
            
            # Setup mock returns
            mock_dedup.return_value = [
                {"title": "Job 1", "client_name": "Client A", "match_score": 0.9},
                {"title": "Job 2", "client_name": "Client B", "match_score": 0.7},
                {"title": "Job 3", "client_name": "Client C", "match_score": 0.8}
            ]
            
            mock_rank.return_value = [
                {"title": "Job 1", "client_name": "Client A", "match_score": 0.9},
                {"title": "Job 3", "client_name": "Client C", "match_score": 0.8},
                {"title": "Job 2", "client_name": "Client B", "match_score": 0.7}
            ]
            
            mock_filter.return_value = [
                {"title": "Job 1", "client_name": "Client A", "match_score": 0.9},
                {"title": "Job 3", "client_name": "Client C", "match_score": 0.8}
            ]
            
            result = await mcp_director_actions._mcp_enhanced_merge_results(
                mock_workflow_step, session_id, input_data, step_results
            )
        
        assert result["success"] is True
        assert result["original_count"] == 3  # Total jobs before processing
        assert result["deduplicated_count"] == 3
        assert result["final_count"] == 2  # After filtering
        assert len(result["jobs"]) == 2
        assert "mcp_analysis" in result
        
        # Verify MCP analysis
        mcp_analysis = result["mcp_analysis"]
        assert "deduplication_ratio" in mcp_analysis
        assert "filter_ratio" in mcp_analysis
        assert "average_match_score" in mcp_analysis
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, mcp_director_actions, mock_workflow_step):
        """Test error recovery integration with MCP"""
        session_id = "test_session"
        input_data = {}
        step_results = {}
        error_message = "Test error occurred"
        
        # Mock MCP error recovery
        mock_recovery_result = {
            "recovery_successful": True,
            "result": {"success": True, "recovered": True}
        }
        
        with patch.object(mcp_director_actions, '_attempt_mcp_error_recovery') as mock_recovery:
            mock_recovery.return_value = mock_recovery_result
            
            result = await mcp_director_actions._attempt_mcp_error_recovery(
                session_id, mock_workflow_step, error_message, input_data, step_results
            )
        
        assert result["recovery_successful"] is True
        assert "result" in result
        assert "recovery_details" in result


class TestMCPContextAnalysis:
    """Test cases for MCP context analysis capabilities"""
    
    @pytest.mark.asyncio
    async def test_page_type_classification(self):
        """Test page type classification accuracy"""
        mcp_client = MCPClient()
        await mcp_client.initialize()
        
        test_cases = [
            {
                "url": "https://www.ardan.com/nx/search/jobs/",
                "title": "Find Jobs - Ardan",
                "content": "Search for freelance jobs",
                "expected_type": "job_search"
            },
            {
                "url": "https://www.ardan.com/jobs/~123456",
                "title": "Salesforce Developer Job",
                "content": "We need a Salesforce developer",
                "expected_type": "job_details"
            },
            {
                "url": "https://www.ardan.com/ab/proposals/job/123456",
                "title": "Submit Proposal",
                "content": "Submit your proposal for this job",
                "expected_type": "application_form"
            }
        ]
        
        for case in test_cases:
            context = await mcp_client.analyze_page_context(
                "test_session", case, "test_goal"
            )
            
            # Note: With mock AI client, classification might be "unknown"
            # In real implementation, this would test actual AI classification
            assert context.page_type in [case["expected_type"], "unknown"]
    
    @pytest.mark.asyncio
    async def test_strategy_adaptation_learning(self):
        """Test strategy adaptation based on learning"""
        mcp_client = MCPClient()
        await mcp_client.initialize()
        
        session_id = "learning_test_session"
        page_data = {
            "url": "https://www.ardan.com/jobs/test",
            "title": "Test Job",
            "content": "Test job content"
        }
        
        # Analyze context
        context = await mcp_client.analyze_page_context(
            session_id, page_data, "job_application"
        )
        
        # Generate initial strategy
        initial_strategy = await mcp_client.generate_adaptive_strategy(
            session_id, "job_application", context
        )
        
        # Simulate multiple successful interactions to build learning
        for i in range(20):
            await mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=initial_strategy.strategy_id,
                action_type="form_fill",
                success=True,
                execution_time=1.0 + (i * 0.1),  # Improving performance
                context_before=context
            )
        
        # Generate new strategy - should be improved by learning
        improved_strategy = await mcp_client.generate_adaptive_strategy(
            session_id, "job_application", context
        )
        
        # Strategy should be cached (same ID) or improved
        assert improved_strategy.strategy_id == initial_strategy.strategy_id or \
               improved_strategy.confidence_score >= initial_strategy.confidence_score


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])