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
BRANCH="main"  # NOTE: Branch switching not yet implemented; reserved for future use
ENABLE_SSL=true
ALLOW_INSTALL=false  # Set via --allow-install to permit automatic Docker/package installation
SKIP_BACKUP=false
SKIP_MIGRATIONS=false
DRY_RUN=false
RESET_ALL=false
NON_INTERACTIVE=false

# Docker configuration
COMPOSE_PROJECT_NAME="ifinsure"
DB_CONTAINER_NAME="ifinsure_db"
REDIS_CONTAINER_NAME="ifinsure_redis"
APP_CONTAINER_NAME="ifinsure_app"
NGINX_CONTAINER_NAME="ifinsure_nginx"

# Determine Docker Compose command
if docker compose version &>/dev/null; then
    readonly DC="docker compose"
elif command -v docker-compose &>/dev/null; then
    readonly DC="docker-compose"
else
    readonly DC="docker compose" # Fallback, likely to fail if not installed
fi

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

# Get public IP with fallbacks
get_public_ip() {
    local ip=""
    local services=("https://api.ipify.org" "https://ifconfig.me" "https://icanhazip.com")
    
    for service in "${services[@]}"; do
        ip=$(curl -s --max-time 5 "$service" 2>/dev/null || true)
        if [[ -n "$ip" ]]; then
            echo "$ip"
            return 0
        fi
    done
    return 1
}

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
    --allow-install         Allow automatic installation of Docker and dependencies
    --non-interactive       Run without interactive prompts (for CI/CD)
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

# =============================================================================
# INPUT VALIDATION
# =============================================================================

validate_domain() {
    local domain="$1"
    # Allow empty (local deployment) or valid domain pattern
    if [[ -z "$domain" ]]; then
        return 0
    fi
    # Basic domain validation: alphanumeric, hyphens, dots; no leading/trailing dot/hyphen
    if [[ ! "$domain" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        log_error "Invalid domain format: $domain"
        log_info "Domain must be a valid hostname (e.g., example.com or sub.example.com)"
        return 1
    fi
    return 0
}

validate_email() {
    local email="$1"
    if [[ -z "$email" ]]; then
        return 0
    fi
    # Basic email validation
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_error "Invalid email format: $email"
        return 1
    fi
    return 0
}

validate_port() {
    local port="$1"
    if [[ -z "$port" ]]; then
        return 0
    fi
    if [[ ! "$port" =~ ^[0-9]+$ ]] || [[ "$port" -lt 1 ]] || [[ "$port" -gt 65535 ]]; then
        log_error "Invalid port: $port (must be 1-65535)"
        return 1
    fi
    return 0
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

# Cross-platform sed in-place edit (handles GNU and BSD sed)
sed_inplace() {
    local pattern="$1"
    local file="$2"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$pattern" "$file"
    else
        sed -i "$pattern" "$file"
    fi
}

# Install packages using the appropriate package manager
install_packages() {
    local packages=("$@")
    
    if [[ ${#packages[@]} -eq 0 ]]; then
        return 0
    fi
    
    if [[ "$ALLOW_INSTALL" != true ]]; then
        log_error "Missing packages: ${packages[*]}"
        log_info "Run with --allow-install to permit automatic installation, or install manually:"
        log_info "  sudo apt-get install -y ${packages[*]}  # Debian/Ubuntu"
        log_info "  sudo dnf install -y ${packages[*]}      # Fedora/RHEL"
        return 1
    fi
    
    if check_command apt-get; then
        sudo apt-get update
        sudo apt-get install -y "${packages[@]}"
    elif check_command dnf; then
        sudo dnf install -y "${packages[@]}"
    elif check_command yum; then
        sudo yum install -y "${packages[@]}"
    elif check_command pacman; then
        sudo pacman -Sy --noconfirm "${packages[@]}"
    elif check_command brew; then
        brew install "${packages[@]}"
    else
        log_error "No supported package manager found (apt-get, dnf, yum, pacman, brew)"
        return 1
    fi
}

install_docker() {
    log_step "Checking Docker..."
    
    if check_command docker; then
        log_success "Docker is already installed: $(docker --version)"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would install Docker"
        return 0
    fi
    
    if [[ "$ALLOW_INSTALL" != true ]]; then
        log_error "Docker is not installed."
        log_info "Install Docker manually: https://docs.docker.com/engine/install/"
        log_info "Or run with --allow-install to permit automatic installation."
        return 1
    fi
    
    log_warning "Installing Docker via get.docker.com script..."

    # Install Docker using official script with verification
    local docker_script="/tmp/get-docker-$$.sh"
    curl -fsSL https://get.docker.com -o "$docker_script"
    
    # Basic sanity check on downloaded script
    if [[ ! -s "$docker_script" ]] || ! head -1 "$docker_script" | grep -q '^#!/'; then
        log_error "Downloaded Docker install script appears invalid"
        rm -f "$docker_script"
        return 1
    fi
    
    sudo sh "$docker_script"
    rm -f "$docker_script"
    
    # Add current user to docker group
    sudo usermod -aG docker "$USER"
    
    # Start and enable Docker (systemd-based systems)
    if check_command systemctl; then
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    
    log_success "Docker installed successfully"
    log_warning "You may need to log out and back in for docker group membership to take effect."
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
    for cmd in curl git openssl envsubst; do
        if ! check_command "$cmd"; then
            if [[ "$cmd" == "envsubst" ]]; then
                # handling for different distros (gettext-base for debian/ubuntu, gettext for others)
                if check_command apt-get; then
                    missing_deps+=("gettext-base")
                else
                    missing_deps+=("gettext")
                fi
            else
                missing_deps+=("$cmd")
            fi
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_warning "Missing dependencies: ${missing_deps[*]}"
        log_step "Installing missing dependencies..."
        
        if [[ "$DRY_RUN" == false ]]; then
            install_packages "${missing_deps[@]}"
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
        
        # Determine hosts - include public IP when no domain
        local allowed_hosts="localhost,127.0.0.1"
        if [[ -n "$DOMAIN" ]]; then
            allowed_hosts="$DOMAIN,www.$DOMAIN,$allowed_hosts"
        else
            # When no domain, add public IP to allowed hosts
            local public_ip=$(get_public_ip || echo "")
            if [[ -n "$public_ip" ]]; then
                allowed_hosts="$public_ip,$allowed_hosts"
                log_info "Added public IP ($public_ip) to ALLOWED_HOSTS"
            fi
        fi
        
        # Determine security settings based on SSL
        local ssl_redirect="False"
        local cookie_secure="False"
        if [[ -n "$DOMAIN" ]] && [[ "$ENABLE_SSL" == true ]]; then
            ssl_redirect="True"
            cookie_secure="True"
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
SECURE_SSL_REDIRECT=${ssl_redirect}
SESSION_COOKIE_SECURE=${cookie_secure}
CSRF_COOKIE_SECURE=${cookie_secure}

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
        
        # Always update security settings based on domain/SSL status
        local ssl_redirect="False"
        local cookie_secure="False"
        if [[ -n "$DOMAIN" ]] && [[ "$ENABLE_SSL" == true ]]; then
            ssl_redirect="True"
            cookie_secure="True"
        fi
        
        log_step "Updating security settings in environment file..."
        sed_inplace "s/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=${ssl_redirect}/" "$env_file"
        sed_inplace "s/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=${cookie_secure}/" "$env_file"
        sed_inplace "s/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=${cookie_secure}/" "$env_file"
        
        # Update domain-specific settings if domain is provided
        if [[ -n "$DOMAIN" ]]; then
            log_step "Updating domain settings in environment file..."
            sed_inplace "s/^DOMAIN=.*/DOMAIN=${DOMAIN}/" "$env_file"
            sed_inplace "s/^ENABLE_SSL=.*/ENABLE_SSL=${ENABLE_SSL}/" "$env_file"
            
            # Update ALLOWED_HOSTS
            local allowed_hosts="$DOMAIN,www.$DOMAIN,localhost,127.0.0.1"
            sed_inplace "s/^DJANGO_ALLOWED_HOSTS=.*/DJANGO_ALLOWED_HOSTS=${allowed_hosts}/" "$env_file"
        else
            # When no domain, add public IP to allowed hosts
            local public_ip=$(get_public_ip || echo "")
            if [[ -n "$public_ip" ]]; then
                local allowed_hosts="$public_ip,localhost,127.0.0.1"
                sed_inplace "s/^DJANGO_ALLOWED_HOSTS=.*/DJANGO_ALLOWED_HOSTS=${allowed_hosts}/" "$env_file"
                log_info "Added public IP ($public_ip) to ALLOWED_HOSTS"
            fi
        fi
    fi
    
    # Load environment variables safely (no shell execution)
    # Only export KEY=VALUE lines, skip comments and empty lines
    log_step "Loading environment variables..."
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Trim whitespace from key
        key=$(echo "$key" | tr -d '[:space:]')
        # Skip if key is empty or contains invalid characters
        [[ -z "$key" || ! "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] && continue
        # Export the variable (value may contain = signs)
        export "$key=$value"
    done < "$env_file"
    
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

    if [[ "$NON_INTERACTIVE" == true ]]; then
        log_warning "Resetting environment in NON-INTERACTIVE mode."
    else
        read -p "Are you absolutely sure you want to delete ALL data? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Reset cancelled by user."
            return 0
        fi
    fi

    # CRITICAL: Change to PROJECT_ROOT for correct docker-compose context
    cd "$PROJECT_ROOT"
    
    log_step "Stopping and removing all services and volumes..."
    ${DC} -f provisioning/docker-compose.yml down -v --remove-orphans
    
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
    
    ${DC} -f provisioning/docker-compose.yml build --no-cache
    
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
    ${DC} -f provisioning/docker-compose.yml up -d db redis
    
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
    ${DC} -f provisioning/docker-compose.yml run --rm app python manage.py migrate --noinput
    
    log_step "Collecting static files..."
    ${DC} -f provisioning/docker-compose.yml run --rm app python manage.py collectstatic --noinput
    
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
    ${DC} -f provisioning/docker-compose.yml up -d app
    
    # Wait for application to be ready
    log_step "Waiting for application to be ready..."
    local max_attempts=30
    local attempt=0
    local app_port="${PORT:-8000}"
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Use Docker's built-in health check status (more reliable than curl inside container)
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "${APP_CONTAINER_NAME}" 2>/dev/null || echo "unknown")
        if [[ "$health_status" == "healthy" ]]; then
            log_success "Application is ready"
            break
        fi
        # Fallback: check if container is running and listening (try curl first, then wget)
        if docker exec "${APP_CONTAINER_NAME}" sh -c 'curl -sf http://localhost:8000/health/ >/dev/null 2>&1 || wget -q --spider http://localhost:8000/health/ 2>/dev/null' 2>/dev/null; then
            log_success "Application is ready (http check)"
            break
        fi
        attempt=$((attempt + 1))
        log_info "Waiting for application... (attempt $attempt/$max_attempts, health: $health_status)"
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
    ${DC} -f provisioning/docker-compose.yml up -d nginx
    
    # Wait for nginx to start and reload its configuration
    sleep 3
    ${DC} -f provisioning/docker-compose.yml exec nginx nginx -s reload 2>/dev/null || true
    sleep 2
    
    log_step "Requesting SSL certificate for $DOMAIN..."
    
    # Request certificate using certbot
    # Capture exit code to handle failure gracefully (set -e would otherwise exit)
    local ssl_result=0
    ${DC} -f provisioning/docker-compose.yml run --rm --entrypoint certbot certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" || ssl_result=$?
    
    if [[ $ssl_result -eq 0 ]]; then
        log_success "SSL certificate obtained successfully"
        
        # Generate ssl.conf from template with atomic write and backup
        log_step "Generating SSL configuration for $DOMAIN..."
        export DOMAIN
        
        local ssl_conf="${SCRIPT_DIR}/nginx/conf.d/ssl.conf"
        local ssl_conf_tmp="${ssl_conf}.tmp.$$"
        local ssl_conf_backup="${ssl_conf}.backup"
        
        # Generate to temp file first (atomic write pattern)
        if ! envsubst '${DOMAIN}' < "${SCRIPT_DIR}/nginx/conf.d/ssl.conf.template" > "$ssl_conf_tmp"; then
            log_error "Failed to generate SSL configuration"
            rm -f "$ssl_conf_tmp"
            return 1
        fi
        
        # Backup existing config if present
        if [[ -f "$ssl_conf" ]]; then
            cp "$ssl_conf" "$ssl_conf_backup"
            log_info "Backed up existing SSL config to $ssl_conf_backup"
        fi
        
        # Move temp file to final location (atomic on same filesystem)
        mv "$ssl_conf_tmp" "$ssl_conf"
        
        # Test nginx configuration before reloading
        log_step "Testing Nginx configuration..."
        if ${DC} -f provisioning/docker-compose.yml exec nginx nginx -t 2>&1; then
            log_step "Reloading Nginx with SSL configuration..."
            ${DC} -f provisioning/docker-compose.yml restart nginx
            log_success "SSL configured successfully for $DOMAIN"
            # Remove backup on success
            rm -f "$ssl_conf_backup"
        else
            log_error "Nginx configuration test failed. Rolling back SSL config..."
            if [[ -f "$ssl_conf_backup" ]]; then
                mv "$ssl_conf_backup" "$ssl_conf"
                log_warning "Restored previous SSL configuration."
            else
                rm -f "$ssl_conf"
                log_warning "SSL configuration removed. Using HTTP only."
            fi
        fi
    else
        log_error "Failed to obtain SSL certificate (exit code: $ssl_result)"
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
    
    # Create renewal script with proper error handling and nginx config test
    # Create renewal script with proper error handling and nginx config test
    # We use unquoted heredoc (EOF) so ${DC} is expanded, but we must escape others
    cat > "${SCRIPT_DIR}/renew-ssl.sh" << EOF
#!/bin/bash
set -e
cd "\$(dirname "\$0")/.."
echo "[\$(date)] Starting SSL renewal..."
${DC} -f provisioning/docker-compose.yml run --rm certbot renew
# Test nginx config before reloading
if ${DC} -f provisioning/docker-compose.yml exec nginx nginx -t 2>&1; then
    ${DC} -f provisioning/docker-compose.yml exec nginx nginx -s reload
    echo "[\$(date)] SSL renewal completed successfully"
else
    echo "[\$(date)] ERROR: Nginx config test failed after renewal"
    exit 1
fi
EOF
    
    chmod +x "${SCRIPT_DIR}/renew-ssl.sh"
    
    # Add cron job for automatic renewal (runs twice daily)
    # Use a unique marker comment to identify our cron entry for safe idempotent updates
    local cron_marker="# ifinsure-ssl-renewal"
    local cron_entry="0 0,12 * * * ${SCRIPT_DIR}/renew-ssl.sh >> ${PROJECT_ROOT}/logs/ssl-renewal.log 2>&1 ${cron_marker}"
    
    # Check if crontab command exists
    if ! check_command crontab; then
        log_warning "crontab not available. Please set up SSL renewal manually."
        log_info "Add this to your cron: $cron_entry"
        return 0
    fi
    
    # Remove only our specific entry (identified by marker), then add the new one
    local current_cron
    current_cron=$(crontab -l 2>/dev/null || true)
    
    # Check if entry already exists with same path
    if echo "$current_cron" | grep -qF "$cron_marker"; then
        log_info "SSL renewal cron job already configured, updating..."
        # Remove old entry with our marker
        current_cron=$(echo "$current_cron" | grep -vF "$cron_marker")
    fi
    
    # Add new entry
    echo -e "${current_cron}\n${cron_entry}" | crontab -
    
    log_success "SSL renewal configured (cron job added)"
}

start_nginx() {
    log_header "Starting Nginx"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would start Nginx"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    ${DC} -f provisioning/docker-compose.yml up -d nginx
    
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
    
    if [[ "$NON_INTERACTIVE" == true ]]; then
        log_info "Skipping superuser creation (non-interactive mode)."
        log_info "Create one later with: ${DC} -f provisioning/docker-compose.yml run --rm app python manage.py createsuperuser"
        return 0
    fi

    read -p "Would you like to create a superuser now? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${DC} -f provisioning/docker-compose.yml run --rm app python manage.py createsuperuser
    else
        log_info "Skipping superuser creation. Run later with:"
        log_info "  ${DC} -f provisioning/docker-compose.yml run --rm app python manage.py createsuperuser"
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
        # Try to get public IP with timeout to avoid hanging
        local public_ip=$(get_public_ip || echo "localhost")
        app_url="http://${public_ip}:${PORT:-8000}"
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
    echo -e "${GREEN}║${NC}  View logs:        ${DC} -f provisioning/docker-compose.yml logs -f${NC}"
    echo -e "${GREEN}║${NC}  Stop:             ${DC} -f provisioning/docker-compose.yml down${NC}"
    echo -e "${GREEN}║${NC}  Restart:          ${DC} -f provisioning/docker-compose.yml restart${NC}"
    echo -e "${GREEN}║${NC}  Shell:            ${DC} -f provisioning/docker-compose.yml exec app bash${NC}"
    echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log_info "Deployment log saved to: $LOG_FILE"
}

# =============================================================================
# CLEANUP
# =============================================================================

# Track temp files for cleanup
TEMP_FILES=()

register_temp_file() {
    TEMP_FILES+=("$1")
}

cleanup_temp_files() {
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
}

cleanup_on_error() {
    local exit_code=$?
    log_error "Deployment failed! (exit code: $exit_code)"
    
    # Clean up any temp files we created
    cleanup_temp_files
    
    # Don't remove containers on error - leave for debugging
    log_info "Containers left running for debugging."
    log_info "To manually clean up: ${DC} -f provisioning/docker-compose.yml down"
    log_info "Check logs: ${DC} -f provisioning/docker-compose.yml logs --tail 50"
    
    exit 1
}

cleanup_on_exit() {
    # Always clean up temp files on exit
    cleanup_temp_files
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
            --allow-install)
                ALLOW_INSTALL=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
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
    if ! validate_domain "$DOMAIN"; then
        exit 1
    fi
    if ! validate_email "$EMAIL"; then
        exit 1
    fi
    if ! validate_port "$PORT"; then
        exit 1
    fi
    
    if [[ -n "$DOMAIN" ]] && [[ "$ENABLE_SSL" == true ]] && [[ -z "$EMAIL" ]]; then
        log_error "Email (-e/--email) is required when using SSL with a domain."
        log_info "Either provide an email or use --no-ssl to disable SSL."
        exit 1
    fi
    
    # If no domain is provided, disable SSL
    if [[ -z "$DOMAIN" ]]; then
        ENABLE_SSL=false
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set up error and exit handling
    trap cleanup_on_error ERR
    trap cleanup_on_exit EXIT
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Print banner
    print_banner
    
    # Display configuration
    log_info "Configuration:"
    log_info "  Domain:          ${DOMAIN:-<none>}"
    log_info "  SSL:             ${ENABLE_SSL}"
    log_info "  Port:            ${PORT:-auto}"
    log_info "  Branch:          ${BRANCH} (not yet implemented)"
    log_info "  Dry Run:         ${DRY_RUN}"
    log_info "  Allow Install:   ${ALLOW_INSTALL}"
    
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
