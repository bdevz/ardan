# Deployment Guide

This guide covers the deployment and operational procedures for the Upwork Automation System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Production Deployment](#production-deployment)
4. [Development Deployment](#development-deployment)
5. [Configuration Management](#configuration-management)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 8GB RAM (16GB recommended for production)
- **Storage**: Minimum 50GB free space (100GB+ recommended for production)
- **CPU**: Minimum 4 cores (8+ cores recommended for production)

### External Service Requirements

- **Browserbase Account**: For managed browser infrastructure
- **OpenAI API Key**: For proposal generation
- **Google Cloud Project**: For Google Docs/Drive integration
- **Slack Workspace**: For notifications (optional)
- **n8n Instance**: For workflow automation (optional)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd upwork-automation
```

### 2. Create Directories

```bash
mkdir -p logs/{api,worker,scheduler,web}
mkdir -p data/{postgres,redis,uploads,sessions}
mkdir -p backups/{postgres,redis,sessions}
mkdir -p credentials
```

### 3. Set Permissions

```bash
chmod +x scripts/*.sh
chmod 600 .env.*
chmod 700 credentials/
```

## Production Deployment

### 1. Environment Configuration

Copy the production environment template:

```bash
cp .env.production .env
```

Edit `.env` with your production values:

```bash
# Required: Set these values
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here
BROWSERBASE_API_KEY=your_browserbase_api_key
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=your_slack_bot_token
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
GRAFANA_PASSWORD=your_grafana_password_here
```

### 2. Google Services Setup

1. Create a Google Cloud Project
2. Enable Google Docs, Drive, and Sheets APIs
3. Create a service account and download credentials
4. Save credentials as `credentials/google-credentials.json`

### 3. SSL/TLS Setup (Optional)

For production with HTTPS:

```bash
# Generate self-signed certificates (or use Let's Encrypt)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout credentials/ssl-key.pem \
  -out credentials/ssl-cert.pem
```

### 4. Deploy Services

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Initialize Database

```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec api-server python -m alembic upgrade head

# Create initial admin user (optional)
docker-compose -f docker-compose.prod.yml exec api-server python -c "
from database.models import User
from database.connection import get_db_session
import asyncio

async def create_admin():
    async with get_db_session() as db:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        db.add(admin)
        await db.commit()

asyncio.run(create_admin())
"
```

### 6. Verify Deployment

```bash
# Run health check
./scripts/health_check.sh

# Check individual services
curl http://localhost:8000/health
curl http://localhost:3000
curl http://localhost:9090  # Prometheus
curl http://localhost:3001  # Grafana
```

## Development Deployment

### 1. Development Environment

```bash
cp .env.development .env
```

### 2. Start Development Services

```bash
# Start with development configuration
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f api-server
```

### 3. Development Tools

Access development tools:

- **API Documentation**: http://localhost:8000/docs
- **Database Admin**: http://localhost:8080 (pgAdmin)
- **Redis Admin**: http://localhost:8081 (Redis Commander)

## Configuration Management

### Environment Variables

The system uses environment-specific configuration files:

- `.env.production` - Production settings
- `.env.development` - Development settings
- `.env.testing` - Testing settings

### Configuration Sections

#### Database Configuration
```bash
POSTGRES_DB=upwork_automation_prod
POSTGRES_USER=upwork_user
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql://user:pass@db:5432/dbname
```

#### Security Configuration
```bash
JWT_SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key
ALLOWED_ORIGINS=["http://localhost:3000"]
```

#### Rate Limiting
```bash
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60
MAX_DAILY_APPLICATIONS=30
MIN_DELAY_BETWEEN_APPLICATIONS=300
```

#### Job Filtering
```bash
MIN_HOURLY_RATE=50.0
TARGET_HOURLY_RATE=75.0
MIN_CLIENT_RATING=4.0
REQUIRED_KEYWORDS=["Salesforce","Agentforce"]
```

### Updating Configuration

1. Edit the appropriate `.env` file
2. Restart affected services:

```bash
docker-compose -f docker-compose.prod.yml restart api-server worker
```

## Monitoring and Logging

### Accessing Monitoring Tools

- **Grafana Dashboard**: http://localhost:3001
  - Username: admin
  - Password: (set in GRAFANA_PASSWORD)

- **Prometheus Metrics**: http://localhost:9090

### Log Locations

Logs are stored in the `logs/` directory:

```
logs/
├── api/           # API server logs
├── worker/        # Background worker logs
├── scheduler/     # Job scheduler logs
├── web/           # Web interface logs
└── system/        # System logs
```

### Log Aggregation

Logs are automatically collected by Promtail and sent to Loki for centralized logging.

### Health Monitoring

Run health checks manually:

```bash
# Comprehensive health check
./scripts/health_check.sh

# API health check
curl http://localhost:8000/health/detailed
```

### Setting Up Alerts

1. Configure Slack webhook in `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

2. Set up cron job for regular health checks:
```bash
# Add to crontab
*/5 * * * * /path/to/upwork-automation/scripts/health_check.sh
```

## Backup and Recovery

### Automated Backups

Backups are configured to run automatically via cron:

```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * /path/to/upwork-automation/scripts/backup.sh
```

### Manual Backup

```bash
# Create immediate backup
./scripts/backup.sh
```

### Restore from Backup

```bash
# List available backups
./scripts/restore.sh -l

# Restore from specific timestamp
./scripts/restore.sh -t 20240101_120000

# Restore only database
./scripts/restore.sh -p -t 20240101_120000
```

### Backup Verification

Backups are automatically verified during the backup process. Manual verification:

```bash
# Check backup integrity
gzip -t /backups/postgres/postgres_backup_20240101_120000.sql.gz
gzip -t /backups/redis/redis_backup_20240101_120000.rdb.gz
```

## Troubleshooting

### Common Issues

#### Services Won't Start

1. Check Docker daemon is running:
```bash
sudo systemctl status docker
```

2. Check port conflicts:
```bash
netstat -tulpn | grep :8000
```

3. Check logs:
```bash
docker-compose -f docker-compose.prod.yml logs api-server
```

#### Database Connection Issues

1. Check database service:
```bash
docker-compose -f docker-compose.prod.yml exec db pg_isready
```

2. Test connection:
```bash
docker-compose -f docker-compose.prod.yml exec db psql -U upwork_user -d upwork_automation_prod -c "SELECT 1;"
```

#### High Resource Usage

1. Check system resources:
```bash
docker stats
```

2. Check application metrics:
```bash
curl http://localhost:8000/health/metrics
```

3. Scale services if needed:
```bash
docker-compose -f docker-compose.prod.yml up -d --scale worker=3
```

#### Browser Automation Issues

1. Check Browserbase connectivity:
```bash
curl -H "Authorization: Bearer $BROWSERBASE_API_KEY" https://api.browserbase.com/v1/sessions
```

2. Check session pool status:
```bash
curl http://localhost:8000/api/browser/sessions/status
```

### Log Analysis

#### Finding Errors

```bash
# Search for errors in API logs
grep -i error logs/api/*.log

# Search for specific correlation ID
grep "correlation_id_here" logs/api/*.log
```

#### Performance Analysis

```bash
# Find slow requests
grep "process_time.*[5-9]\." logs/api/*.log

# Find high error rates
grep "status_code.*[45][0-9][0-9]" logs/api/*.log
```

### Recovery Procedures

#### Service Recovery

1. Restart individual service:
```bash
docker-compose -f docker-compose.prod.yml restart api-server
```

2. Full system restart:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

#### Data Recovery

1. Database corruption:
```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop api-server worker scheduler

# Restore from backup
./scripts/restore.sh -p -t LATEST_BACKUP_TIMESTAMP

# Restart services
docker-compose -f docker-compose.prod.yml start api-server worker scheduler
```

2. Redis data loss:
```bash
# Restore Redis data
./scripts/restore.sh -r -t LATEST_BACKUP_TIMESTAMP
```

### Performance Tuning

#### Database Optimization

1. Monitor query performance:
```sql
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

2. Adjust connection pool:
```bash
# In .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

#### Redis Optimization

1. Monitor memory usage:
```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory
```

2. Adjust memory settings:
```bash
# In docker-compose.prod.yml
command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Security Considerations

#### Regular Security Tasks

1. Update passwords regularly:
```bash
# Generate new passwords
openssl rand -base64 32
```

2. Rotate API keys:
- Update Browserbase API key
- Update OpenAI API key
- Update Slack tokens

3. Review access logs:
```bash
grep "authentication" logs/api/*.log
```

#### Security Monitoring

1. Monitor failed login attempts:
```bash
grep "authentication.*failed" logs/api/*.log
```

2. Check for suspicious activity:
```bash
grep -E "(rate.limit|suspicious|blocked)" logs/api/*.log
```

## Maintenance Procedures

### Regular Maintenance

#### Daily Tasks
- Check system health
- Review error logs
- Monitor resource usage

#### Weekly Tasks
- Review backup integrity
- Update dependencies
- Performance analysis

#### Monthly Tasks
- Security audit
- Capacity planning
- Documentation updates

### Update Procedures

#### Application Updates

1. Backup current system:
```bash
./scripts/backup.sh
```

2. Pull latest changes:
```bash
git pull origin main
```

3. Rebuild and restart:
```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

4. Run migrations:
```bash
docker-compose -f docker-compose.prod.yml exec api-server python -m alembic upgrade head
```

5. Verify deployment:
```bash
./scripts/health_check.sh
```

#### System Updates

1. Update Docker:
```bash
sudo apt update && sudo apt upgrade docker-ce docker-compose-plugin
```

2. Update base images:
```bash
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

For additional support or questions, refer to the project documentation or contact the development team.