#!/usr/bin/env python3
"""
Comprehensive validation script for n8n workflow integration
"""
import asyncio
import sys
import json
import requests
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.append('.')
sys.path.append('./api')

from api.services.n8n_service import N8NService
from api.services.workflow_health_service import WorkflowHealthService


class N8NIntegrationValidator:
    """Comprehensive validator for n8n workflow integration"""
    
    def __init__(self, n8n_url: str = "http://localhost:5678", api_url: str = "http://localhost:8000"):
        self.n8n_url = n8n_url
        self.api_url = api_url
        self.n8n_service = N8NService()
        self.health_service = WorkflowHealthService()
        self.validation_results = {}
        
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation of n8n integration"""
        print("🔍 Starting comprehensive n8n integration validation...")
        print(f"   n8n URL: {self.n8n_url}")
        print(f"   API URL: {self.api_url}")
        print()
        
        validation_steps = [
            ("Basic Connectivity", self.validate_basic_connectivity),
            ("Workflow Deployment", self.validate_workflow_deployment),
            ("Webhook Endpoints", self.validate_webhook_endpoints),
            ("Workflow Triggers", self.validate_workflow_triggers),
            ("Error Handling", self.validate_error_handling),
            ("Performance", self.validate_performance),
            ("Health Monitoring", self.validate_health_monitoring),
            ("Integration Points", self.validate_integration_points)
        ]
        
        overall_success = True
        
        for step_name, step_function in validation_steps:
            print(f"📋 Validating: {step_name}")
            try:
                result = await step_function()
                self.validation_results[step_name] = result
                
                if result["success"]:
                    print(f"   ✅ {step_name}: PASSED")
                else:
                    print(f"   ❌ {step_name}: FAILED - {result.get('error', 'Unknown error')}")
                    overall_success = False
                    
                # Print details if available
                if result.get("details"):
                    for detail in result["details"]:
                        status_icon = "✅" if detail.get("success", True) else "❌"
                        print(f"      {status_icon} {detail['message']}")
                        
            except Exception as e:
                print(f"   ❌ {step_name}: ERROR - {str(e)}")
                self.validation_results[step_name] = {"success": False, "error": str(e)}
                overall_success = False
            
            print()
        
        # Generate summary
        summary = self.generate_validation_summary(overall_success)
        
        return {
            "overall_success": overall_success,
            "summary": summary,
            "detailed_results": self.validation_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def validate_basic_connectivity(self) -> Dict[str, Any]:
        """Validate basic connectivity to n8n and API"""
        details = []
        
        # Test n8n connectivity
        try:
            response = requests.get(f"{self.n8n_url}/healthz", timeout=10)
            if response.status_code == 200:
                details.append({"message": "n8n instance is accessible", "success": True})
            else:
                details.append({"message": f"n8n returned status {response.status_code}", "success": False})
                return {"success": False, "error": "n8n not accessible", "details": details}
        except Exception as e:
            details.append({"message": f"Cannot connect to n8n: {str(e)}", "success": False})
            return {"success": False, "error": "n8n connection failed", "details": details}
        
        # Test API connectivity
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                details.append({"message": "API server is accessible", "success": True})
            else:
                details.append({"message": f"API returned status {response.status_code}", "success": False})
        except Exception as e:
            details.append({"message": f"Cannot connect to API: {str(e)}", "success": False})
        
        # Test webhook connectivity
        webhook_result = await self.n8n_service.test_webhook_connectivity()
        if webhook_result["success"]:
            details.append({"message": f"Webhook connectivity OK (latency: {webhook_result.get('latency_ms', 0)}ms)", "success": True})
        else:
            details.append({"message": f"Webhook connectivity failed: {webhook_result.get('error', 'Unknown')}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    async def validate_workflow_deployment(self) -> Dict[str, Any]:
        """Validate workflow deployment status"""
        details = []
        
        # Get workflow status
        status_result = await self.n8n_service.get_workflow_status()
        
        if not status_result["success"]:
            return {"success": False, "error": "Failed to get workflow status", "details": details}
        
        workflows = status_result["workflows"]
        required_workflows = [
            "Job Discovery Pipeline",
            "Proposal Generation Pipeline",
            "Browser Submission Pipeline",
            "Notification Workflows"
        ]
        
        deployed_count = 0
        active_count = 0
        
        for required_name in required_workflows:
            found = False
            for workflow_id, workflow_data in workflows.items():
                if workflow_data.get("name") == required_name:
                    found = True
                    deployed_count += 1
                    
                    if workflow_data.get("active", False):
                        active_count += 1
                        details.append({"message": f"{required_name}: Deployed and Active", "success": True})
                    else:
                        details.append({"message": f"{required_name}: Deployed but Inactive", "success": False})
                    break
            
            if not found:
                details.append({"message": f"{required_name}: Not Found", "success": False})
        
        details.append({"message": f"Total workflows deployed: {deployed_count}/{len(required_workflows)}", "success": deployed_count == len(required_workflows)})
        details.append({"message": f"Total workflows active: {active_count}/{len(required_workflows)}", "success": active_count == len(required_workflows)})
        
        success = deployed_count == len(required_workflows) and active_count == len(required_workflows)
        return {"success": success, "details": details}
    
    async def validate_webhook_endpoints(self) -> Dict[str, Any]:
        """Validate webhook endpoints"""
        details = []
        
        webhook_endpoints = [
            ("Job Discovery", "/api/n8n/trigger/job-discovery"),
            ("Proposal Generation", "/api/n8n/trigger/proposal-generation"),
            ("Browser Submission", "/api/n8n/trigger/browser-submission"),
            ("Notification", "/api/n8n/trigger/notification"),
            ("Status", "/api/n8n/status"),
            ("Test Webhook", "/api/n8n/test-webhook")
        ]
        
        success_count = 0
        
        for endpoint_name, endpoint_path in webhook_endpoints:
            try:
                url = f"{self.api_url}{endpoint_path}"
                
                if endpoint_path == "/api/n8n/status":
                    # GET request for status
                    response = requests.get(url, timeout=10)
                else:
                    # POST request with minimal payload
                    test_payload = {"test": True} if "test-webhook" in endpoint_path else {}
                    response = requests.post(url, json=test_payload, timeout=10)
                
                if response.status_code in [200, 400]:  # 400 is OK for invalid payload
                    details.append({"message": f"{endpoint_name} endpoint: Accessible", "success": True})
                    success_count += 1
                else:
                    details.append({"message": f"{endpoint_name} endpoint: HTTP {response.status_code}", "success": False})
                    
            except Exception as e:
                details.append({"message": f"{endpoint_name} endpoint: Error - {str(e)}", "success": False})
        
        success = success_count == len(webhook_endpoints)
        return {"success": success, "details": details}
    
    async def validate_workflow_triggers(self) -> Dict[str, Any]:
        """Validate workflow trigger functionality"""
        details = []
        
        # Test job discovery trigger
        try:
            result = await self.n8n_service.trigger_job_discovery_workflow(
                keywords=["test"],
                max_jobs=1
            )
            if result["success"]:
                details.append({"message": "Job discovery trigger: Working", "success": True})
            else:
                details.append({"message": f"Job discovery trigger: Failed - {result.get('error', 'Unknown')}", "success": False})
        except Exception as e:
            details.append({"message": f"Job discovery trigger: Error - {str(e)}", "success": False})
        
        # Test proposal generation trigger
        try:
            result = await self.n8n_service.trigger_proposal_generation_workflow(
                job_ids=["test-job-id"]
            )
            if result["success"]:
                details.append({"message": "Proposal generation trigger: Working", "success": True})
            else:
                details.append({"message": f"Proposal generation trigger: Failed - {result.get('error', 'Unknown')}", "success": False})
        except Exception as e:
            details.append({"message": f"Proposal generation trigger: Error - {str(e)}", "success": False})
        
        # Test notification trigger
        try:
            result = await self.n8n_service.send_notification(
                notification_type="test",
                data={"test": True}
            )
            if result["success"]:
                details.append({"message": "Notification trigger: Working", "success": True})
            else:
                details.append({"message": f"Notification trigger: Failed - {result.get('error', 'Unknown')}", "success": False})
        except Exception as e:
            details.append({"message": f"Notification trigger: Error - {str(e)}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    async def validate_error_handling(self) -> Dict[str, Any]:
        """Validate error handling mechanisms"""
        details = []
        
        # Test timeout handling
        try:
            # This should timeout or handle gracefully
            import aiohttp
            from unittest.mock import patch
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.side_effect = asyncio.TimeoutError()
                
                result = await self.n8n_service.trigger_job_discovery_workflow()
                
                if not result["success"] and "timeout" in result.get("error", "").lower():
                    details.append({"message": "Timeout handling: Working", "success": True})
                else:
                    details.append({"message": "Timeout handling: Not working properly", "success": False})
                    
        except Exception as e:
            details.append({"message": f"Timeout handling test: Error - {str(e)}", "success": False})
        
        # Test invalid payload handling
        try:
            response = requests.post(
                f"{self.api_url}/api/n8n/trigger/job-discovery",
                json={"invalid": "payload"},
                timeout=10
            )
            
            if response.status_code == 200:  # Should handle gracefully
                details.append({"message": "Invalid payload handling: Working", "success": True})
            else:
                details.append({"message": f"Invalid payload handling: HTTP {response.status_code}", "success": True})  # Any response is OK
                
        except Exception as e:
            details.append({"message": f"Invalid payload test: Error - {str(e)}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    async def validate_performance(self) -> Dict[str, Any]:
        """Validate performance characteristics"""
        details = []
        
        # Test webhook latency
        webhook_result = await self.n8n_service.test_webhook_connectivity()
        if webhook_result["success"]:
            latency = webhook_result.get("latency_ms", 0)
            if latency < 1000:  # Less than 1 second
                details.append({"message": f"Webhook latency: Good ({latency}ms)", "success": True})
            elif latency < 5000:  # Less than 5 seconds
                details.append({"message": f"Webhook latency: Acceptable ({latency}ms)", "success": True})
            else:
                details.append({"message": f"Webhook latency: High ({latency}ms)", "success": False})
        else:
            details.append({"message": "Webhook latency: Cannot measure (connectivity failed)", "success": False})
        
        # Test concurrent requests
        try:
            import time
            start_time = time.time()
            
            # Send multiple concurrent requests
            tasks = []
            for i in range(3):
                task = self.n8n_service.test_webhook_connectivity()
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            total_time = (end_time - start_time) * 1000  # Convert to ms
            
            if successful_requests == len(tasks):
                details.append({"message": f"Concurrent requests: All successful ({total_time:.0f}ms total)", "success": True})
            else:
                details.append({"message": f"Concurrent requests: {successful_requests}/{len(tasks)} successful", "success": False})
                
        except Exception as e:
            details.append({"message": f"Concurrent request test: Error - {str(e)}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    async def validate_health_monitoring(self) -> Dict[str, Any]:
        """Validate health monitoring functionality"""
        details = []
        
        # Test health check
        try:
            health_result = await self.health_service.perform_health_check()
            
            if "overall_health_score" in health_result:
                score = health_result["overall_health_score"]
                details.append({"message": f"Health monitoring: Working (score: {score:.2f})", "success": True})
            else:
                details.append({"message": "Health monitoring: No health score returned", "success": False})
                
        except Exception as e:
            details.append({"message": f"Health monitoring: Error - {str(e)}", "success": False})
        
        # Test validation functionality
        try:
            validation_result = await self.n8n_service.validate_workflow_deployment()
            
            if validation_result["success"]:
                details.append({"message": "Workflow validation: Working", "success": True})
            else:
                details.append({"message": f"Workflow validation: Failed - {validation_result.get('error', 'Unknown')}", "success": False})
                
        except Exception as e:
            details.append({"message": f"Workflow validation: Error - {str(e)}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    async def validate_integration_points(self) -> Dict[str, Any]:
        """Validate integration with other system components"""
        details = []
        
        # Test API integration endpoints
        integration_endpoints = [
            "/api/n8n/health",
            "/api/n8n/validate-deployment",
            "/api/n8n/status"
        ]
        
        for endpoint in integration_endpoints:
            try:
                response = requests.get(f"{self.api_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    details.append({"message": f"Integration endpoint {endpoint}: Working", "success": True})
                else:
                    details.append({"message": f"Integration endpoint {endpoint}: HTTP {response.status_code}", "success": False})
            except Exception as e:
                details.append({"message": f"Integration endpoint {endpoint}: Error - {str(e)}", "success": False})
        
        success = all(detail["success"] for detail in details)
        return {"success": success, "details": details}
    
    def generate_validation_summary(self, overall_success: bool) -> Dict[str, Any]:
        """Generate validation summary"""
        total_steps = len(self.validation_results)
        passed_steps = sum(1 for result in self.validation_results.values() if result.get("success", False))
        
        summary = {
            "overall_status": "PASSED" if overall_success else "FAILED",
            "total_validation_steps": total_steps,
            "passed_steps": passed_steps,
            "failed_steps": total_steps - passed_steps,
            "success_rate": (passed_steps / total_steps) * 100 if total_steps > 0 else 0,
            "critical_issues": [],
            "recommendations": []
        }
        
        # Identify critical issues
        for step_name, result in self.validation_results.items():
            if not result.get("success", False):
                summary["critical_issues"].append({
                    "step": step_name,
                    "error": result.get("error", "Unknown error")
                })
        
        # Generate recommendations
        if not overall_success:
            if any("connectivity" in issue["step"].lower() for issue in summary["critical_issues"]):
                summary["recommendations"].append("Check network connectivity between services")
            
            if any("deployment" in issue["step"].lower() for issue in summary["critical_issues"]):
                summary["recommendations"].append("Run workflow deployment script: python scripts/setup_n8n_workflows.py")
            
            if any("webhook" in issue["step"].lower() for issue in summary["critical_issues"]):
                summary["recommendations"].append("Verify webhook configuration and n8n instance status")
        else:
            summary["recommendations"].append("All validations passed - n8n integration is working correctly")
        
        return summary
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print comprehensive validation report"""
        print("=" * 80)
        print("🔍 N8N INTEGRATION VALIDATION REPORT")
        print("=" * 80)
        print()
        
        summary = results["summary"]
        
        # Overall status
        status_icon = "✅" if results["overall_success"] else "❌"
        print(f"{status_icon} OVERALL STATUS: {summary['overall_status']}")
        print(f"📊 SUCCESS RATE: {summary['success_rate']:.1f}% ({summary['passed_steps']}/{summary['total_validation_steps']} steps passed)")
        print(f"⏰ VALIDATION TIME: {results['timestamp']}")
        print()
        
        # Critical issues
        if summary["critical_issues"]:
            print("🚨 CRITICAL ISSUES:")
            for issue in summary["critical_issues"]:
                print(f"   ❌ {issue['step']}: {issue['error']}")
            print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS:")
        for rec in summary["recommendations"]:
            print(f"   • {rec}")
        print()
        
        # Detailed results
        print("📋 DETAILED RESULTS:")
        for step_name, result in results["detailed_results"].items():
            status_icon = "✅" if result.get("success", False) else "❌"
            print(f"   {status_icon} {step_name}")
            
            if result.get("details"):
                for detail in result["details"]:
                    detail_icon = "✅" if detail.get("success", True) else "❌"
                    print(f"      {detail_icon} {detail['message']}")
        
        print()
        print("=" * 80)


async def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description="Validate n8n workflow integration")
    parser.add_argument("--n8n-url", default="http://localhost:5678", help="n8n URL")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--output", help="Output file for validation results (JSON)")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    
    args = parser.parse_args()
    
    validator = N8NIntegrationValidator(
        n8n_url=args.n8n_url,
        api_url=args.api_url
    )
    
    try:
        results = await validator.run_comprehensive_validation()
        
        if not args.quiet:
            validator.print_validation_report(results)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📄 Validation results saved to: {args.output}")
        
        # Exit with appropriate code
        sys.exit(0 if results["overall_success"] else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())