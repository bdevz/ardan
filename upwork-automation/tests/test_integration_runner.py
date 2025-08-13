"""
Integration Test Runner
Part of Task 18: Integration Testing and System Validation

This module provides a comprehensive test runner for all integration tests:
- Runs all integration test suites
- Generates detailed test reports
- Validates system requirements compliance
- Provides performance benchmarks
- Creates test coverage reports
"""
import asyncio
import pytest
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.database.connection import init_db


class IntegrationTestRunner:
    """Comprehensive integration test runner"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.test_suites = [
            "test_integration_comprehensive.py",
            "test_performance_load.py", 
            "test_failure_recovery.py",
            "test_external_services_integration.py"
        ]
        
    async def setup_test_environment(self):
        """Set up the test environment"""
        print("🔧 Setting up test environment...")
        
        try:
            # Initialize database
            await init_db()
            print("✅ Database initialized")
            
            # Set test environment variables
            os.environ["TESTING"] = "true"
            os.environ["LOG_LEVEL"] = "WARNING"  # Reduce log noise during tests
            
            print("✅ Test environment setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Test environment setup failed: {e}")
            return False
    
    def run_test_suite(self, test_file: str, markers: List[str] = None) -> Dict[str, Any]:
        """Run a specific test suite"""
        print(f"\n📋 Running {test_file}...")
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", test_file, "-v", "--tb=short"]
        
        # Add markers if specified
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Add coverage if available
        try:
            import pytest_cov
            cmd.extend(["--cov=api", "--cov=browser_automation", "--cov=shared"])
        except ImportError:
            pass
        
        start_time = time.time()
        
        try:
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Parse results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')
            
            # Extract test counts from pytest output
            passed_count = 0
            failed_count = 0
            skipped_count = 0
            
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Parse line like "5 passed, 2 failed, 1 skipped in 10.5s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed_count = int(parts[i-1])
                        elif part == "failed":
                            failed_count = int(parts[i-1])
                        elif part == "skipped":
                            skipped_count = int(parts[i-1])
                elif line.strip().endswith("passed"):
                    # Parse line like "10 passed in 5.2s"
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "passed":
                        passed_count = int(parts[0])
            
            return {
                "test_file": test_file,
                "passed": passed_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": passed_count + failed_count + skipped_count,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "test_file": test_file,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total": 0,
                "execution_time": 300,
                "return_code": -1,
                "stdout": "",
                "stderr": "Test suite timed out after 5 minutes",
                "success": False,
                "timeout": True
            }
        except Exception as e:
            return {
                "test_file": test_file,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total": 0,
                "execution_time": 0,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration test suites"""
        print("🚀 Starting Comprehensive Integration Testing...")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Setup test environment
        setup_success = await self.setup_test_environment()
        if not setup_success:
            return {"success": False, "error": "Test environment setup failed"}
        
        # Run each test suite
        suite_results = []
        
        for test_file in self.test_suites:
            test_path = os.path.join(os.path.dirname(__file__), test_file)
            
            if os.path.exists(test_path):
                result = self.run_test_suite(test_file)
                suite_results.append(result)
                
                # Print immediate results
                if result["success"]:
                    print(f"✅ {test_file}: {result['passed']} passed, {result['failed']} failed, {result['skipped']} skipped ({result['execution_time']:.1f}s)")
                else:
                    print(f"❌ {test_file}: FAILED ({result['execution_time']:.1f}s)")
                    if result.get("timeout"):
                        print(f"   ⏰ Test suite timed out")
                    elif result.get("error"):
                        print(f"   💥 Error: {result['error']}")
            else:
                print(f"⚠️  {test_file}: File not found, skipping")
                suite_results.append({
                    "test_file": test_file,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total": 0,
                    "execution_time": 0,
                    "success": False,
                    "error": "File not found"
                })
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        # Calculate overall statistics
        total_passed = sum(r["passed"] for r in suite_results)
        total_failed = sum(r["failed"] for r in suite_results)
        total_skipped = sum(r["skipped"] for r in suite_results)
        total_tests = sum(r["total"] for r in suite_results)
        successful_suites = sum(1 for r in suite_results if r["success"])
        
        overall_success = total_failed == 0 and successful_suites == len(self.test_suites)
        
        # Generate comprehensive report
        report = {
            "success": overall_success,
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
                "total_execution_time": total_time,
                "successful_suites": successful_suites,
                "total_suites": len(self.test_suites)
            },
            "suite_results": suite_results,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": os.getcwd()
            }
        }
        
        return report
    
    def generate_detailed_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed test report"""
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("UPWORK AUTOMATION SYSTEM - INTEGRATION TEST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {results['timestamp']}")
        report_lines.append(f"Total Execution Time: {results['summary']['total_execution_time']:.2f} seconds")
        report_lines.append("")
        
        # Overall Summary
        summary = results['summary']
        report_lines.append("📊 OVERALL SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Tests: {summary['total_tests']}")
        report_lines.append(f"Passed: {summary['passed']} ✅")
        report_lines.append(f"Failed: {summary['failed']} ❌")
        report_lines.append(f"Skipped: {summary['skipped']} ⏭️")
        report_lines.append(f"Success Rate: {summary['success_rate']:.1f}%")
        report_lines.append(f"Successful Suites: {summary['successful_suites']}/{summary['total_suites']}")
        report_lines.append("")
        
        # Suite Details
        report_lines.append("📋 TEST SUITE DETAILS")
        report_lines.append("-" * 40)
        
        for suite_result in results['suite_results']:
            status_icon = "✅" if suite_result['success'] else "❌"
            report_lines.append(f"{status_icon} {suite_result['test_file']}")
            report_lines.append(f"   Passed: {suite_result['passed']}, Failed: {suite_result['failed']}, Skipped: {suite_result['skipped']}")
            report_lines.append(f"   Execution Time: {suite_result['execution_time']:.2f}s")
            
            if not suite_result['success']:
                if suite_result.get('timeout'):
                    report_lines.append("   ⏰ TIMEOUT: Test suite exceeded 5 minute limit")
                elif suite_result.get('error'):
                    report_lines.append(f"   💥 ERROR: {suite_result['error']}")
                elif suite_result['stderr']:
                    # Show first few lines of stderr
                    error_lines = suite_result['stderr'].split('\n')[:3]
                    for line in error_lines:
                        if line.strip():
                            report_lines.append(f"   💥 {line.strip()}")
            
            report_lines.append("")
        
        # Requirements Compliance
        report_lines.append("✅ REQUIREMENTS COMPLIANCE VALIDATION")
        report_lines.append("-" * 40)
        
        compliance_checks = [
            ("End-to-End Workflows", "test_integration_comprehensive.py", "TestEndToEndWorkflows"),
            ("Browser Automation", "test_integration_comprehensive.py", "TestBrowserAutomationMockPages"),
            ("Performance & Concurrency", "test_performance_load.py", "TestConcurrentSessionPerformance"),
            ("Failure Recovery", "test_failure_recovery.py", "TestBrowserSessionFailures"),
            ("External Services", "test_external_services_integration.py", "TestOpenAIIntegration"),
            ("System Validation", "test_integration_comprehensive.py", "TestSystemValidation")
        ]
        
        for check_name, test_file, test_class in compliance_checks:
            suite_result = next((r for r in results['suite_results'] if r['test_file'] == test_file), None)
            if suite_result and suite_result['success']:
                report_lines.append(f"✅ {check_name}: PASSED")
            else:
                report_lines.append(f"❌ {check_name}: FAILED")
        
        report_lines.append("")
        
        # Performance Benchmarks
        report_lines.append("⚡ PERFORMANCE BENCHMARKS")
        report_lines.append("-" * 40)
        
        perf_suite = next((r for r in results['suite_results'] if 'performance' in r['test_file']), None)
        if perf_suite and perf_suite['success']:
            report_lines.append("✅ Concurrent Session Handling: PASSED")
            report_lines.append("✅ Database Performance: PASSED")
            report_lines.append("✅ Memory Usage: PASSED")
            report_lines.append("✅ API Response Times: PASSED")
        else:
            report_lines.append("❌ Performance benchmarks not completed successfully")
        
        report_lines.append("")
        
        # Final Status
        report_lines.append("🎯 FINAL STATUS")
        report_lines.append("-" * 40)
        
        if results['success']:
            report_lines.append("🎉 ALL INTEGRATION TESTS PASSED!")
            report_lines.append("✅ System is ready for production deployment")
        else:
            report_lines.append("⚠️  SOME TESTS FAILED")
            report_lines.append("❌ Review failed tests before deployment")
            
            # List critical failures
            critical_failures = [r for r in results['suite_results'] if not r['success']]
            if critical_failures:
                report_lines.append("")
                report_lines.append("Critical Failures:")
                for failure in critical_failures:
                    report_lines.append(f"  - {failure['test_file']}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def save_report(self, results: Dict[str, Any], report_text: str):
        """Save test results and report to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create reports directory
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Save JSON results
        json_file = reports_dir / f"integration_test_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save text report
        report_file = reports_dir / f"integration_test_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        print(f"\n📄 Reports saved:")
        print(f"   JSON: {json_file}")
        print(f"   Text: {report_file}")


async def main():
    """Main test runner function"""
    runner = IntegrationTestRunner()
    
    try:
        # Run all integration tests
        results = await runner.run_all_tests()
        
        # Generate detailed report
        report_text = runner.generate_detailed_report(results)
        
        # Print report to console
        print("\n" + report_text)
        
        # Save reports to files
        runner.save_report(results, report_text)
        
        # Return appropriate exit code
        return 0 if results['success'] else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        return 1


def run_specific_suite(suite_name: str):
    """Run a specific test suite"""
    runner = IntegrationTestRunner()
    
    if suite_name not in runner.test_suites:
        print(f"❌ Unknown test suite: {suite_name}")
        print(f"Available suites: {', '.join(runner.test_suites)}")
        return 1
    
    print(f"🚀 Running specific test suite: {suite_name}")
    
    result = runner.run_test_suite(suite_name)
    
    if result['success']:
        print(f"✅ {suite_name} completed successfully")
        print(f"   Passed: {result['passed']}, Failed: {result['failed']}, Skipped: {result['skipped']}")
        print(f"   Execution Time: {result['execution_time']:.2f}s")
        return 0
    else:
        print(f"❌ {suite_name} failed")
        if result.get('error'):
            print(f"   Error: {result['error']}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific suite
        suite_name = sys.argv[1]
        exit_code = run_specific_suite(suite_name)
        sys.exit(exit_code)
    else:
        # Run all tests
        exit_code = asyncio.run(main())
        sys.exit(exit_code)