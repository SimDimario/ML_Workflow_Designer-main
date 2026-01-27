from rest_framework import serializers
from .models import WorkflowGeneration

class WorkflowGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowGeneration
        fields = [
            'id', 'config_name', 'config_data', 'generated_class_name',
            'generated_file_path', 'generated_content', 'status', 
            'error_message', 'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'generated_class_name', 'generated_file_path', 
            'generated_content', 'status', 'error_message', 
            'created_at', 'completed_at'
        ]

class CreateWorkflowSerializer(serializers.ModelSerializer):    
    class Meta:
        model = WorkflowGeneration
        fields = ['config_name', 'config_data']
    
    def validate_config_data(self, value):
        required_fields = ['class']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Campo '{field}' richiesto nel JSON di configurazione")
        if 'name' not in value['class']:
            raise serializers.ValidationError("Il campo 'class.name' è richiesto")
        return value

class UploadWorkflowConfigSerializer(serializers.Serializer):
    config_name = serializers.CharField(max_length=200)
    config_file = serializers.FileField()
    
    def validate_config_file(self, value):
        if not value.name.endswith('.json'):
            raise serializers.ValidationError("Il file deve essere un JSON (.json)")
        try:
            import json
            content = value.read()
            value.seek(0)  # Reset file pointer
            json.loads(content.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise serializers.ValidationError("Il file non contiene un JSON valido")
        return value