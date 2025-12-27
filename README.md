# Full-Stack Best Practices Example

A comprehensive example application demonstrating best practices for building production-ready applications with Django, PostgreSQL, Redis, Celery, AmazonMQ, and NextJS.

## Tech Stack

**Backend:**
- Python 3.11+ with Django 5.0
- PostgreSQL for primary database
- Redis for caching and Celery broker
- Celery for async task processing
- AmazonMQ (RabbitMQ) for message queuing

**Frontend:**
- NextJS 14 (App Router)
- TypeScript
- TailwindCSS

## Project Structure

```
fullstack-best-practices/
├── backend/              # Django application
│   ├── config/          # Django settings and configuration
│   ├── apps/            # Django apps (modular design)
│   ├── core/            # Shared utilities and base classes
│   ├── manage.py
│   └── requirements/    # Split requirements files
├── frontend/            # NextJS application
│   ├── src/
│   │   ├── app/        # App router pages
│   │   ├── components/ # Reusable components
│   │   ├── lib/        # Utilities and API clients
│   │   └── types/      # TypeScript type definitions
├── docker/              # Docker configurations
├── docs/               # Additional documentation
└── docker-compose.yml  # Local development orchestration
```

## Quick Start

```bash
# Clone and navigate to project
cd fullstack-best-practices

# Start all services with Docker
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Admin: http://localhost:8000/admin
```

## Best Practices Demonstrated

See [BEST_PRACTICES.md](./BEST_PRACTICES.md) for detailed explanations.

### Backend Best Practices

1. **Project Structure**
   - Modular app design
   - Separation of concerns
   - Configuration management with environment variables

2. **Database**
   - Proper model design with indexes
   - Database migrations workflow
   - Connection pooling
   - Read replicas support

3. **API Design**
   - RESTful endpoints with Django REST Framework
   - Proper serialization and validation
   - Pagination and filtering
   - API versioning

4. **Caching Strategy**
   - Redis integration
   - Cache invalidation patterns
   - Query result caching

5. **Async Tasks**
   - Celery task organization
   - Error handling and retries
   - Monitoring and logging
   - Task result backends

6. **Security**
   - CORS configuration
   - Authentication (JWT)
   - Rate limiting
   - Input validation

### Frontend Best Practices

1. **Project Organization**
   - Component composition
   - Custom hooks
   - API client abstraction
   - Type safety with TypeScript

2. **Performance**
   - Server components vs client components
   - Data fetching strategies
   - Image optimization
   - Code splitting

3. **State Management**
   - Server state with React Query
   - Client state management
   - Form handling

4. **Error Handling**
   - Error boundaries
   - API error handling
   - User feedback

## Development Workflow

See [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) for detailed workflow.

## Testing

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend npm test
```

## License

MIT
