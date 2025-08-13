# Ardan Automation System Setup Guide

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- Git

## Required API Keys and Credentials

Before starting, obtain the following:

1. **Browserbase API Key**
   - Sign up at https://browserbase.com
   - Create a project and get API key

2. **OpenAI API Key**
   - Get from https://platform.openai.com/api-keys

3. **Google Service Account**
   - Create service account in Google Cloud Console
   - Enable Google Docs and Drive APIs
   - Download JSON credentials file

4. **Slack Bot Token**
   - Create Slack app at https://api.slack.com/apps
   - Add bot token scopes: chat:write, files:write
   - Install app to workspace

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd ardan-automation
   cp .env.example .env
   ```

2. **Configure Environment**
   Edit `.env` file with your API keys and credentials:
   ```bash
   BROWSERBASE_API_KEY=your_key_here
   OPENAI_API_KEY=your_key_here
   GOOGLE_CREDENTIALS=path_to_service_account.json
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_CHANNEL_ID=your_channel_id
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Verify Installation**
   - API: http://localhost:8000/health
   - Web Interface: http://localhost:3000
   - n8n: http://localhost:5678 (admin/automation123)

## Service Configuration

### Database
- PostgreSQL runs on port 5432
- Database: `ardan_automation`
- User: `ardan_user`
- Password: `ardan_pass`

### Redis
- Runs on port 6379
- Used for task queue and caching

### n8n Workflows
1. Access n8n at http://localhost:5678
2. Import workflows from `n8n-workflows/` directory
3. Configure webhook URLs and credentials
4. Activate workflows

## Development Setup

### API Development
```bash
cd api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Web Development
```bash
cd web
npm install
npm run dev
```

## Configuration

### System Settings
Access the web interface at http://localhost:3000/settings to configure:
- Daily application limits
- Rate ranges
- Keywords for job filtering
- Notification preferences

### Browser Automation
- Sessions are managed automatically
- Stealth mode enabled by default
- Proxy rotation for IP diversity
- Human-like interaction delays

## Monitoring

### Logs
```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker
```

### Health Checks
- API Health: http://localhost:8000/health
- System Status: http://localhost:8000/api/system/status
- Database Health: Included in system status

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check if PostgreSQL container is running
   - Verify DATABASE_URL in environment

2. **Browserbase API Errors**
   - Verify API key is correct
   - Check Browserbase account limits

3. **Google Services Authentication**
   - Ensure service account JSON is accessible
   - Verify APIs are enabled in Google Cloud Console

4. **Slack Notifications Not Working**
   - Check bot token permissions
   - Verify channel ID is correct

### Reset System
```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart fresh
docker-compose up -d
```

## Security Notes

- Never commit API keys to version control
- Use strong passwords for production
- Regularly rotate API keys
- Monitor for unusual activity
- Keep dependencies updated

## Next Steps

After setup:
1. Configure job search keywords in settings
2. Upload work samples to Google Drive
3. Test with manual job discovery
4. Enable automation gradually
5. Monitor success rates and adjust