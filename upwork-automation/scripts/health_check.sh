#!/bin/bash

# Upwork Automation System Health Check Script
# This script performs comprehensive health checks and can be used for monitoring

set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
LOG_FILE="/var/log/health_check.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
ALERT_THRESHOLD_DISK=90

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-10}
    
    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service_name is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is unhealthy"
        return 1
    fi
}

check_docker_service() {
    local service_name=$1
    
    if docker-compose ps "$service_name" | grep -q "Up"; then
        echo -e "${GREEN}✓${NC} Docker service $service_name is running"
        return 0
    else
        echo -e "${RED}✗${NC} Docker service $service_name is not running"
        return 1
    fi
}

get_health_status() {
    local endpoint=$1
    curl -s --max-time 10 "$API_URL$endpoint" 2>/dev/null || echo '{"status":"error"}'
}

send_alert() {
    local message=$1
    local severity=${2:-"warning"}
    
    log "ALERT [$severity]: $message"
    
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local emoji="⚠️"
        local color="warning"
        
        case $severity in
            "critical")
                emoji="🚨"
                color="danger"
                ;;
            "warning")
                emoji="⚠️"
                color="warning"
                ;;
            "info")
                emoji="ℹ️"
                color="good"
                ;;
        esac
        
        curl -X POST -H 'Content-type: application/json' \
             --data "{
                 \"text\": \"$emoji Health Check Alert\",
                 \"attachments\": [{
                     \"color\": \"$color\",
                     \"fields\": [{
                         \"title\": \"Alert\",
                         \"value\": \"$message\",
                         \"short\": false
                     }],
                     \"footer\": \"Upwork Automation Health Check\",
                     \"ts\": $(date +%s)
                 }]
             }" \
             "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
}

echo "=== Upwork Automation System Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check Docker services
echo "Checking Docker services..."
services_healthy=true

if ! check_docker_service "db"; then
    services_healthy=false
    send_alert "PostgreSQL database service is down" "critical"
fi

if ! check_docker_service "redis"; then
    services_healthy=false
    send_alert "Redis service is down" "critical"
fi

if ! check_docker_service "api-server"; then
    services_healthy=false
    send_alert "API server service is down" "critical"
fi

if ! check_docker_service "web-interface"; then
    services_healthy=false
    send_alert "Web interface service is down" "warning"
fi

if ! check_docker_service "worker"; then
    services_healthy=false
    send_alert "Worker service is down" "critical"
fi

echo ""

# Check HTTP endpoints
echo "Checking HTTP endpoints..."
endpoints_healthy=true

if ! check_service "API Health Check" "$API_URL/health"; then
    endpoints_healthy=false
    send_alert "API health check endpoint is not responding" "critical"
fi

if ! check_service "Web Interface" "http://localhost:3000"; then
    endpoints_healthy=false
    send_alert "Web interface is not responding" "warning"
fi

echo ""

# Get detailed health status
echo "Getting detailed health status..."
health_response=$(get_health_status "/health/detailed")
overall_status=$(echo "$health_response" | jq -r '.overall_status // "unknown"' 2>/dev/null)

case $overall_status in
    "healthy")
        echo -e "${GREEN}✓${NC} Overall system status: HEALTHY"
        ;;
    "degraded")
        echo -e "${YELLOW}⚠${NC} Overall system status: DEGRADED"
        send_alert "System status is degraded" "warning"
        ;;
    "unhealthy")
        echo -e "${RED}✗${NC} Overall system status: UNHEALTHY"
        send_alert "System status is unhealthy" "critical"
        ;;
    *)
        echo -e "${RED}✗${NC} Overall system status: UNKNOWN"
        send_alert "Unable to determine system status" "critical"
        ;;
esac

# Check system metrics
echo ""
echo "Checking system metrics..."
metrics_response=$(get_health_status "/health/metrics")

if [ "$metrics_response" != '{"status":"error"}' ]; then
    cpu_usage=$(echo "$metrics_response" | jq -r '.cpu_usage // 0' 2>/dev/null)
    memory_usage=$(echo "$metrics_response" | jq -r '.memory_usage // 0' 2>/dev/null)
    disk_usage=$(echo "$metrics_response" | jq -r '.disk_usage // 0' 2>/dev/null)
    queue_size=$(echo "$metrics_response" | jq -r '.queue_size // 0' 2>/dev/null)
    error_rate=$(echo "$metrics_response" | jq -r '.error_rate // 0' 2>/dev/null)
    
    echo "CPU Usage: ${cpu_usage}%"
    echo "Memory Usage: ${memory_usage}%"
    echo "Disk Usage: ${disk_usage}%"
    echo "Queue Size: $queue_size"
    echo "Error Rate: ${error_rate}%"
    
    # Check thresholds
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        send_alert "High CPU usage: ${cpu_usage}%" "warning"
    fi
    
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        send_alert "High memory usage: ${memory_usage}%" "warning"
    fi
    
    if (( $(echo "$disk_usage > $ALERT_THRESHOLD_DISK" | bc -l) )); then
        send_alert "High disk usage: ${disk_usage}%" "critical"
    fi
    
    if (( $(echo "$queue_size > 100" | bc -l) )); then
        send_alert "High queue size: $queue_size tasks pending" "warning"
    fi
    
    if (( $(echo "$error_rate > 5" | bc -l) )); then
        send_alert "High error rate: ${error_rate}%" "warning"
    fi
else
    echo -e "${RED}✗${NC} Unable to retrieve system metrics"
    send_alert "Unable to retrieve system metrics" "warning"
fi

echo ""

# Check component health
echo "Checking individual components..."
if [ "$health_response" != '{"status":"error"}' ]; then
    components=$(echo "$health_response" | jq -r '.components[]? | "\(.name):\(.status)"' 2>/dev/null)
    
    if [ -n "$components" ]; then
        while IFS=':' read -r component_name component_status; do
            case $component_status in
                "healthy")
                    echo -e "${GREEN}✓${NC} $component_name: $component_status"
                    ;;
                "degraded")
                    echo -e "${YELLOW}⚠${NC} $component_name: $component_status"
                    ;;
                "unhealthy")
                    echo -e "${RED}✗${NC} $component_name: $component_status"
                    send_alert "Component $component_name is unhealthy" "warning"
                    ;;
            esac
        done <<< "$components"
    fi
fi

echo ""

# Summary
echo "=== Health Check Summary ==="
if [ "$services_healthy" = true ] && [ "$endpoints_healthy" = true ] && [ "$overall_status" = "healthy" ]; then
    echo -e "${GREEN}✓ All systems are healthy${NC}"
    exit 0
elif [ "$overall_status" = "degraded" ]; then
    echo -e "${YELLOW}⚠ System is degraded but operational${NC}"
    exit 1
else
    echo -e "${RED}✗ System has critical issues${NC}"
    exit 2
fi