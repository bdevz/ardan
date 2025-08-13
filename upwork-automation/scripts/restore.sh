#!/bin/bash

# Upwork Automation System Restore Script
# This script restores backups of PostgreSQL database, Redis data, and session data

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/backups"
LOG_FILE="$BACKUP_DIR/restore.log"

# Database configuration
POSTGRES_HOST=${POSTGRES_HOST:-"db"}
POSTGRES_PORT=${POSTGRES_PORT:-"5432"}
POSTGRES_DB=${POSTGRES_DB:-"upwork_automation_prod"}
POSTGRES_USER=${POSTGRES_USER:-"upwork_user"}

# Redis configuration
REDIS_HOST=${REDIS_HOST:-"redis"}
REDIS_PORT=${REDIS_PORT:-"6379"}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t TIMESTAMP    Restore from specific timestamp (format: YYYYMMDD_HHMMSS)"
    echo "  -l              List available backups"
    echo "  -p              Restore PostgreSQL only"
    echo "  -r              Restore Redis only"
    echo "  -s              Restore sessions only"
    echo "  -c              Restore configuration only"
    echo "  -h              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -t 20240101_120000    # Restore from specific timestamp"
    echo "  $0 -l                    # List available backups"
    echo "  $0 -p -t 20240101_120000 # Restore only PostgreSQL from timestamp"
}

list_backups() {
    echo "=== AVAILABLE BACKUPS ==="
    echo ""
    echo "PostgreSQL backups:"
    ls -la "$BACKUP_DIR/postgres/" | grep "postgres_backup_" | sort -r
    echo ""
    echo "Redis backups:"
    ls -la "$BACKUP_DIR/redis/" | grep "redis_backup_" | sort -r
    echo ""
    echo "Session backups:"
    ls -la "$BACKUP_DIR/sessions/" | grep "sessions_backup_" | sort -r
    echo ""
    echo "Configuration backups:"
    ls -la "$BACKUP_DIR/" | grep "config_backup_" | sort -r
    echo "========================="
}

restore_postgres() {
    local timestamp=$1
    local backup_file="$BACKUP_DIR/postgres/postgres_backup_${timestamp}.sql.gz"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: PostgreSQL backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring PostgreSQL database from $backup_file..."
    
    # Stop API server to prevent connections during restore
    log "Stopping API server..."
    docker-compose stop api-server worker scheduler 2>>"$LOG_FILE" || true
    
    # Wait for connections to close
    sleep 5
    
    # Drop existing database and recreate
    log "Dropping existing database..."
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres \
         -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" 2>>"$LOG_FILE"
    
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres \
         -c "CREATE DATABASE $POSTGRES_DB;" 2>>"$LOG_FILE"
    
    # Restore from backup
    log "Restoring database from backup..."
    if gunzip -c "$backup_file" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
       -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>>"$LOG_FILE"; then
        log "PostgreSQL restore completed successfully"
    else
        log "ERROR: PostgreSQL restore failed"
        return 1
    fi
    
    # Restart services
    log "Restarting services..."
    docker-compose start api-server worker scheduler 2>>"$LOG_FILE"
}

restore_redis() {
    local timestamp=$1
    local backup_file="$BACKUP_DIR/redis/redis_backup_${timestamp}.rdb.gz"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Redis backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring Redis data from $backup_file..."
    
    # Stop services that use Redis
    log "Stopping services..."
    docker-compose stop api-server worker scheduler 2>>"$LOG_FILE" || true
    
    # Stop Redis
    docker-compose stop redis 2>>"$LOG_FILE"
    
    # Clear existing Redis data
    docker-compose run --rm redis redis-cli FLUSHALL 2>>"$LOG_FILE" || true
    
    # Restore Redis data
    log "Restoring Redis data..."
    if gunzip -c "$backup_file" > /tmp/dump.rdb && \
       docker cp /tmp/dump.rdb $(docker-compose ps -q redis):/data/dump.rdb 2>>"$LOG_FILE"; then
        log "Redis restore completed successfully"
        rm -f /tmp/dump.rdb
    else
        log "ERROR: Redis restore failed"
        return 1
    fi
    
    # Restart Redis and other services
    log "Restarting services..."
    docker-compose start redis 2>>"$LOG_FILE"
    sleep 5
    docker-compose start api-server worker scheduler 2>>"$LOG_FILE"
}

restore_sessions() {
    local timestamp=$1
    local backup_file="$BACKUP_DIR/sessions/sessions_backup_${timestamp}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Session backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring session data from $backup_file..."
    
    # Create sessions directory if it doesn't exist
    mkdir -p /app/sessions
    
    # Clear existing session data
    rm -rf /app/sessions/*
    
    # Restore session data
    if tar -xzf "$backup_file" -C /app/sessions 2>>"$LOG_FILE"; then
        log "Session data restore completed successfully"
    else
        log "ERROR: Session data restore failed"
        return 1
    fi
}

restore_config() {
    local timestamp=$1
    local backup_file="$BACKUP_DIR/config_backup_${timestamp}.tar.gz"
    
    if [ ! -f "$backup_file" ]; then
        log "ERROR: Configuration backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring configuration from $backup_file..."
    
    # Create backup of current config
    tar -czf "$BACKUP_DIR/config_current_backup_$(date +%Y%m%d_%H%M%S).tar.gz" \
        /app/.env* /app/docker-compose*.yml /app/monitoring/ 2>>"$LOG_FILE" || true
    
    # Restore configuration
    if tar -xzf "$backup_file" -C / 2>>"$LOG_FILE"; then
        log "Configuration restore completed successfully"
        log "NOTE: You may need to restart services for configuration changes to take effect"
    else
        log "ERROR: Configuration restore failed"
        return 1
    fi
}

# Parse command line arguments
TIMESTAMP=""
LIST_ONLY=false
POSTGRES_ONLY=false
REDIS_ONLY=false
SESSIONS_ONLY=false
CONFIG_ONLY=false

while getopts "t:lprsch" opt; do
    case $opt in
        t)
            TIMESTAMP="$OPTARG"
            ;;
        l)
            LIST_ONLY=true
            ;;
        p)
            POSTGRES_ONLY=true
            ;;
        r)
            REDIS_ONLY=true
            ;;
        s)
            SESSIONS_ONLY=true
            ;;
        c)
            CONFIG_ONLY=true
            ;;
        h)
            usage
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
    esac
done

# Handle list option
if [ "$LIST_ONLY" = true ]; then
    list_backups
    exit 0
fi

# Validate timestamp
if [ -z "$TIMESTAMP" ]; then
    echo "ERROR: Timestamp is required"
    usage
    exit 1
fi

# Validate timestamp format
if ! [[ "$TIMESTAMP" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
    echo "ERROR: Invalid timestamp format. Use YYYYMMDD_HHMMSS"
    exit 1
fi

log "Starting restore process for timestamp: $TIMESTAMP"

# Confirmation prompt
echo "WARNING: This will overwrite existing data!"
echo "Timestamp: $TIMESTAMP"
echo "Are you sure you want to continue? (yes/no)"
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    log "Restore cancelled by user"
    exit 0
fi

# Perform restore based on options
if [ "$POSTGRES_ONLY" = true ]; then
    restore_postgres "$TIMESTAMP"
elif [ "$REDIS_ONLY" = true ]; then
    restore_redis "$TIMESTAMP"
elif [ "$SESSIONS_ONLY" = true ]; then
    restore_sessions "$TIMESTAMP"
elif [ "$CONFIG_ONLY" = true ]; then
    restore_config "$TIMESTAMP"
else
    # Restore everything
    restore_postgres "$TIMESTAMP"
    restore_redis "$TIMESTAMP"
    restore_sessions "$TIMESTAMP"
    restore_config "$TIMESTAMP"
fi

# Send notification (if Slack webhook is configured)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
         --data "{\"text\":\"🔄 Restore completed successfully\n📅 Restored from: $TIMESTAMP\"}" \
         "$SLACK_WEBHOOK_URL" 2>>"$LOG_FILE" || log "WARNING: Failed to send Slack notification"
fi

log "Restore process completed successfully"