"""
Core views providing health checks and API root.
"""

from django.http import JsonResponse
from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
import redis


def health_check(request):
    """
    Health check endpoint for monitoring.

    Checks:
    - Database connectivity
    - Redis/Cache connectivity
    - Overall system health

    Returns appropriate HTTP status codes:
    - 200: All systems operational
    - 503: Service unavailable (database or cache down)
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = 'error'
        health_status['status'] = 'unhealthy'
        health_status['checks']['database_error'] = str(e)

    # Check Redis/Cache
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        if result == 'ok':
            health_status['checks']['cache'] = 'ok'
        else:
            health_status['checks']['cache'] = 'error'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['cache'] = 'error'
        health_status['status'] = 'unhealthy'
        health_status['checks']['cache_error'] = str(e)

    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503

    return JsonResponse(health_status, status=status_code)


@api_view(['GET'])
def api_root(request, format=None):
    """
    API root endpoint listing all available API versions.
    """
    return Response({
        'v1': reverse('api-v1-root', request=request, format=format) if 'api-v1-root' in request.resolver_match.app_names else request.build_absolute_uri('/api/v1/'),
        'health': reverse('health-check', request=request, format=format),
    })
