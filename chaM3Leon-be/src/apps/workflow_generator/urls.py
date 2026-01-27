from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowGenerationViewSet

router = DefaultRouter()
router.register(r'workflows', WorkflowGenerationViewSet, basename='workflow')

urlpatterns = [
    path('api/workflow-generator/', include(router.urls)),
]