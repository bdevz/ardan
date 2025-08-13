#!/usr/bin/env python3
"""
Complete System Validation Script for Upwork Automation System
Validates all components: Browserbase + Stagehand + Director + MCP + n8n
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any


class SystemValidator:
    """Comprehensive system validation for the Upwork Automation System."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.results = {}
        self.errors = []
        self.warnings = []
        
    def log_success(self, message: str):
        """Log a success message."""
        print(f"✅ {message}")
        
    def log_warning(self, message: str):
        """Log a warning message."""
        print(f"⚠️  {message}")
        self.warnings.append(message)
        
    def log_error(self, message: str):
        """Log an error message."""
        print(f"❌ {message}")
        self.errors.append(message)
        
    def log_info(self, message: str):
        """Log an info message."""
        print(f"ℹ️  {message}")

    def validate_file_structure(self) -> bool:
        """Validate the complete file structure."""
        print("\n🔍 Validating File Structure...")
        
        required_files = [
            # Browser Automation - Core Components
            "browser-automation/browserbase_client.py",
            "browser-automation/session_manager.py",
            "browser-automation/stagehand_controller.py",
            "browser-automation/stagehand_error_handler.py",
            "browser-automation/director.py",
            "browser-automation/director_actions.py",
            "browser-automation/mcp_client.py",
            "browser-automation/mcp_integration.py",
            "browser-automation/mcp_director_actions.py",
            "browser-automation/job_discovery_service.py",
            
            # n8n Workflows
            "n8n-workflows/job-discovery-pipeline.json",
            "n8n-workflows/proposal-generation-pipeline.json",
            "n8n-workflows/browser-submission-pipeline.json",
            "n8n-workflows/notification-workflows.json",
            
            # API Services
            "api/main.py",
            "api/requirements.txt",
            "api/services/browser_service.py",
            "api/services/n8n_service.py",
            "api/services/task_queue_service.py",
            "api/services/workflow_service.py",
            
            # Configuration
            "shared/config.py",
            "docker-compose.yml",
            ".env.example",
            
            # Scripts
            "scripts/setup.sh",
            "scripts/setup_n8n_workflows.py",
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
            else:
                self.log_success(f"Found {file_path}")
        
        if missing_files:
            for missing in missing_files:
                self.log_error(f"Missing file: {missing}")
            return False
        
        self.log_success("All required files present")
        return True

    def validate_browser_automation_stack(self) -> bool:
        """Validate the browser automation stack components."""
        print("\n🔍 Validating Browser Automation Stack...")
        
        # Check Browserbase integration
        browserbase_file = self.project_root / "browser-automation/browserbase_client.py"
        if browserbase_file.exists():
            content = browserbase_file.read_text()
            required_classes = [
                "class BrowserbaseClient",
                "class SessionConfig",
                "class SessionStatus",
                "class SessionPool"
            ]
            
            for cls in required_classes:
                if cls in content:
                    self.log_success(f"Browserbase: {cls} found")
                else:
                    self.log_error(f"Browserbase: {cls} missing")
                    return False
        
        # Check Stagehand integration
        stagehand_file = self.project_root / "browser-automation/stagehand_controller.py"
        if stagehand_file.exists():
            content = stagehand_file.read_text()
            required_classes = [
                "class StagehandController",
                "class ArdanJobSearchController",
                "class ArdanApplicationController"
            ]
            
            for cls in required_classes:
                if cls in content:
                    self.log_success(f"Stagehand: {cls} found")
                else:
                    self.log_error(f"Stagehand: {cls} missing")
                    return False
        
        # Check Director orchestration
        director_file = self.project_root / "browser-automation/director.py"
        if director_file.exists():
            content = director_file.read_text()
            required_classes = [
                "class DirectorOrchestrator",
                "class WorkflowDefinition",
                "class WorkflowExecution"
            ]
            
            for cls in required_classes:
                if cls in content:
                    self.log_success(f"Director: {cls} found")
                else:
                    self.log_error(f"Director: {cls} missing")
                    return False
        
        # Check MCP integration
        mcp_integration_file = self.project_root / "browser-automation/mcp_integration.py"
        mcp_client_file = self.project_root / "browser-automation/mcp_client.py"
        
        if mcp_integration_file.exists():
            content = mcp_integration_file.read_text()
            if "class MCPIntegration" in content:
                self.log_success("MCP: class MCPIntegration found")
            else:
                self.log_error("MCP: class MCPIntegration missing")
                return False
        
        if mcp_client_file.exists():
            content = mcp_client_file.read_text()
            if "class MCPClient" in content:
                self.log_success("MCP: class MCPClient found")
            else:
                self.log_error("MCP: class MCPClient missing")
                return False
        
        self.log_success("Browser automation stack validation complete")
        return True

    def validate_n8n_workflows(self) -> bool:
        """Validate n8n workflow definitions."""
        print("\n🔍 Validating n8n Workflows...")
        
        workflow_files = [
            "n8n-workflows/job-discovery-pipeline.json",
            "n8n-workflows/proposal-generation-pipeline.json",
            "n8n-workflows/browser-submission-pipeline.json",
            "n8n-workflows/notification-workflows.json"
        ]
        
        for workflow_file in workflow_files:
            file_path = self.project_root / workflow_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        workflow_data = json.load(f)
                    
                    # Basic validation
                    if 'nodes' in workflow_data and 'connections' in workflow_data:
                        self.log_success(f"Valid n8n workflow: {workflow_file}")
                    else:
                        self.log_error(f"Invalid n8n workflow structure: {workflow_file}")
                        return False
                        
                except json.JSONDecodeError:
                    self.log_error(f"Invalid JSON in workflow: {workflow_file}")
                    return False
            else:
                self.log_error(f"Missing workflow file: {workflow_file}")
                return False
        
        self.log_success("n8n workflows validation complete")
        return True

    def validate_dependencies(self) -> bool:
        """Validate all required dependencies."""
        print("\n🔍 Validating Dependencies...")
        
        requirements_file = self.project_root / "api/requirements.txt"
        if not requirements_file.exists():
            self.log_error("requirements.txt not found")
            return False
        
        content = requirements_file.read_text()
        
        required_deps = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "redis",
            "browserbase",
            "playwright",
            "stagehand",
            "openai",
            "google-api-python-client",
            "slack-sdk",
            "aiohttp",
            "pydantic"
        ]
        
        for dep in required_deps:
            if dep in content.lower():
                self.log_success(f"Dependency found: {dep}")
            else:
                self.log_error(f"Missing dependency: {dep}")
                return False
        
        self.log_success("Dependencies validation complete")
        return True

    def validate_docker_configuration(self) -> bool:
        """Validate Docker Compose configuration."""
        print("\n🔍 Validating Docker Configuration...")
        
        docker_compose_file = self.project_root / "docker-compose.yml"
        if not docker_compose_file.exists():
            self.log_error("docker-compose.yml not found")
            return False
        
        content = docker_compose_file.read_text()
        
        required_services = [
            "db:",
            "redis:",
            "api:",
            "web:",
            "worker:",
            "scheduler:",
            "n8n:"
        ]
        
        for service in required_services:
            if service in content:
                self.log_success(f"Docker service found: {service.rstrip(':')}")
            else:
                self.log_error(f"Missing Docker service: {service.rstrip(':')}")
                return False
        
        self.log_success("Docker configuration validation complete")
        return True

    def validate_environment_configuration(self) -> bool:
        """Validate environment configuration."""
        print("\n🔍 Validating Environment Configuration...")
        
        # Check if .env.example exists
        env_example = self.project_root / ".env.example"
        if not env_example.exists():
            self.log_error(".env.example not found")
            return False
        
        content = env_example.read_text()
        
        required_env_vars = [
            "BROWSERBASE_API_KEY",
            "OPENAI_API_KEY",
            "SLACK_BOT_TOKEN",
            "N8N_WEBHOOK_URL",
            "DATABASE_URL",
            "REDIS_URL",
            "GOOGLE_CREDENTIALS_PATH"
        ]
        
        for var in required_env_vars:
            if var in content:
                self.log_success(f"Environment variable template: {var}")
            else:
                self.log_error(f"Missing environment variable template: {var}")
                return False
        
        # Check if actual .env exists
        env_file = self.project_root / ".env"
        if env_file.exists():
            self.log_success("Environment file (.env) exists")
        else:
            self.log_warning("Environment file (.env) not found - copy from .env.example")
        
        self.log_success("Environment configuration validation complete")
        return True

    def validate_api_endpoints(self) -> bool:
        """Validate API endpoint definitions."""
        print("\n🔍 Validating API Endpoints...")
        
        main_file = self.project_root / "api/main.py"
        if not main_file.exists():
            self.log_error("API main.py not found")
            return False
        
        content = main_file.read_text()
        
        required_routers = [
            "browser.router",
            "workflows.router",
            "n8n_webhooks.router",
            "queue.router",
            "health.router"
        ]
        
        for router in required_routers:
            if router in content:
                self.log_success(f"API router included: {router}")
            else:
                self.log_error(f"Missing API router: {router}")
                return False
        
        self.log_success("API endpoints validation complete")
        return True

    def validate_test_coverage(self) -> bool:
        """Validate test coverage."""
        print("\n🔍 Validating Test Coverage...")
        
        test_files = [
            "tests/test_browserbase_client.py",
            "tests/test_stagehand_integration.py",
            "tests/test_director_standalone.py",
            "tests/test_n8n_integration.py",
            "tests/test_task_queue.py"
        ]
        
        found_tests = 0
        for test_file in test_files:
            file_path = self.project_root / test_file
            if file_path.exists():
                self.log_success(f"Test file found: {test_file}")
                found_tests += 1
            else:
                self.log_warning(f"Test file missing: {test_file}")
        
        if found_tests >= len(test_files) * 0.8:  # At least 80% of tests present
            self.log_success("Test coverage validation complete")
            return True
        else:
            self.log_error("Insufficient test coverage")
            return False

    def check_system_readiness(self) -> Dict[str, Any]:
        """Check if the system is ready for deployment."""
        print("\n🔍 Checking System Readiness...")
        
        readiness_checks = {
            "docker_available": self._check_docker(),
            "python_version": self._check_python_version(),
            "required_ports": self._check_required_ports(),
            "disk_space": self._check_disk_space()
        }
        
        for check, result in readiness_checks.items():
            if result:
                self.log_success(f"Readiness check passed: {check}")
            else:
                self.log_warning(f"Readiness check failed: {check}")
        
        return readiness_checks

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _check_python_version(self) -> bool:
        """Check if Python version is adequate."""
        return sys.version_info >= (3, 8)

    def _check_required_ports(self) -> bool:
        """Check if required ports are available."""
        import socket
        
        required_ports = [3000, 5432, 5678, 6379, 8000]
        
        for port in required_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', port))
                if result == 0:  # Port is in use
                    self.log_warning(f"Port {port} is already in use")
                    return False
        
        return True

    def _check_disk_space(self) -> bool:
        """Check if there's adequate disk space."""
        import shutil
        
        total, used, free = shutil.disk_usage(self.project_root)
        free_gb = free // (1024**3)
        
        return free_gb >= 5  # At least 5GB free

    def generate_setup_instructions(self) -> List[str]:
        """Generate setup instructions based on validation results."""
        instructions = [
            "🚀 Setup Instructions for Upwork Automation System",
            "=" * 60,
            "",
            "1. Environment Setup:",
            "   cp .env.example .env",
            "   # Edit .env and add your API keys:",
            "   #   - BROWSERBASE_API_KEY",
            "   #   - OPENAI_API_KEY", 
            "   #   - SLACK_BOT_TOKEN",
            "",
            "2. Google Credentials:",
            "   mkdir -p credentials",
            "   # Add your Google service account JSON to:",
            "   # credentials/google-credentials.json",
            "",
            "3. Start the System:",
            "   docker-compose up -d",
            "",
            "4. Setup n8n Workflows:",
            "   python scripts/setup_n8n_workflows.py",
            "",
            "5. Access the System:",
            "   - Web Interface: http://localhost:3000",
            "   - API Documentation: http://localhost:8000/docs",
            "   - n8n Interface: http://localhost:5678",
            "",
            "6. Run Tests:",
            "   pytest tests/ -v",
            "",
            "7. Monitor Logs:",
            "   docker-compose logs -f",
        ]
        
        if self.warnings:
            instructions.extend([
                "",
                "⚠️  Warnings to Address:",
                *[f"   - {warning}" for warning in self.warnings]
            ])
        
        if self.errors:
            instructions.extend([
                "",
                "❌ Errors to Fix:",
                *[f"   - {error}" for error in self.errors]
            ])
        
        return instructions

    def run_complete_validation(self) -> bool:
        """Run complete system validation."""
        print("🚀 Upwork Automation System - Complete Validation")
        print("=" * 60)
        
        validations = [
            ("File Structure", self.validate_file_structure),
            ("Browser Automation Stack", self.validate_browser_automation_stack),
            ("n8n Workflows", self.validate_n8n_workflows),
            ("Dependencies", self.validate_dependencies),
            ("Docker Configuration", self.validate_docker_configuration),
            ("Environment Configuration", self.validate_environment_configuration),
            ("API Endpoints", self.validate_api_endpoints),
            ("Test Coverage", self.validate_test_coverage),
        ]
        
        results = {}
        for name, validation_func in validations:
            try:
                results[name] = validation_func()
            except Exception as e:
                self.log_error(f"{name} validation failed with error: {e}")
                results[name] = False
        
        # System readiness checks
        readiness = self.check_system_readiness()
        
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
        
        # System readiness summary
        ready_checks = sum(1 for result in readiness.values() if result)
        total_checks = len(readiness)
        print(f"🔧 System Readiness: {ready_checks}/{total_checks} checks passed")
        
        # Generate and display setup instructions
        instructions = self.generate_setup_instructions()
        print("\n" + "\n".join(instructions))
        
        # Final assessment
        all_passed = passed == total and ready_checks >= total_checks * 0.8
        
        if all_passed:
            print("\n🎉 System is ready for deployment!")
            print("✅ All critical validations passed")
            print("✅ Browser Automation: Browserbase + Stagehand + Director + MCP")
            print("✅ Orchestration: n8n workflows with business logic integration")
            print("✅ Minimal customization required - just add API keys!")
        else:
            print(f"\n⚠️  System needs attention before deployment")
            print(f"   {total - passed} validation(s) failed")
            print(f"   {total_checks - ready_checks} readiness check(s) failed")
        
        return all_passed


def main():
    """Main validation function."""
    validator = SystemValidator()
    success = validator.run_complete_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()