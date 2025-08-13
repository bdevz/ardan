"""
MCP (Model Context Protocol) Integration Demo

This demo shows how the MCP integration works with browser automation
for intelligent context-aware automation strategies.
"""
import asyncio
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'browser-automation'))

from datetime import datetime

# Mock the shared module to avoid import errors
class MockSettings:
    openai_api_key = "test_key"
    debug = False

class MockSharedConfig:
    settings = MockSettings()

class MockSharedUtils:
    def setup_logging(name):
        import logging
        return logging.getLogger(name)

sys.modules['shared'] = type('MockShared', (), {})()
sys.modules['shared.config'] = MockSharedConfig()
sys.modules['shared.utils'] = MockSharedUtils()
sys.modules['shared.models'] = type('MockModels', (), {})()

from mcp_client import MCPClient, PageContext, AutomationStrategy


async def demo_mcp_context_analysis():
    """Demo MCP page context analysis"""
    print("=== MCP Context Analysis Demo ===")
    
    # Initialize MCP client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    # Sample page data for different Ardan pages
    job_search_page = {
        "url": "https://www.ardan.com/nx/search/jobs/?q=Salesforce%20Agentforce",
        "title": "Salesforce Agentforce Jobs - Ardan",
        "content": "Find Salesforce Agentforce jobs on Ardan. Browse job listings and apply to projects.",
    }
    
    job_details_page = {
        "url": "https://www.ardan.com/jobs/~123456789",
        "title": "Salesforce Agentforce Developer Needed - Ardan",
        "content": "We need an experienced Salesforce Agentforce developer to build AI agents for our customer service platform.",
    }
    
    application_form_page = {
        "url": "https://www.ardan.com/ab/proposals/job/123456789",
        "title": "Submit Proposal - Ardan",
        "content": "Submit your proposal for this Salesforce Agentforce project. Include your cover letter and bid amount.",
    }
    
    # Analyze different page contexts
    pages = [
        ("Job Search", job_search_page, "search_jobs"),
        ("Job Details", job_details_page, "extract_job_info"),
        ("Application Form", application_form_page, "submit_application")
    ]
    
    for page_name, page_data, automation_goal in pages:
        print(f"\n--- Analyzing {page_name} Page ---")
        
        session_id = f"demo_session_{page_name.lower().replace(' ', '_')}"
        
        # Analyze page context
        context = await mcp_client.analyze_page_context(
            session_id, page_data, automation_goal
        )
        
        print(f"Page Type: {context.page_type}")
        print(f"URL: {context.url}")
        print(f"Content Hash: {context.content_hash[:8]}...")
        print(f"Automation Goal: {automation_goal}")
        
        # Generate adaptive strategy
        strategy = await mcp_client.generate_adaptive_strategy(
            session_id, automation_goal, context
        )
        
        print(f"Strategy ID: {strategy.strategy_id[:8]}...")
        print(f"Confidence Score: {strategy.confidence_score:.2f}")
        print(f"Success Probability: {strategy.success_probability:.2f}")
        print(f"Estimated Duration: {strategy.estimated_duration}s")
        print(f"Recommended Actions: {len(strategy.recommended_actions)}")
        
        # Show first few actions
        for i, action in enumerate(strategy.recommended_actions[:3]):
            print(f"  Action {i+1}: {action.get('action', 'unknown')}")
        
        if len(strategy.recommended_actions) > 3:
            print(f"  ... and {len(strategy.recommended_actions) - 3} more actions")
    
    await mcp_client.cleanup()


async def demo_mcp_learning_system():
    """Demo MCP learning system with interaction results"""
    print("\n=== MCP Learning System Demo ===")
    
    # Initialize MCP client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    # Create a consistent context for learning
    context = PageContext(
        session_id="learning_demo_session",
        url="https://www.ardan.com/jobs/search",
        title="Job Search",
        page_type="job_search",
        content_hash="learning_demo_hash",
        interactive_elements=[
            {"type": "input", "name": "search_input"},
            {"type": "button", "name": "search_button"}
        ]
    )
    
    # Store context
    mcp_client.page_contexts["learning_demo_session"] = context
    
    # Generate initial strategy
    strategy = await mcp_client.generate_adaptive_strategy(
        "learning_demo_session", "search_jobs", context
    )
    
    print(f"Initial Strategy Confidence: {strategy.confidence_score:.2f}")
    
    # Simulate multiple interactions with varying success rates
    print("\nSimulating interactions to build learning patterns...")
    
    interaction_scenarios = [
        # Early interactions - mixed results
        (True, 1.5, None, "Initial successful search"),
        (False, 5.0, "Timeout error", "Search timeout"),
        (True, 2.0, None, "Successful retry"),
        (True, 1.8, None, "Another successful search"),
        (False, 4.0, "Element not found", "Button not found"),
        
        # Middle interactions - improving success rate
        (True, 1.2, None, "Optimized search"),
        (True, 1.3, None, "Fast successful search"),
        (True, 1.1, None, "Very fast search"),
        (False, 3.0, "Rate limited", "Too many requests"),
        (True, 1.4, None, "Successful after rate limit"),
        
        # Later interactions - high success rate
        (True, 1.0, None, "Highly optimized search"),
        (True, 0.9, None, "Fastest search yet"),
        (True, 1.1, None, "Consistent performance"),
        (True, 1.0, None, "Excellent performance"),
        (True, 0.8, None, "Peak performance"),
    ]
    
    successful_count = 0
    total_count = len(interaction_scenarios)
    
    for i, (success, exec_time, error_msg, description) in enumerate(interaction_scenarios):
        await mcp_client.record_interaction_result(
            session_id="learning_demo_session",
            strategy_id=strategy.strategy_id,
            action_type="search",
            success=success,
            execution_time=exec_time,
            error_message=error_msg,
            context_before=context
        )
        
        if success:
            successful_count += 1
        
        # Show progress every 5 interactions
        if (i + 1) % 5 == 0:
            current_success_rate = successful_count / (i + 1)
            print(f"  After {i + 1} interactions: {current_success_rate:.1%} success rate")
    
    # Check if learning patterns were created
    pattern_key = f"{context.page_type}:{strategy.strategy_id}"
    if pattern_key in mcp_client.learning_patterns:
        pattern = mcp_client.learning_patterns[pattern_key]
        print(f"\nLearning Pattern Created:")
        print(f"  Pattern ID: {pattern.pattern_id}")
        print(f"  Sample Size: {pattern.sample_size}")
        print(f"  Confidence: {pattern.confidence:.2f}")
        print(f"  Page Type: {pattern.page_type}")
    else:
        print(f"\nLearning pattern not yet created (need {mcp_client.learning_threshold} samples)")
    
    # Generate new strategy to see if learning was applied
    new_strategy = await mcp_client.generate_adaptive_strategy(
        "learning_demo_session_2", "search_jobs", context
    )
    
    print(f"\nStrategy Comparison:")
    print(f"  Original Confidence: {strategy.confidence_score:.2f}")
    print(f"  New Strategy Confidence: {new_strategy.confidence_score:.2f}")
    
    if new_strategy.confidence_score > strategy.confidence_score:
        print("  ✓ Learning improved strategy confidence!")
    else:
        print("  → Strategy confidence maintained")
    
    await mcp_client.cleanup()


async def demo_mcp_error_adaptation():
    """Demo MCP error adaptation strategies"""
    print("\n=== MCP Error Adaptation Demo ===")
    
    # Initialize MCP client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    # Create a strategy for testing error adaptation
    strategy = AutomationStrategy(
        strategy_id="error_demo_strategy",
        context_hash="error_demo_hash",
        page_type="application_form",
        automation_goal="submit_application",
        recommended_actions=[
            {"action": "fill_form", "target": "cover_letter"},
            {"action": "upload_files", "target": "attachments"},
            {"action": "submit", "target": "submit_button"}
        ],
        fallback_strategies=["manual_review", "retry_submission"]
    )
    
    # Test different error scenarios
    error_scenarios = [
        {
            "name": "Timeout Error",
            "error_context": {
                "error_type": "timeout_error",
                "error_message": "Request timeout after 30 seconds",
                "failed_action": "form_submit"
            }
        },
        {
            "name": "Element Not Found",
            "error_context": {
                "error_type": "element_not_found",
                "error_message": "Could not locate submit button",
                "failed_action": "click_submit"
            }
        },
        {
            "name": "Validation Error",
            "error_context": {
                "error_type": "validation_error",
                "error_message": "Cover letter is required",
                "failed_action": "form_validation"
            }
        },
        {
            "name": "CAPTCHA Challenge",
            "error_context": {
                "error_type": "captcha_challenge",
                "error_message": "Please complete CAPTCHA verification",
                "failed_action": "form_submit"
            }
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\n--- {scenario['name']} Scenario ---")
        
        adaptation = await mcp_client.adapt_to_error(
            "error_demo_session", scenario["error_context"], strategy
        )
        
        print(f"Adaptation Strategy: {adaptation['strategy']}")
        print(f"Confidence: {adaptation['confidence']:.2f}")
        print(f"Estimated Recovery Time: {adaptation['estimated_recovery_time']}s")
        print(f"Recommended Actions:")
        
        for i, action in enumerate(adaptation["recommended_actions"][:3]):
            action_name = action.get("action", "unknown")
            print(f"  {i+1}. {action_name}")
            
            # Show action details if available
            if "duration" in action:
                print(f"     Duration: {action['duration']}s")
            if "reason" in action:
                print(f"     Reason: {action['reason']}")
    
    await mcp_client.cleanup()


async def demo_mcp_session_memory():
    """Demo MCP session memory and context tracking"""
    print("\n=== MCP Session Memory Demo ===")
    
    # Initialize MCP client
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    session_id = "memory_demo_session"
    
    # Simulate a multi-step automation session
    steps = [
        {
            "page_data": {
                "url": "https://www.ardan.com/nx/search/jobs/",
                "title": "Job Search",
                "content": "Search for jobs"
            },
            "goal": "search_jobs",
            "interactions": [
                ("search", True, 1.5, None),
                ("filter", True, 0.8, None)
            ]
        },
        {
            "page_data": {
                "url": "https://www.ardan.com/jobs/~123456",
                "title": "Job Details",
                "content": "Salesforce Agentforce job details"
            },
            "goal": "extract_job_info",
            "interactions": [
                ("extract", True, 2.0, None),
                ("analyze", True, 1.2, None)
            ]
        },
        {
            "page_data": {
                "url": "https://www.ardan.com/ab/proposals/job/123456",
                "title": "Submit Proposal",
                "content": "Application form"
            },
            "goal": "submit_application",
            "interactions": [
                ("fill_form", False, 5.0, "Validation error"),
                ("fix_form", True, 2.5, None),
                ("submit", True, 1.8, None)
            ]
        }
    ]
    
    print("Simulating multi-step automation session...")
    
    for step_num, step in enumerate(steps, 1):
        print(f"\n--- Step {step_num}: {step['goal']} ---")
        
        # Analyze page context
        context = await mcp_client.analyze_page_context(
            session_id, step["page_data"], step["goal"]
        )
        
        # Generate strategy
        strategy = await mcp_client.generate_adaptive_strategy(
            session_id, step["goal"], context
        )
        
        print(f"Page: {context.page_type}")
        print(f"Strategy Confidence: {strategy.confidence_score:.2f}")
        
        # Record interactions
        for action_type, success, exec_time, error_msg in step["interactions"]:
            await mcp_client.record_interaction_result(
                session_id=session_id,
                strategy_id=strategy.strategy_id,
                action_type=action_type,
                success=success,
                execution_time=exec_time,
                error_message=error_msg,
                context_before=context
            )
            
            status = "✓" if success else "✗"
            print(f"  {status} {action_type}: {exec_time}s")
    
    # Get comprehensive session memory
    print(f"\n--- Session Memory Summary ---")
    memory = await mcp_client.get_session_memory(session_id)
    
    print(f"Current Context: {memory['current_context']['page_type'] if memory['current_context'] else 'None'}")
    print(f"Context History: {len(memory['context_history'])} pages visited")
    print(f"Successful Strategies: {len(memory['successful_strategies'])}")
    print(f"Failed Strategies: {len(memory['failed_strategies'])}")
    print(f"Learned Patterns: {len(memory['learned_patterns'])}")
    
    # Show strategy performance
    if memory['successful_strategies']:
        print("\nSuccessful Strategy Performance:")
        for strategy_id, count in memory['successful_strategies'].items():
            print(f"  {strategy_id[:8]}...: {count} successes")
    
    if memory['failed_strategies']:
        print("\nFailed Strategy Performance:")
        for strategy_id, count in memory['failed_strategies'].items():
            print(f"  {strategy_id[:8]}...: {count} failures")
    
    await mcp_client.cleanup()


async def main():
    """Run all MCP demos"""
    print("MCP (Model Context Protocol) Integration Demo")
    print("=" * 50)
    
    try:
        await demo_mcp_context_analysis()
        await demo_mcp_learning_system()
        await demo_mcp_error_adaptation()
        await demo_mcp_session_memory()
        
        print("\n" + "=" * 50)
        print("MCP Demo completed successfully!")
        print("\nKey MCP Features Demonstrated:")
        print("✓ Page context analysis and classification")
        print("✓ Adaptive strategy generation")
        print("✓ Learning system with interaction results")
        print("✓ Error adaptation and recovery strategies")
        print("✓ Session memory and context tracking")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())