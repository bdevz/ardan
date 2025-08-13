#!/bin/bash

# Upwork Automation System Backup Script
# This script creates backups of PostgreSQL database, Redis data, and session data

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Database configuration
POSTGRES_HOST=${POSTGRES_HOST:-"db"}
POSTGRES_PORT=${POSTGRES_PORT:-"5432"}
POSTGRES_DB=${POSTGRES_DB:-"upwork_automation_prod"}
POSTGRES_USER=${POSTGRES_USER:-"upwork_user"}

# Redis configuration
REDIS_HOST=${REDIS_HOST:-"redis"}
REDIS_PORT=${REDIS_PORT:-"6379"}

# Logging
LOG_FILE="$BACKUP_DIR/backup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create backup directories
mkdir -p "$BACKUP_DIR/postgres"
mkdir -p "$BACKUP_DIR/redis"
mkdir -p "$BACKUP_DIR/sessions"

log "Starting backup process..."

# 1. PostgreSQL Database Backup
log "Backing up PostgreSQL database..."
POSTGRES_BACKUP_FILE="$BACKUP_DIR/postgres/postgres_backup_$TIMESTAMP.sql"

if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
   --no-password --verbose --clean --if-exists --create > "$POSTGRES_BACKUP_FILE" 2>>"$LOG_FILE"; then
    
    # Compress the backup
    gzip "$POSTGRES_BACKUP_FILE"
    log "PostgreSQL backup completed: ${POSTGRES_BACKUP_FILE}.gz"
else
    log "ERROR: PostgreSQL backup failed"
    exit 1
fi

# 2. Redis Data Backup
log "Backing up Redis data..."
REDIS_BACKUP_FILE="$BACKUP_DIR/redis/redis_backup_$TIMESTAMP.rdb"

if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb "$REDIS_BACKUP_FILE" 2>>"$LOG_FILE"; then
    # Compress the backup
    gzip "$REDIS_BACKUP_FILE"
    log "Redis backup completed: ${REDIS_BACKUP_FILE}.gz"
else
    log "ERROR: Redis backup failed"
    exit 1
fi

# 3. Session Data Backup (if exists)
SESSION_DATA_DIR="/app/sessions"
if [ -d "$SESSION_DATA_DIR" ]; then
    log "Backing up session data..."
    SESSION_BACKUP_FILE="$BACKUP_DIR/sessions/sessions_backup_$TIMESTAMP.tar.gz"
    
    if tar -czf "$SESSION_BACKUP_FILE" -C "$SESSION_DATA_DIR" . 2>>"$LOG_FILE"; then
        log "Session data backup completed: $SESSION_BACKUP_FILE"
    else
        log "WARNING: Session data backup failed"
    fi
fi

# 4. Configuration Backup
log "Backing up configuration files..."
CONFIG_BACKUP_FILE="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"

if tar -czf "$CONFIG_BACKUP_FILE" \
   --exclude="*.log" \
   --exclude="node_modules" \
   --exclude=".git" \
   --exclude="__pycache__" \
   /app/.env* /app/docker-compose*.yml /app/monitoring/ 2>>"$LOG_FILE"; then
    log "Configuration backup completed: $CONFIG_BACKUP_FILE"
else
    log "WARNING: Configuration backup failed"
fi

# 5. Cleanup old backups
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."

find "$BACKUP_DIR/postgres" -name "postgres_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE" || true
find "$BACKUP_DIR/redis" -name "redis_backup_*.rdb.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE" || true
find "$BACKUP_DIR/sessions" -name "sessions_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE" || true
find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE" || true

log "Old backup cleanup completed"

# 6. Backup verification
log "Verifying backups..."

# Verify PostgreSQL backup
if [ -f "${POSTGRES_BACKUP_FILE}.gz" ]; then
    if gzip -t "${POSTGRES_BACKUP_FILE}.gz" 2>>"$LOG_FILE"; then
        log "PostgreSQL backup verification: PASSED"
    else
        log "ERROR: PostgreSQL backup verification: FAILED"
        exit 1
    fi
fi

# Verify Redis backup
if [ -f "${REDIS_BACKUP_FILE}.gz" ]; then
    if gzip -t "${REDIS_BACKUP_FILE}.gz" 2>>"$LOG_FILE"; then
        log "Redis backup verification: PASSED"
    else
        log "ERROR: Redis backup verification: FAILED"
        exit 1
    fi
fi

# 7. Send notification (if Slack webhook is configured)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    curl -X POST -H 'Content-type: application/json' \
         --data "{\"text\":\"✅ Backup completed successfully\n📊 Total backup size: $BACKUP_SIZE\n🕐 Timestamp: $TIMESTAMP\"}" \
         "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || log "WARNING: Failed to send Slack notification"
fi

log "Backup process completed successfully"

# Output backup summary
echo "=== BACKUP SUMMARY ==="
echo "Timestamp: $TIMESTAMP"
echo "PostgreSQL backup: ${POSTGRES_BACKUP_FILE}.gz"
echo "Redis backup: ${REDIS_BACKUP_FILE}.gz"
echo "Session backup: $SESSION_BACKUP_FILE"
echo "Config backup: $CONFIG_BACKUP_FILE"
echo "Total backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo "======================="