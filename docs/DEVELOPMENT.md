# Development Guide

This guide covers the development workflow for this full-stack application.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)
- Git

## Quick Start with Docker

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd fullstack-best-practices

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Django Admin: http://localhost:8000/admin
# RabbitMQ Management: http://localhost:15672 (guest/guest)
# Flower (Celery): http://localhost:5555
```

## Local Development (Without Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Set up environment
cp .env.example .env
# Edit .env with your local configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local with your configuration

# Run development server
npm run dev
```

### Running Celery Locally

You need to run three separate processes:

```bash
# Terminal 1: Celery worker
celery -A config worker -l info

# Terminal 2: Celery beat (for periodic tasks)
celery -A config beat -l info

# Terminal 3: Flower (monitoring)
celery -A config flower
```

## Development Workflow

### 1. Creating a New Django App

```bash
# Navigate to backend directory
cd backend

# Create new app
python manage.py startapp apps/myapp

# Add to INSTALLED_APPS in settings/base.py
```

### 2. Database Migrations

```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# View migration SQL (optional)
python manage.py sqlmigrate app_name migration_name

# With Docker
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

### 3. Running Tests

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific test file
pytest apps/products/tests.py

# With Docker
docker-compose exec backend pytest

# Frontend tests
cd frontend
npm test
npm run test:coverage
```

### 4. Code Quality

```bash
# Backend linting
cd backend

# Black (formatting)
black .

# Flake8 (linting)
flake8

# isort (import sorting)
isort .

# Type checking
mypy apps

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

### 5. Working with Celery Tasks

```python
# Create a task in apps/myapp/tasks.py
from celery import shared_task

@shared_task
def my_task(arg):
    # Task logic
    return result

# Call the task
from apps.myapp.tasks import my_task

# Async execution
my_task.delay(arg)

# Get result
result = my_task.delay(arg)
result.get(timeout=10)
```

### 6. Working with Cache

```python
from django.core.cache import cache

# Set cache
cache.set('key', 'value', timeout=3600)

# Get cache
value = cache.get('key')

# Delete cache
cache.delete('key')

# Clear all cache
cache.clear()

# With Docker - access Redis CLI
docker-compose exec redis redis-cli
```

## API Development

### Testing API Endpoints

```bash
# Using curl
curl http://localhost:8000/api/v1/products/

# With authentication
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/orders/

# Using httpie (recommended)
http GET localhost:8000/api/v1/products/

# Using Postman or Insomnia
# Import the API endpoints
```

### API Documentation

```python
# Add to installed apps for automatic API docs
INSTALLED_APPS += [
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Generate schema
python manage.py spectacular --file schema.yml

# Access Swagger UI
# /api/schema/swagger-ui/
```

## Database Management

### Accessing Database

```bash
# With Docker
docker-compose exec postgres psql -U postgres -d myapp

# Local PostgreSQL
psql -U postgres -d myapp
```

### Common Database Tasks

```sql
-- List tables
\dt

-- Describe table
\d tablename

-- Show all databases
\l

-- Connect to database
\c database_name

-- Show all users
\du
```

### Database Backup and Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres myapp > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres myapp < backup.sql
```

## Debugging

### Backend Debugging

```python
# Use Django Debug Toolbar (already configured in development)
# Access at http://localhost:8000

# IPython for debugging
import ipdb; ipdb.set_trace()

# Logging
import logging
logger = logging.getLogger(__name__)
logger.debug('Debug message')
logger.info('Info message')
logger.error('Error message')
```

### Frontend Debugging

```typescript
// React Developer Tools browser extension
// Console logging
console.log('Debug:', data);

// Debugging with browser
debugger;

// React Query Devtools (already configured)
// Appears at bottom of screen in development
```

## Common Issues and Solutions

### Issue: Port already in use

```bash
# Find process using port
lsof -i :8000
# Or on Windows
netstat -ano | findstr :8000

# Stop Docker containers
docker-compose down

# Remove all containers
docker-compose down -v
```

### Issue: Database migrations conflict

```bash
# Reset migrations (development only!)
python manage.py migrate app_name zero
rm apps/app_name/migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

### Issue: Celery tasks not running

```bash
# Check Celery worker is running
docker-compose ps

# Check RabbitMQ connection
docker-compose exec rabbitmq rabbitmqctl list_queues

# Restart Celery worker
docker-compose restart celery_worker
```

### Issue: Frontend can't connect to backend

```bash
# Check backend is running
curl http://localhost:8000/health/

# Check CORS settings in backend/config/settings/development.py
# Ensure frontend URL is in CORS_ALLOWED_ORIGINS

# Check network in docker-compose
docker-compose exec frontend ping backend
```

## Best Practices

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push to remote
git push origin feature/my-feature

# Create pull request
```

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No console.log or print statements
- [ ] Environment variables used for secrets
- [ ] Migrations included if needed
- [ ] No hardcoded URLs or values

## Performance Monitoring

### Backend

```python
# Django Debug Toolbar shows:
# - SQL queries
# - Cache hits/misses
# - Template rendering time
# - Signal handlers

# Access at http://localhost:8000/__debug__/
```

### Frontend

```typescript
// React Query Devtools shows:
// - Query status
// - Cache data
// - Refetch behavior

// Use Chrome DevTools:
// - Network tab for API calls
// - Performance tab for rendering
// - React DevTools for component tree
```

## Deployment Preparation

Before deploying to production:

1. Set `DEBUG=False`
2. Update `SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Set up production database
5. Configure AmazonMQ instead of RabbitMQ
6. Set up email service
7. Configure static file storage (S3)
8. Set up Sentry for error tracking
9. Enable SSL/HTTPS
10. Run security checks:
    ```bash
    python manage.py check --deploy
    ```

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Celery Documentation](https://docs.celeryproject.org/)
- [React Query Documentation](https://tanstack.com/query/latest)
