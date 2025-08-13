#!/usr/bin/env python3
"""
Quick Start Script for Upwork Automation System
Provides an interactive setup experience for first-time users
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List


class QuickStart:
    """Interactive quick start setup for the Upwork Automation System."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.env_file = self.project_root / ".env"
        self.credentials_dir = self.project_root / "credentials"
        
    def print_banner(self):
        """Print the welcome banner."""
        print("🚀 Upwork Automation System - Quick Start")
        print("=" * 60)
        print("Browser Automation: Browserbase + Stagehand + Director + MCP")
        print("Orchestration: n8n workflows with business logic integration")
        print("=" * 60)
        print()
        
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are installed."""
        print("🔍 Checking Prerequisites...")
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker is installed")
            else:
                print("❌ Docker is not working properly")
                return False
        except FileNotFoundError:
            print("❌ Docker is not installed")
            print("   Please install Docker: https://docs.docker.com/get-docker/")
            return False
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker Compose is installed")
            else:
                print("❌ Docker Compose is not working properly")
                return False
        except FileNotFoundError:
            print("❌ Docker Compose is not installed")
            print("   Please install Docker Compose")
            return False
        
        # Check Python version
        if sys.version_info >= (3, 8):
            print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is adequate")
        else:
            print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} is too old")
            print("   Please upgrade to Python 3.8 or higher")
            return False
        
        print("✅ All prerequisites met")
        return True
    
    def setup_environment(self):
        """Interactive environment setup."""
        print("\n🔧 Environment Setup")
        print("-" * 30)
        
        # Create .env file if it doesn't exist
        if not self.env_file.exists():
            print("Creating .env file from template...")
            subprocess.run(['cp', '.env.example', '.env'])
            print("✅ .env file created")
        else:
            print("✅ .env file already exists")
        
        # Collect API keys
        api_keys = self.collect_api_keys()
        
        # Update .env file
        self.update_env_file(api_keys)
        
        print("✅ Environment configuration complete")
    
    def collect_api_keys(self) -> Dict[str, str]:
        """Collect API keys from user."""
        print("\n📝 API Keys Configuration")
        print("You'll need the following API keys to run the system:")
        print()
        
        api_keys = {}
        
        # Browserbase API Key
        print("1. Browserbase API Key")
        print("   Get it from: https://browserbase.com/dashboard")
        browserbase_key = input("   Enter your Browserbase API key (or press Enter to skip): ").strip()
        if browserbase_key:
            api_keys['BROWSERBASE_API_KEY'] = browserbase_key
        
        # OpenAI API Key
        print("\n2. OpenAI API Key")
        print("   Get it from: https://platform.openai.com/api-keys")
        openai_key = input("   Enter your OpenAI API key (or press Enter to skip): ").strip()
        if openai_key:
            api_keys['OPENAI_API_KEY'] = openai_key
        
        # Slack Bot Token
        print("\n3. Slack Bot Token (Optional)")
        print("   Create a Slack app at: https://api.slack.com/apps")
        slack_token = input("   Enter your Slack Bot Token (or press Enter to skip): ").strip()
        if slack_token:
            api_keys['SLACK_BOT_TOKEN'] = slack_token
        
        return api_keys
    
    def update_env_file(self, api_keys: Dict[str, str]):
        """Update the .env file with provided API keys."""
        if not api_keys:
            return
        
        # Read current .env file
        env_content = self.env_file.read_text()
        
        # Update with provided keys
        for key, value in api_keys.items():
            # Replace placeholder values
            env_content = env_content.replace(f"{key}=your_{key.lower()}_here", f"{key}={value}")
            env_content = env_content.replace(f"{key}=your_browserbase_api_key_here", f"{key}={value}")
            env_content = env_content.replace(f"{key}=your_openai_api_key_here", f"{key}={value}")
            env_content = env_content.replace(f"{key}=your_slack_bot_token_here", f"{key}={value}")
        
        # Write back to file
        self.env_file.write_text(env_content)
    
    def setup_google_credentials(self):
        """Setup Google credentials."""
        print("\n🔐 Google Credentials Setup (Optional)")
        print("-" * 40)
        
        # Create credentials directory
        self.credentials_dir.mkdir(exist_ok=True)
        
        google_creds_file = self.credentials_dir / "google-credentials.json"
        
        if google_creds_file.exists():
            print("✅ Google credentials already exist")
            return
        
        print("For Google Docs/Drive integration, you need a service account:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Docs, Drive, and Sheets APIs")
        print("4. Create a service account")
        print("5. Download the credentials JSON file")
        print("6. Save it as credentials/google-credentials.json")
        print()
        
        setup_google = input("Do you want to set up Google credentials now? (y/n): ").strip().lower()
        if setup_google == 'y':
            creds_path = input("Enter path to your Google credentials JSON file: ").strip()
            if creds_path and Path(creds_path).exists():
                subprocess.run(['cp', creds_path, str(google_creds_file)])
                print("✅ Google credentials copied")
            else:
                print("⚠️  File not found. You can add it later to credentials/google-credentials.json")
        else:
            print("⚠️  Skipping Google credentials setup")
    
    def start_system(self):
        """Start the system using Docker Compose."""
        print("\n🚀 Starting the System")
        print("-" * 25)
        
        print("Starting Docker containers...")
        try:
            # Start the system
            result = subprocess.run(['docker-compose', 'up', '-d'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ System started successfully!")
                print()
                print("🌐 Access Points:")
                print("   - Web Interface: http://localhost:3000")
                print("   - API Documentation: http://localhost:8000/docs")
                print("   - n8n Interface: http://localhost:5678")
                print("     (Username: admin, Password: automation123)")
                print()
                
                # Setup n8n workflows
                self.setup_n8n_workflows()
                
            else:
                print("❌ Failed to start system")
                print("Error:", result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error starting system: {e}")
            return False
        
        return True
    
    def setup_n8n_workflows(self):
        """Setup n8n workflows."""
        print("📋 Setting up n8n workflows...")
        
        setup_workflows = input("Do you want to automatically setup n8n workflows? (y/n): ").strip().lower()
        if setup_workflows == 'y':
            try:
                # Wait a bit for n8n to start
                print("Waiting for n8n to start...")
                import time
                time.sleep(10)
                
                result = subprocess.run(['python', 'scripts/setup_n8n_workflows.py'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ n8n workflows setup complete")
                else:
                    print("⚠️  n8n workflows setup had issues")
                    print("You can set them up manually later")
                    
            except Exception as e:
                print(f"⚠️  Error setting up workflows: {e}")
                print("You can set them up manually later")
        else:
            print("⚠️  Skipping n8n workflows setup")
            print("You can set them up later with: python scripts/setup_n8n_workflows.py")
    
    def show_next_steps(self):
        """Show next steps to the user."""
        print("\n🎉 Setup Complete!")
        print("=" * 30)
        print()
        print("📋 Next Steps:")
        print("1. Open the web interface: http://localhost:3000")
        print("2. Check the API documentation: http://localhost:8000/docs")
        print("3. Configure n8n workflows: http://localhost:5678")
        print("4. Monitor logs: docker-compose logs -f")
        print("5. Run tests: pytest tests/ -v")
        print()
        print("📚 Documentation:")
        print("- README.md - System overview")
        print("- docs/ - Detailed documentation")
        print("- browser-automation/README.md - Browser automation guide")
        print("- n8n-workflows/README.md - Workflow configuration")
        print()
        print("🆘 Need Help?")
        print("- Check logs: docker-compose logs [service-name]")
        print("- Restart services: docker-compose restart")
        print("- Stop system: docker-compose down")
        print()
        print("Happy automating! 🤖")
    
    def run(self):
        """Run the complete quick start process."""
        self.print_banner()
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please install required software and try again.")
            return False
        
        # Setup environment
        self.setup_environment()
        
        # Setup Google credentials
        self.setup_google_credentials()
        
        # Start the system
        if not self.start_system():
            print("\n❌ Failed to start the system. Please check the logs and try again.")
            return False
        
        # Show next steps
        self.show_next_steps()
        
        return True


def main():
    """Main function."""
    quick_start = QuickStart()
    success = quick_start.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()