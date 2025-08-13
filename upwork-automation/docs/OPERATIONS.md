# Operations Manual

This manual provides detailed operational procedures for managing the Upwork Automation System in production.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [System Monitoring](#system-monitoring)
3. [Incident Response](#incident-response)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Performance Optimization](#performance-optimization)
6. [Security Operations](#security-operations)
7. [Backup Operations](#backup-operations)
8. [Troubleshooting Guide](#troubleshooting-guide)

## Daily Operations

### Morning Checklist

1. **System Health Check**
   ```bash
   ./scripts/health_check.sh
   ```

2. **Review Overnight Logs**
   ```bash
   # Check for errors
   grep -i error logs/api/$(date +%Y-%m-%d)*.log
   grep -i error logs/worker/$(date +%Y-%m-%d)*.log
   
   # Check application metrics
   curl -s http://localhost:8000/health/metrics | jq
   ```

3. **Verify Backup Completion**
   ```bash
   # Check latest backup
   ls -la backups/postgres/ | head -5
   ls -la backups/redis/ | head -5
   
   # Verify backup integrity
   latest_backup=$(ls -t backups/postgres/postgres_backup_*.sql.gz | head -1)
   gzip -t "$latest_backup" && echo "Backup integrity: OK"
   ```

4. **Check Queue Status**
   ```bash
   curl -s http://localhost:8000/api/queue/status | jq
   ```

5. **Review Application Performance**
   ```bash
   # Check success rates
   curl -s http://localhost:8000/api/metrics/daily | jq '.success_rate'
   
   # Check application volume
   curl -s http://localhost:8000/api/metrics/daily | jq '.applications_submitted'
   ```

### Evening Checklist

1. **Review Daily Metrics**
   ```bash
   # Generate daily report
   curl -s http://localhost:8000/api/reports/daily | jq
   ```

2. **Check Resource Usage**
   ```bash
   # System resources
   docker stats --no-stream
   
   # Disk usage
   df -h
   ```

3. **Verify Scheduled Tasks**
   ```bash
   # Check cron jobs
   crontab -l
   
   # Check scheduler status
   curl -s http://localhost:8000/api/scheduler/status | jq
   ```

## System Monitoring

### Key Metrics to Monitor

#### Application Metrics
- **Job Discovery Rate**: Jobs discovered per hour
- **Application Success Rate**: Successful applications / total attempts
- **Proposal Generation Time**: Average time to generate proposals
- **Browser Session Health**: Active sessions and success rates
- **Queue Processing Rate**: Tasks processed per minute

#### System Metrics
- **CPU Usage**: Should stay below 80%
- **Memory Usage**: Should stay below 80%
- **Disk Usage**: Should stay below 90%
- **Network I/O**: Monitor for unusual spikes
- **Database Connections**: Monitor pool utilization

#### Error Metrics
- **API Error Rate**: Should stay below 5%
- **Browser Automation Failures**: Monitor CAPTCHA and timeout rates
- **External Service Failures**: Track API failures for Browserbase, OpenAI, etc.

### Monitoring Commands

```bash
# Real-time system monitoring
watch -n 5 './scripts/health_check.sh'

# Application metrics
curl -s http://localhost:8000/health/metrics | jq '{
  cpu_usage: .cpu_usage,
  memory_usage: .memory_usage,
  queue_size: .queue_size,
  error_rate: .error_rate
}'

# Database performance
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT 
  schemaname,
  tablename,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes
FROM pg_stat_user_tables 
ORDER BY n_tup_ins DESC;
"

# Redis performance
docker-compose exec redis redis-cli info stats
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | 70% | 85% |
| Memory Usage | 75% | 90% |
| Disk Usage | 80% | 95% |
| Error Rate | 3% | 10% |
| Queue Size | 50 tasks | 100 tasks |
| Response Time | 2 seconds | 5 seconds |

## Incident Response

### Severity Levels

#### Critical (P1)
- System completely down
- Data loss or corruption
- Security breach
- All applications failing

**Response Time**: Immediate (< 15 minutes)

#### High (P2)
- Significant feature degradation
- High error rates (>10%)
- Performance severely impacted
- External service failures

**Response Time**: 1 hour

#### Medium (P3)
- Minor feature issues
- Moderate performance impact
- Non-critical errors

**Response Time**: 4 hours

#### Low (P4)
- Cosmetic issues
- Documentation problems
- Enhancement requests

**Response Time**: Next business day

### Incident Response Procedures

#### 1. Initial Response

```bash
# Immediate assessment
./scripts/health_check.sh

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check recent logs
tail -100 logs/api/$(date +%Y-%m-%d)*.log
tail -100 logs/worker/$(date +%Y-%m-%d)*.log
```

#### 2. Communication

```bash
# Send alert to team (if Slack configured)
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 INCIDENT: [Brief description] - Investigating"}' \
  $SLACK_WEBHOOK_URL
```

#### 3. Investigation

```bash
# Collect system information
echo "=== INCIDENT REPORT ===" > incident_$(date +%Y%m%d_%H%M%S).log
date >> incident_$(date +%Y%m%d_%H%M%S).log
./scripts/health_check.sh >> incident_$(date +%Y%m%d_%H%M%S).log
docker-compose -f docker-compose.prod.yml logs --tail=500 >> incident_$(date +%Y%m%d_%H%M%S).log
```

#### 4. Resolution

Common resolution steps:

```bash
# Restart specific service
docker-compose -f docker-compose.prod.yml restart api-server

# Full system restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Restore from backup (if data corruption)
./scripts/restore.sh -t LATEST_BACKUP_TIMESTAMP
```

#### 5. Post-Incident

```bash
# Verify resolution
./scripts/health_check.sh

# Update team
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"✅ RESOLVED: [Brief description] - System restored"}' \
  $SLACK_WEBHOOK_URL
```

## Maintenance Procedures

### Scheduled Maintenance Windows

**Weekly Maintenance**: Sundays 2:00 AM - 4:00 AM UTC
- System updates
- Database maintenance
- Log rotation
- Performance optimization

**Monthly Maintenance**: First Sunday of month 1:00 AM - 5:00 AM UTC
- Major updates
- Security patches
- Capacity planning
- Full system backup verification

### Pre-Maintenance Checklist

```bash
# 1. Create maintenance backup
./scripts/backup.sh

# 2. Notify users (if applicable)
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🔧 MAINTENANCE: System maintenance starting in 30 minutes"}' \
  $SLACK_WEBHOOK_URL

# 3. Stop non-critical services
docker-compose -f docker-compose.prod.yml stop worker scheduler

# 4. Enable maintenance mode (if implemented)
curl -X POST http://localhost:8000/api/system/maintenance -d '{"enabled": true}'
```

### Database Maintenance

```bash
# Vacuum and analyze database
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
VACUUM ANALYZE;
REINDEX DATABASE upwork_automation_prod;
"

# Update table statistics
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
ANALYZE;
"

# Check for unused indexes
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY n_distinct DESC;
"
```

### Log Rotation

```bash
# Rotate application logs
find logs/ -name "*.log" -size +100M -exec gzip {} \;
find logs/ -name "*.log.gz" -mtime +30 -delete

# Rotate Docker logs
docker system prune -f
```

### Post-Maintenance Checklist

```bash
# 1. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 2. Verify system health
./scripts/health_check.sh

# 3. Disable maintenance mode
curl -X POST http://localhost:8000/api/system/maintenance -d '{"enabled": false}'

# 4. Notify completion
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"✅ MAINTENANCE COMPLETE: All systems operational"}' \
  $SLACK_WEBHOOK_URL
```

## Performance Optimization

### Database Optimization

#### Query Performance

```sql
-- Find slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements 
WHERE mean_time > 1000  -- queries taking more than 1 second
ORDER BY mean_time DESC 
LIMIT 10;

-- Find most frequent queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements 
ORDER BY calls DESC 
LIMIT 10;
```

#### Index Optimization

```sql
-- Find unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 
AND schemaname = 'public';

-- Find missing indexes
SELECT schemaname, tablename, seq_scan, seq_tup_read, 
       seq_tup_read / seq_scan as avg_tup_read
FROM pg_stat_user_tables 
WHERE seq_scan > 0 
ORDER BY seq_tup_read DESC;
```

### Application Performance

#### Connection Pool Tuning

```bash
# Monitor connection usage
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT state, count(*) 
FROM pg_stat_activity 
GROUP BY state;
"

# Adjust pool settings in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
```

#### Redis Performance

```bash
# Monitor Redis performance
docker-compose exec redis redis-cli info stats

# Check memory usage
docker-compose exec redis redis-cli info memory

# Monitor slow queries
docker-compose exec redis redis-cli slowlog get 10
```

### Browser Automation Optimization

```bash
# Monitor session performance
curl -s http://localhost:8000/api/browser/sessions/metrics | jq

# Optimize session pool
# In .env:
MAX_BROWSER_SESSIONS=5
BROWSER_SESSION_TIMEOUT=3600
```

## Security Operations

### Daily Security Checks

```bash
# Check for failed authentication attempts
grep -i "authentication.*failed" logs/api/*.log | wc -l

# Check for suspicious IP addresses
grep -E "rate.limit|blocked" logs/api/*.log | cut -d' ' -f5 | sort | uniq -c | sort -nr

# Check SSL certificate expiration
openssl x509 -in credentials/ssl-cert.pem -noout -dates
```

### Security Monitoring

```bash
# Monitor API access patterns
awk '{print $1}' logs/api/access.log | sort | uniq -c | sort -nr | head -20

# Check for unusual user agents
grep "user-agent" logs/api/*.log | cut -d'"' -f6 | sort | uniq -c | sort -nr

# Monitor error patterns
grep -E "40[0-9]|50[0-9]" logs/api/*.log | cut -d' ' -f9 | sort | uniq -c
```

### Security Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Rotate secrets (monthly)
# Generate new JWT secret
openssl rand -base64 64

# Generate new encryption key
openssl rand -base64 32
```

## Backup Operations

### Backup Verification

```bash
# Daily backup verification
latest_postgres_backup=$(ls -t backups/postgres/postgres_backup_*.sql.gz | head -1)
latest_redis_backup=$(ls -t backups/redis/redis_backup_*.rdb.gz | head -1)

# Test backup integrity
gzip -t "$latest_postgres_backup" && echo "PostgreSQL backup: OK"
gzip -t "$latest_redis_backup" && echo "Redis backup: OK"

# Test restore (on test environment)
./scripts/restore.sh -t $(basename "$latest_postgres_backup" .sql.gz | cut -d'_' -f3-)
```

### Backup Monitoring

```bash
# Check backup sizes
du -sh backups/*/

# Check backup frequency
find backups/postgres/ -name "*.gz" -mtime -7 | wc -l  # Should be 7 for daily backups

# Monitor backup storage usage
df -h /backups
```

### Disaster Recovery Testing

Monthly disaster recovery test:

```bash
# 1. Create test environment
cp docker-compose.prod.yml docker-compose.test.yml
# Edit ports to avoid conflicts

# 2. Deploy test environment
docker-compose -f docker-compose.test.yml up -d

# 3. Restore from backup
./scripts/restore.sh -t LATEST_BACKUP_TIMESTAMP

# 4. Verify functionality
curl http://localhost:8001/health  # Assuming different port

# 5. Cleanup
docker-compose -f docker-compose.test.yml down
```

## Troubleshooting Guide

### Common Issues and Solutions

#### High CPU Usage

```bash
# Identify CPU-intensive processes
docker stats --no-stream

# Check for runaway queries
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

# Solution: Kill long-running queries
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes';
"
```

#### Memory Issues

```bash
# Check memory usage by container
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check for memory leaks
grep -i "memory\|oom" /var/log/syslog

# Solution: Restart memory-intensive services
docker-compose -f docker-compose.prod.yml restart worker
```

#### Database Connection Issues

```bash
# Check connection count
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT count(*) FROM pg_stat_activity;
"

# Check for blocking queries
docker-compose exec db psql -U upwork_user -d upwork_automation_prod -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

#### Browser Automation Issues

```bash
# Check Browserbase connectivity
curl -H "Authorization: Bearer $BROWSERBASE_API_KEY" \
     https://api.browserbase.com/v1/sessions

# Check session status
curl -s http://localhost:8000/api/browser/sessions/status | jq

# Solution: Reset session pool
curl -X POST http://localhost:8000/api/browser/sessions/reset
```

### Emergency Procedures

#### Complete System Failure

```bash
# 1. Stop all services
docker-compose -f docker-compose.prod.yml down

# 2. Check system resources
df -h
free -h
docker system df

# 3. Clean up if needed
docker system prune -f

# 4. Restore from backup
./scripts/restore.sh -t LATEST_BACKUP_TIMESTAMP

# 5. Start services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify
./scripts/health_check.sh
```

#### Data Corruption

```bash
# 1. Stop services immediately
docker-compose -f docker-compose.prod.yml stop api-server worker scheduler

# 2. Backup current state (even if corrupted)
./scripts/backup.sh

# 3. Restore from last known good backup
./scripts/restore.sh -t LAST_KNOWN_GOOD_TIMESTAMP

# 4. Restart services
docker-compose -f docker-compose.prod.yml start api-server worker scheduler
```

For additional operational support, refer to the deployment documentation or contact the development team.