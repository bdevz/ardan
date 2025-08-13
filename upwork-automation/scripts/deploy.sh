#!/bin/bash

# Upwork Automation System Deployment Script
# This script handles deployment for different environments

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-"production"}
ACTION=${2:-"deploy"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

usage() {
    echo "Usage: $0 [ENVIRONMENT] [ACTION]"
    echo ""
    echo "ENVIRONMENT:"
    echo "  production  - Deploy to production (default)"
    echo "  development - Deploy to development"
    echo ""
    echo "ACTION:"
    echo "  deploy      - Full deployment (default)"
    echo "  start       - Start services"
    echo "  stop        - Stop services"
    echo "  restart     - Restart services"
    echo "  status      - Check service status"
    echo "  logs        - Show service logs"
    echo "  health      - Run health check"
    echo "  backup      - Create backup"
    echo "  update      - Update and restart services"
    echo ""
    echo "Examples:"
    echo "  $0 production deploy"
    echo "  $0 development start"
    echo "  $0 production health"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$PROJECT_DIR/.env.$ENVIRONMENT" ]; then
        error "Environment file .env.$ENVIRONMENT not found"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

setup_environment() {
    log "Setting up environment: $ENVIRONMENT"
    
    # Copy environment file
    cp "$PROJECT_DIR/.env.$ENVIRONMENT" "$PROJECT_DIR/.env"
    
    # Create required directories
    mkdir -p "$PROJECT_DIR/logs"/{api,worker,scheduler,web}
    mkdir -p "$PROJECT_DIR/data"/{postgres,redis,uploads,sessions}
    mkdir -p "$PROJECT_DIR/backups"/{postgres,redis,sessions}
    mkdir -p "$PROJECT_DIR/credentials"
    
    # Set permissions
    chmod +x "$PROJECT_DIR/scripts"/*.sh
    chmod 600 "$PROJECT_DIR/.env"*
    chmod 700 "$PROJECT_DIR/credentials"
    
    success "Environment setup completed"
}

deploy_services() {
    log "Deploying services for $ENVIRONMENT environment..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    # Build and start services
    docker-compose -f "$COMPOSE_FILE" build
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to start
    log "Waiting for services to start..."
    sleep 30
    
    # Run database migrations (production only)
    if [ "$ENVIRONMENT" = "production" ]; then
        log "Running database migrations..."
        docker-compose -f "$COMPOSE_FILE" exec -T api-server python -m alembic upgrade head || true
    fi
    
    success "Services deployed successfully"
}

start_services() {
    log "Starting services..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    docker-compose -f "$COMPOSE_FILE" start
    
    success "Services started"
}

stop_services() {
    log "Stopping services..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    docker-compose -f "$COMPOSE_FILE" stop
    
    success "Services stopped"
}

restart_services() {
    log "Restarting services..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    docker-compose -f "$COMPOSE_FILE" restart
    
    success "Services restarted"
}

check_status() {
    log "Checking service status..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    docker-compose -f "$COMPOSE_FILE" ps
}

show_logs() {
    log "Showing service logs..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
}

run_health_check() {
    log "Running health check..."
    
    cd "$PROJECT_DIR"
    
    if [ -x "$PROJECT_DIR/scripts/health_check.sh" ]; then
        "$PROJECT_DIR/scripts/health_check.sh"
    else
        warning "Health check script not found or not executable"
        
        # Basic health check
        if curl -f -s --max-time 10 "http://localhost:8000/health" > /dev/null; then
            success "API server is healthy"
        else
            error "API server is not responding"
        fi
        
        if curl -f -s --max-time 10 "http://localhost:3000" > /dev/null; then
            success "Web interface is healthy"
        else
            error "Web interface is not responding"
        fi
    fi
}

create_backup() {
    log "Creating backup..."
    
    cd "$PROJECT_DIR"
    
    if [ -x "$PROJECT_DIR/scripts/backup.sh" ]; then
        "$PROJECT_DIR/scripts/backup.sh"
    else
        error "Backup script not found or not executable"
        exit 1
    fi
}

update_services() {
    log "Updating services..."
    
    cd "$PROJECT_DIR"
    
    # Create backup before update
    create_backup
    
    if [ "$ENVIRONMENT" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker-compose.dev.yml"
    fi
    
    # Pull latest images
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Rebuild and restart
    docker-compose -f "$COMPOSE_FILE" build
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Run migrations
    if [ "$ENVIRONMENT" = "production" ]; then
        log "Running database migrations..."
        docker-compose -f "$COMPOSE_FILE" exec -T api-server python -m alembic upgrade head || true
    fi
    
    # Health check
    sleep 30
    run_health_check
    
    success "Services updated successfully"
}

# Main script logic
case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
esac

if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "development" ]; then
    error "Invalid environment: $ENVIRONMENT"
    usage
    exit 1
fi

log "Starting deployment script for $ENVIRONMENT environment"
log "Action: $ACTION"

case "$ACTION" in
    deploy)
        check_prerequisites
        setup_environment
        deploy_services
        run_health_check
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    health)
        run_health_check
        ;;
    backup)
        create_backup
        ;;
    update)
        update_services
        ;;
    *)
        error "Invalid action: $ACTION"
        usage
        exit 1
        ;;
esac

success "Deployment script completed successfully"