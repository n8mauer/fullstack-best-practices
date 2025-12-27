# Best Practices Guide

This document explains the best practices implemented in this example application.

## Table of Contents

1. [Backend Best Practices](#backend-best-practices)
2. [Frontend Best Practices](#frontend-best-practices)
3. [DevOps Best Practices](#devops-best-practices)

## Backend Best Practices

### 1. Project Structure

**Why it matters:** A well-organized project structure improves maintainability and scalability.

**Implementation:**
- Use Django apps for modular functionality
- Each app should have a single responsibility
- Shared code goes in `core/`
- Configuration is environment-based

```python
# Good: Modular app structure
apps/
├── users/          # User management
├── products/       # Product catalog
└── orders/         # Order processing

# Bad: Monolithic structure with everything in one app
```

### 2. Settings Management

**Why it matters:** Different environments need different configurations without code changes.

**Implementation:**
- Base settings with environment-specific overrides
- Use environment variables for secrets
- Never commit secrets to version control

```python
# settings/base.py - Common settings
# settings/development.py - Dev overrides
# settings/production.py - Prod overrides

# Use python-decouple or django-environ
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
```

### 3. Database Best Practices

**Why it matters:** Proper database design ensures performance and data integrity.

**Key practices:**
- Add database indexes on frequently queried fields
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries
- Implement soft deletes for audit trails
- Use database constraints

```python
class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.ForeignKey('Category', on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-created_at']),
        ]

# Good: Optimize queries
products = Product.objects.select_related('category').filter(is_active=True)

# Bad: N+1 query problem
products = Product.objects.filter(is_active=True)
for product in products:
    print(product.category.name)  # Additional query for each product
```

### 4. API Design with Django REST Framework

**Why it matters:** Well-designed APIs are easier to use and maintain.

**Key practices:**
- Use viewsets for standard CRUD operations
- Implement proper serializer validation
- Add pagination to list endpoints
- Version your API
- Use throttling/rate limiting

```python
# serializers.py
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category', 'category_name', 'price']
        read_only_fields = ['id', 'created_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value

# views.py
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'sku']
    ordering_fields = ['price', 'created_at']
    throttle_classes = [UserRateThrottle]
```

### 5. Caching with Redis

**Why it matters:** Reduces database load and improves response times.

**Key practices:**
- Cache expensive queries
- Set appropriate TTLs
- Implement cache invalidation
- Use cache versioning

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache expensive query
def get_popular_products():
    cache_key = 'popular_products_v1'
    products = cache.get(cache_key)

    if products is None:
        products = Product.objects.filter(
            is_active=True
        ).order_by('-view_count')[:10]
        cache.set(cache_key, products, timeout=3600)  # 1 hour

    return products

# Invalidate cache on update
def update_product(product_id, data):
    product = Product.objects.get(id=product_id)
    product.name = data['name']
    product.save()

    # Invalidate related caches
    cache.delete('popular_products_v1')
    cache.delete(f'product_{product_id}')

# Cache view responses
@cache_page(60 * 15)  # 15 minutes
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products.html', {'products': products})
```

### 6. Celery Task Management

**Why it matters:** Offload long-running tasks to background workers.

**Key practices:**
- Keep tasks idempotent
- Set timeouts
- Implement retry logic
- Use task routing for prioritization
- Monitor task execution

```python
# tasks.py
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    soft_time_limit=300,  # 5 minutes
)
def process_order(self, order_id):
    """
    Process an order asynchronously.

    This task is idempotent - running it multiple times with the
    same order_id will not cause duplicate processing.
    """
    try:
        order = Order.objects.get(id=order_id)

        # Check if already processed (idempotency)
        if order.status == 'processed':
            logger.info(f"Order {order_id} already processed")
            return

        # Process the order
        order.process()
        order.status = 'processed'
        order.save()

        # Send notification
        send_order_confirmation.delay(order_id)

    except SoftTimeLimitExceeded:
        logger.error(f"Order {order_id} processing timed out")
        raise
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise

@shared_task
def send_order_confirmation(order_id):
    """Send order confirmation email."""
    order = Order.objects.get(id=order_id)
    # Send email logic
    pass
```

### 7. AmazonMQ Integration

**Why it matters:** Reliable message queuing for distributed systems.

**Key practices:**
- Use AmazonMQ for production message broker
- Configure failover for high availability
- Monitor queue depths
- Use dead letter queues

```python
# celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('myapp')
app.config_from_object('django.conf:settings', namespace='CELERY')

# AmazonMQ Configuration
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL'),
    # Example: 'amqps://username:password@b-xxxxx.mq.us-east-1.amazonaws.com:5671'

    broker_use_ssl={
        'ssl_cert_reqs': 'CERT_REQUIRED',
    },

    # Failover configuration
    broker_failover_strategy='round-robin',

    # Result backend
    result_backend='redis://redis:6379/1',

    # Task routing
    task_routes={
        'apps.orders.tasks.process_order': {'queue': 'high_priority'},
        'apps.notifications.tasks.*': {'queue': 'low_priority'},
    },

    # Dead letter queue
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

app.autodiscover_tasks()
```

### 8. Security Best Practices

**Why it matters:** Protect user data and prevent attacks.

**Key practices:**
- Use HTTPS only
- Implement CORS properly
- Use JWT for authentication
- Rate limit API endpoints
- Validate all inputs
- Keep dependencies updated

```python
# settings/production.py
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CORS
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
]
CORS_ALLOW_CREDENTIALS = True

# Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

## Frontend Best Practices

### 1. NextJS Project Structure

**Why it matters:** Organization improves maintainability and team collaboration.

```
src/
├── app/                    # App router pages
│   ├── (auth)/            # Route groups
│   ├── api/               # API routes
│   └── layout.tsx         # Root layout
├── components/            # Reusable components
│   ├── ui/               # Base UI components
│   └── features/         # Feature-specific components
├── lib/                  # Utilities
│   ├── api.ts           # API client
│   ├── utils.ts         # Helper functions
│   └── constants.ts     # Constants
└── types/               # TypeScript definitions
```

### 2. Server vs Client Components

**Why it matters:** Optimize bundle size and performance.

```typescript
// Server Component (default) - Good for data fetching
async function ProductList() {
  const products = await fetch('http://api/products').then(r => r.json());

  return (
    <div>
      {products.map(product => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}

// Client Component - Only when needed for interactivity
'use client';

import { useState } from 'react';

function ProductCard({ product }) {
  const [isLiked, setIsLiked] = useState(false);

  return (
    <div>
      <h3>{product.name}</h3>
      <button onClick={() => setIsLiked(!isLiked)}>
        {isLiked ? '❤️' : '🤍'}
      </button>
    </div>
  );
}
```

### 3. API Client Abstraction

**Why it matters:** Centralize API logic and error handling.

```typescript
// lib/api.ts
class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new APIError(response.status, await response.json());
    }

    return response.json();
  }

  get<T>(endpoint: string) {
    return this.request<T>(endpoint);
  }

  post<T>(endpoint: string, data: any) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const api = new APIClient(process.env.NEXT_PUBLIC_API_URL!);
```

### 4. Error Handling

**Why it matters:** Provide good user experience when things go wrong.

```typescript
// app/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}

// components/ErrorBoundary.tsx
'use client';

import { Component, ReactNode } from 'react';

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <div>Error occurred</div>;
    }

    return this.props.children;
  }
}
```

### 5. Type Safety

**Why it matters:** Catch errors at compile time and improve IDE support.

```typescript
// types/index.ts
export interface Product {
  id: number;
  name: string;
  sku: string;
  price: number;
  category: Category;
}

export interface Category {
  id: number;
  name: string;
}

// Use types everywhere
async function getProduct(id: number): Promise<Product> {
  return api.get<Product>(`/products/${id}`);
}
```

## DevOps Best Practices

### 1. Environment Variables

Never hardcode configuration. Use environment variables.

```bash
# .env.example
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 2. Docker for Development

**Why it matters:** Consistent development environment across team.

```dockerfile
# Use multi-stage builds
# Separate development and production configurations
# Use .dockerignore to reduce context size
```

### 3. Health Checks

**Why it matters:** Monitor service health.

```python
# urls.py
path('health/', health_check, name='health'),

# views.py
def health_check(request):
    # Check database
    try:
        Product.objects.first()
        db_status = 'ok'
    except:
        db_status = 'error'

    # Check Redis
    try:
        cache.set('health_check', 'ok', 10)
        redis_status = 'ok'
    except:
        redis_status = 'error'

    return JsonResponse({
        'status': 'healthy' if db_status == 'ok' and redis_status == 'ok' else 'unhealthy',
        'database': db_status,
        'redis': redis_status,
    })
```

### 4. Logging

**Why it matters:** Debug issues in production.

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

### 5. Testing

**Why it matters:** Prevent regressions and ensure code quality.

```python
# tests/test_models.py
import pytest
from apps.products.models import Product

@pytest.mark.django_db
def test_product_creation():
    product = Product.objects.create(
        name='Test Product',
        sku='TEST-001',
        price=19.99
    )
    assert product.name == 'Test Product'
    assert str(product) == 'Test Product'
```

## Conclusion

These best practices are implemented throughout this example application. Review the code to see them in action, and adapt them to your specific needs.
