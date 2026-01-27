from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SSHConnectionViewSet, FileDeploymentViewSet

router = DefaultRouter()
router.register(r'connections', SSHConnectionViewSet, basename='sshconnection')
router.register(r'deployments', FileDeploymentViewSet, basename='filedeployment')

app_name = 'ssh_deployment'

urlpatterns = [
    path('api/ssh/', include(router.urls)),
]