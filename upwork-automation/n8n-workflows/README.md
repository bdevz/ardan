# n8n Workflows

This directory contains n8n workflow definitions for the Upwork Automation System.

## Workflows

### 1. Job Discovery Pipeline
- **File**: `job-discovery-pipeline.json`
- **Trigger**: Cron schedule (every 30 minutes) or webhook
- **Purpose**: Automated job search and filtering using browser automation
- **Features**: 
  - Intelligent job search with multiple browser sessions
  - AI-powered job filtering and ranking
  - Slack notifications with job details
  - Automatic trigger of proposal generation

### 2. Proposal Generation Pipeline
- **File**: `proposal-generation-pipeline.json`
- **Trigger**: Webhook from job discovery or manual trigger
- **Purpose**: Generate tailored proposals for discovered jobs
- **Features**:
  - OpenAI-powered job requirement analysis
  - Automated proposal content generation
  - Google Docs integration for proposal storage
  - Automatic attachment selection from Google Drive
  - Quality scoring and auto-submission for high-quality proposals

### 3. Browser Submission Pipeline
- **File**: `browser-submission-pipeline.json`
- **Trigger**: Webhook from proposal generation or manual trigger
- **Purpose**: Submit proposals through browser automation
- **Features**:
  - Stagehand AI-powered form filling
  - Director session orchestration
  - Retry logic with exponential backoff
  - Screenshot capture for confirmation
  - Application record creation

### 4. Notification Workflows
- **File**: `notification-workflows.json`
- **Trigger**: Various system events via webhooks
- **Purpose**: Send comprehensive notifications and updates
- **Features**:
  - Multi-channel notifications (Slack, Email)
  - Rich notification templates for different event types
  - Daily summary reports
  - Error alerts with detailed information

## Quick Setup

### Automated Setup (Recommended)
```bash
# Start the system with n8n
docker-compose up -d

# Wait for n8n to be ready, then deploy workflows
python scripts/setup_n8n_workflows.py

# Validate deployment
python scripts/setup_n8n_workflows.py --validate-only
```

### Manual Setup
1. Access n8n interface at http://localhost:5678
   - Username: `admin`
   - Password: `automation123`

2. Import workflow files:
   - Go to Workflows → Import from File
   - Import each JSON file from this directory
   - Activate each workflow after import

3. Configure credentials (see Credentials section below)

4. Test webhook connectivity:
   ```bash
   curl -X POST http://localhost:5678/webhook/test-webhook \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```

## Credentials Configuration

Each workflow requires specific credentials to be configured in n8n:

### Required Credentials

1. **Slack OAuth2 API**
   - Type: `Slack OAuth2 API`
   - Required for: All notification workflows
   - Setup: Configure with your Slack Bot Token
   - Scopes: `chat:write`, `files:write`, `channels:read`

2. **Google Service Account**
   - Type: `Google Service Account`
   - Required for: Proposal generation (Google Docs/Drive)
   - Setup: Upload service account JSON file
   - APIs: Google Docs API, Google Drive API

3. **OpenAI API**
   - Type: `OpenAI API`
   - Required for: Proposal generation (job analysis)
   - Setup: Configure with OpenAI API key
   - Model: GPT-4 recommended

4. **HTTP Basic Auth (API)**
   - Type: `HTTP Basic Auth`
   - Required for: API endpoint communication
   - Setup: Configure for local API server authentication

5. **Gmail OAuth2 API**
   - Type: `Gmail OAuth2 API`
   - Required for: Email notifications
   - Setup: Configure OAuth2 flow for Gmail

### Credential Setup Steps

1. In n8n, go to **Settings** → **Credentials**
2. Click **Add Credential** for each required type
3. Follow the setup wizard for each credential
4. Test credentials using the built-in test functionality
5. Assign credentials to appropriate workflow nodes

## Webhook Endpoints

The workflows expose the following webhook endpoints:

### Trigger Endpoints
- `POST /webhook/trigger-job-discovery` - Trigger job discovery
- `POST /webhook/trigger-proposal-generation` - Trigger proposal generation  
- `POST /webhook/trigger-browser-submission` - Trigger browser submission
- `POST /webhook/trigger-notification` - Send notifications

### Callback Endpoints
- `POST /webhook/job-discovery-complete` - Job discovery completion callback

### Test Endpoints
- `POST /webhook/test-webhook` - Test webhook connectivity

## Workflow Configuration

### Environment Variables
Set these in your `.env` file:
```bash
N8N_WEBHOOK_URL=http://localhost:5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=automation123
SLACK_CHANNEL_ID=C1234567890  # Your Slack channel ID
```

### Workflow Parameters

#### Job Discovery Pipeline
```json
{
  "keywords": ["Salesforce Agentforce", "Salesforce AI"],
  "session_pool_size": 3,
  "max_jobs": 20,
  "filters": {
    "min_hourly_rate": 50,
    "min_client_rating": 4.0,
    "payment_verified": true
  }
}
```

#### Proposal Generation Pipeline
```json
{
  "job_ids": ["job-uuid-1", "job-uuid-2"],
  "auto_create_docs": true,
  "select_attachments": true,
  "quality_threshold": 0.7
}
```

#### Browser Submission Pipeline
```json
{
  "proposal_ids": ["proposal-uuid-1"],
  "session_type": "proposal_submission",
  "stealth_mode": true,
  "retry_attempts": 3
}
```

## Monitoring and Debugging

### Workflow Execution Logs
- Access execution logs in n8n interface
- Monitor workflow performance and success rates
- Debug failed executions with detailed error information

### Health Checks
```bash
# Check n8n health
curl http://localhost:5678/healthz

# Test API connectivity
curl -X POST http://localhost:8000/api/n8n/status

# Validate workflow deployment
python scripts/setup_n8n_workflows.py --validate-only
```

### Common Issues

1. **Webhook Timeouts**
   - Increase timeout values in workflow nodes
   - Check API server response times

2. **Credential Errors**
   - Verify all credentials are properly configured
   - Test credentials individually in n8n

3. **Browser Automation Failures**
   - Check Browserbase API key and quota
   - Verify Stagehand service availability

4. **Notification Failures**
   - Verify Slack bot permissions
   - Check channel IDs and user permissions

## Development and Testing

### Local Development
```bash
# Start n8n in development mode
docker-compose up n8n

# Test individual workflows
curl -X POST http://localhost:5678/webhook/trigger-job-discovery \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["test"], "max_jobs": 1}'
```

### Testing Workflows
```bash
# Run n8n integration tests
pytest tests/test_n8n_integration.py -v

# Test specific workflow
pytest tests/test_n8n_integration.py::TestN8NService::test_trigger_job_discovery_workflow_success -v
```

## Scaling and Performance

### Concurrent Execution
- Workflows support parallel execution
- Browser sessions are pooled for efficiency
- Rate limiting prevents API overload

### Resource Management
- Monitor n8n memory and CPU usage
- Scale browser session pools based on load
- Implement queue management for high-volume processing

### Performance Optimization
- Use workflow caching where appropriate
- Optimize API call patterns
- Monitor and tune timeout values

## Security Considerations

### Credential Security
- Store sensitive credentials securely in n8n
- Use environment variables for configuration
- Regularly rotate API keys and tokens

### Network Security
- Use HTTPS for production deployments
- Implement proper authentication for webhooks
- Monitor for suspicious activity

### Data Privacy
- Ensure compliance with data protection regulations
- Implement proper data retention policies
- Secure transmission of sensitive job and proposal data