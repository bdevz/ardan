#!/bin/bash

# Upwork Automation System Initial Setup Script
# This script prepares the system for first-time deployment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

prompt() {
    echo -e "${YELLOW}?${NC} $1"
}

echo "=== Upwork Automation System Setup ==="
echo ""

log "Starting initial system setup..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    warning "Running as root. Consider using a non-root user for better security."
fi

# Check operating system
OS=$(uname -s)
log "Detected operating system: $OS"

# Install Docker (Linux only)
if [ "$OS" = "Linux" ]; then
    if ! command -v docker &> /dev/null; then
        prompt "Docker not found. Install Docker? (y/n)"
        read -r install_docker
        if [ "$install_docker" = "y" ] || [ "$install_docker" = "Y" ]; then
            log "Installing Docker..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            success "Docker installed successfully"
            warning "Please log out and log back in for Docker group changes to take effect"
        fi
    else
        success "Docker is already installed"
    fi
    
    # Install Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        prompt "Docker Compose not found. Install Docker Compose? (y/n)"
        read -r install_compose
        if [ "$install_compose" = "y" ] || [ "$install_compose" = "Y" ]; then
            log "Installing Docker Compose..."
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            success "Docker Compose installed successfully"
        fi
    else
        success "Docker Compose is already installed"
    fi
fi

# Create directory structure
log "Creating directory structure..."
cd "$PROJECT_DIR"

mkdir -p logs/{api,worker,scheduler,web,system}
mkdir -p data/{postgres,redis,uploads,sessions}
mkdir -p backups/{postgres,redis,sessions}
mkdir -p credentials
mkdir -p monitoring/{grafana/{dashboards,datasources},prometheus,loki}

success "Directory structure created"

# Set permissions
log "Setting permissions..."
chmod +x scripts/*.sh
chmod 700 credentials/
chmod 755 logs/ data/ backups/

success "Permissions set"

# Generate secrets
log "Generating security secrets..."

# Generate JWT secret
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')

# Generate encryption key
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')

# Generate database password
DB_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')

# Generate Redis password
REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '\n')

# Generate Grafana password
GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')

success "Security secrets generated"

# Create environment file
log "Creating environment configuration..."

if [ ! -f ".env" ]; then
    cp .env.production .env.template
    
    # Replace placeholders with generated values
    sed -i.bak "s/your_secure_password_here/$DB_PASSWORD/g" .env.template
    sed -i.bak "s/your_redis_password_here/$REDIS_PASSWORD/g" .env.template
    sed -i.bak "s/your_jwt_secret_key_here/$JWT_SECRET/g" .env.template
    sed -i.bak "s/your_encryption_key_here/$ENCRYPTION_KEY/g" .env.template
    sed -i.bak "s/your_grafana_password_here/$GRAFANA_PASSWORD/g" .env.template
    
    mv .env.template .env
    rm .env.template.bak
    
    chmod 600 .env
    
    success "Environment configuration created"
    warning "Please edit .env file and add your API keys:"
    echo "  - BROWSERBASE_API_KEY"
    echo "  - OPENAI_API_KEY"
    echo "  - SLACK_BOT_TOKEN"
    echo "  - N8N_WEBHOOK_URL"
else
    warning ".env file already exists, skipping creation"
fi

# Setup Google credentials
log "Setting up Google credentials..."
if [ ! -f "credentials/google-credentials.json" ]; then
    warning "Google credentials not found"
    echo "To set up Google services integration:"
    echo "1. Go to Google Cloud Console"
    echo "2. Create a new project or select existing one"
    echo "3. Enable Google Docs, Drive, and Sheets APIs"
    echo "4. Create a service account"
    echo "5. Download the credentials JSON file"
    echo "6. Save it as credentials/google-credentials.json"
else
    success "Google credentials found"
fi

# Setup SSL certificates (optional)
prompt "Generate self-signed SSL certificates for HTTPS? (y/n)"
read -r generate_ssl
if [ "$generate_ssl" = "y" ] || [ "$generate_ssl" = "Y" ]; then
    log "Generating SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout credentials/ssl-key.pem \
        -out credentials/ssl-cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    chmod 600 credentials/ssl-*.pem
    success "SSL certificates generated"
fi

# Setup cron jobs
prompt "Setup automated backups with cron? (y/n)"
read -r setup_cron
if [ "$setup_cron" = "y" ] || [ "$setup_cron" = "Y" ]; then
    log "Setting up cron jobs..."
    
    # Create cron job for backups
    (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/scripts/backup.sh") | crontab -
    
    # Create cron job for health checks
    (crontab -l 2>/dev/null; echo "*/5 * * * * $PROJECT_DIR/scripts/health_check.sh") | crontab -
    
    success "Cron jobs configured"
    echo "  - Daily backups at 2:00 AM"
    echo "  - Health checks every 5 minutes"
fi

# Test Docker setup
log "Testing Docker setup..."
if docker --version && docker-compose --version; then
    success "Docker setup is working"
else
    error "Docker setup has issues"
    exit 1
fi

# Final instructions
echo ""
echo "=== Setup Complete ==="
echo ""
success "Initial setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Add Google credentials to credentials/google-credentials.json"
echo "3. Run deployment: ./scripts/deploy.sh production deploy"
echo "4. Access the system:"
echo "   - Web Interface: http://localhost:3000"
echo "   - API Documentation: http://localhost:8000/docs"
echo "   - Grafana Dashboard: http://localhost:3001"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "Generated credentials:"
echo "  - Database password: $DB_PASSWORD"
echo "  - Redis password: $REDIS_PASSWORD"
echo "  - Grafana password: $GRAFANA_PASSWORD"
echo ""
warning "Save these credentials securely!"
echo ""
echo "For more information, see docs/DEPLOYMENT.md"