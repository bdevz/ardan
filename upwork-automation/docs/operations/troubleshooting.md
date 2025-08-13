# Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for common issues in the Upwork Automation System. Issues are organized by category with step-by-step resolution procedures.

## Quick Diagnostic Commands

### System Health Check
```bash
# Check all services status
docker-compose ps

# Check system resources
docker stats --no-stream

# Check API health
curl http://localhost:8000/api/system/status

# Check web interface
curl http://localhost:3000

# Check database connectivity
docker-compose exec db pg_isready -U user -d upwork_automation
```

### Log Analysis
```bash
# View recent logs for all services
docker-compose logs --tail=50

# View specific service logs
docker-compose logs api-server
docker-compose logs worker
docker-compose logs web-interface

# Follow logs in real-time
docker-compose logs -f api-server

# Search for errors
docker-compose logs | grep -i error
docker-compose logs | grep -i exception
```

## Browser Automation Issues

### Browser Sessions Not Starting

**Symptoms**:
- "Failed to create browser session" errors
- Timeout errors when creating sessions
- Browser automation tasks stuck in queue

**Diagnostic Steps**:
```bash
# Check Browserbase connectivity
curl -H "Authorization: Bearer YOUR_BROWSERBASE_API_KEY" \
  https://www.browserbase.com/v1/sessions

# Check browser service logs
docker-compose logs api-server | grep -i browser

# Check environment variables
docker-compose exec api-server env | grep BROWSERBASE
```

**Common Causes and Solutions**:

1. **Invalid Browserbase API Key**
   ```bash
   # Verify API key in environment
   docker-compose exec api-server env | grep BROWSERBASE_API_KEY
   
   # Update API key if needed
   echo "BROWSERBASE_API_KEY=your_new_key" >> .env
   docker-compose restart api-server
   ```

2. **Browserbase Account Limits**
   - Check your Browserbase dashboard for usage limits
   - Upgrade plan if necessary
   - Reduce concurrent session pool size temporarily

3. **Network Connectivity Issues**
   ```bash
   # Test network connectivity
   docker-compose exec api-server ping browserbase.com
   
   # Check DNS resolution
   docker-compose exec api-server nslookup browserbase.com
   ```

4. **Session Pool Exhaustion**
   ```bash
   # Check active sessions
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/browser/sessions
   
   # Clean up stale sessions
   curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/browser/sessions/cleanup
   ```

### Stagehand Automation Failures

**Symptoms**:
- "Element not found" errors
- Timeout errors during page interactions
- Incorrect form filling or navigation

**Diagnostic Steps**:
```bash
# Check Stagehand service logs
docker-compose logs api-server | grep -i stagehand

# Check recent browser automation attempts
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/browser/sessions?status=error"
```

**Common Causes and Solutions**:

1. **Page Structure Changes**
   - Upwork may have updated their UI
   - Check browser session recordings in Browserbase dashboard
   - Update Stagehand selectors if needed

2. **Slow Page Loading**
   ```bash
   # Increase timeout settings
   # Update in system configuration
   curl -X PUT -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"browser_timeout": 30000}' \
     http://localhost:8000/api/system/config
   ```

3. **CAPTCHA Detection**
   - System should automatically pause when CAPTCHA detected
   - Check Slack notifications for CAPTCHA alerts
   - Manually solve CAPTCHA in Browserbase dashboard
   - Resume automation after solving

4. **Login Session Expired**
   ```bash
   # Trigger manual login
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"action": "login", "force": true}' \
     http://localhost:8000/api/browser/login
   ```

### Rate Limiting and Detection Issues

**Symptoms**:
- Applications being rejected immediately
- Unusual response patterns from Upwork
- Account warnings or restrictions

**Immediate Actions**:
1. **Emergency Stop**
   ```bash
   # Stop all automation immediately
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/system/emergency-stop
   ```

2. **Review Recent Activity**
   ```bash
   # Check recent applications
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/api/applications?limit=20&sort=submitted_at&order=desc"
   ```

3. **Adjust Rate Limits**
   ```bash
   # Reduce application frequency
   curl -X PUT -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"daily_application_limit": 5, "applications_per_hour": 1}' \
     http://localhost:8000/api/system/config
   ```

**Prevention Measures**:
- Enable extra safety mode
- Increase delays between applications
- Use more human-like behavior patterns
- Monitor success rates closely

## Database Issues

### Database Connection Failures

**Symptoms**:
- "Database connection failed" errors
- API endpoints returning 500 errors
- Data not saving or loading

**Diagnostic Steps**:
```bash
# Check database container status
docker-compose ps db

# Check database logs
docker-compose logs db

# Test database connectivity
docker-compose exec db pg_isready -U user -d upwork_automation

# Check database connections
docker-compose exec db psql -U user -d upwork_automation -c "SELECT count(*) FROM pg_stat_activity;"
```

**Common Solutions**:

1. **Database Container Not Running**
   ```bash
   # Start database container
   docker-compose up -d db
   
   # Wait for database to be ready
   sleep 30
   
   # Restart dependent services
   docker-compose restart api-server worker
   ```

2. **Connection Pool Exhaustion**
   ```bash
   # Check active connections
   docker-compose exec db psql -U user -d upwork_automation -c \
     "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
   
   # Restart API server to reset connection pool
   docker-compose restart api-server
   ```

3. **Database Corruption**
   ```bash
   # Check database integrity
   docker-compose exec db psql -U user -d upwork_automation -c \
     "SELECT pg_database_size('upwork_automation');"
   
   # If corruption detected, restore from backup
   # See backup restoration procedures below
   ```

### Database Performance Issues

**Symptoms**:
- Slow API responses
- High database CPU usage
- Query timeouts

**Diagnostic Steps**:
```bash
# Check database performance
docker-compose exec db psql -U user -d upwork_automation -c \
  "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check database size
docker-compose exec db psql -U user -d upwork_automation -c \
  "SELECT pg_size_pretty(pg_database_size('upwork_automation'));"

# Check table sizes
docker-compose exec db psql -U user -d upwork_automation -c \
  "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

**Solutions**:

1. **Add Database Indexes**
   ```sql
   -- Connect to database
   docker-compose exec db psql -U user -d upwork_automation
   
   -- Add indexes for common queries
   CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
   CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
   CREATE INDEX IF NOT EXISTS idx_applications_submitted_at ON applications(submitted_at);
   ```

2. **Clean Old Data**
   ```sql
   -- Remove old job records (older than 90 days)
   DELETE FROM jobs WHERE created_at < NOW() - INTERVAL '90 days' AND status IN ('rejected', 'applied');
   
   -- Vacuum database
   VACUUM ANALYZE;
   ```

3. **Increase Database Resources**
   ```yaml
   # In docker-compose.yml, update database service
   db:
     image: postgres:15
     environment:
       - POSTGRES_SHARED_PRELOAD_LIBRARIES=pg_stat_statements
     command: >
       postgres
       -c shared_buffers=256MB
       -c effective_cache_size=1GB
       -c maintenance_work_mem=64MB
   ```

## API and Web Interface Issues

### API Server Not Responding

**Symptoms**:
- Web interface shows connection errors
- API endpoints return timeouts
- 502 Bad Gateway errors

**Diagnostic Steps**:
```bash
# Check API server status
docker-compose ps api-server

# Check API server logs
docker-compose logs api-server

# Test API directly
curl -v http://localhost:8000/api/system/status

# Check port binding
netstat -tlnp | grep 8000
```

**Solutions**:

1. **Restart API Server**
   ```bash
   docker-compose restart api-server
   
   # Wait for startup
   sleep 30
   
   # Verify it's responding
   curl http://localhost:8000/api/system/status
   ```

2. **Check Resource Usage**
   ```bash
   # Check memory usage
   docker stats api-server --no-stream
   
   # If high memory usage, restart with more memory
   # Update docker-compose.yml:
   # api-server:
   #   deploy:
   #     resources:
   #       limits:
   #         memory: 2G
   ```

3. **Port Conflicts**
   ```bash
   # Check if port 8000 is in use
   lsof -i :8000
   
   # If conflict, change port in docker-compose.yml
   # ports: ["8001:8000"]
   ```

### Web Interface Loading Issues

**Symptoms**:
- Blank page or loading spinner
- JavaScript errors in browser console
- 404 errors for static assets

**Diagnostic Steps**:
```bash
# Check web interface container
docker-compose ps web-interface

# Check web interface logs
docker-compose logs web-interface

# Test web server directly
curl -v http://localhost:3000

# Check browser console for errors
# Open browser developer tools (F12)
```

**Solutions**:

1. **Clear Browser Cache**
   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   - Clear browser cache and cookies
   - Try incognito/private browsing mode

2. **Restart Web Interface**
   ```bash
   docker-compose restart web-interface
   
   # Check if it's building correctly
   docker-compose logs web-interface
   ```

3. **Rebuild Web Interface**
   ```bash
   # Rebuild the web interface container
   docker-compose build web-interface
   docker-compose up -d web-interface
   ```

### Authentication Issues

**Symptoms**:
- Login failures with correct credentials
- "Unauthorized" errors after login
- JWT token errors

**Diagnostic Steps**:
```bash
# Check authentication configuration
docker-compose exec api-server env | grep JWT

# Test login endpoint
curl -X POST -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}' \
  http://localhost:8000/api/auth/login

# Check user database
docker-compose exec db psql -U user -d upwork_automation -c \
  "SELECT username, created_at FROM users;"
```

**Solutions**:

1. **Reset JWT Secret**
   ```bash
   # Generate new JWT secret
   echo "JWT_SECRET=$(openssl rand -base64 32)" >> .env
   docker-compose restart api-server
   ```

2. **Reset User Password**
   ```bash
   # Connect to database and reset password
   docker-compose exec db psql -U user -d upwork_automation -c \
     "UPDATE users SET password_hash = crypt('new_password', gen_salt('bf')) WHERE username = 'admin';"
   ```

3. **Check Token Expiration**
   ```bash
   # Increase token expiration time
   echo "JWT_EXPIRATION_HOURS=24" >> .env
   docker-compose restart api-server
   ```

## External Service Integration Issues

### Google Services Integration

**Symptoms**:
- "Google API authentication failed" errors
- Proposals not saving to Google Docs
- Attachment selection failures

**Diagnostic Steps**:
```bash
# Check Google credentials
docker-compose exec api-server env | grep GOOGLE

# Test Google API connectivity
curl -H "Authorization: Bearer YOUR_GOOGLE_TOKEN" \
  "https://www.googleapis.com/drive/v3/about?fields=user"

# Check Google service logs
docker-compose logs api-server | grep -i google
```

**Solutions**:

1. **Refresh Google Credentials**
   ```bash
   # Update Google service account key
   # Download new key from Google Cloud Console
   # Update GOOGLE_SERVICE_ACCOUNT_KEY in .env
   docker-compose restart api-server
   ```

2. **Check API Quotas**
   - Visit Google Cloud Console
   - Check API usage and quotas
   - Enable required APIs if disabled
   - Increase quotas if necessary

3. **Test Google Integration**
   ```bash
   # Test Google Docs creation
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Test Document", "content": "Test content"}' \
     http://localhost:8000/api/google/docs/create
   ```

### Slack Integration Issues

**Symptoms**:
- Slack notifications not being sent
- "Slack API error" messages
- Missing or delayed alerts

**Diagnostic Steps**:
```bash
# Check Slack configuration
docker-compose exec api-server env | grep SLACK

# Test Slack API
curl -X POST -H "Authorization: Bearer YOUR_SLACK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "#test", "text": "Test message"}' \
  https://slack.com/api/chat.postMessage

# Check Slack service logs
docker-compose logs api-server | grep -i slack
```

**Solutions**:

1. **Update Slack Token**
   ```bash
   # Get new token from Slack App settings
   echo "SLACK_BOT_TOKEN=xoxb-your-new-token" >> .env
   docker-compose restart api-server
   ```

2. **Check Bot Permissions**
   - Verify bot has required scopes: `chat:write`, `files:write`
   - Ensure bot is added to notification channels
   - Check workspace permissions

3. **Test Slack Integration**
   ```bash
   # Send test notification
   curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "Test notification", "channel": "#upwork-automation"}' \
     http://localhost:8000/api/notifications/slack
   ```

### n8n Workflow Issues

**Symptoms**:
- Workflows not triggering
- "n8n connection failed" errors
- Incomplete workflow execution

**Diagnostic Steps**:
```bash
# Check n8n service status
docker-compose ps n8n

# Check n8n logs
docker-compose logs n8n

# Test n8n API
curl http://localhost:5678/rest/workflows

# Check webhook endpoints
curl http://localhost:5678/webhook-test/job-discovery
```

**Solutions**:

1. **Restart n8n Service**
   ```bash
   docker-compose restart n8n
   
   # Wait for startup
   sleep 30
   
   # Check if workflows are active
   curl http://localhost:5678/rest/workflows
   ```

2. **Re-import Workflows**
   ```bash
   # Access n8n interface
   # Navigate to http://localhost:5678
   # Import workflow files from n8n-workflows/ directory
   ```

3. **Check Webhook Configuration**
   ```bash
   # Verify webhook URLs in system configuration
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/system/config | grep webhook
   ```

## Performance Issues

### High CPU Usage

**Symptoms**:
- System becomes slow or unresponsive
- High CPU usage in Docker stats
- Browser automation timeouts

**Diagnostic Steps**:
```bash
# Check CPU usage by container
docker stats --no-stream

# Check system load
top
htop

# Check browser session count
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/browser/sessions | jq '.sessions | length'
```

**Solutions**:

1. **Reduce Browser Session Pool**
   ```bash
   # Reduce concurrent sessions
   curl -X PUT -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"browser_session_pool_size": 2}' \
     http://localhost:8000/api/system/config
   ```

2. **Optimize Database Queries**
   ```sql
   -- Add missing indexes
   docker-compose exec db psql -U user -d upwork_automation -c \
     "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);"
   ```

3. **Increase System Resources**
   ```yaml
   # Update docker-compose.yml
   services:
     api-server:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 2G
   ```

### High Memory Usage

**Symptoms**:
- Out of memory errors
- Container restarts
- Slow performance

**Diagnostic Steps**:
```bash
# Check memory usage
docker stats --no-stream

# Check memory usage by process
docker-compose exec api-server ps aux --sort=-%mem

# Check for memory leaks
docker-compose logs api-server | grep -i "memory\|oom"
```

**Solutions**:

1. **Restart High Memory Services**
   ```bash
   # Restart API server
   docker-compose restart api-server
   
   # Restart worker processes
   docker-compose restart worker
   ```

2. **Increase Memory Limits**
   ```yaml
   # Update docker-compose.yml
   services:
     api-server:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

3. **Optimize Data Processing**
   ```bash
   # Reduce batch sizes
   curl -X PUT -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"job_discovery_batch_size": 10}' \
     http://localhost:8000/api/system/config
   ```

## Data Recovery Procedures

### Database Backup and Restore

**Create Backup**:
```bash
# Create full database backup
docker-compose exec db pg_dump -U user upwork_automation > backup_$(date +%Y%m%d_%H%M%S).sql

# Create compressed backup
docker-compose exec db pg_dump -U user upwork_automation | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Restore from Backup**:
```bash
# Stop services that use database
docker-compose stop api-server worker scheduler

# Drop and recreate database
docker-compose exec db psql -U user -c "DROP DATABASE IF EXISTS upwork_automation;"
docker-compose exec db psql -U user -c "CREATE DATABASE upwork_automation;"

# Restore from backup
docker-compose exec -T db psql -U user upwork_automation < backup_20241210_120000.sql

# Or restore from compressed backup
gunzip -c backup_20241210_120000.sql.gz | docker-compose exec -T db psql -U user upwork_automation

# Restart services
docker-compose start api-server worker scheduler
```

### Configuration Recovery

**Backup Configuration**:
```bash
# Backup environment files
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Backup system configuration from database
docker-compose exec db psql -U user -d upwork_automation -c \
  "COPY (SELECT * FROM system_config) TO STDOUT WITH CSV HEADER;" > system_config_backup.csv
```

**Restore Configuration**:
```bash
# Restore environment file
cp .env.backup.20241210_120000 .env

# Restore system configuration
docker-compose exec -T db psql -U user -d upwork_automation -c \
  "TRUNCATE system_config; COPY system_config FROM STDIN WITH CSV HEADER;" < system_config_backup.csv

# Restart services
docker-compose restart
```

## Monitoring and Alerting

### Set Up Monitoring

**Health Check Script**:
```bash
#!/bin/bash
# health_check.sh

# Check all services
services=("db" "redis" "api-server" "web-interface" "worker")
for service in "${services[@]}"; do
    if ! docker-compose ps $service | grep -q "Up"; then
        echo "ALERT: $service is not running"
        # Send alert notification
        curl -X POST -H "Content-Type: application/json" \
          -d "{\"text\": \"ALERT: $service is not running\"}" \
          YOUR_SLACK_WEBHOOK_URL
    fi
done

# Check API health
if ! curl -f http://localhost:8000/api/system/status > /dev/null 2>&1; then
    echo "ALERT: API server is not responding"
fi

# Check database connectivity
if ! docker-compose exec db pg_isready -U user -d upwork_automation > /dev/null 2>&1; then
    echo "ALERT: Database is not accessible"
fi
```

**Set Up Cron Job**:
```bash
# Add to crontab (run every 5 minutes)
*/5 * * * * /path/to/health_check.sh
```

### Log Monitoring

**Set Up Log Rotation**:
```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/upwork-automation << EOF
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        docker kill --signal=USR1 \$(docker ps -q) 2>/dev/null || true
    endscript
}
EOF
```

**Monitor Error Logs**:
```bash
# Set up error monitoring script
#!/bin/bash
# error_monitor.sh

# Check for errors in logs
errors=$(docker-compose logs --since=5m | grep -i "error\|exception\|failed" | wc -l)

if [ $errors -gt 10 ]; then
    echo "ALERT: High error rate detected ($errors errors in last 5 minutes)"
    # Send detailed error report
    docker-compose logs --since=5m | grep -i "error\|exception\|failed" | tail -20
fi
```

## Emergency Contacts and Escalation

### Escalation Procedures

**Level 1: Automated Recovery**
- System attempts automatic recovery
- Restarts failed services
- Sends initial alerts

**Level 2: Manual Intervention**
- System administrator notified
- Manual troubleshooting required
- Follow procedures in this guide

**Level 3: Emergency Response**
- Critical system failure
- Business impact assessment
- Emergency stop procedures
- Vendor support engagement

### Contact Information

**System Administrator**: [Your contact info]
**Browserbase Support**: support@browserbase.com
**Google Cloud Support**: [Your support case URL]
**Slack Workspace Admin**: [Admin contact]

### Emergency Procedures

**Complete System Failure**:
1. Execute emergency stop
2. Assess data integrity
3. Restore from latest backup
4. Gradually restart services
5. Monitor for stability
6. Document incident

**Data Loss Event**:
1. Stop all write operations
2. Assess extent of data loss
3. Restore from backup
4. Verify data integrity
5. Resume operations
6. Implement prevention measures

This troubleshooting guide covers the most common issues you may encounter. For issues not covered here, check the system logs, contact support, or refer to the vendor documentation for specific services.