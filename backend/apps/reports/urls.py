"""Report URLs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, ReportScheduleViewSet

app_name = 'reports'

router = DefaultRouter()
router.register(r'', ReportViewSet, basename='report')
router.register(r'schedules', ReportScheduleViewSet, basename='report-schedule')

urlpatterns = [
    path('', include(router.urls)),
]
