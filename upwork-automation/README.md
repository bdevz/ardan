# Ardan Automation System

An automated job application system for Salesforce Agentforce Developer positions that scales from 2-3 manual applications to 20-30 automated applications per day using advanced browser automation.

## Architecture

- **Browser Automation**: Browserbase + Stagehand + Director + MCP for intelligent browser control
- **Orchestration**: n8n workflows connecting browser automation with business logic
- **Backend**: FastAPI with PostgreSQL and Redis
- **Frontend**: React dashboard for monitoring and control
- **Deployment**: Local Docker environment with cloud service integrations

## Quick Start

```bash
# Clone and setup
git clone <repository>
cd ardan-automation

# Start services
docker-compose up -d

# Access web interface
open http://localhost:3000
```

## Project Structure

```
ardan-automation/
├── api/                    # FastAPI backend server
├── web/                    # React frontend interface
├── browser-automation/     # Browser automation services
├── n8n-workflows/         # n8n workflow definitions
├── shared/                # Shared utilities and models
├── docker-compose.yml     # Local deployment configuration
└── docs/                  # Documentation
```

## Services

- **API Server**: http://localhost:8000
- **Web Interface**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **n8n**: http://localhost:5678

## Development

See individual service README files for development setup and testing instructions.