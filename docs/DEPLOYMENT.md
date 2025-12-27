# Deployment Guide

This guide covers deploying the application to production.

## Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Security audit completed
- [ ] Environment variables configured
- [ ] Database backups configured
- [ ] Monitoring and logging set up
- [ ] SSL certificates obtained
- [ ] Domain names configured
- [ ] CDN configured for static files
- [ ] Error tracking (Sentry) configured

## Environment Variables

### Backend Production Variables

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com

# Database
DB_NAME=production_db
DB_USER=prod_user
DB_PASSWORD=<secure-password>
DB_HOST=<rds-endpoint>
DB_PORT=5432

# Redis (ElastiCache)
REDIS_URL=redis://<elasticache-endpoint>:6379/0

# Celery (AmazonMQ)
CELERY_BROKER_URL=amqps://user:pass@<amazonmq-endpoint>:5671
CELERY_RESULT_BACKEND=redis://<elasticache-endpoint>:6379/1

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>

# Sentry
SENTRY_DSN=<your-sentry-dsn>

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

### Frontend Production Variables

```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## AWS Deployment

### Architecture

```
                    ┌─────────────┐
                    │   Route 53  │
                    │   (DNS)     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ CloudFront  │
                    │   (CDN)     │
                    └──────┬──────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
      ┌─────▼─────┐               ┌──────▼──────┐
      │  S3       │               │  ALB        │
      │  (Static) │               │  (Load      │
      └───────────┘               │  Balancer)  │
                                  └──────┬──────┘
                                         │
                                  ┌──────┴──────┐
                                  │   ECS       │
                                  │   (Backend) │
                                  └──────┬──────┘
                                         │
              ┌──────────────────────────┼──────────────────────┐
              │                          │                      │
      ┌───────▼────────┐       ┌────────▼────────┐    ┌───────▼────────┐
      │  RDS           │       │  ElastiCache    │    │  AmazonMQ      │
      │  (PostgreSQL)  │       │  (Redis)        │    │  (RabbitMQ)    │
      └────────────────┘       └─────────────────┘    └────────────────┘
```

### Step 1: Database Setup (RDS)

```bash
# Create PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier myapp-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username postgres \
    --master-user-password <password> \
    --allocated-storage 20

# Run migrations
python manage.py migrate
```

### Step 2: Redis Setup (ElastiCache)

```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id myapp-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1
```

### Step 3: Message Queue (AmazonMQ)

```bash
# Create RabbitMQ broker
aws mq create-broker \
    --broker-name myapp-mq \
    --engine-type RABBITMQ \
    --engine-version 3.9.16 \
    --host-instance-type mq.t3.micro \
    --users Username=admin,Password=<password>
```

### Step 4: Container Registry (ECR)

```bash
# Create repositories
aws ecr create-repository --repository-name myapp-backend
aws ecr create-repository --repository-name myapp-frontend

# Build and push images
docker build -t myapp-backend ./backend
docker tag myapp-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/myapp-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/myapp-backend:latest
```

### Step 5: ECS Deployment

```yaml
# task-definition.json
{
  "family": "myapp-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/myapp-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DJANGO_SETTINGS_MODULE",
          "value": "config.settings.production"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ]
    }
  ]
}
```

### Step 6: Frontend Deployment (Vercel/Netlify)

```bash
# Vercel
vercel --prod

# Or Netlify
netlify deploy --prod

# Or S3 + CloudFront
npm run build
aws s3 sync out/ s3://myapp-frontend/
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

## Alternative: Docker Compose Production

For smaller deployments on a single server:

```bash
# On production server
git clone <repository>
cd fullstack-best-practices

# Copy and configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files with production values

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput
```

## SSL/TLS Configuration

### Using Let's Encrypt with Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring and Logging

### Sentry Setup

```python
# Already configured in settings/production.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    traces_sample_rate=0.1,
)
```

### CloudWatch Logs

```python
# Add to LOGGING configuration
'handlers': {
    'watchtower': {
        'class': 'watchtower.CloudWatchLogHandler',
        'log_group': 'myapp-backend',
        'stream_name': 'django',
    },
}
```

## Database Backups

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

docker-compose exec -T postgres pg_dump -U postgres myapp > $BACKUP_FILE
gzip $BACKUP_FILE

# Upload to S3
aws s3 cp $BACKUP_FILE.gz s3://myapp-backups/

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

## Health Checks

```python
# Already implemented at /health/
# Set up monitoring to check this endpoint regularly

# CloudWatch Alarm
aws cloudwatch put-metric-alarm \
    --alarm-name myapp-health-check \
    --alarm-description "Alert when health check fails" \
    --metric-name HealthCheckStatus \
    --namespace AWS/Route53 \
    --statistic Minimum \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 1 \
    --comparison-operator LessThanThreshold
```

## Scaling

### Horizontal Scaling (ECS)

```bash
# Update service desired count
aws ecs update-service \
    --cluster myapp-cluster \
    --service myapp-backend \
    --desired-count 3
```

### Auto Scaling

```bash
# Configure auto-scaling
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/myapp-cluster/myapp-backend \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10
```

## Troubleshooting

### Check Application Logs

```bash
# ECS logs
aws logs tail /ecs/myapp-backend --follow

# Docker logs
docker-compose logs -f backend
```

### Database Connection Issues

```bash
# Test database connection
psql -h <rds-endpoint> -U postgres -d myapp

# Check security groups
aws ec2 describe-security-groups --group-ids <sg-id>
```

### Celery Not Processing Tasks

```bash
# Check Celery worker logs
docker-compose logs celery_worker

# Check AmazonMQ broker
aws mq describe-broker --broker-id <broker-id>

# Purge tasks if needed
celery -A config purge
```

## Rollback Strategy

```bash
# ECS rollback to previous task definition
aws ecs update-service \
    --cluster myapp-cluster \
    --service myapp-backend \
    --task-definition myapp-backend:previous-version

# Database rollback
python manage.py migrate app_name migration_name
```

## Security Hardening

1. Enable Django's security middleware
2. Use security headers
3. Enable CSRF protection
4. Use parameterized queries
5. Implement rate limiting
6. Regular security audits
7. Keep dependencies updated
8. Use secrets management (AWS Secrets Manager)
9. Enable WAF (Web Application Firewall)
10. Regular penetration testing

## Cost Optimization

1. Use reserved instances for predictable workloads
2. Enable auto-scaling
3. Use CloudFront CDN
4. Optimize database queries
5. Implement caching strategy
6. Use spot instances for Celery workers
7. Regular cost reviews
