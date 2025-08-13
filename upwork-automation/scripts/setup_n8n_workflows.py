#!/usr/bin/env python3
"""
Setup script for deploying n8n workflows
"""
import os
import json
import requests
import time
from typing import Dict, List
import argparse


class N8NWorkflowDeployer:
    """Deploy and manage n8n workflows"""
    
    def __init__(self, n8n_url: str = "http://localhost:5678", auth: tuple = None):
        self.n8n_url = n8n_url.rstrip('/')
        self.auth = auth or ("admin", "automation123")  # Default from docker-compose
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth
    
    def wait_for_n8n(self, timeout: int = 60) -> bool:
        """Wait for n8n to be ready"""
        print(f"Waiting for n8n at {self.n8n_url}...")
        
        for i in range(timeout):
            try:
                response = self.session.get(f"{self.n8n_url}/healthz", timeout=5)
                if response.status_code == 200:
                    print("✅ n8n is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if i % 10 == 0:
                print(f"Still waiting... ({i}/{timeout}s)")
            time.sleep(1)
        
        print("❌ n8n failed to become ready within timeout")
        return False
    
    def load_workflow_file(self, filepath: str) -> Dict:
        """Load workflow from JSON file"""
        try:
            with open(filepath, 'r') as f:
                workflow = json.load(f)
            print(f"✅ Loaded workflow: {workflow.get('name', 'Unknown')}")
            return workflow
        except Exception as e:
            print(f"❌ Failed to load workflow from {filepath}: {e}")
            return None
    
    def deploy_workflow(self, workflow: Dict) -> bool:
        """Deploy a single workflow to n8n"""
        try:
            workflow_name = workflow.get('name', 'Unknown')
            print(f"Deploying workflow: {workflow_name}")
            
            # Check if workflow already exists
            existing_workflows = self.list_workflows()
            existing_workflow = None
            
            for existing in existing_workflows:
                if existing.get('name') == workflow_name:
                    existing_workflow = existing
                    break
            
            if existing_workflow:
                # Update existing workflow
                workflow_id = existing_workflow['id']
                url = f"{self.n8n_url}/api/v1/workflows/{workflow_id}"
                response = self.session.put(url, json=workflow)
                
                if response.status_code == 200:
                    print(f"✅ Updated workflow: {workflow_name}")
                    return True
                else:
                    print(f"❌ Failed to update workflow {workflow_name}: {response.status_code} - {response.text}")
                    return False
            else:
                # Create new workflow
                url = f"{self.n8n_url}/api/v1/workflows"
                response = self.session.post(url, json=workflow)
                
                if response.status_code == 201:
                    print(f"✅ Created workflow: {workflow_name}")
                    return True
                else:
                    print(f"❌ Failed to create workflow {workflow_name}: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error deploying workflow: {e}")
            return False
    
    def list_workflows(self) -> List[Dict]:
        """List all workflows in n8n"""
        try:
            url = f"{self.n8n_url}/api/v1/workflows"
            response = self.session.get(url)
            
            if response.status_code == 200:
                workflows = response.json().get('data', [])
                return workflows
            else:
                print(f"❌ Failed to list workflows: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error listing workflows: {e}")
            return []
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow"""
        try:
            url = f"{self.n8n_url}/api/v1/workflows/{workflow_id}/activate"
            response = self.session.post(url)
            
            if response.status_code == 200:
                print(f"✅ Activated workflow: {workflow_id}")
                return True
            else:
                print(f"❌ Failed to activate workflow {workflow_id}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error activating workflow: {e}")
            return False
    
    def deploy_all_workflows(self, workflows_dir: str) -> bool:
        """Deploy all workflows from directory"""
        workflow_files = [
            "job-discovery-pipeline.json",
            "proposal-generation-pipeline.json", 
            "browser-submission-pipeline.json",
            "notification-workflows.json"
        ]
        
        success_count = 0
        total_count = len(workflow_files)
        
        for workflow_file in workflow_files:
            filepath = os.path.join(workflows_dir, workflow_file)
            
            if not os.path.exists(filepath):
                print(f"⚠️  Workflow file not found: {filepath}")
                continue
            
            workflow = self.load_workflow_file(filepath)
            if workflow and self.deploy_workflow(workflow):
                success_count += 1
        
        print(f"\n📊 Deployment Summary: {success_count}/{total_count} workflows deployed successfully")
        
        if success_count == total_count:
            print("🎉 All workflows deployed successfully!")
            return True
        else:
            print("⚠️  Some workflows failed to deploy")
            return False
    
    def activate_all_workflows(self) -> bool:
        """Activate all deployed workflows"""
        workflows = self.list_workflows()
        success_count = 0
        
        for workflow in workflows:
            workflow_id = workflow.get('id')
            workflow_name = workflow.get('name')
            
            if workflow.get('active'):
                print(f"✅ Workflow already active: {workflow_name}")
                success_count += 1
            else:
                if self.activate_workflow(workflow_id):
                    success_count += 1
        
        print(f"\n📊 Activation Summary: {success_count}/{len(workflows)} workflows active")
        return success_count == len(workflows)
    
    def validate_deployment(self) -> bool:
        """Validate that all required workflows are deployed and active"""
        required_workflows = [
            "Job Discovery Pipeline",
            "Proposal Generation Pipeline",
            "Browser Submission Pipeline", 
            "Notification Workflows"
        ]
        
        workflows = self.list_workflows()
        workflow_names = [w.get('name') for w in workflows]
        
        print("\n🔍 Validating deployment...")
        
        all_valid = True
        validation_results = {}
        
        for required in required_workflows:
            if required in workflow_names:
                workflow = next(w for w in workflows if w.get('name') == required)
                is_active = workflow.get('active', False)
                
                if is_active:
                    print(f"✅ {required}: Deployed and Active")
                    validation_results[required] = "active"
                else:
                    print(f"⚠️  {required}: Deployed but Inactive")
                    validation_results[required] = "inactive"
                    all_valid = False
            else:
                print(f"❌ {required}: Not Found")
                validation_results[required] = "missing"
                all_valid = False
        
        # Test webhook connectivity
        print("\n🔗 Testing webhook connectivity...")
        webhook_test = self.test_webhook_connectivity()
        
        if webhook_test:
            print("✅ Webhook connectivity: Working")
        else:
            print("❌ Webhook connectivity: Failed")
            all_valid = False
        
        # Print summary
        print(f"\n📊 Validation Summary:")
        print(f"   Total workflows: {len(workflows)}")
        print(f"   Required workflows: {len(required_workflows)}")
        print(f"   Active workflows: {sum(1 for w in workflows if w.get('active'))}")
        print(f"   Missing workflows: {len([r for r in validation_results.values() if r == 'missing'])}")
        print(f"   Inactive workflows: {len([r for r in validation_results.values() if r == 'inactive'])}")
        print(f"   Webhook connectivity: {'✅' if webhook_test else '❌'}")
        
        if all_valid:
            print("\n🎉 All workflows are properly deployed and active!")
        else:
            print("\n⚠️  Some workflows need attention")
            
            # Provide specific remediation steps
            missing = [name for name, status in validation_results.items() if status == "missing"]
            inactive = [name for name, status in validation_results.items() if status == "inactive"]
            
            if missing:
                print(f"\n🔧 To fix missing workflows:")
                print(f"   Run: python scripts/setup_n8n_workflows.py")
                
            if inactive:
                print(f"\n🔧 To activate inactive workflows:")
                print(f"   1. Go to n8n interface: {self.n8n_url}")
                print(f"   2. Activate these workflows: {', '.join(inactive)}")
                
            if not webhook_test:
                print(f"\n🔧 To fix webhook connectivity:")
                print(f"   1. Check n8n is running: {self.n8n_url}")
                print(f"   2. Verify network connectivity")
                print(f"   3. Check authentication credentials")
        
        return all_valid
    
    def test_webhook_connectivity(self) -> bool:
        """Test webhook connectivity to n8n"""
        try:
            test_payload = {"test": True, "timestamp": "2024-01-01T00:00:00Z"}
            webhook_url = f"{self.n8n_url}/webhook/test-webhook"
            
            response = self.session.post(webhook_url, json=test_payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"   Webhook test error: {e}")
            return False
    
    def setup_credentials(self) -> bool:
        """Setup required credentials for workflows"""
        print("\n🔑 Setting up credentials...")
        
        # This would set up credentials for:
        # - Slack OAuth
        # - Google Service Account
        # - OpenAI API Key
        # - HTTP Basic Auth for API endpoints
        
        # For now, just print instructions
        print("""
📋 Manual Credential Setup Required:

1. Slack OAuth2 API:
   - Go to n8n Credentials
   - Add 'Slack OAuth2 API' credential
   - Configure with your Slack Bot Token

2. Google Service Account:
   - Add 'Google Service Account' credential
   - Upload your service account JSON file

3. OpenAI API:
   - Add 'OpenAI API' credential
   - Configure with your OpenAI API key

4. HTTP Basic Auth:
   - Add 'HTTP Basic Auth' credential for API endpoints
   - Use appropriate authentication for your API server

5. Gmail OAuth2:
   - Add 'Gmail OAuth2 API' credential
   - Configure OAuth2 flow for email notifications
        """)
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Deploy n8n workflows for Upwork Automation")
    parser.add_argument("--n8n-url", default="http://localhost:5678", help="n8n URL")
    parser.add_argument("--username", default="admin", help="n8n username")
    parser.add_argument("--password", default="automation123", help="n8n password")
    parser.add_argument("--workflows-dir", default="n8n-workflows", help="Workflows directory")
    parser.add_argument("--wait-timeout", type=int, default=60, help="Wait timeout for n8n")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for n8n")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing deployment")
    
    args = parser.parse_args()
    
    deployer = N8NWorkflowDeployer(
        n8n_url=args.n8n_url,
        auth=(args.username, args.password)
    )
    
    if args.validate_only:
        print("🔍 Validating existing deployment...")
        success = deployer.validate_deployment()
        exit(0 if success else 1)
    
    # Wait for n8n to be ready
    if not args.skip_wait:
        if not deployer.wait_for_n8n(args.wait_timeout):
            print("❌ n8n is not ready. Exiting.")
            exit(1)
    
    # Deploy workflows
    print("\n🚀 Starting workflow deployment...")
    if not deployer.deploy_all_workflows(args.workflows_dir):
        print("❌ Workflow deployment failed")
        exit(1)
    
    # Activate workflows
    print("\n⚡ Activating workflows...")
    if not deployer.activate_all_workflows():
        print("❌ Workflow activation failed")
        exit(1)
    
    # Setup credentials (manual instructions)
    deployer.setup_credentials()
    
    # Validate deployment
    if not deployer.validate_deployment():
        print("❌ Deployment validation failed")
        exit(1)
    
    print("\n🎉 n8n workflow setup completed successfully!")
    print(f"🌐 Access n8n at: {args.n8n_url}")
    print("📚 Check the workflows in the n8n interface and configure credentials as needed.")


if __name__ == "__main__":
    main()