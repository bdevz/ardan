"""
MCP Integration layer connecting MCP client with browser automation components
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from mcp_client import MCPClient, PageContext, AutomationStrategy, InteractionResult
from stagehand_controller import StagehandController, NavigationResult, ExtractionResult, InteractionResult as StagehandInteractionResult
from director import DirectorOrchestrator
from browserbase_client import BrowserbaseClient
from shared.config import settings
from shared.utils import setup_logging, retry_async

logger = setup_logging("mcp-integration")


@dataclass
class MCPEnhancedResult:
    """Enhanced result with MCP context and adaptation"""
    original_result: Union[NavigationResult, ExtractionResult, StagehandInteractionResult]
    mcp_context: Optional[PageContext] = None
    applied_strategy: Optional[AutomationStrategy] = None
    adaptation_applied: Optional[Dict[str, Any]] = None
    learning_recorded: bool = False


class MCPIntegration:
    """Integration layer for MCP with browser automation components"""
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        stagehand_controller: Optional[StagehandController] = None,
        director: Optional[DirectorOrchestrator] = None,
        browserbase_client: Optional[BrowserbaseClient] = None
    ):
        self.mcp_client = mcp_client or MCPClient()
        self.stagehand_controller = stagehand_controller or StagehandController()
        self.director = director or DirectorOrchestrator()
        self.browserbase_client = browserbase_client or BrowserbaseClient()
        
        # Integration state
        self.active_strategies: Dict[str, AutomationStrategy] = {}
        self.session_contexts: Dict[str, PageContext] = {}
        
    async def initialize(self):
        """Initialize MCP integration"""
        logger.info("Initializing MCP integration...")
        
        try:
            await self.mcp_client.initialize()
            logger.info("MCP integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP integration: {e}")
            raise
    
    async def enhanced_navigate(
        self,
        session_id: str,
        target_description: str,
        automation_goal: str = "navigate",
        context_data: Optional[Dict[str, Any]] = None
    ) -> MCPEnhancedResult:
        """Enhanced navigation with MCP context analysis and adaptation"""
        try:
            # Capture initial page context
            initial_context = await self._capture_page_context(session_id, automation_goal)
            
            # Generate adaptive strategy
            strategy = await self.mcp_client.generate_adaptive_strategy(
                session_id, automation_goal, initial_context
            )
            
            self.active_strategies[session_id] = strategy
            
            # Execute navigation with strategy guidance
            nav_result = await self._execute_navigation_with_strategy(
                session_id, target_description, strategy, context_data
            )
            
            # Capture post-navigation context
            post_context = await self._capture_page_context(session_id, automation_goal)
            
            # Record interaction result for learning
            await self.mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy.strategy_id,
                action_type="navigation",
                success=nav_result.success,
                execution_time=nav_result.execution_time,
                error_message=nav_result.error_message,
                context_before=initial_context,
                context_after=post_context
            )
            
            # Handle errors with MCP adaptation if needed
            adaptation_applied = None
            if not nav_result.success:
                adaptation_applied = await self._handle_navigation_error(
                    session_id, nav_result, strategy
                )
            
            return MCPEnhancedResult(
                original_result=nav_result,
                mcp_context=post_context,
                applied_strategy=strategy,
                adaptation_applied=adaptation_applied,
                learning_recorded=True
            )
            
        except Exception as e:
            logger.error(f"Enhanced navigation failed for session {session_id}: {e}")
            # Return basic result on MCP failure
            nav_result = await self.stagehand_controller.intelligent_navigate(
                session_id, target_description
            )
            return MCPEnhancedResult(original_result=nav_result)
    
    async def enhanced_extract(
        self,
        session_id: str,
        extraction_prompt: str,
        extraction_type: str,
        automation_goal: str = "extract_content"
    ) -> MCPEnhancedResult:
        """Enhanced content extraction with MCP context analysis"""
        try:
            # Capture current page context
            current_context = await self._capture_page_context(session_id, automation_goal)
            
            # Generate extraction strategy
            strategy = await self.mcp_client.generate_adaptive_strategy(
                session_id, automation_goal, current_context
            )
            
            # Enhance extraction prompt with context insights
            enhanced_prompt = await self._enhance_extraction_prompt(
                extraction_prompt, current_context, strategy
            )
            
            # Execute extraction
            from stagehand_controller import ExtractionType
            extraction_result = await self.stagehand_controller.extract_content(
                session_id, enhanced_prompt, ExtractionType(extraction_type)
            )
            
            # Record interaction result
            await self.mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy.strategy_id,
                action_type="extraction",
                success=extraction_result.success,
                execution_time=0.0,  # Extraction doesn't track time
                error_message=extraction_result.error_message,
                context_before=current_context
            )
            
            # Handle extraction errors with adaptation
            adaptation_applied = None
            if not extraction_result.success:
                adaptation_applied = await self._handle_extraction_error(
                    session_id, extraction_result, strategy
                )
            
            return MCPEnhancedResult(
                original_result=extraction_result,
                mcp_context=current_context,
                applied_strategy=strategy,
                adaptation_applied=adaptation_applied,
                learning_recorded=True
            )
            
        except Exception as e:
            logger.error(f"Enhanced extraction failed for session {session_id}: {e}")
            # Fallback to basic extraction
            from stagehand_controller import ExtractionType
            extraction_result = await self.stagehand_controller.extract_content(
                session_id, extraction_prompt, ExtractionType(extraction_type)
            )
            return MCPEnhancedResult(original_result=extraction_result)
    
    async def enhanced_form_interaction(
        self,
        session_id: str,
        form_data: Dict[str, Any],
        submit: bool = False,
        automation_goal: str = "form_interaction"
    ) -> MCPEnhancedResult:
        """Enhanced form interaction with MCP context analysis"""
        try:
            # Capture pre-interaction context
            pre_context = await self._capture_page_context(session_id, automation_goal)
            
            # Generate interaction strategy
            strategy = await self.mcp_client.generate_adaptive_strategy(
                session_id, automation_goal, pre_context
            )
            
            # Optimize form data based on context
            optimized_form_data = await self._optimize_form_data(
                form_data, pre_context, strategy
            )
            
            # Execute form interaction
            interaction_result = await self.stagehand_controller.interact_with_form(
                session_id, optimized_form_data, submit
            )
            
            # Capture post-interaction context
            post_context = await self._capture_page_context(session_id, automation_goal)
            
            # Record interaction result
            await self.mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy.strategy_id,
                action_type="form_interaction",
                success=interaction_result.success,
                execution_time=0.0,
                error_message=interaction_result.error_message,
                context_before=pre_context,
                context_after=post_context
            )
            
            # Handle interaction errors
            adaptation_applied = None
            if not interaction_result.success:
                adaptation_applied = await self._handle_interaction_error(
                    session_id, interaction_result, strategy
                )
            
            return MCPEnhancedResult(
                original_result=interaction_result,
                mcp_context=post_context,
                applied_strategy=strategy,
                adaptation_applied=adaptation_applied,
                learning_recorded=True
            )
            
        except Exception as e:
            logger.error(f"Enhanced form interaction failed for session {session_id}: {e}")
            # Fallback to basic interaction
            interaction_result = await self.stagehand_controller.interact_with_form(
                session_id, form_data, submit
            )
            return MCPEnhancedResult(original_result=interaction_result)
    
    async def context_aware_error_recovery(
        self,
        session_id: str,
        error_context: Dict[str, Any],
        max_recovery_attempts: int = 3
    ) -> Dict[str, Any]:
        """Context-aware error recovery using MCP adaptation"""
        try:
            current_strategy = self.active_strategies.get(session_id)
            if not current_strategy:
                logger.warning(f"No active strategy for session {session_id}, using basic recovery")
                return {"recovery_attempted": False, "reason": "No active strategy"}
            
            # Get adaptation recommendations from MCP
            adaptation = await self.mcp_client.adapt_to_error(
                session_id, error_context, current_strategy
            )
            
            recovery_results = []
            
            # Execute adaptation recommendations
            for i, action in enumerate(adaptation["recommended_actions"]):
                if i >= max_recovery_attempts:
                    break
                
                try:
                    result = await self._execute_recovery_action(session_id, action)
                    recovery_results.append(result)
                    
                    if result.get("success", False):
                        logger.info(f"Recovery successful with action: {action['action']}")
                        return {
                            "recovery_attempted": True,
                            "recovery_successful": True,
                            "successful_action": action,
                            "attempts": i + 1,
                            "results": recovery_results
                        }
                
                except Exception as e:
                    logger.warning(f"Recovery action failed: {action['action']} - {e}")
                    recovery_results.append({"success": False, "error": str(e)})
            
            # All recovery attempts failed
            return {
                "recovery_attempted": True,
                "recovery_successful": False,
                "attempts": len(recovery_results),
                "results": recovery_results,
                "escalation_needed": True
            }
            
        except Exception as e:
            logger.error(f"Context-aware error recovery failed: {e}")
            return {
                "recovery_attempted": False,
                "error": str(e),
                "escalation_needed": True
            }
    
    async def get_enhanced_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session state with MCP insights"""
        try:
            # Get basic session state
            basic_state = await self.stagehand_controller.get_session_context(session_id)
            
            # Get MCP memory and insights
            mcp_memory = await self.mcp_client.get_session_memory(session_id)
            
            # Get current strategy
            current_strategy = self.active_strategies.get(session_id)
            
            # Combine all information
            enhanced_state = {
                "basic_state": basic_state,
                "mcp_memory": mcp_memory,
                "current_strategy": {
                    "strategy_id": current_strategy.strategy_id,
                    "automation_goal": current_strategy.automation_goal,
                    "confidence_score": current_strategy.confidence_score,
                    "success_probability": current_strategy.success_probability
                } if current_strategy else None,
                "session_insights": await self._generate_session_insights(session_id),
                "recommendations": await self._generate_session_recommendations(session_id)
            }
            
            return enhanced_state
            
        except Exception as e:
            logger.error(f"Failed to get enhanced session state: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    async def _capture_page_context(
        self,
        session_id: str,
        automation_goal: str
    ) -> Optional[PageContext]:
        """Capture current page context using browser automation tools"""
        try:
            # Get page state from Stagehand
            page_state = await self.stagehand_controller.capture_page_state(session_id)
            
            if not page_state:
                return None
            
            # Analyze context with MCP
            context = await self.mcp_client.analyze_page_context(
                session_id, page_state, automation_goal
            )
            
            self.session_contexts[session_id] = context
            return context
            
        except Exception as e:
            logger.warning(f"Failed to capture page context: {e}")
            return None
    
    async def _execute_navigation_with_strategy(
        self,
        session_id: str,
        target_description: str,
        strategy: AutomationStrategy,
        context_data: Optional[Dict[str, Any]]
    ) -> NavigationResult:
        """Execute navigation using strategy guidance"""
        try:
            # Use strategy recommendations to enhance navigation
            navigation_actions = [
                action for action in strategy.recommended_actions
                if action.get("action") in ["navigate", "click", "search"]
            ]
            
            if navigation_actions:
                # Execute strategy-guided navigation
                for action in navigation_actions:
                    if action["action"] == "navigate":
                        return await self.stagehand_controller.intelligent_navigate(
                            session_id, target_description
                        )
            
            # Fallback to standard navigation
            return await self.stagehand_controller.intelligent_navigate(
                session_id, target_description
            )
            
        except Exception as e:
            logger.error(f"Strategy-guided navigation failed: {e}")
            # Fallback to basic navigation
            return await self.stagehand_controller.intelligent_navigate(
                session_id, target_description
            )
    
    async def _enhance_extraction_prompt(
        self,
        original_prompt: str,
        context: PageContext,
        strategy: AutomationStrategy
    ) -> str:
        """Enhance extraction prompt with context insights"""
        try:
            # Add context-specific enhancements
            enhancements = []
            
            if context.page_type == "job_search":
                enhancements.append("Focus on job listings and their key details.")
            elif context.page_type == "job_details":
                enhancements.append("Extract comprehensive job information including requirements and client details.")
            elif context.page_type == "application_form":
                enhancements.append("Identify form fields and their requirements.")
            
            # Add interactive elements context
            if context.interactive_elements:
                element_types = [elem.get("type") for elem in context.interactive_elements]
                enhancements.append(f"Page contains these interactive elements: {', '.join(set(element_types))}")
            
            # Combine original prompt with enhancements
            if enhancements:
                enhanced_prompt = f"{original_prompt}\n\nContext insights:\n" + "\n".join(f"- {e}" for e in enhancements)
                return enhanced_prompt
            
            return original_prompt
            
        except Exception as e:
            logger.warning(f"Failed to enhance extraction prompt: {e}")
            return original_prompt
    
    async def _optimize_form_data(
        self,
        form_data: Dict[str, Any],
        context: PageContext,
        strategy: AutomationStrategy
    ) -> Dict[str, Any]:
        """Optimize form data based on context analysis"""
        try:
            optimized_data = form_data.copy()
            
            # Use context form fields to validate and optimize
            if context.form_fields:
                for field in context.form_fields:
                    field_name = field.get("name")
                    if field_name in optimized_data:
                        # Apply field-specific optimizations
                        if field.get("type") == "number":
                            # Ensure numeric values are properly formatted
                            try:
                                optimized_data[field_name] = float(optimized_data[field_name])
                            except (ValueError, TypeError):
                                pass
                        
                        elif field.get("required") and not optimized_data[field_name]:
                            logger.warning(f"Required field {field_name} is empty")
            
            return optimized_data
            
        except Exception as e:
            logger.warning(f"Failed to optimize form data: {e}")
            return form_data
    
    async def _handle_navigation_error(
        self,
        session_id: str,
        nav_result: NavigationResult,
        strategy: AutomationStrategy
    ) -> Optional[Dict[str, Any]]:
        """Handle navigation errors with MCP adaptation"""
        try:
            error_context = {
                "error_type": "navigation_error",
                "error_message": nav_result.error_message or "Navigation failed",
                "failed_action": "navigation",
                "target_url": nav_result.url
            }
            
            return await self.mcp_client.adapt_to_error(
                session_id, error_context, strategy
            )
            
        except Exception as e:
            logger.error(f"Failed to handle navigation error: {e}")
            return None
    
    async def _handle_extraction_error(
        self,
        session_id: str,
        extraction_result: ExtractionResult,
        strategy: AutomationStrategy
    ) -> Optional[Dict[str, Any]]:
        """Handle extraction errors with MCP adaptation"""
        try:
            error_context = {
                "error_type": "extraction_error",
                "error_message": extraction_result.error_message or "Extraction failed",
                "failed_action": "extraction",
                "extraction_type": extraction_result.extraction_type.value
            }
            
            return await self.mcp_client.adapt_to_error(
                session_id, error_context, strategy
            )
            
        except Exception as e:
            logger.error(f"Failed to handle extraction error: {e}")
            return None
    
    async def _handle_interaction_error(
        self,
        session_id: str,
        interaction_result: StagehandInteractionResult,
        strategy: AutomationStrategy
    ) -> Optional[Dict[str, Any]]:
        """Handle interaction errors with MCP adaptation"""
        try:
            error_context = {
                "error_type": "interaction_error",
                "error_message": interaction_result.error_message or "Interaction failed",
                "failed_action": interaction_result.action_performed,
                "validation_errors": interaction_result.validation_errors or []
            }
            
            return await self.mcp_client.adapt_to_error(
                session_id, error_context, strategy
            )
            
        except Exception as e:
            logger.error(f"Failed to handle interaction error: {e}")
            return None
    
    async def _execute_recovery_action(
        self,
        session_id: str,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific recovery action"""
        action_type = action.get("action")
        
        try:
            if action_type == "wait":
                duration = action.get("duration", 3)
                await asyncio.sleep(duration)
                return {"success": True, "action": "wait", "duration": duration}
            
            elif action_type == "retry_last_action":
                # This would require storing the last action
                return {"success": False, "error": "Retry not implemented"}
            
            elif action_type == "refresh_page":
                stagehand = await self.stagehand_controller.get_stagehand(session_id)
                await stagehand.page.reload(wait_until="networkidle")
                return {"success": True, "action": "refresh_page"}
            
            elif action_type == "navigate_back":
                stagehand = await self.stagehand_controller.get_stagehand(session_id)
                await stagehand.page.go_back(wait_until="networkidle")
                return {"success": True, "action": "navigate_back"}
            
            elif action_type == "escalate_to_human":
                logger.warning(f"Escalating error to human for session {session_id}")
                return {"success": True, "action": "escalate_to_human", "escalated": True}
            
            else:
                return {"success": False, "error": f"Unknown recovery action: {action_type}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_session_insights(self, session_id: str) -> Dict[str, Any]:
        """Generate insights about the current session"""
        try:
            current_context = self.session_contexts.get(session_id)
            current_strategy = self.active_strategies.get(session_id)
            
            insights = {
                "page_analysis": {},
                "strategy_performance": {},
                "recommendations": []
            }
            
            if current_context:
                insights["page_analysis"] = {
                    "page_type": current_context.page_type,
                    "complexity": len(current_context.interactive_elements),
                    "has_forms": len(current_context.form_fields) > 0,
                    "error_indicators": len(current_context.error_indicators),
                    "success_indicators": len(current_context.success_indicators)
                }
            
            if current_strategy:
                insights["strategy_performance"] = {
                    "confidence": current_strategy.confidence_score,
                    "success_probability": current_strategy.success_probability,
                    "estimated_duration": current_strategy.estimated_duration,
                    "risk_factors": current_strategy.risk_factors
                }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate session insights: {e}")
            return {}
    
    async def _generate_session_recommendations(self, session_id: str) -> List[str]:
        """Generate recommendations for the current session"""
        try:
            recommendations = []
            
            current_context = self.session_contexts.get(session_id)
            current_strategy = self.active_strategies.get(session_id)
            
            if current_context:
                if current_context.error_indicators:
                    recommendations.append("Page shows error indicators - consider error recovery")
                
                if not current_context.interactive_elements:
                    recommendations.append("Page has limited interactive elements - verify page loaded correctly")
                
                if current_context.page_type == "unknown":
                    recommendations.append("Page type unclear - may need manual verification")
            
            if current_strategy:
                if current_strategy.confidence_score < 0.5:
                    recommendations.append("Strategy confidence is low - consider manual oversight")
                
                if current_strategy.risk_factors:
                    recommendations.append(f"Strategy has risk factors: {', '.join(current_strategy.risk_factors)}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate session recommendations: {e}")
            return []
    
    async def cleanup(self):
        """Clean up MCP integration resources"""
        logger.info("Cleaning up MCP integration...")
        
        try:
            await self.mcp_client.cleanup()
            
            # Clear state
            self.active_strategies.clear()
            self.session_contexts.clear()
            
            logger.info("MCP integration cleanup complete")
            
        except Exception as e:
            logger.error(f"MCP integration cleanup failed: {e}")