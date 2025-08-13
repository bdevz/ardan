#!/usr/bin/env python3
"""
Basic test script for n8n integration functionality
"""
import sys
import asyncio
import json

# Add paths
sys.path.append('.')
sys.path.append('./api')

from api.services.n8n_service import N8NService


async def test_basic_functionality():
    """Test basic n8n service functionality"""
    print("🔍 Testing N8N Integration Basic Functionality")
    print("=" * 50)
    
    service = N8NService()
    
    # Test 1: Service initialization
    print("1. Service Initialization:")
    print(f"   ✅ Base URL: {service.base_url}")
    print(f"   ✅ Webhook Base: {service.webhook_base}")
    print(f"   ✅ API Base: {service.api_base}")
    print()
    
    # Test 2: Workflow status (mock)
    print("2. Workflow Status:")
    try:
        status = await service.get_workflow_status()
        if status["success"]:
            print(f"   ✅ Status retrieved successfully")
            print(f"   ✅ Total workflows: {status['total_workflows']}")
            print(f"   ✅ Active workflows: {status['active_workflows']}")
        else:
            print(f"   ⚠️  Status retrieval failed: {status.get('error', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ Status test error: {e}")
    print()
    
    # Test 3: Workflow validation
    print("3. Workflow Validation:")
    try:
        validation = await service.validate_workflow_deployment()
        if validation["success"]:
            print(f"   ✅ Validation completed")
            print(f"   ✅ All workflows valid: {validation['all_workflows_valid']}")
            print(f"   ✅ Missing workflows: {len(validation.get('missing_workflows', []))}")
            print(f"   ✅ Inactive workflows: {len(validation.get('inactive_workflows', []))}")
        else:
            print(f"   ❌ Validation failed: {validation.get('error', 'Unknown')}")
    except Exception as e:
        print(f"   ❌ Validation test error: {e}")
    print()
    
    # Test 4: Workflow triggers (mock)
    print("4. Workflow Triggers:")
    
    # Job discovery trigger
    try:
        result = await service.trigger_job_discovery_workflow(
            keywords=["test"],
            max_jobs=1
        )
        if result["success"]:
            print(f"   ✅ Job discovery trigger: Working")
        else:
            print(f"   ⚠️  Job discovery trigger: {result.get('error', 'Failed')}")
    except Exception as e:
        print(f"   ❌ Job discovery trigger error: {e}")
    
    # Proposal generation trigger
    try:
        result = await service.trigger_proposal_generation_workflow(
            job_ids=["test-job"]
        )
        if result["success"]:
            print(f"   ✅ Proposal generation trigger: Working")
        else:
            print(f"   ⚠️  Proposal generation trigger: {result.get('error', 'Failed')}")
    except Exception as e:
        print(f"   ❌ Proposal generation trigger error: {e}")
    
    # Browser submission trigger
    try:
        result = await service.trigger_browser_submission_workflow(
            proposal_ids=["test-proposal"]
        )
        if result["success"]:
            print(f"   ✅ Browser submission trigger: Working")
        else:
            print(f"   ⚠️  Browser submission trigger: {result.get('error', 'Failed')}")
    except Exception as e:
        print(f"   ❌ Browser submission trigger error: {e}")
    
    # Notification trigger
    try:
        result = await service.send_notification(
            notification_type="test",
            data={"test": True}
        )
        if result["success"]:
            print(f"   ✅ Notification trigger: Working")
        else:
            print(f"   ⚠️  Notification trigger: {result.get('error', 'Failed')}")
    except Exception as e:
        print(f"   ❌ Notification trigger error: {e}")
    
    print()
    
    # Test 5: Webhook connectivity
    print("5. Webhook Connectivity:")
    try:
        result = await service.test_webhook_connectivity()
        if result["success"]:
            print(f"   ✅ Webhook connectivity: Working")
            print(f"   ✅ Latency: {result.get('latency_ms', 0)}ms")
        else:
            print(f"   ⚠️  Webhook connectivity: {result.get('error', 'Failed')}")
    except Exception as e:
        print(f"   ❌ Webhook connectivity error: {e}")
    
    print()
    print("=" * 50)
    print("🎉 Basic functionality test completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())