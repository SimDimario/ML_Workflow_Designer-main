from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # TEMPORANEO per test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import os

from .models import WorkflowGeneration
from .serializers import (
    WorkflowGenerationSerializer, 
    CreateWorkflowSerializer,
    UploadWorkflowConfigSerializer
)
from .services import generate_workflow_from_config, process_uploaded_json, WorkflowGenerationError

class WorkflowGenerationViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire la generazione di workflow"""
    serializer_class = WorkflowGenerationSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_queryset(self):
        # Per i test, restituisci tutte le generazioni
        return WorkflowGeneration.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateWorkflowSerializer
        elif self.action == 'upload_config':
            return UploadWorkflowConfigSerializer
        return WorkflowGenerationSerializer
    
    def perform_create(self, serializer):
        """Crea una nuova generazione di workflow"""
        workflow_generation = serializer.save()
        
        # Processa la generazione in modo asincrono (per ora sincrono)
        try:
            processed_workflow = generate_workflow_from_config(workflow_generation)
            return processed_workflow
        except WorkflowGenerationError as e:
            workflow_generation.status = 'failed'
            workflow_generation.error_message = str(e)
            workflow_generation.save()
            return workflow_generation
    
    def create(self, request, *args, **kwargs):
        """Crea e processa un nuovo workflow"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        workflow_generation = self.perform_create(serializer)
        
        response_serializer = WorkflowGenerationSerializer(workflow_generation)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def upload_config(self, request):
        """Endpoint per caricare un file JSON di configurazione"""
        serializer = UploadWorkflowConfigSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Processa il file JSON
                config_data = process_uploaded_json(serializer.validated_data['config_file'])
                
                # Crea la generazione del workflow
                workflow_generation = WorkflowGeneration.objects.create(
                    config_name=serializer.validated_data['config_name'],
                    config_data=config_data
                )
                
                # Genera il workflow
                processed_workflow = generate_workflow_from_config(workflow_generation)
                
                response_serializer = WorkflowGenerationSerializer(processed_workflow)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except WorkflowGenerationError as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download_generated_file(self, request, pk=None):
        """Download del file Python generato"""
        workflow_generation = self.get_object()
        
        if workflow_generation.status != 'completed':
            return Response(
                {'error': 'Il workflow non è stato ancora generato con successo'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not os.path.exists(workflow_generation.generated_file_path):
            return Response(
                {'error': 'File generato non trovato'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Leggi il contenuto del file
        with open(workflow_generation.generated_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Restituisci il file come download
        response = HttpResponse(content, content_type='text/x-python')
        response['Content-Disposition'] = f'attachment; filename="{workflow_generation.generated_class_name}.py"'
        return response
    
    @action(detail=True, methods=['get'])
    def preview_generated_code(self, request, pk=None):
        """Anteprima del codice generato"""
        workflow_generation = self.get_object()
        
        if workflow_generation.status != 'completed':
            return Response(
                {'error': 'Il workflow non è stato ancora generato con successo'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'class_name': workflow_generation.generated_class_name,
            'file_path': workflow_generation.generated_file_path,
            'generated_code': workflow_generation.generated_content
        })
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Rigenera un workflow fallito"""
        workflow_generation = self.get_object()
        
        if workflow_generation.status not in ['failed', 'completed']:
            return Response(
                {'error': 'Solo i workflow falliti o completati possono essere rigenerati'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset dello stato
        workflow_generation.status = 'pending'
        workflow_generation.error_message = ''
        workflow_generation.generated_content = ''
        workflow_generation.save()
        
        try:
            processed_workflow = generate_workflow_from_config(workflow_generation)
            response_serializer = WorkflowGenerationSerializer(processed_workflow)
            return Response(response_serializer.data)
        except WorkflowGenerationError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
