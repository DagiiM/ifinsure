# iFinsure Provisioning & Deployment

This directory contains all deployment-related configurations and scripts for the iFinsure application.

## 📁 Directory Structure

```
provisioning/
├── deploy.sh                    # Main one-step deployment script
├── docker-compose.yml           # Docker services orchestration
├── Dockerfile                   # Application container definition
├── init-db.sql                  # PostgreSQL initialization
├── .env.production.template     # Environment template
├── renew-ssl.sh                 # SSL auto-renewal script (auto-generated)
└── nginx/
    ├── nginx.conf               # Main Nginx configuration
    └── conf.d/
        ├── default.conf         # HTTP server configuration
        └── ssl.conf.template    # HTTPS template (used when SSL enabled)
```

## 🚀 Quick Start

### Local Development (No Domain)

```bash
cd ifinsure
chmod +x provisioning/deploy.sh
./provisioning/deploy.sh
```

This will:
- Start PostgreSQL and Redis in Docker
- Run database migrations
- Start the Django application on port 8000

### Production Deployment (With SSL)

```bash
./provisioning/deploy.sh -d your-domain.com -e admin@your-domain.com
```

This will:
- Install Docker if not present
- Start all services (PostgreSQL, Redis, Django, Nginx)
- Automatically obtain SSL certificates from Let's Encrypt
- Configure HTTPS with automatic renewal

### Production Deployment (Without SSL)

```bash
./provisioning/deploy.sh -d your-domain.com --no-ssl
```

## 📋 Command Options

| Option | Description |
|--------|-------------|
| `-d, --domain DOMAIN` | Domain name (enables SSL by default) |
| `-e, --email EMAIL` | Email for Let's Encrypt (required with SSL) |
| `-p, --port PORT` | Custom port (default: 80/443 with domain, 8000 without) |
| `-b, --branch BRANCH` | Git branch to deploy (default: main) |
| `--no-ssl` | Disable SSL even with domain |
| `--skip-backup` | Skip database backup |
| `--skip-migrations` | Skip database migrations |
| `--dry-run` | Preview changes without executing |
| `-h, --help` | Show help message |

## 🔧 Environment Configuration

Before first deployment, review and customize `.env.production`:

```bash
# The script auto-generates this file, but you should review it
nano .env.production
```

### Critical Settings

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Auto-generated, keep it secret |
| `DB_PASSWORD` | Auto-generated database password |
| `EMAIL_HOST_USER` | SMTP username for email sending |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `MPESA_*` | M-Pesa API credentials |
| `STRIPE_*` | Stripe payment credentials |

## 🐳 Docker Commands

### View Logs
```bash
docker compose -f provisioning/docker-compose.yml logs -f
docker compose -f provisioning/docker-compose.yml logs -f app  # App only
```

### Access Django Shell
```bash
docker compose -f provisioning/docker-compose.yml exec app python manage.py shell
```

### Create Superuser
```bash
docker compose -f provisioning/docker-compose.yml exec app python manage.py createsuperuser
```

### Run Migrations
```bash
docker compose -f provisioning/docker-compose.yml exec app python manage.py migrate
```

### Stop Services
```bash
docker compose -f provisioning/docker-compose.yml down
```

### Stop and Remove Volumes (⚠️ Data Loss)
```bash
docker compose -f provisioning/docker-compose.yml down -v
```

## 🔒 SSL Certificate Management

### Manual Certificate Renewal
```bash
docker compose -f provisioning/docker-compose.yml run --rm certbot renew
docker compose -f provisioning/docker-compose.yml exec nginx nginx -s reload
```

### Check Certificate Status
```bash
docker compose -f provisioning/docker-compose.yml run --rm certbot certificates
```

## 📊 Monitoring

### Container Status
```bash
docker compose -f provisioning/docker-compose.yml ps
```

### Resource Usage
```bash
docker stats
```

### Health Checks
```bash
curl http://localhost/health/          # HTTP
curl https://your-domain.com/health/   # HTTPS
```

## 🔄 Backup & Restore

### Manual Backup
```bash
docker exec ifinsure_db pg_dump -U ifinsure ifinsure_db | gzip > backup.sql.gz
```

### Restore from Backup
```bash
gunzip -c backup.sql.gz | docker exec -i ifinsure_db psql -U ifinsure ifinsure_db
```

## ⚠️ Troubleshooting

### Database Connection Issues
```bash
docker compose -f provisioning/docker-compose.yml logs db
docker exec ifinsure_db pg_isready -U ifinsure
```

### Application Won't Start
```bash
docker compose -f provisioning/docker-compose.yml logs app
docker compose -f provisioning/docker-compose.yml exec app python manage.py check
```

### SSL Certificate Issues
```bash
docker compose -f provisioning/docker-compose.yml logs certbot
# Ensure DNS A record points to your server
nslookup your-domain.com
```

### Nginx Issues
```bash
docker compose -f provisioning/docker-compose.yml exec nginx nginx -t
docker compose -f provisioning/docker-compose.yml logs nginx
```

## 🔐 Security Checklist

- [ ] Change auto-generated `DJANGO_SECRET_KEY` for extra security
- [ ] Configure proper `ALLOWED_HOSTS` in `.env.production`
- [ ] Set up proper firewall rules (ports 80, 443 only)
- [ ] Enable SSL for production deployments
- [ ] Configure email credentials for notifications
- [ ] Set up monitoring and alerting
- [ ] Configure regular backups
- [ ] Review and minimize exposed ports

## 📞 Support

For issues with deployment, check the logs in `logs/deploy_*.log` and raise an issue with relevant log excerpts.
