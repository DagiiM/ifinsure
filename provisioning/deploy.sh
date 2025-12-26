#!/bin/bash
#
# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║                           iFinsure Deployment Script                           ║
# ║                        One-Step Production Deployment                          ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   -d, --domain DOMAIN     Domain name for the application (enables SSL via Let's Encrypt)
#   -e, --email EMAIL       Email for Let's Encrypt SSL certificates
#   -p, --port PORT         Port to run the application (default: 80/443 with domain, 8000 without)
#   -b, --branch BRANCH     Git branch to deploy (default: main)
#   --no-ssl                Disable SSL even with domain
#   --skip-backup           Skip database backup before deployment
#   --skip-migrations       Skip database migrations
#   --dry-run               Show what would be done without executing
#   -h, --help              Show this help message
#
# Examples:
#   ./deploy.sh                                     # Local deployment
#   ./deploy.sh -d example.com -e admin@example.com # Production with SSL
#   ./deploy.sh -d example.com --no-ssl             # Production without SSL
#
# Author: iFinsure Team
# Version: 1.0.0
# Last Updated: 2025-12-26
#

set -euo pipefail

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_FILE="${PROJECT_ROOT}/logs/deploy_$(date +%Y%m%d_%H%M%S).log"
readonly BACKUP_DIR="${PROJECT_ROOT}/backups"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
PORT=""
BRANCH="main"
ENABLE_SSL=true
SKIP_BACKUP=false
SKIP_MIGRATIONS=false
DRY_RUN=false
RESET_ALL=false

# Docker configuration
COMPOSE_PROJECT_NAME="ifinsure"
DB_CONTAINER_NAME="ifinsure_db"
REDIS_CONTAINER_NAME="ifinsure_redis"
APP_CONTAINER_NAME="ifinsure_app"
NGINX_CONTAINER_NAME="ifinsure_nginx"

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "${BLUE}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}✓ $*${NC}"; }
log_warning() { log "WARNING" "${YELLOW}⚠ $*${NC}"; }
log_error() { log "ERROR" "${RED}✗ $*${NC}"; }
log_step() { log "STEP" "${PURPLE}→ $*${NC}"; }
log_header() { 
    echo "" | tee -a "$LOG_FILE"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}  $*${NC}" | tee -a "$LOG_FILE"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
    ██╗███████╗██╗███╗   ██╗███████╗██╗   ██╗██████╗ ███████╗
    ██║██╔════╝██║████╗  ██║██╔════╝██║   ██║██╔══██╗██╔════╝
    ██║█████╗  ██║██╔██╗ ██║███████╗██║   ██║██████╔╝█████╗  
    ██║██╔══╝  ██║██║╚██╗██║╚════██║██║   ██║██╔══██╗██╔══╝  
    ██║██║     ██║██║ ╚████║███████║╚██████╔╝██║  ██║███████╗
    ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
                 One-Step Deployment Script v1.0.0
EOF
    echo -e "${NC}"
}

show_help() {
    cat << EOF
iFinsure Deployment Script - One-Step Production Deployment

Usage: $(basename "$0") [OPTIONS]

Options:
    -d, --domain DOMAIN     Domain name for the application (enables SSL via Let's Encrypt)
    -e, --email EMAIL       Email for Let's Encrypt SSL certificates (required with domain)
    -p, --port PORT         Port to run the application (default: 80/443 with domain, 8000 without)
    -b, --branch BRANCH     Git branch to deploy (default: main)
    --no-ssl                Disable SSL even with domain
    --skip-backup           Skip database backup before deployment
    --skip-migrations       Skip database migrations
    --dry-run               Show what would be done without executing
    --reset                 Reset everything (delete all data and start fresh)
    -h, --help              Show this help message

Examples:
    # Local development deployment
    ./deploy.sh

    # Production deployment with SSL (recommended)
    ./deploy.sh -d ifinsure.example.com -e admin@example.com

    # Production deployment without SSL
    ./deploy.sh -d ifinsure.example.com --no-ssl

    # Deploy specific branch
    ./deploy.sh -d ifinsure.example.com -e admin@example.com -b staging

Environment Variables (can be set in .env.production):
    DJANGO_SECRET_KEY       Django secret key (auto-generated if not set)
    DB_PASSWORD             PostgreSQL password (auto-generated if not set)
    REDIS_URL               Redis connection URL (default: redis://redis:6379/0)

EOF
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Consider using a non-root user with sudo privileges."
    fi
}

check_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log_info "Detected OS: $OS $VER"
    else
        log_error "Cannot detect OS. This script supports Ubuntu/Debian and CentOS/RHEL."
        exit 1
    fi
}

# =============================================================================
# DEPENDENCY CHECKS & INSTALLATION
# =============================================================================

check_command() {
    command -v "$1" &> /dev/null
}

install_docker() {
    log_step "Installing Docker..."
    
    if check_command docker; then
        log_success "Docker is already installed: $(docker --version)"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would install Docker"
        return 0
    fi

    # Install Docker using official script
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    
    # Add current user to docker group
    sudo usermod -aG docker "$USER"
    
    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker installed successfully"
}

install_docker_compose() {
    log_step "Installing Docker Compose..."
    
    if check_command docker-compose || docker compose version &> /dev/null; then
        log_success "Docker Compose is already installed"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would install Docker Compose"
        return 0
    fi

    # Install Docker Compose plugin
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    
    log_success "Docker Compose installed successfully"
}

check_dependencies() {
    log_header "Checking Dependencies"
    
    local missing_deps=()
    
    # Check for required commands
    for cmd in curl git openssl; do
        if ! check_command "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_warning "Missing dependencies: ${missing_deps[*]}"
        log_step "Installing missing dependencies..."
        
        if [[ "$DRY_RUN" == false ]]; then
            sudo apt-get update
            sudo apt-get install -y "${missing_deps[@]}"
        fi
    fi
    
    # Install Docker and Docker Compose
    install_docker
    install_docker_compose
    
    log_success "All dependencies satisfied"
}

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

generate_secret_key() {
    openssl rand -base64 50 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c 50
}

generate_db_password() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24
}

setup_environment() {
    log_header "Setting Up Environment"
    
    local env_file="${PROJECT_ROOT}/.env.production"
    local env_template="${SCRIPT_DIR}/.env.production.template"
    
    if [[ ! -f "$env_file" ]]; then
        log_step "Creating production environment file..."
        
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY-RUN] Would create $env_file"
            return 0
        fi
        
        # Generate secrets
        local secret_key=$(generate_secret_key)
        local db_password=$(generate_db_password)
        
        # Determine hosts
        local allowed_hosts="localhost,127.0.0.1"
        if [[ -n "$DOMAIN" ]]; then
            allowed_hosts="$DOMAIN,www.$DOMAIN,$allowed_hosts"
        fi
        
        # Create environment file
        cat > "$env_file" << EOF
# =============================================================================
# iFinsure Production Environment Configuration
# Generated: $(date)
# =============================================================================

# Django Settings
DJANGO_SECRET_KEY=${secret_key}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${allowed_hosts}
DJANGO_SETTINGS_MODULE=config.settings.production

# Domain Configuration
DOMAIN=${DOMAIN}
ENABLE_SSL=${ENABLE_SSL}
LETSENCRYPT_EMAIL=${EMAIL}

# Database (PostgreSQL in Docker)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ifinsure_db
DB_USER=ifinsure
DB_PASSWORD=${db_password}
DB_HOST=db
DB_PORT=5432

# Redis (Cache & Celery)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Email Configuration (Update with your SMTP settings)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@${DOMAIN:-ifinsure.local}

# Security Settings
SECURE_SSL_REDIRECT=${ENABLE_SSL}
SESSION_COOKIE_SECURE=${ENABLE_SSL}
CSRF_COOKIE_SECURE=${ENABLE_SSL}

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=

# =============================================================================
# PAYMENT INTEGRATIONS (Configure as needed)
# =============================================================================

# M-Pesa
MPESA_ENVIRONMENT=production
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_CALLBACK_URL=https://${DOMAIN:-localhost}/api/webhooks/mpesa/

# Stripe
STRIPE_ENVIRONMENT=live
STRIPE_PUBLIC_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# =============================================================================
# SMS INTEGRATIONS
# =============================================================================

# Africa's Talking
AT_USERNAME=
AT_API_KEY=
AT_SENDER_ID=ifinsure

# =============================================================================
# FILE STORAGE
# =============================================================================

# AWS S3 (Optional - leave empty for local storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=
EOF

        chmod 600 "$env_file"
        log_success "Environment file created: $env_file"
        log_warning "Please review and update the environment file with your production values"
    else
        log_info "Environment file already exists: $env_file"
        
        # Update domain-specific settings if domain is provided
        if [[ -n "$DOMAIN" ]]; then
            log_step "Updating domain settings in environment file..."
            sed -i "s/^DOMAIN=.*/DOMAIN=${DOMAIN}/" "$env_file"
            sed -i "s/^ENABLE_SSL=.*/ENABLE_SSL=${ENABLE_SSL}/" "$env_file"
            
            # Update ALLOWED_HOSTS
            local allowed_hosts="$DOMAIN,www.$DOMAIN,localhost,127.0.0.1"
            sed -i "s/^DJANGO_ALLOWED_HOSTS=.*/DJANGO_ALLOWED_HOSTS=${allowed_hosts}/" "$env_file"
        fi
    fi
    
    # Source the environment file
    set -a
    source "$env_file"
    set +a
    
    log_success "Environment configured"
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

backup_database() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        log_info "Skipping database backup (--skip-backup flag set)"
        return 0
    fi
    
    log_header "Creating Database Backup"
    
    # Check if database container exists and is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NAME}$"; then
        log_info "No existing database container found. Skipping backup."
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would create database backup"
        return 0
    fi
    
    mkdir -p "$BACKUP_DIR"
    local backup_file="${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    log_step "Backing up database to $backup_file..."
    
    docker exec "${DB_CONTAINER_NAME}" pg_dump -U ifinsure ifinsure_db | gzip > "$backup_file"
    
    if [[ -f "$backup_file" ]]; then
        log_success "Database backup created: $backup_file ($(du -h "$backup_file" | cut -f1))"
        
        # Keep only last 10 backups
        log_step "Cleaning up old backups..."
        ls -t "${BACKUP_DIR}"/db_backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm
    else
        log_error "Failed to create database backup"
        exit 1
    fi
}

reset_environment() {
    if [[ "$RESET_ALL" != true ]]; then
        return 0
    fi

    log_header "RESETTING EVERYTHING"
    log_warning "This will delete all containers, images, and VOLUMES (database data!)"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would reset environment"
        return 0
    fi

    read -p "Are you absolutely sure you want to delete ALL data? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Reset cancelled by user."
        return 0
    fi

    log_step "Stopping and removing all services and volumes..."
    docker compose -f provisioning/docker-compose.yml down -v --remove-orphans
    
    log_step "Cleaning up any dangling images..."
    docker image prune -f
    
    log_success "Environment reset successfully"
}

# =============================================================================
# DOCKER SETUP
# =============================================================================

create_docker_network() {
    log_step "Creating Docker network..."
    
    if docker network ls --format '{{.Name}}' | grep -q "^ifinsure_network$"; then
        log_info "Docker network 'ifinsure_network' already exists"
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would create Docker network 'ifinsure_network'"
        return 0
    fi
    
    docker network create ifinsure_network
    log_success "Docker network created"
}

build_application() {
    log_header "Building Application"
    
    cd "$PROJECT_ROOT"
    
    log_step "Building Docker images..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would build Docker images"
        return 0
    fi
    
    docker compose -f provisioning/docker-compose.yml build --no-cache
    
    log_success "Docker images built successfully"
}

fix_permissions() {
    log_step "Fixing directory permissions..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would fix directory permissions"
        return 0
    fi

    # Create directories if they don't exist
    mkdir -p "${PROJECT_ROOT}/staticfiles" "${PROJECT_ROOT}/media" "${PROJECT_ROOT}/logs"
    
    # Ensure directories are owned by UID 1000 (appuser in Dockerfile)
    # We use sudo to ensure we can change ownership if they were created by root
    if command -v sudo >/dev/null 2>&1; then
        sudo chown -R 1000:1000 "${PROJECT_ROOT}/staticfiles" "${PROJECT_ROOT}/media" "${PROJECT_ROOT}/logs" || true
        sudo chmod -R 775 "${PROJECT_ROOT}/staticfiles" "${PROJECT_ROOT}/media" "${PROJECT_ROOT}/logs" || true
    else
        chown -R 1000:1000 "${PROJECT_ROOT}/staticfiles" "${PROJECT_ROOT}/media" "${PROJECT_ROOT}/logs" || true
        chmod -R 775 "${PROJECT_ROOT}/staticfiles" "${PROJECT_ROOT}/media" "${PROJECT_ROOT}/logs" || true
    fi
    
    log_success "Permissions fixed"
}

start_services() {
    log_header "Starting Services"
    
    cd "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would start Docker services"
        return 0
    fi
    
    log_step "Starting database and Redis..."
    docker compose -f provisioning/docker-compose.yml up -d db redis
    
    # Wait for database to be ready
    log_step "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker exec "${DB_CONTAINER_NAME}" pg_isready -U ifinsure -d ifinsure_db &>/dev/null; then
            log_success "Database is ready"
            break
        fi
        attempt=$((attempt + 1))
        log_info "Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Database failed to start within timeout"
        docker logs "${DB_CONTAINER_NAME}" --tail 50
        exit 1
    fi
    
    # Wait for Redis
    log_step "Waiting for Redis to be ready..."
    attempt=0
    while [[ $attempt -lt 15 ]]; do
        if docker exec "${REDIS_CONTAINER_NAME}" redis-cli ping | grep -q "PONG"; then
            log_success "Redis is ready"
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_success "Core services started"
}

run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_info "Skipping migrations (--skip-migrations flag set)"
        return 0
    fi
    
    log_header "Running Database Migrations"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would run database migrations"
        return 0
    fi
    
    log_step "Running Django migrations..."
    docker compose -f provisioning/docker-compose.yml run --rm app python manage.py migrate --noinput
    
    log_step "Collecting static files..."
    docker compose -f provisioning/docker-compose.yml run --rm app python manage.py collectstatic --noinput
    
    log_success "Migrations completed"
}

start_application() {
    log_header "Starting Application"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would start application containers"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    log_step "Starting application with Gunicorn..."
    docker compose -f provisioning/docker-compose.yml up -d app
    
    # Wait for application to be ready
    log_step "Waiting for application to be ready..."
    local max_attempts=30
    local attempt=0
    local app_port="${PORT:-8000}"
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker exec "${APP_CONTAINER_NAME}" curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ 2>/dev/null | grep -q "200"; then
            log_success "Application is ready"
            break
        fi
        attempt=$((attempt + 1))
        log_info "Waiting for application... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_warning "Application health check timed out. Checking logs..."
        docker logs "${APP_CONTAINER_NAME}" --tail 20
    fi
    
    log_success "Application started"
}

# =============================================================================
# SSL & NGINX SETUP
# =============================================================================

setup_ssl() {
    if [[ -z "$DOMAIN" ]] || [[ "$ENABLE_SSL" != true ]]; then
        log_info "SSL setup skipped (no domain or --no-ssl flag)"
        return 0
    fi
    
    if [[ -z "$EMAIL" ]]; then
        log_error "Email is required for Let's Encrypt SSL. Use -e or --email option."
        exit 1
    fi
    
    log_header "Setting Up SSL with Let's Encrypt"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would set up SSL for $DOMAIN"
        return 0
    fi
    
    # Create certbot directories with full path for challenge files
    mkdir -p "${PROJECT_ROOT}/certbot/conf"
    mkdir -p "${PROJECT_ROOT}/certbot/www/.well-known/acme-challenge"
    
    # Ensure correct permissions
    chmod -R 755 "${PROJECT_ROOT}/certbot"
    
    log_step "Starting Nginx for SSL certificate request..."
    docker compose -f provisioning/docker-compose.yml up -d nginx
    
    # Wait for nginx to start and reload its configuration
    sleep 3
    docker compose -f provisioning/docker-compose.yml exec nginx nginx -s reload 2>/dev/null || true
    sleep 2
    
    log_step "Requesting SSL certificate for $DOMAIN..."
    
    # Request certificate using certbot
    docker compose -f provisioning/docker-compose.yml run --rm --entrypoint certbot certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    if [[ $? -eq 0 ]]; then
        log_success "SSL certificate obtained successfully"
        
        # Reload nginx with SSL configuration
        log_step "Reloading Nginx with SSL configuration..."
        docker compose -f provisioning/docker-compose.yml restart nginx
        
        log_success "SSL configured successfully for $DOMAIN"
    else
        log_error "Failed to obtain SSL certificate"
        log_warning "Continuing without SSL. Check your domain DNS settings."
    fi
}

setup_ssl_renewal() {
    if [[ -z "$DOMAIN" ]] || [[ "$ENABLE_SSL" != true ]]; then
        return 0
    fi
    
    log_step "Setting up automatic SSL renewal..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would set up SSL renewal cron job"
        return 0
    fi
    
    # Create renewal script
    cat > "${SCRIPT_DIR}/renew-ssl.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/.."
docker compose -f provisioning/docker-compose.yml run --rm certbot renew
docker compose -f provisioning/docker-compose.yml exec nginx nginx -s reload
EOF
    
    chmod +x "${SCRIPT_DIR}/renew-ssl.sh"
    
    # Add cron job for automatic renewal (runs twice daily)
    (crontab -l 2>/dev/null; echo "0 0,12 * * * ${SCRIPT_DIR}/renew-ssl.sh >> ${PROJECT_ROOT}/logs/ssl-renewal.log 2>&1") | crontab -
    
    log_success "SSL renewal configured"
}

start_nginx() {
    log_header "Starting Nginx"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would start Nginx"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    docker compose -f provisioning/docker-compose.yml up -d nginx
    
    log_success "Nginx started"
}

# =============================================================================
# FINALIZATION
# =============================================================================

create_superuser() {
    log_header "Admin User Setup"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would prompt for superuser creation"
        return 0
    fi
    
    read -p "Would you like to create a superuser now? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f provisioning/docker-compose.yml run --rm app python manage.py createsuperuser
    else
        log_info "Skipping superuser creation. Run later with:"
        log_info "  docker compose -f provisioning/docker-compose.yml run --rm app python manage.py createsuperuser"
    fi
}

print_summary() {
    log_header "Deployment Complete!"
    
    local app_url
    if [[ -n "$DOMAIN" ]]; then
        if [[ "$ENABLE_SSL" == true ]]; then
            app_url="https://$DOMAIN"
        else
            app_url="http://$DOMAIN"
        fi
    else
        app_url="http://localhost:${PORT:-8000}"
    fi
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    DEPLOYMENT SUCCESSFUL!                      ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  Application URL:  ${CYAN}${app_url}${NC}"
    echo -e "${GREEN}║${NC}  Admin Panel:      ${CYAN}${app_url}/admin/${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    if [[ -n "$DOMAIN" ]] && [[ "$ENABLE_SSL" == true ]]; then
        echo -e "${GREEN}║${NC}  SSL Status:       ${GREEN}✓ Enabled (Let's Encrypt)${NC}"
    else
        echo -e "${GREEN}║${NC}  SSL Status:       ${YELLOW}⚠ Disabled${NC}"
    fi
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  ${YELLOW}Useful Commands:${NC}                                            ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  View logs:        docker compose -f provisioning/docker-compose.yml logs -f${NC}"
    echo -e "${GREEN}║${NC}  Stop:             docker compose -f provisioning/docker-compose.yml down${NC}"
    echo -e "${GREEN}║${NC}  Restart:          docker compose -f provisioning/docker-compose.yml restart${NC}"
    echo -e "${GREEN}║${NC}  Shell:            docker compose -f provisioning/docker-compose.yml exec app bash${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log_info "Deployment log saved to: $LOG_FILE"
}

# =============================================================================
# CLEANUP
# =============================================================================

cleanup_on_error() {
    log_error "Deployment failed! Cleaning up..."
    
    # Don't remove containers on error - leave for debugging
    log_info "Containers left running for debugging."
    log_info "To manually clean up: docker compose -f provisioning/docker-compose.yml down"
    
    exit 1
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            --no-ssl)
                ENABLE_SSL=false
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --reset)
                RESET_ALL=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -n "$DOMAIN" ]] && [[ "$ENABLE_SSL" == true ]] && [[ -z "$EMAIL" ]]; then
        log_error "Email (-e/--email) is required when using SSL with a domain."
        log_info "Either provide an email or use --no-ssl to disable SSL."
        exit 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Print banner
    print_banner
    
    # Display configuration
    log_info "Configuration:"
    log_info "  Domain:          ${DOMAIN:-<none>}"
    log_info "  SSL:             ${ENABLE_SSL}"
    log_info "  Port:            ${PORT:-auto}"
    log_info "  Branch:          ${BRANCH}"
    log_info "  Dry Run:         ${DRY_RUN}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "Running in DRY-RUN mode - no changes will be made"
    fi
    
    # Run deployment steps
    check_root
    check_os
    check_dependencies
    
    # Setup environment and backup
    setup_environment
    reset_environment
    backup_database
    
    # Docker deployment
    create_docker_network
    build_application
    fix_permissions
    start_services
    run_migrations
    start_application
    
    # SSL and Nginx
    if [[ -n "$DOMAIN" ]]; then
        setup_ssl
        setup_ssl_renewal
    fi
    start_nginx
    
    # Finalization
    create_superuser
    print_summary
}

# Run main function
main "$@"
