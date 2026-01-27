from rest_framework import serializers
from .models import LLMProvider, LLMModel, LLMRequest, LLMConversation, ConversationMessage, WorkflowFileAnalysis
import os

class LLMProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = ['id', 'name', 'display_name', 'is_active']

class LLMModelSerializer(serializers.ModelSerializer):
    provider = LLMProviderSerializer(read_only=True)
    
    class Meta:
        model = LLMModel
        fields = ['id', 'provider', 'name', 'display_name', 'max_tokens', 'supports_streaming', 'is_active']

class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = ['id', 'role', 'content', 'created_at']

class LLMConversationSerializer(serializers.ModelSerializer):
    messages = ConversationMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMConversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'messages', 'message_count']
    
    def get_message_count(self, obj):
        return obj.messages.count()

class LLMRequestSerializer(serializers.ModelSerializer):
    model_info = LLMModelSerializer(source='model', read_only=True)
    
    class Meta:
        model = LLMRequest
        fields = [
            'id', 'model', 'model_info', 'prompt', 'system_message', 
            'max_tokens', 'temperature', 'response', 'status', 
            'error_message', 'tokens_used', 'response_time_ms',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'response', 'status', 'error_message', 'tokens_used', 'response_time_ms', 'completed_at']

class CreateLLMRequestSerializer(serializers.ModelSerializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        model = LLMRequest
        fields = ['model', 'prompt', 'system_message', 'max_tokens', 'temperature', 'conversation_id']

class WorkflowFileAnalysisSerializer(serializers.ModelSerializer):
    model_info = LLMModelSerializer(source='model', read_only=True)
    
    class Meta:
        model = WorkflowFileAnalysis
        fields = [
            'id', 'model', 'model_info', 'workflow_file_path', 'workflow_content',
            'system_prompt', 'user_prompt', 'analysis_response', 'status',
            'error_message', 'tokens_used', 'response_time_ms',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'workflow_content', 'analysis_response', 'status', 
            'error_message', 'tokens_used', 'response_time_ms', 'completed_at'
        ]

class CreateWorkflowFileAnalysisSerializer(serializers.ModelSerializer):
    workflow_id = serializers.UUIDField(required=False, allow_null=True, help_text="ID del workflow generato (opzionale)")
    workflow_file_name = serializers.CharField(required=False, allow_blank=True, help_text="Nome del file nella cartella generated_workflows (opzionale)")
    workflow_file_path = serializers.CharField(required=False, allow_blank=True, help_text="Path completo del file (opzionale)")
    
    class Meta:
        model = WorkflowFileAnalysis
        fields = [
            'model', 'workflow_id', 'workflow_file_name', 'workflow_file_path',
            'system_prompt', 'user_prompt'
        ]
        extra_kwargs = {
            'workflow_file_path': {'required': False, 'allow_blank': True}
        }
    
    def validate(self, data):
        """Valida che sia specificato almeno uno tra workflow_id, workflow_file_name o workflow_file_path"""
        workflow_id = data.get('workflow_id')
        workflow_file_name = data.get('workflow_file_name')
        workflow_file_path = data.get('workflow_file_path')
        
        if not any([workflow_id, workflow_file_name, workflow_file_path]):
            raise serializers.ValidationError(
                "Devi specificare almeno uno tra 'workflow_id', 'workflow_file_name' o 'workflow_file_path'"
            )
        
        return data
    
    def validate_workflow_file_path(self, value):
        """Valida che il file esista se specificato"""
        if value and value.strip() and not os.path.exists(value):
            raise serializers.ValidationError(f"Il file {value} non esiste")
        return value

class AvailableWorkflowFileSerializer(serializers.Serializer):
    """Serializer per listare i file workflow disponibili"""
    workflow_id = serializers.UUIDField()
    file_name = serializers.CharField()
    file_path = serializers.CharField()
    created_at = serializers.DateTimeField()
    file_size = serializers.IntegerField()