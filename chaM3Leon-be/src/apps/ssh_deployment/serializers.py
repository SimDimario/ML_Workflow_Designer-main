from rest_framework import serializers
from .models import SSHConnection, FileDeployment


class SSHConnectionSerializer(serializers.ModelSerializer):
    """Serializer per le connessioni SSH"""
    
    class Meta:
        model = SSHConnection
        fields = [
            'id', 'name', 'host', 'port', 'username', 'remote_base_path',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateSSHConnectionSerializer(serializers.ModelSerializer):
    """Serializer per creare connessioni SSH"""
    
    class Meta:
        model = SSHConnection
        fields = [
            'name', 'host', 'port', 'username', 'password', 
            'private_key_path', 'remote_base_path', 'is_active'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'private_key_path': {'required': False}
        }


class FileDeploymentSerializer(serializers.ModelSerializer):
    """Serializer per i deployment dei file"""
    ssh_connection_name = serializers.CharField(source='ssh_connection.name', read_only=True)
    ssh_connection_host = serializers.CharField(source='ssh_connection.host', read_only=True)
    
    class Meta:
        model = FileDeployment
        fields = [
            'id', 'ssh_connection', 'ssh_connection_name', 'ssh_connection_host',
            'local_file_path', 'remote_file_path', 'file_name', 'status',
            'error_message', 'workflow_id', 'deployment_notes',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'ssh_connection_name', 'ssh_connection_host',
            'status', 'error_message', 'created_at', 'started_at', 'completed_at'
        ]


class DeployWorkflowFileSerializer(serializers.Serializer):
    """Serializer per deployare un file workflow"""
    ssh_connection_id = serializers.UUIDField(help_text="ID della connessione SSH da utilizzare")
    file_content = serializers.CharField(help_text="Contenuto del file Python da deployare")
    file_name = serializers.CharField(max_length=255, help_text="Nome del file (es: my_workflow.py)")
    workflow_id = serializers.UUIDField(required=False, help_text="ID del workflow associato (opzionale)")
    deployment_notes = serializers.CharField(required=False, allow_blank=True, help_text="Note aggiuntive")
    
    def validate_file_name(self, value):
        """Valida che il nome del file abbia estensione .py"""
        if not value.endswith('.py'):
            raise serializers.ValidationError("Il nome del file deve avere estensione .py")
        return value


class TestSSHConnectionSerializer(serializers.Serializer):
    """Serializer per testare una connessione SSH"""
    ssh_connection_id = serializers.UUIDField(help_text="ID della connessione SSH da testare")