from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LLMProviderViewSet, LLMModelViewSet, LLMRequestViewSet, LLMConversationViewSet, WorkflowFileAnalysisViewSet

router = DefaultRouter()
router.register(r'providers', LLMProviderViewSet, basename='llmprovider')
router.register(r'models', LLMModelViewSet, basename='llmmodel')
router.register(r'requests', LLMRequestViewSet, basename='llmrequest')
router.register(r'conversations', LLMConversationViewSet, basename='llmconversation')
router.register(r'workflow-analysis', WorkflowFileAnalysisViewSet, basename='workflowfileanalysis')

app_name = 'llm_requests'

urlpatterns = [
    path('api/llm/', include(router.urls)),
]