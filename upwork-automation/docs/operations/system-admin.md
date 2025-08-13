# System Administration Guide

## Overview

This guide provides comprehensive system administration procedures for the Upwork Automation System. It covers installation, configuration, maintenance, monitoring, and security management.

## System Requirements

### Hardware Requirements

**Minimum Requirements**:
- CPU: 4 cores (2.0 GHz or higher)
- RAM: 8 GB
- Storage: 50 GB available space
- Network: Stable broadband internet connection

**Recommended Requirements**:
- CPU: 8 cores (3.0 GHz or higher)
- RAM: 16 GB
- Storage: 100 GB SSD
- Network: High-speed internet with low latency

### Software Requirements

**Operating System**:
- Ubuntu 20.04 LTS or later
- macOS 10.15 or later
- Windows 10 Pro with WSL2

**Required Software**:
- Docker 20.10 or later
- Docker Compose 2.0 or later
- Git 2.30 or later
- curl and wget
- OpenSSL

## Installation and Setup

### Initial Installation

#### 1. Clone Repository
```bash
# Clone the repository
git clone https://github.com/your-org/upwork-automation.git
cd upwork-automation

# Verify repository structure
ls -la
```

#### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables**:
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@db:5432/upwork_automation
POSTGRES_USER=user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=upwork_automation

# Redis Configuration
REDIS_URL=redis://redis:6379

# API Configuration
JWT_SECRET=your_jwt_secret_key_here
JWT_EXPIRATION_HOURS=24
API_HOST=0.0.0.0
API_PORT=8000

# Browser Automation
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_project_id

# Google Services
GOOGLE_SERVICE_ACCOUNT_KEY=path/to/service-account-key.json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#upwork-automation

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# n8n Configuration
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=secure_password
```

#### 3. SSL Certificate Setup (Production)
```bash
# Generate SSL certificates for production
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key -out ssl/certificate.crt

# Update docker-compose.yml for SSL
# Add SSL volume mounts and environment variables
```

#### 4. Initial Deployment
```bash
# Build and start all services
docker-compose up -d

# Wait for services to initialize
sleep 60

# Verify all services are running
docker-compose ps

# Check service health
curl http://localhost:8000/api/system/status
curl http://localhost:3000
```

#### 5. Database Initialization
```bash
# Run database migrations
docker-compose exec api-server alembic upgrade head

# Create initial admin user
docker-compose exec api-server python -c "
from api.database.models import User
from api.database.connection import get_db
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = next(get_db())

admin_user = User(
    username='admin',
    email='admin@example.com',
    password_hash=pwd_context.hash('admin_password'),
    is_active=True,
    is_admin=True
)
db.add(admin_user)
db.commit()
print('Admin user created successfully')
"
```

### Service Configuration

#### API Server Configuration
```bash
# Create API server configuration file
cat > api/config/production.yaml << EOF
database:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600

redis:
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5

browser_automation:
  session_pool_size: 5
  session_timeout: 1800
  max_retries: 3
  retry_delay: 5

rate_limiting:
  applications_per_hour: 3
  applications_per_day: 30
  safety_delay_min: 300
  safety_delay_max: 900

logging:
  level: INFO
  format: json
  file: /var/log/upwork-automation/api.log
EOF
```

#### Worker Configuration
```bash
# Configure background workers
cat > worker/config/production.yaml << EOF
concurrency: 4
max_tasks_per_child: 100
task_soft_time_limit: 300
task_time_limit: 600

queues:
  job_discovery:
    priority: 3
    max_retries: 3
  proposal_generation:
    priority: 2
    max_retries: 2
  application_submission:
    priority: 1
    max_retries: 1

logging:
  level: INFO
  file: /var/log/upwork-automation/worker.log
EOF
```

#### n8n Workflow Setup
```bash
# Import n8n workflows
docker-compose exec n8n n8n import:workflow --input=/data/workflows/

# Activate workflows
docker-compose exec n8n n8n update:workflow --id=1 --active=true
docker-compose exec n8n n8n update:workflow --id=2 --active=true
docker-compose exec n8n n8n update:workflow --id=3 --active=true
```

## User Management

### Creating Users

#### Admin User Creation
```bash
# Create admin user via API
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@company.com",
    "password": "secure_password",
    "is_admin": true
  }' \
  http://localhost:8000/api/auth/register
```

#### Regular User Creation
```bash
# Create regular user
curl -X POST -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator",
    "email": "operator@company.com",
    "password": "user_password",
    "is_admin": false
  }' \
  http://localhost:8000/api/users
```

### User Role Management

#### Role Definitions
```sql
-- Connect to database
docker-compose exec db psql -U user -d upwork_automation

-- Create roles table
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role_name VARCHAR(50) NOT NULL,
    permissions JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Define role permissions
INSERT INTO user_roles (user_id, role_name, permissions) VALUES
(1, 'admin', '{"system": ["read", "write", "delete"], "jobs": ["read", "write", "delete"], "applications": ["read", "write", "delete"]}'),
(2, 'operator', '{"system": ["read"], "jobs": ["read", "write"], "applications": ["read", "write"]}'),
(3, 'viewer', '{"system": ["read"], "jobs": ["read"], "applications": ["read"]}');
```

### Password Management

#### Password Reset
```bash
# Reset user password
docker-compose exec db psql -U user -d upwork_automation -c "
UPDATE users 
SET password_hash = crypt('new_password', gen_salt('bf')) 
WHERE username = 'username';
"
```

#### Password Policy Configuration
```bash
# Update API configuration for password policy
cat >> api/config/production.yaml << EOF
security:
  password_policy:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_special_chars: true
    max_age_days: 90
    history_count: 5
EOF
```

## Security Configuration

### SSL/TLS Configuration

#### Production SSL Setup
```bash
# Generate production SSL certificate
# Option 1: Let's Encrypt (recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Option 2: Self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/private.key -out ssl/certificate.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Update docker-compose.yml for SSL
```

#### SSL Configuration in Docker Compose
```yaml
# Add to docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - api-server
      - web-interface

  api-server:
    # Remove port exposure (handled by nginx)
    expose:
      - "8000"

  web-interface:
    expose:
      - "3000"
```

#### Nginx Configuration
```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api-server:8000;
    }
    
    upstream web {
        server web-interface:3000;
    }
    
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name your-domain.com;
        
        ssl_certificate /etc/ssl/certs/certificate.crt;
        ssl_certificate_key /etc/ssl/certs/private.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Firewall Configuration

#### UFW Setup (Ubuntu)
```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow specific IPs for admin access
sudo ufw allow from YOUR_ADMIN_IP to any port 22

# Deny all other incoming traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check status
sudo ufw status verbose
```

#### Docker Network Security
```yaml
# Add to docker-compose.yml
networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge

services:
  db:
    networks:
      - internal
  
  redis:
    networks:
      - internal
  
  api-server:
    networks:
      - internal
      - external
```

### API Security

#### Rate Limiting Configuration
```python
# Add to API configuration
RATE_LIMITING = {
    "default": "100/minute",
    "auth": "5/minute",
    "browser": "10/minute",
    "admin": "1000/minute"
}

# Implement in FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

#### API Key Management
```bash
# Generate API keys for external integrations
python -c "
import secrets
import base64

api_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
print(f'API_KEY={api_key}')
"

# Store in database
docker-compose exec db psql -U user -d upwork_automation -c "
INSERT INTO api_keys (key_hash, name, permissions, created_at) 
VALUES (
    crypt('your_api_key', gen_salt('bf')), 
    'External Integration', 
    '{\"read\": true, \"write\": false}',
    NOW()
);
"
```

## Backup and Recovery

### Automated Backup Setup

#### Database Backup Script
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/var/backups/upwork-automation"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/database_backup_$DATE.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose exec -T db pg_dump -U user upwork_automation > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "database_backup_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/database/

echo "Database backup completed: $BACKUP_FILE.gz"
```

#### Configuration Backup Script
```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/var/backups/upwork-automation"
DATE=$(date +%Y%m%d_%H%M%S)
CONFIG_BACKUP="$BACKUP_DIR/config_backup_$DATE.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration files
tar -czf $CONFIG_BACKUP \
  .env \
  docker-compose.yml \
  api/config/ \
  worker/config/ \
  n8n-workflows/ \
  ssl/

echo "Configuration backup completed: $CONFIG_BACKUP"
```

#### Automated Backup Cron Jobs
```bash
# Add to crontab
crontab -e

# Database backup every 6 hours
0 */6 * * * /path/to/backup_database.sh

# Configuration backup daily at 2 AM
0 2 * * * /path/to/backup_config.sh

# System health check every 5 minutes
*/5 * * * * /path/to/health_check.sh
```

### Recovery Procedures

#### Database Recovery
```bash
# Stop services
docker-compose stop api-server worker scheduler

# Restore database from backup
gunzip -c /var/backups/upwork-automation/database_backup_20241210_120000.sql.gz | \
  docker-compose exec -T db psql -U user upwork_automation

# Restart services
docker-compose start api-server worker scheduler

# Verify recovery
curl http://localhost:8000/api/system/status
```

#### Configuration Recovery
```bash
# Extract configuration backup
tar -xzf /var/backups/upwork-automation/config_backup_20241210_120000.tar.gz

# Restart services with restored configuration
docker-compose down
docker-compose up -d

# Verify configuration
docker-compose ps
```

#### Disaster Recovery Plan
```bash
#!/bin/bash
# disaster_recovery.sh

echo "Starting disaster recovery process..."

# 1. Stop all services
docker-compose down

# 2. Restore latest database backup
LATEST_DB_BACKUP=$(ls -t /var/backups/upwork-automation/database_backup_*.sql.gz | head -1)
echo "Restoring database from: $LATEST_DB_BACKUP"

# Recreate database
docker-compose up -d db
sleep 30
docker-compose exec db psql -U user -c "DROP DATABASE IF EXISTS upwork_automation;"
docker-compose exec db psql -U user -c "CREATE DATABASE upwork_automation;"
gunzip -c $LATEST_DB_BACKUP | docker-compose exec -T db psql -U user upwork_automation

# 3. Restore latest configuration
LATEST_CONFIG_BACKUP=$(ls -t /var/backups/upwork-automation/config_backup_*.tar.gz | head -1)
echo "Restoring configuration from: $LATEST_CONFIG_BACKUP"
tar -xzf $LATEST_CONFIG_BACKUP

# 4. Start all services
docker-compose up -d

# 5. Verify system health
sleep 60
curl http://localhost:8000/api/system/status

echo "Disaster recovery completed"
```

## Monitoring and Alerting

### System Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'upwork-automation-api'
    static_configs:
      - targets: ['api-server:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

#### Grafana Dashboard Setup
```json
{
  "dashboard": {
    "title": "Upwork Automation System",
    "panels": [
      {
        "title": "Job Discovery Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(jobs_discovered_total[5m])",
            "legendFormat": "Jobs/minute"
          }
        ]
      },
      {
        "title": "Application Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "applications_successful_total / applications_submitted_total * 100",
            "legendFormat": "Success Rate %"
          }
        ]
      },
      {
        "title": "System Health",
        "type": "table",
        "targets": [
          {
            "expr": "up",
            "legendFormat": "{{job}}"
          }
        ]
      }
    ]
  }
}
```

#### Custom Metrics Collection
```python
# Add to API server
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
jobs_discovered = Counter('jobs_discovered_total', 'Total jobs discovered')
applications_submitted = Counter('applications_submitted_total', 'Total applications submitted')
applications_successful = Counter('applications_successful_total', 'Successful applications')
browser_sessions_active = Gauge('browser_sessions_active', 'Active browser sessions')
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')

# Use in code
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    api_request_duration.observe(process_time)
    return response
```

### Alerting Configuration

#### Slack Alerting Setup
```python
# alerting.py
import requests
import json

class AlertManager:
    def __init__(self, slack_webhook_url):
        self.slack_webhook_url = slack_webhook_url
    
    def send_alert(self, severity, message, details=None):
        color_map = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }
        
        payload = {
            'attachments': [{
                'color': color_map.get(severity, 'warning'),
                'title': f'{severity.upper()}: Upwork Automation Alert',
                'text': message,
                'fields': [
                    {
                        'title': 'Timestamp',
                        'value': datetime.now().isoformat(),
                        'short': True
                    }
                ]
            }]
        }
        
        if details:
            payload['attachments'][0]['fields'].append({
                'title': 'Details',
                'value': json.dumps(details, indent=2),
                'short': False
            })
        
        requests.post(self.slack_webhook_url, json=payload)

# Usage
alert_manager = AlertManager(os.getenv('SLACK_WEBHOOK_URL'))
alert_manager.send_alert('critical', 'Database connection failed', {'error': str(e)})
```

#### Email Alerting Setup
```python
# email_alerts.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailAlerts:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_alert(self, to_emails, subject, message):
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()
```

### Log Management

#### Centralized Logging Setup
```yaml
# Add to docker-compose.yml
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

#### Log Rotation Configuration
```bash
# /etc/logrotate.d/upwork-automation
/var/log/upwork-automation/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 upwork-automation upwork-automation
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
```

## Performance Optimization

### Database Optimization

#### Index Optimization
```sql
-- Connect to database
docker-compose exec db psql -U user -d upwork_automation

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM jobs WHERE status = 'discovered' ORDER BY created_at DESC LIMIT 50;

-- Add performance indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_applications_submitted_at ON applications(submitted_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_proposals_job_id ON proposals(job_id);

-- Update table statistics
ANALYZE jobs;
ANALYZE applications;
ANALYZE proposals;
```

#### Database Maintenance
```bash
#!/bin/bash
# db_maintenance.sh

# Vacuum and analyze database
docker-compose exec db psql -U user -d upwork_automation -c "VACUUM ANALYZE;"

# Reindex database
docker-compose exec db psql -U user -d upwork_automation -c "REINDEX DATABASE upwork_automation;"

# Check database size
docker-compose exec db psql -U user -d upwork_automation -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Application Performance

#### Connection Pool Optimization
```python
# database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

#### Redis Optimization
```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### Browser Session Optimization
```python
# Optimize browser session management
BROWSER_CONFIG = {
    "session_pool_size": 5,
    "session_timeout": 1800,
    "max_concurrent_sessions": 3,
    "session_cleanup_interval": 300,
    "stealth_mode": True,
    "proxy_rotation": True
}
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Maintenance
```bash
#!/bin/bash
# daily_maintenance.sh

echo "Starting daily maintenance..."

# Check disk space
df -h

# Check service health
docker-compose ps

# Clean up old logs
find /var/log/upwork-automation -name "*.log" -mtime +7 -delete

# Clean up old browser sessions
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/browser/sessions/cleanup

# Database maintenance
docker-compose exec db psql -U user -d upwork_automation -c "
DELETE FROM jobs WHERE created_at < NOW() - INTERVAL '90 days' AND status IN ('rejected', 'applied');
VACUUM ANALYZE;
"

echo "Daily maintenance completed"
```

#### Weekly Maintenance
```bash
#!/bin/bash
# weekly_maintenance.sh

echo "Starting weekly maintenance..."

# Full database backup
/path/to/backup_database.sh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Docker cleanup
docker system prune -f
docker volume prune -f

# Check SSL certificate expiration
openssl x509 -in ssl/certificate.crt -noout -dates

# Performance analysis
docker-compose exec db psql -U user -d upwork_automation -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"

echo "Weekly maintenance completed"
```

#### Monthly Maintenance
```bash
#!/bin/bash
# monthly_maintenance.sh

echo "Starting monthly maintenance..."

# Full system backup
/path/to/backup_config.sh

# Security updates
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# Certificate renewal (if using Let's Encrypt)
sudo certbot renew

# Performance review
# Generate monthly performance report
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/metrics?period=30d" > monthly_report.json

# Database optimization
docker-compose exec db psql -U user -d upwork_automation -c "
REINDEX DATABASE upwork_automation;
VACUUM FULL;
ANALYZE;
"

echo "Monthly maintenance completed"
```

### Update Procedures

#### Application Updates
```bash
#!/bin/bash
# update_application.sh

echo "Starting application update..."

# Backup current state
/path/to/backup_database.sh
/path/to/backup_config.sh

# Pull latest code
git fetch origin
git checkout main
git pull origin main

# Update dependencies
docker-compose build --no-cache

# Run database migrations
docker-compose exec api-server alembic upgrade head

# Restart services
docker-compose down
docker-compose up -d

# Verify update
sleep 60
curl http://localhost:8000/api/system/status

echo "Application update completed"
```

#### Security Updates
```bash
#!/bin/bash
# security_updates.sh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Update SSL certificates
sudo certbot renew

# Rotate API keys (if needed)
# Generate new JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 32)
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_JWT_SECRET/" .env

# Restart services
docker-compose restart api-server

echo "Security updates completed"
```

This comprehensive system administration guide covers all aspects of managing the Upwork Automation System. Regular maintenance and monitoring are essential for optimal performance and security. For additional support or advanced configurations, refer to the vendor documentation for specific services or contact technical support.