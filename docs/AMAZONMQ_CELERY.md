# Amazon MQ with Celery Integration Guide

This guide explains how to configure Celery with AmazonMQ (managed RabbitMQ) for production use, demonstrating best practices for message queuing at scale.

## Overview

**AmazonMQ** is AWS's managed message broker service that supports RabbitMQ and ActiveMQ. For this application, we use RabbitMQ as the message broker for Celery.

### Why AmazonMQ?

- **Managed Service**: AWS handles broker maintenance, patching, and upgrades
- **High Availability**: Multi-AZ deployments with automatic failover
- **Scalability**: Support for multiple broker instances
- **Security**: VPC integration, encryption at rest and in transit
- **Monitoring**: CloudWatch integration for metrics and logs

## Architecture

```
┌─────────────┐
│   Django    │
│  Web App    │
└──────┬──────┘
       │ (publish tasks)
       ▼
┌─────────────────┐
│   AmazonMQ      │
│  (RabbitMQ)     │
│                 │
│  Queues:        │
│  - high_priority│
│  - default      │
│  - low_priority │
│  - reports      │
│  - maintenance  │
└───────┬─────────┘
        │ (consume tasks)
        ▼
┌────────────────────┐
│  Celery Workers    │
│  (multiple workers │
│   per queue)       │
└────────┬───────────┘
         │ (store results)
         ▼
┌────────────────────┐
│  Redis             │
│  (Result Backend)  │
└────────────────────┘
```

## Creating AmazonMQ Broker

### 1. Via AWS Console

1. Navigate to Amazon MQ console
2. Click "Create broker"
3. Configure:
   - **Broker engine**: RabbitMQ
   - **Deployment mode**: Cluster deployment (for HA)
   - **Instance type**: mq.m5.large (or appropriate size)
   - **Broker name**: `myapp-rabbitmq-prod`
   - **Network**: Select VPC and subnets
   - **Public accessibility**: No (use VPN/bastion)

### 2. Via AWS CLI

```bash
aws mq create-broker \
    --broker-name myapp-rabbitmq-prod \
    --engine-type RABBITMQ \
    --engine-version 3.11 \
    --host-instance-type mq.m5.large \
    --deployment-mode CLUSTER_MULTI_AZ \
    --users Username=admin,Password=SecurePassword123! \
    --subnet-ids subnet-xxxxx subnet-yyyyy \
    --security-groups sg-xxxxx \
    --logs '{"General":true}'
```

### 3. Via Terraform

```hcl
resource "aws_mq_broker" "rabbitmq" {
  broker_name = "myapp-rabbitmq-prod"
  engine_type = "RabbitMQ"
  engine_version = "3.11"
  host_instance_type = "mq.m5.large"
  deployment_mode = "CLUSTER_MULTI_AZ"

  user {
    username = "admin"
    password = var.rabbitmq_password
  }

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]

  security_groups = [aws_security_group.rabbitmq.id]

  logs {
    general = true
  }

  encryption_options {
    use_aws_owned_key = true
  }

  tags = {
    Environment = "production"
    Application = "myapp"
  }
}
```

## Celery Configuration for AmazonMQ

### Production Settings

Update `backend/config/celery.py`:

```python
import os
from celery import Celery

app = Celery('myapp')
app.config_from_object('django.conf:settings', namespace='CELERY')

if os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings.production':
    # AmazonMQ connection string
    # Format: amqps://username:password@broker-id.mq.region.amazonaws.com:5671
    broker_url = os.environ.get('CELERY_BROKER_URL')

    app.conf.update(
        # Broker configuration
        broker_url=broker_url,

        # SSL/TLS configuration
        broker_use_ssl={
            'ssl_cert_reqs': 'CERT_REQUIRED',
            'ssl_ca_certs': '/etc/ssl/certs/ca-certificates.crt',
        },

        # Connection pool
        broker_pool_limit=20,
        broker_connection_timeout=30,
        broker_connection_retry=True,
        broker_connection_max_retries=10,
        broker_connection_retry_on_startup=True,

        # Heartbeat (detect dead connections)
        broker_heartbeat=30,
        broker_heartbeat_checkrate=2,

        # Prefetch and acknowledgments
        worker_prefetch_multiplier=4,
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Worker configuration
        worker_max_tasks_per_child=1000,
        worker_disable_rate_limits=False,

        # Result backend (Redis)
        result_backend=os.environ.get('CELERY_RESULT_BACKEND'),
        result_expires=3600,

        # Serialization
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],

        # Timezone
        timezone='UTC',
        enable_utc=True,
    )
```

### Environment Variables

```bash
# Production .env
CELERY_BROKER_URL=amqps://admin:password@b-xxxxx-xxxx.mq.us-east-1.amazonaws.com:5671
CELERY_RESULT_BACKEND=redis://redis-cluster.xxxxx.cache.amazonaws.com:6379/1
```

## Queue Configuration

### Define Queues with Priorities

```python
# config/celery.py

# Define queue routing
app.conf.task_routes = {
    # Critical tasks - highest priority
    'apps.orders.tasks.process_order': {
        'queue': 'high_priority',
        'routing_key': 'high.priority',
        'priority': 10,
    },

    # Standard tasks - normal priority
    'apps.orders.tasks.send_order_confirmation': {
        'queue': 'default',
        'routing_key': 'default',
        'priority': 5,
    },

    # Report generation - dedicated queue
    'apps.reports.tasks.generate_report': {
        'queue': 'reports',
        'routing_key': 'reports.generate',
        'priority': 5,
    },

    # Background tasks - lowest priority
    'apps.reports.tasks.cleanup_expired_reports': {
        'queue': 'maintenance',
        'routing_key': 'maintenance.cleanup',
        'priority': 1,
    },
}

# Define queue priorities
app.conf.task_queue_max_priority = 10
app.conf.task_default_priority = 5
```

## Worker Deployment

### Multiple Workers for Different Queues

```bash
# High priority worker (dedicated, more instances)
celery -A config worker \
    -Q high_priority \
    --concurrency=8 \
    --loglevel=info \
    --max-tasks-per-child=100 \
    -n high_priority_worker@%h

# Default queue worker
celery -A config worker \
    -Q default \
    --concurrency=4 \
    --loglevel=info \
    -n default_worker@%h

# Reports worker (CPU intensive)
celery -A config worker \
    -Q reports \
    --concurrency=2 \
    --loglevel=info \
    --max-tasks-per-child=50 \
    -n reports_worker@%h

# Maintenance worker (low priority)
celery -A config worker \
    -Q maintenance \
    --concurrency=1 \
    --loglevel=info \
    -n maintenance_worker@%h
```

### ECS Task Definition

```json
{
  "family": "celery-worker",
  "containerDefinitions": [
    {
      "name": "high-priority-worker",
      "image": "account.dkr.ecr.region.amazonaws.com/myapp-celery:latest",
      "command": [
        "celery", "-A", "config", "worker",
        "-Q", "high_priority",
        "--concurrency=8",
        "--loglevel=info"
      ],
      "environment": [
        {
          "name": "DJANGO_SETTINGS_MODULE",
          "value": "config.settings.production"
        }
      ],
      "secrets": [
        {
          "name": "CELERY_BROKER_URL",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ]
    }
  ]
}
```

## Monitoring and Management

### RabbitMQ Management Console

Access the RabbitMQ web console:

```bash
# Get broker endpoint from AWS
aws mq describe-broker --broker-id b-xxxxx

# Access via bastion/VPN
# URL: https://b-xxxxx.mq.region.amazonaws.com
# Username/Password: From AWS Secrets Manager
```

### Flower for Celery Monitoring

```bash
# Start Flower
celery -A config flower \
    --port=5555 \
    --broker=$CELERY_BROKER_URL

# Or with authentication
celery -A config flower \
    --port=5555 \
    --basic_auth=admin:securepassword
```

### CloudWatch Metrics

Enable CloudWatch integration:

```python
# settings/production.py

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'region': 'us-east-1',
    'queue_name_prefix': 'myapp-',
}

# Celery CloudWatch exporter
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster',
    'socket_keepalive': True,
}
```

Key metrics to monitor:
- **MessageCount**: Messages in queue
- **ConsumerCount**: Active consumers
- **PublishRate**: Messages published/second
- **AckRate**: Messages acknowledged/second
- **MemoryUsage**: Broker memory utilization
- **ConnectionCount**: Active connections

## Best Practices

### 1. Connection Management

```python
# Use connection pooling
CELERY_BROKER_POOL_LIMIT = 20

# Enable connection retry
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Heartbeat to detect dead connections
CELERY_BROKER_HEARTBEAT = 30
```

### 2. Task Acknowledgment

```python
# Late acknowledgment - only ack after task completes
CELERY_TASK_ACKS_LATE = True

# Reject tasks if worker crashes
CELERY_TASK_REJECT_ON_WORKER_LOST = True
```

### 3. Rate Limiting

```python
@shared_task(rate_limit='100/m')  # 100 tasks per minute
def rate_limited_task():
    pass

# Or per-queue rate limits
CELERY_TASK_DEFAULT_RATE_LIMIT = '1000/m'
```

### 4. Task Retries

```python
@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes
    retry_jitter=True,  # Add randomness
)
def resilient_task():
    pass
```

### 5. Dead Letter Queues

```python
# Configure DLQ for failed tasks
CELERY_TASK_ROUTES = {
    'apps.orders.tasks.process_order': {
        'queue': 'high_priority',
        'routing_key': 'high.priority',
        'exchange': 'high_priority',
        'exchange_type': 'topic',
        'dead_letter_exchange': 'dlx',
        'dead_letter_routing_key': 'high_priority.dlq',
    },
}
```

## Security

### 1. Network Security

```bash
# Security group rules (limit access)
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxx \
    --protocol tcp \
    --port 5671 \
    --source-group sg-yyyyy  # Only allow from worker SG
```

### 2. Encryption

```python
# TLS/SSL encryption in transit
CELERY_BROKER_USE_SSL = {
    'ssl_cert_reqs': 'CERT_REQUIRED',
    'ssl_ca_certs': '/etc/ssl/certs/ca-certificates.crt',
}

# Enable encryption at rest in AmazonMQ
# (Configure via AWS Console or Terraform)
```

### 3. Secrets Management

```python
# Use AWS Secrets Manager
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Load broker credentials
credentials = get_secret('myapp/celery/broker')
CELERY_BROKER_URL = credentials['BROKER_URL']
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
python -c "from celery import Celery; app = Celery(); app.conf.broker_url='amqps://...'; print(app.connection().connect())"

# Check network connectivity
telnet b-xxxxx.mq.region.amazonaws.com 5671

# Verify SSL certificate
openssl s_client -connect b-xxxxx.mq.region.amazonaws.com:5671
```

### Task Not Executing

```bash
# Check active queues
celery -A config inspect active_queues

# Check registered tasks
celery -A config inspect registered

# Purge queue (development only!)
celery -A config purge
```

### Performance Issues

```python
# Increase worker concurrency
celery -A config worker --concurrency=16

# Reduce prefetch multiplier
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Enable task compression
CELERY_TASK_COMPRESSION = 'gzip'
```

## Cost Optimization

1. **Right-size instances**: Start with mq.t3.micro for dev, scale up for prod
2. **Use multi-AZ only for production**: Single-instance for dev/staging
3. **Monitor queue depth**: Scale workers based on queue length
4. **Set task expiration**: Prevent old tasks from accumulating
5. **Use spot instances for workers**: Reduce EC2 costs by 70%

## Example: Reports Feature with AmazonMQ

The reports feature demonstrates AmazonMQ integration:

1. **Task Creation**: User requests report via API
2. **Queue Routing**: Task routed to `reports` queue based on priority
3. **Worker Processing**: Dedicated report worker processes task
4. **Progress Updates**: Real-time progress via Celery task states
5. **Result Storage**: CSV file stored in S3, metadata in PostgreSQL
6. **Notification**: Email sent via separate notification queue

This architecture ensures:
- High-priority orders aren't blocked by long-running reports
- Report workers can be scaled independently
- Failed report generation doesn't affect other systems
- Complete audit trail of all operations

## Additional Resources

- [Amazon MQ Documentation](https://docs.aws.amazon.com/amazon-mq/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [RabbitMQ Best Practices](https://www.rabbitmq.com/best-practices.html)
