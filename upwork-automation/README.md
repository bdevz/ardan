# Ardan Automation System

An intelligent, AI-powered job application automation system that scales from manual applications to 20-30 automated applications per day using cutting-edge browser automation technology.

## 🚀 Key Features

- **🤖 AI-Powered Browser Automation**: Browserbase + Stagehand + Director + MCP for intelligent browser control
- **🔄 Workflow Orchestration**: n8n workflows connecting browser automation with business logic
- **📊 Performance Analytics**: Comprehensive tracking and learning system
- **🛡️ Safety & Compliance**: Built-in rate limiting and ethical automation practices
- **📱 Real-time Monitoring**: React dashboard with live updates and notifications
- **🔧 Minimal Setup**: Ready to go with just API keys - no complex customization needed

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser Automation Stack                     │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│   Browserbase   │   Stagehand     │    Director     │    MCP    │
│   (Sessions)    │   (AI Control)  │ (Orchestration) │ (Context) │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    n8n Workflow Engine                         │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│ Job Discovery   │   Proposal      │   Submission    │   Alerts  │
│   Pipeline      │   Generation    │   Pipeline      │ & Reports │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Services                          │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│   FastAPI       │   PostgreSQL    │     Redis       │  Workers  │
│   (REST API)    │   (Database)    │   (Queue)       │ (Tasks)   │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
```

## ⚡ Quick Start

### Option 1: Interactive Setup (Recommended)
```bash
# Clone the repository
git clone <repository>
cd ardan-automation

# Run interactive setup
python quick_start.py
```

### Option 2: Manual Setup
```bash
# Clone and setup
git clone <repository>
cd ardan-automation

# Copy environment template
cp .env.example .env
# Edit .env and add your API keys

# Start services
docker-compose up -d

# Setup n8n workflows
python scripts/setup_n8n_workflows.py

# Access web interface
open http://localhost:3000
```

## 📁 Project Structure

```
ardan-automation/
├── 🤖 browser-automation/     # AI Browser Control Stack
│   ├── browserbase_client.py  # Browserbase session management
│   ├── stagehand_controller.py # AI-powered browser control
│   ├── director.py            # Workflow orchestration
│   ├── mcp_client.py          # Model Context Protocol
│   └── workflows/             # Automation workflows
├── 🔄 n8n-workflows/          # Business Logic Orchestration
│   ├── job-discovery-pipeline.json
│   ├── proposal-generation-pipeline.json
│   ├── browser-submission-pipeline.json
│   └── notification-workflows.json
├── 🚀 api/                    # FastAPI Backend
│   ├── services/              # Business logic services
│   ├── workers/               # Background task workers
│   ├── routers/               # API endpoints
│   └── main.py               # Application entry point
├── 🌐 web/                    # React Frontend
├── 🔧 shared/                 # Shared utilities and models
├── 📊 monitoring/             # Grafana dashboards & metrics
├── 🧪 tests/                  # Comprehensive test suite
├── 📜 scripts/                # Setup and utility scripts
├── 🐳 docker-compose.yml      # Container orchestration
└── 📚 docs/                   # Documentation
```

## 🌐 Services & Access Points

| Service | URL | Purpose | Credentials |
|---------|-----|---------|-------------|
| **Web Interface** | http://localhost:3000 | Main dashboard & monitoring | - |
| **API Documentation** | http://localhost:8000/docs | REST API documentation | - |
| **n8n Workflows** | http://localhost:5678 | Workflow management | admin / automation123 |
| **PostgreSQL** | localhost:5432 | Database | ardan_user / ardan_pass |
| **Redis** | localhost:6379 | Task queue & cache | - |
| **Grafana** | http://localhost:3001 | Monitoring dashboards | admin / [generated] |

## 🔑 Required API Keys

To run the system, you'll need these API keys:

### Essential (Required)
- **Browserbase API Key**: Get from [Browserbase Dashboard](https://browserbase.com/dashboard)
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

### Optional (Enhanced Features)
- **Slack Bot Token**: For notifications - [Create Slack App](https://api.slack.com/apps)
- **Google Service Account**: For Docs/Drive integration - [Google Cloud Console](https://console.cloud.google.com/)

## 🚀 Browser Automation Stack

### Browserbase Integration
- **Managed Browser Sessions**: Cloud-based browser infrastructure
- **Session Pooling**: Efficient session reuse and management
- **Stealth Mode**: Advanced anti-detection capabilities
- **Proxy Support**: IP rotation and geographic distribution

### Stagehand AI Control
- **Intelligent Navigation**: AI-powered page understanding
- **Dynamic Content Handling**: Adapts to changing page structures
- **Form Interaction**: Smart form filling and submission
- **Error Recovery**: Automatic error detection and recovery

### Director Orchestration
- **Workflow Management**: Complex multi-step automation
- **Parallel Execution**: Concurrent task processing
- **Checkpoint System**: Recovery from failures
- **Session Distribution**: Load balancing across browser sessions

### MCP Integration
- **Context Awareness**: Maintains page and session context
- **Strategy Adaptation**: Learns and adapts automation strategies
- **Performance Optimization**: Continuous improvement based on results

## 🔄 n8n Workflow Engine

### Pre-built Workflows
1. **Job Discovery Pipeline**
   - Automated job search with AI filtering
   - Multi-keyword strategy execution
   - Result deduplication and ranking

2. **Proposal Generation Pipeline**
   - AI-powered proposal creation
   - Google Docs integration
   - Quality scoring and optimization

3. **Browser Submission Pipeline**
   - Automated application submission
   - Screenshot capture for verification
   - Error handling and retry logic

4. **Notification & Reporting**
   - Real-time Slack notifications
   - Daily summary reports
   - Performance alerts

## 📊 Performance & Analytics

- **Application Pipeline Tracking**: From discovery to hire
- **Success Pattern Analysis**: AI-powered optimization
- **Strategy Adjustment**: Automatic improvement based on results
- **Recommendation Engine**: Profile and approach optimization
- **Alert System**: Performance monitoring and corrective actions

## 🛡️ Safety & Compliance

- **Rate Limiting**: Configurable application limits (default: 30/day)
- **Human-like Delays**: Randomized timing to avoid detection
- **Ethical Automation**: Respects platform terms of service
- **Error Handling**: Graceful failure management
- **Audit Trail**: Complete logging of all actions

## 🧪 Testing & Validation

```bash
# Run complete system validation
python validate_complete_system.py

# Run specific component tests
python validate_stagehand_implementation.py
python validate_task_queue_implementation.py
python validate_performance_implementation.py

# Run test suite
pytest tests/ -v

# Run integration tests
pytest tests/test_*_integration.py -v
```

## 🔧 Development & Customization

### Local Development
```bash
# Start individual services for development
docker-compose up db redis -d  # Start dependencies
python api/main.py            # Start API server
cd web && npm start           # Start frontend

# Run workers separately
python api/workers/worker_manager.py
python api/scheduler_runner.py
```

### Configuration
- **Environment Variables**: See `.env.example` for all options
- **Job Filters**: Customize in `shared/config.py`
- **Rate Limits**: Adjust in environment configuration
- **Workflow Customization**: Modify n8n workflows via web interface

## 📚 Documentation

- **[Browser Automation Guide](browser-automation/README.md)**: Detailed browser automation documentation
- **[Director Orchestration](browser-automation/README_DIRECTOR.md)**: Workflow orchestration system
- **[n8n Workflows](n8n-workflows/README.md)**: Workflow configuration and setup
- **[API Documentation](http://localhost:8000/docs)**: Interactive API documentation
- **[Worker System](api/workers/README.md)**: Background task processing

## 🆘 Troubleshooting

### Common Issues

**System won't start**
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart services
docker-compose restart
```

**Browser automation fails**
- Verify Browserbase API key is valid
- Check session limits and quotas
- Review browser automation logs

**n8n workflows not working**
- Ensure n8n is accessible at http://localhost:5678
- Check webhook URLs in workflow configurations
- Verify API connectivity

**Performance issues**
- Monitor resource usage: `docker stats`
- Check Redis queue status
- Review worker logs for bottlenecks

### Getting Help

1. **Check Logs**: `docker-compose logs -f [service]`
2. **System Status**: Visit http://localhost:8000/health
3. **Validation**: Run `python validate_complete_system.py`
4. **Reset**: `docker-compose down && docker-compose up -d`

## 🎯 Next Steps After Setup

1. **Configure Job Filters**: Customize search criteria in settings
2. **Test Workflows**: Run manual workflow tests in n8n
3. **Monitor Performance**: Check dashboards and metrics
4. **Optimize Settings**: Adjust rate limits and delays based on results
5. **Scale Up**: Increase session pools and worker counts as needed

## 📈 Scaling & Production

- **Horizontal Scaling**: Add more worker containers
- **Session Scaling**: Increase Browserbase session limits
- **Database Optimization**: Configure PostgreSQL for production
- **Monitoring**: Set up Grafana dashboards and alerts
- **Backup Strategy**: Implement automated backups

---

**Ready to automate your job applications?** 🚀

Run `python quick_start.py` to get started in minutes!