from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # TEMPORANEO per test
from django.shortcuts import get_object_or_404

from .models import SSHConnection, FileDeployment
from .serializers import (
    SSHConnectionSerializer, CreateSSHConnectionSerializer,
    FileDeploymentSerializer, DeployWorkflowFileSerializer,
    TestSSHConnectionSerializer
)
from .services import (
    deploy_workflow_file, SSHDeploymentService, SSHDeploymentError,
    get_ml_runner_connection, create_ml_runner_connection
)


class SSHConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire le connessioni SSH"""
    queryset = SSHConnection.objects.all()
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateSSHConnectionSerializer
        return SSHConnectionSerializer
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Testa una connessione SSH"""
        ssh_connection = self.get_object()
        
        try:
            service = SSHDeploymentService(ssh_connection)
            service.connect()
            
            # Esegui un comando di test
            result = service.execute_command('echo "Connection test successful"')
            service.disconnect()
            
            if result['success']:
                return Response({
                    'status': 'success',
                    'message': 'Connessione SSH stabilita con successo',
                    'test_output': result['stdout'].strip()
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Test command failed',
                    'error': result['stderr']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except SSHDeploymentError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def setup_ml_runner(self, request):
        """Configura automaticamente la connessione per ml_runner"""
        try:
            connection = create_ml_runner_connection()
            serializer = SSHConnectionSerializer(connection)
            
            return Response({
                'status': 'success',
                'message': 'Connessione ml_runner configurata con successo',
                'connection': serializer.data
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Errore nella configurazione: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class FileDeploymentViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire i deployment dei file"""
    queryset = FileDeployment.objects.all()
    serializer_class = FileDeploymentSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    @action(detail=False, methods=['post'])
    def deploy_workflow(self, request):
        """Deploya un file workflow sul server remoto"""
        serializer = DeployWorkflowFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            deployment = deploy_workflow_file(
                ssh_connection_id=serializer.validated_data['ssh_connection_id'],
                file_content=serializer.validated_data['file_content'],
                file_name=serializer.validated_data['file_name'],
                workflow_id=serializer.validated_data.get('workflow_id'),
                user=request.user if request.user.is_authenticated else None,
                deployment_notes=serializer.validated_data.get('deployment_notes', '')
            )
            
            response_serializer = FileDeploymentSerializer(deployment)
            return Response({
                'status': 'success',
                'message': 'File deployato con successo',
                'deployment': response_serializer.data
            })
            
        except SSHDeploymentError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def deploy_to_ml_runner(self, request):
        """Deploya direttamente sul container ml_runner"""
        # Verifica che esista la connessione ml_runner
        ml_connection = get_ml_runner_connection()
        if not ml_connection:
            ml_connection = create_ml_runner_connection()
        
        # Prepara i dati per il deployment
        data = request.data.copy()
        data['ssh_connection_id'] = str(ml_connection.id)
        
        serializer = DeployWorkflowFileSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        try:
            deployment = deploy_workflow_file(
                ssh_connection_id=ml_connection.id,
                file_content=serializer.validated_data['file_content'],
                file_name=serializer.validated_data['file_name'],
                workflow_id=serializer.validated_data.get('workflow_id'),
                user=request.user if request.user.is_authenticated else None,
                deployment_notes=serializer.validated_data.get('deployment_notes', '')
            )
            
            response_serializer = FileDeploymentSerializer(deployment)
            return Response({
                'status': 'success',
                'message': f'File deployato con successo su ml_runner: {deployment.remote_file_path}',
                'deployment': response_serializer.data
            })
            
        except SSHDeploymentError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def retry_deployment(self, request, pk=None):
        """Riprova un deployment fallito"""
        deployment = self.get_object()
        
        if deployment.status not in ['failed', 'pending']:
            return Response({
                'status': 'error',
                'message': 'Il deployment può essere riprovato solo se è fallito o in pending'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Riprova il deployment
            new_deployment = deploy_workflow_file(
                ssh_connection_id=deployment.ssh_connection.id,
                file_content=deployment.file_content,
                file_name=deployment.file_name,
                workflow_id=deployment.workflow_id,
                user=request.user if request.user.is_authenticated else None,
                deployment_notes=f"Retry of deployment {deployment.id}"
            )
            
            response_serializer = FileDeploymentSerializer(new_deployment)
            return Response({
                'status': 'success',
                'message': 'Deployment riprovato con successo',
                'deployment': response_serializer.data
            })
            
        except SSHDeploymentError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
