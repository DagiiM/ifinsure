# ifinsure - Insurance Agency Management System

A professional, minimal-dependency Django application for managing insurance operations. Built with a focus on clean code, business logic, and a sleek user interface.

## 🚀 Features

### Core Functionality
- **User Management** - Custom user model with role-based access (Customer, Agent, Staff, Admin)
- **Policy Management** - Products, applications, and active policies with workflow
- **Claims Processing** - Full claims lifecycle from submission to payment
- **Billing & Payments** - Invoice generation and payment tracking
- **Audit Logging** - Comprehensive activity tracking for compliance

### User Roles
| Role | Capabilities |
|------|-------------|
| **Customer** | View policies, submit claims, pay invoices |
| **Agent** | Review applications, manage client policies |
| **Staff** | Process claims, manage billing |
| **Admin** | Full system access, integrations, reports |

## 📋 Requirements

- Python 3.11+
- Django 5.1+
- Container Runtime (Docker & Docker Compose) - *Recommended for production*

## ⚡ Quick Setup (Recommended)

The easiest way to get started is using our one-step deployment script.

### Local Development / Quick Start
```bash
# Make the script executable
chmod +x provisioning/deploy.sh

# Run the deployment script
./provisioning/deploy.sh
```

### Production Deployment (with SSL)
```bash
./provisioning/deploy.sh --domain yourdomain.com --email admin@yourdomain.com
```

### Fresh Re-installation (Full Reset)
If you need to wipe existing data and start completely fresh:
```bash
./provisioning/deploy.sh --domain yourdomain.com --email admin@yourdomain.com --reset
```

This will automatically:
- Check and install dependencies (Docker, etc.)
- Set up a production-ready PostgreSQL & Redis environment
- Obtain and configure SSL via Let's Encrypt
- Handle database migrations and static files
- Start the application with Gunicorn behind Nginx

---

## 🛠️ Manual Installation (Development)

If you prefer to run the application locally without Docker:

### 1. Clone the repository
```bash
git clone <repository-url>
cd ifinsure
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
# Development
pip install -r requirements/development.txt

# Production
pip install -r requirements/production.txt
```

### 4. Configure environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create superuser
```bash
python manage.py createsuperuser
```

### 7. Run development server
```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/

## 📁 Project Structure

```
ifinsure/
├── apps/
│   ├── core/           # Base models, utilities, mixins
│   ├── accounts/       # User authentication & profiles
│   ├── policies/       # Insurance products & policies
│   ├── claims/         # Claims management
│   ├── billing/        # Invoicing & payments
│   ├── dashboard/      # Role-based dashboards
│   └── integrations/   # Third-party integrations (Phase 2)
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── static/
│   ├── css/
│   │   ├── variables.css
│   │   ├── base.css
│   │   └── components.css
│   └── js/
│       └── main.js
├── templates/
│   ├── accounts/
│   ├── policies/
│   ├── claims/
│   ├── billing/
│   ├── dashboard/
│   ├── integrations/
│   ├── includes/
│   ├── errors/
│   └── base.html
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── manage.py
└── README.md
```

## 🎨 Design System

The application uses a custom CSS design system with:
- CSS custom properties for theming
- Responsive layouts using CSS Grid and Flexbox
- Component-based styling (buttons, cards, forms, tables)
- Minimal JavaScript for interactions

### Color Palette
- **Primary**: #2563eb (Blue)
- **Success**: #10b981 (Green)
- **Warning**: #f59e0b (Amber)
- **Danger**: #ef4444 (Red)

## 📊 Database Models

### Core Models
- `AuditLog` - Activity tracking

### Accounts Models
- `User` - Custom user with email authentication
- `Profile` - Extended user information

### Policy Models
- `InsuranceProduct` - Available insurance products
- `Policy` - Active insurance policies
- `PolicyApplication` - Policy applications in workflow
- `PolicyDocument` - Attached documents

### Claims Models
- `Claim` - Insurance claims
- `ClaimDocument` - Supporting documents
- `ClaimNote` - Internal/external notes
- `ClaimStatusHistory` - Audit trail

### Billing Models
- `Invoice` - Customer invoices
- `Payment` - Payment records

## 🔐 Security

- CSRF protection enabled
- Secure password hashing
- Session security
- Role-based access control
- Audit logging for sensitive actions

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL
- [ ] Enable HTTPS
- [ ] Set up static file serving
- [ ] Configure email backend
- [ ] Set up logging

### Docker Deployment (Recommended)

The system uses a comprehensive provisioning setup located in the `provisioning/` directory.

```bash
# Deploy locally or for testing
./provisioning/deploy.sh

# Deploy to production with SSL
./provisioning/deploy.sh -d example.com -e admin@example.com
```

Refer to [provisioning/README.md](provisioning/README.md) for detailed documentation on Docker services, SSL management, and production configuration.

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Secret key for Django | Required |
| `DJANGO_DEBUG` | Debug mode | False |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | localhost |
| `DB_NAME` | Database name | ifinsure_db |
| `DB_USER` | Database user | - |
| `DB_PASSWORD` | Database password | - |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |

## 🗺️ Roadmap

See [PRODUCTION_READY_PLAN.md](.agent/artifacts/PRODUCTION_READY_PLAN.md) for detailed implementation plan.

### Phase 1: Foundation (Week 1)
- Environment configuration
- PostgreSQL migration
- Security hardening
- Logging setup

### Phase 2: Integrations (Week 2)
- Integrations Center app
- M-Pesa integration
- SMS gateway
- Email service

### Phase 3: Features (Week 3)
- Email notifications
- PDF generation
- REST API
- Background tasks

### Phase 4: Quality (Week 4)
- Unit tests
- Integration tests
- Security testing
- Performance testing

### Phase 5: Deployment (Week 5)
- Docker configuration
- CI/CD pipeline
- Production deployment

### Phase 6: Monitoring (Week 6)
- Application monitoring
- Health checks
- Backup & recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support, please contact: support@ifinsure.com
