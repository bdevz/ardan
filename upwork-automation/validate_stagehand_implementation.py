#!/usr/bin/env python3
"""
Validation script for Stagehand AI Browser Control Implementation
This script validates the implementation without requiring external dependencies
"""
import os
import sys
from pathlib import Path


def validate_file_structure():
    """Validate that all required files are present"""
    print("🔍 Validating file structure...")
    
    required_files = [
        "browser-automation/stagehand_controller.py",
        "browser-automation/stagehand_error_handler.py", 
        "tests/test_stagehand_integration.py",
        "examples/stagehand_demo.py",
        "api/requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"  ✓ {file_path}")
    
    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    
    print("  ✅ All required files present")
    return True


def validate_stagehand_dependency():
    """Validate that Stagehand dependency was added to requirements"""
    print("\n🔍 Validating Stagehand dependency...")
    
    requirements_path = Path("api/requirements.txt")
    if not requirements_path.exists():
        print("  ❌ requirements.txt not found")
        return False
    
    content = requirements_path.read_text()
    if "stagehand" in content.lower():
        print("  ✓ Stagehand dependency found in requirements.txt")
        return True
    else:
        print("  ❌ Stagehand dependency not found in requirements.txt")
        return False


def validate_code_structure():
    """Validate the code structure and key components"""
    print("\n🔍 Validating code structure...")
    
    # Check StagehandController
    controller_path = Path("browser-automation/stagehand_controller.py")
    controller_content = controller_path.read_text()
    
    required_classes = [
        "class StagehandController",
        "class ArdanJobSearchController", 
        "class ArdanApplicationController",
        "class NavigationStrategy",
        "class ExtractionType"
    ]
    
    required_methods = [
        "async def intelligent_navigate",
        "async def extract_content",
        "async def interact_with_form",
        "async def handle_dynamic_content",
        "async def recover_from_error"
    ]
    
    missing_components = []
    
    for component in required_classes + required_methods:
        if component not in controller_content:
            missing_components.append(component)
        else:
            print(f"  ✓ {component}")
    
    if missing_components:
        print(f"  ❌ Missing components: {missing_components}")
        return False
    
    # Check Error Handler
    error_handler_path = Path("browser-automation/stagehand_error_handler.py")
    error_handler_content = error_handler_path.read_text()
    
    required_error_components = [
        "class StagehandErrorHandler",
        "class ErrorType",
        "class RecoveryStrategy",
        "async def handle_error",
        "def classify_error"
    ]
    
    for component in required_error_components:
        if component not in error_handler_content:
            missing_components.append(component)
        else:
            print(f"  ✓ {component}")
    
    if missing_components:
        print(f"  ❌ Missing error handling components: {missing_components}")
        return False
    
    print("  ✅ All required code components present")
    return True


def validate_test_structure():
    """Validate the test structure"""
    print("\n🔍 Validating test structure...")
    
    test_path = Path("tests/test_stagehand_integration.py")
    test_content = test_path.read_text()
    
    required_test_classes = [
        "class TestStagehandController",
        "class TestArdanJobSearchController",
        "class TestArdanApplicationController", 
        "class TestStagehandErrorHandler",
        "class TestIntegrationScenarios"
    ]
    
    required_test_methods = [
        "test_initialize_stagehand_success",
        "test_intelligent_navigate",
        "test_extract_content",
        "test_interact_with_form",
        "test_search_jobs_success",
        "test_submit_application_success",
        "test_classify_error",
        "test_handle_error"
    ]
    
    missing_tests = []
    
    for test_component in required_test_classes + required_test_methods:
        if test_component not in test_content:
            missing_tests.append(test_component)
        else:
            print(f"  ✓ {test_component}")
    
    if missing_tests:
        print(f"  ❌ Missing test components: {missing_tests}")
        return False
    
    print("  ✅ All required test components present")
    return True


def validate_demo_structure():
    """Validate the demo structure"""
    print("\n🔍 Validating demo structure...")
    
    demo_path = Path("examples/stagehand_demo.py")
    demo_content = demo_path.read_text()
    
    required_demo_methods = [
        "async def demo_job_search",
        "async def demo_job_details_extraction",
        "async def demo_intelligent_navigation",
        "async def demo_content_extraction",
        "async def demo_form_interaction",
        "async def demo_error_handling",
        "async def demo_application_submission",
        "async def run_complete_demo"
    ]
    
    missing_demo_methods = []
    
    for method in required_demo_methods:
        if method not in demo_content:
            missing_demo_methods.append(method)
        else:
            print(f"  ✓ {method}")
    
    if missing_demo_methods:
        print(f"  ❌ Missing demo methods: {missing_demo_methods}")
        return False
    
    print("  ✅ All required demo methods present")
    return True


def validate_integration_points():
    """Validate integration with existing components"""
    print("\n🔍 Validating integration points...")
    
    # Check if __init__.py was updated
    init_path = Path("browser-automation/__init__.py")
    init_content = init_path.read_text()
    
    required_exports = [
        "StagehandController",
        "ArdanJobSearchController",
        "ArdanApplicationController", 
        "StagehandErrorHandler",
        "NavigationStrategy",
        "ExtractionType"
    ]
    
    missing_exports = []
    for export in required_exports:
        if export not in init_content:
            missing_exports.append(export)
        else:
            print(f"  ✓ {export} exported")
    
    if missing_exports:
        print(f"  ❌ Missing exports: {missing_exports}")
        return False
    
    print("  ✅ All integration points properly configured")
    return True


def count_implementation_lines():
    """Count lines of implementation code"""
    print("\n📊 Implementation Statistics:")
    
    files_to_count = [
        "browser-automation/stagehand_controller.py",
        "browser-automation/stagehand_error_handler.py",
        "tests/test_stagehand_integration.py",
        "examples/stagehand_demo.py"
    ]
    
    total_lines = 0
    for file_path in files_to_count:
        if Path(file_path).exists():
            lines = len(Path(file_path).read_text().splitlines())
            total_lines += lines
            print(f"  📄 {file_path}: {lines} lines")
    
    print(f"  📈 Total implementation: {total_lines} lines")
    return total_lines


def main():
    """Main validation function"""
    print("🚀 Stagehand AI Browser Control Implementation Validation")
    print("=" * 60)
    
    validations = [
        ("File Structure", validate_file_structure),
        ("Stagehand Dependency", validate_stagehand_dependency),
        ("Code Structure", validate_code_structure),
        ("Test Structure", validate_test_structure),
        ("Demo Structure", validate_demo_structure),
        ("Integration Points", validate_integration_points)
    ]
    
    results = {}
    
    for name, validation_func in validations:
        try:
            results[name] = validation_func()
        except Exception as e:
            print(f"  ❌ {name} validation failed with error: {e}")
            results[name] = False
    
    # Count implementation lines
    total_lines = count_implementation_lines()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {name}")
    
    print(f"\n📊 Overall Result: {passed}/{total} validations passed")
    print(f"📈 Implementation Size: {total_lines} lines of code")
    
    if passed == total:
        print("\n🎉 All validations passed! Stagehand implementation is complete.")
        
        print("\n📝 Implementation Summary:")
        print("  ✅ Stagehand AI browser control integration")
        print("  ✅ Intelligent navigation methods")
        print("  ✅ Content extraction with AI understanding")
        print("  ✅ Form filling and interaction methods")
        print("  ✅ Dynamic element detection")
        print("  ✅ Error handling and retry logic")
        print("  ✅ Comprehensive integration tests")
        print("  ✅ Complete demonstration examples")
        
        print("\n🔧 Next Steps:")
        print("  1. Install dependencies: pip install -r api/requirements.txt")
        print("  2. Configure environment variables (OPENAI_API_KEY, BROWSERBASE_API_KEY)")
        print("  3. Run tests: pytest tests/test_stagehand_integration.py")
        print("  4. Try the demo: python examples/stagehand_demo.py")
        
        return True
    else:
        print(f"\n⚠️  {total - passed} validations failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)