# Reports Feature - Celery & AmazonMQ Integration

This document describes the Reports feature, which demonstrates advanced Celery and AmazonMQ integration patterns.

## Overview

The Reports feature is a comprehensive example of async task processing with:
- **Celery** for distributed task execution
- **AmazonMQ (RabbitMQ)** for reliable message queuing
- **Redis** for result caching and progress tracking
- **Django** for API and business logic
- **PostgreSQL** for data persistence

## Features Demonstrated

### 1. Async Report Generation
Generate reports asynchronously without blocking the web server:
- Sales reports
- Inventory reports
- Customer reports
- Order reports
- Analytics dashboards

### 2. Progress Tracking
Real-time progress updates during report generation:
- Task state monitoring
- Percentage completion
- Status messages
- Error reporting

### 3. Priority Queues
Different priority levels for task execution:
- **Urgent**: Immediate processing
- **High**: Priority over normal tasks
- **Normal**: Standard processing
- **Low**: Background processing

### 4. Scheduled Reports
Automated report generation on schedule:
- Daily, weekly, monthly frequencies
- Custom cron expressions
- Email delivery
- Execution history tracking

### 5. Task Management
Complete task lifecycle management:
- Task creation
- Progress monitoring
- Task cancellation
- Retry failed tasks
- Automatic cleanup

## Architecture

```
User Request
    ↓
Django API (apps/reports/views.py)
    ↓
Create Report Model (apps/reports/models.py)
    ↓
Dispatch Celery Task (apps/reports/tasks.py)
    ↓
AmazonMQ Queue (reports queue)
    ↓
Celery Worker (consumes from queue)
    ↓
Execute Report Generation
    ├─ Query Database
    ├─ Process Data
    ├─ Generate CSV
    └─ Update Progress
    ↓
Save Results (File + Metadata)
    ↓
Send Notification (email/webhook)
    ↓
Return Result to User
```

## API Endpoints

### Report Management

```bash
# List reports
GET /api/v1/reports/
GET /api/v1/reports/?status=completed
GET /api/v1/reports/?report_type=sales

# Get report types
GET /api/v1/reports/types/

# Create report
POST /api/v1/reports/
{
  "report_type": "sales",
  "title": "Q4 Sales Report",
  "priority": "normal",
  "parameters": {
    "start_date": "2024-10-01",
    "end_date": "2024-12-31"
  }
}

# Get report details
GET /api/v1/reports/{id}/

# Get generation progress
GET /api/v1/reports/{id}/progress/

# Download report
GET /api/v1/reports/{id}/download/

# Cancel report
POST /api/v1/reports/{id}/cancel/

# Regenerate report
POST /api/v1/reports/{id}/regenerate/

# Recent reports
GET /api/v1/reports/recent/
```

### Scheduled Reports

```bash
# List schedules
GET /api/v1/reports/schedules/

# Create schedule
POST /api/v1/reports/schedules/
{
  "report_type": "sales",
  "title": "Weekly Sales Report",
  "frequency": "weekly",
  "parameters": {
    "start_date": "{{last_week_start}}",
    "end_date": "{{last_week_end}}"
  },
  "send_email": true,
  "email_recipients": ["manager@example.com"]
}

# Run schedule immediately
POST /api/v1/reports/schedules/{id}/run-now/

# Toggle schedule
POST /api/v1/reports/schedules/{id}/toggle/

# View execution history
GET /api/v1/reports/schedules/{id}/executions/
```

## Usage Examples

### 1. Generate Sales Report

```python
import requests

# Create report
response = requests.post(
    'http://localhost:8000/api/v1/reports/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'report_type': 'sales',
        'title': 'December Sales Report',
        'priority': 'high',
        'parameters': {
            'start_date': '2024-12-01',
            'end_date': '2024-12-31'
        }
    }
)

report_id = response.json()['id']

# Monitor progress
while True:
    progress_response = requests.get(
        f'http://localhost:8000/api/v1/reports/{report_id}/progress/',
        headers={'Authorization': 'Bearer YOUR_TOKEN'}
    )

    progress_data = progress_response.json()
    print(f"Progress: {progress_data['progress']}% - {progress_data['message']}")

    if progress_data['status'] == 'completed':
        break

    time.sleep(2)

# Download report
download_response = requests.get(
    f'http://localhost:8000/api/v1/reports/{report_id}/download/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

with open('sales_report.csv', 'wb') as f:
    f.write(download_response.content)
```

### 2. Schedule Weekly Report

```python
import requests

# Create weekly schedule
response = requests.post(
    'http://localhost:8000/api/v1/reports/schedules/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'report_type': 'sales',
        'title': 'Weekly Sales Summary',
        'frequency': 'weekly',
        'parameters': {
            'start_date': '{{week_start}}',
            'end_date': '{{week_end}}'
        },
        'send_email': True,
        'email_recipients': [
            'sales@example.com',
            'manager@example.com'
        ]
    }
)

schedule_id = response.json()['id']
print(f"Schedule created: {schedule_id}")
```

### 3. Cancel Long-Running Report

```python
import requests

# Cancel report
response = requests.post(
    f'http://localhost:8000/api/v1/reports/{report_id}/cancel/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

print(response.json()['message'])
```

## Celery Task Details

### Task: `generate_report`

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    soft_time_limit=600,
    track_started=True,
)
def generate_report(self, report_id):
    # Generate report with progress tracking
    pass
```

**Features:**
- Automatic retry on failure (3 attempts)
- 10-minute time limit
- Progress tracking via `self.update_state()`
- Idempotent (can run multiple times safely)

**Queue**: `reports`
**Priority**: Configurable per report
**Routing Key**: `reports.generate`

### Task Chain

```python
chain(
    generate_report.s(report_id),
    post_process_report.s(report_id),
    send_report_notification.s(report_id),
).apply_async()
```

1. **generate_report**: Create the report
2. **post_process_report**: Compress, upload to S3
3. **send_report_notification**: Email user

## Database Schema

### Report Model

```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    report_type VARCHAR(20),
    title VARCHAR(255),
    parameters JSONB,
    status VARCHAR(20),
    priority VARCHAR(10),
    celery_task_id VARCHAR(255),
    progress INTEGER DEFAULT 0,
    progress_message VARCHAR(255),
    result_file VARCHAR(255),
    result_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_user_status ON reports(user_id, status);
CREATE INDEX idx_reports_expires ON reports(expires_at);
```

## Monitoring

### Flower Dashboard

Access Celery task monitoring:

```bash
# Start Flower
celery -A config flower --port=5555

# Open browser
http://localhost:5555
```

**Metrics Available:**
- Active tasks
- Task success/failure rates
- Worker status
- Queue lengths
- Task execution time

### Admin Interface

Django admin provides:
- Report status overview
- Progress visualization
- Bulk actions (cancel, retry)
- Execution history
- Error details

Access at: `http://localhost:8000/admin/reports/`

### CloudWatch Metrics

For production (AmazonMQ):
- Task execution count
- Queue depth
- Worker utilization
- Task duration
- Failure rate

## Best Practices Demonstrated

### 1. Idempotency

```python
# Check if already processed
if report.status == Report.Status.COMPLETED:
    return {'status': 'already_completed'}

# Process report
# ...
```

### 2. Progress Tracking

```python
# Update progress at key stages
self.update_state(
    state='PROGRESS',
    meta={'progress': 50, 'message': 'Processing data'}
)
```

### 3. Error Handling

```python
try:
    # Generate report
    pass
except SoftTimeLimitExceeded:
    # Handle timeout
    report.status = 'failed'
    report.error_message = 'Timeout'
    raise
except Exception as e:
    # Handle other errors
    report.retry_count += 1
    raise
```

### 4. Resource Cleanup

```python
@shared_task
def cleanup_expired_reports():
    """Remove old reports automatically."""
    expired = Report.objects.filter(expires_at__lt=timezone.now())
    for report in expired:
        if report.result_file:
            report.result_file.delete()
        report.delete()
```

### 5. Task Routing

```python
# Priority-based routing
if report.priority == Report.Priority.URGENT:
    generate_report.apply_async(
        args=[report_id],
        queue='reports_high_priority'
    )
else:
    generate_report.delay(report_id)
```

## Testing

### Unit Tests

```python
@pytest.mark.django_db
def test_report_creation():
    report = Report.objects.create(
        user=user,
        report_type='sales',
        title='Test Report',
        parameters={'start_date': '2024-01-01'}
    )
    assert report.status == Report.Status.PENDING

@pytest.mark.django_db
@patch('apps.reports.tasks.generate_report.delay')
def test_api_create_report(mock_task, api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.post('/api/v1/reports/', {
        'report_type': 'sales',
        'title': 'Test',
        'parameters': {'start_date': '2024-01-01', 'end_date': '2024-12-31'}
    })
    assert response.status_code == 201
    mock_task.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.django_db
def test_report_generation_flow():
    # Create report
    report = Report.objects.create(...)

    # Execute task synchronously
    result = generate_report.apply(args=[report.id])

    # Verify results
    report.refresh_from_database()
    assert report.status == Report.Status.COMPLETED
    assert report.result_file is not None
```

## Deployment Checklist

- [ ] Configure AmazonMQ broker
- [ ] Update CELERY_BROKER_URL with AmazonMQ endpoint
- [ ] Set up dedicated Celery workers for reports queue
- [ ] Configure S3 bucket for report files
- [ ] Set up Celery beat for scheduled reports
- [ ] Configure email service for notifications
- [ ] Set up monitoring (Flower, CloudWatch)
- [ ] Configure auto-scaling for workers
- [ ] Set up dead letter queue
- [ ] Enable CloudWatch logs

## Troubleshooting

### Report Stuck in Processing

```python
# Check Celery task status
from celery.result import AsyncResult
task = AsyncResult(report.celery_task_id)
print(task.state, task.info)

# Manually revoke
from celery import current_app
current_app.control.revoke(report.celery_task_id, terminate=True)
```

### Worker Not Picking Up Tasks

```bash
# Check worker is consuming from reports queue
celery -A config inspect active_queues

# Check queue depth
# Via Flower or RabbitMQ Management Console
```

### High Memory Usage

```python
# Limit queryset size in report generation
orders = Order.objects.filter(...)[:10000]  # Limit results

# Or use iterator for large datasets
for order in Order.objects.filter(...).iterator(chunk_size=1000):
    # Process in chunks
    pass
```

## Next Steps

1. **Add More Report Types**: Extend with custom report types
2. **Visualization**: Generate charts with matplotlib/plotly
3. **Excel Export**: Use openpyxl for Excel format
4. **Compression**: Add gzip compression for large files
5. **Webhooks**: Notify external systems on completion
6. **Multi-format**: Support PDF, Excel, JSON exports
7. **Incremental Reports**: Only generate delta since last run
8. **Caching**: Cache frequently requested reports

## Conclusion

This Reports feature demonstrates production-ready patterns for:
- Async task processing with Celery
- Message queuing with AmazonMQ
- Progress tracking and monitoring
- Error handling and retries
- Task prioritization and routing
- Scheduled task execution
- Resource cleanup and management

Use this as a reference for building your own async features!
