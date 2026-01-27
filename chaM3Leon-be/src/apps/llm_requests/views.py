from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
import os
import logging
from datetime import datetime
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import LLMProvider, LLMModel, LLMRequest, LLMConversation, ConversationMessage, WorkflowFileAnalysis
from .serializers import (
    LLMProviderSerializer, LLMModelSerializer, LLMRequestSerializer,
    CreateLLMRequestSerializer, LLMConversationSerializer, ConversationMessageSerializer,
    WorkflowFileAnalysisSerializer, CreateWorkflowFileAnalysisSerializer, AvailableWorkflowFileSerializer
)
from .services import (
    process_llm_request, LLMServiceError, get_available_workflow_files, 
    resolve_workflow_file_path, process_workflow_file_analysis
)
import mlflow

# Configura il logger
logger = logging.getLogger(__name__)

class LLMProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet per visualizzare i provider LLM disponibili"""
    queryset = LLMProvider.objects.filter(is_active=True)
    serializer_class = LLMProviderSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test

class LLMModelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet per visualizzare i modelli LLM disponibili"""
    queryset = LLMModel.objects.filter(is_active=True).select_related('provider')
    serializer_class = LLMModelSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_queryset(self):
        queryset = super().get_queryset()
        provider = self.request.query_params.get('provider', None)
        if provider:
            queryset = queryset.filter(provider__name=provider)
        return queryset

class LLMConversationViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire le conversazioni LLM"""
    serializer_class = LLMConversationSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_queryset(self):
        # Per i test, restituisci tutte le conversazioni
        return LLMConversation.objects.all().prefetch_related('messages')
        # return LLMConversation.objects.filter(user=self.request.user).prefetch_related('messages')
    
    def perform_create(self, serializer):
        # Per i test, non associare un utente specifico
        serializer.save()
        # serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Aggiungi un messaggio alla conversazione"""
        conversation = self.get_object()
        serializer = ConversationMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(conversation=conversation)
            conversation.updated_at = timezone.now()
            conversation.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Ottieni tutti i messaggi di una conversazione"""
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = ConversationMessageSerializer(messages, many=True)
        return Response(serializer.data)

class LLMRequestViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire le richieste LLM"""
    serializer_class = LLMRequestSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_queryset(self):
        # Per i test, restituisci tutte le richieste
        return LLMRequest.objects.all().select_related('model__provider')
        # return LLMRequest.objects.filter(user=self.request.user).select_related('model__provider')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateLLMRequestSerializer
        return LLMRequestSerializer
    
    def perform_create(self, serializer):
        # Ottieni o crea la conversazione se specificata
        conversation = None
        conversation_id = serializer.validated_data.pop('conversation_id', None)
        
        if conversation_id:
            conversation = get_object_or_404(
                LLMConversation, 
                id=conversation_id
                # user=self.request.user  # Commentato per test
            )
        
        # Crea la richiesta
        request_obj = serializer.save(
            # user=self.request.user,  # Commentato per test
            conversation=conversation
        )
        
        # Processa la richiesta in modo asincrono (per ora sincrono)
        try:
            processed_request = process_llm_request(request_obj)
            return processed_request
        except LLMServiceError as e:
            request_obj.status = 'failed'
            request_obj.error_message = str(e)
            request_obj.save()
            return request_obj
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        request_obj = self.perform_create(serializer)
        
        # Restituisci la richiesta processata
        response_serializer = LLMRequestSerializer(request_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def quick_request(self, request):
        """Endpoint per richieste rapide senza conversazione"""
        serializer = CreateLLMRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            request_obj = serializer.save()  # Rimosso user=request.user per test
            
            try:
                processed_request = process_llm_request(request_obj)
                response_serializer = LLMRequestSerializer(processed_request)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            except LLMServiceError as e:
                request_obj.status = 'failed'
                request_obj.error_message = str(e)
                request_obj.save()
                response_serializer = LLMRequestSerializer(request_obj)
                return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Riprova una richiesta fallita"""
        request_obj = self.get_object()
        
        if request_obj.status != 'failed':
            return Response(
                {'error': 'Solo le richieste fallite possono essere riprovate'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset dello stato
        request_obj.status = 'pending'
        request_obj.error_message = ''
        request_obj.response = ''
        request_obj.save()
        
        try:
            processed_request = process_llm_request(request_obj)
            response_serializer = LLMRequestSerializer(processed_request)
            return Response(response_serializer.data)
        except LLMServiceError as e:
            request_obj.status = 'failed'
            request_obj.error_message = str(e)
            request_obj.save()
            response_serializer = LLMRequestSerializer(request_obj)
            return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)

class WorkflowFileAnalysisViewSet(viewsets.ModelViewSet):
    """ViewSet per gestire l'analisi dei file workflow tramite LLM"""
    serializer_class = WorkflowFileAnalysisSerializer
    permission_classes = [AllowAny]  # TEMPORANEO per test
    
    def get_queryset(self):
        # Per i test, restituisci tutte le analisi
        return WorkflowFileAnalysis.objects.all().select_related('model__provider')
        # return WorkflowFileAnalysis.objects.filter(user=self.request.user).select_related('model__provider')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateWorkflowFileAnalysisSerializer
        return WorkflowFileAnalysisSerializer
    
    def perform_create(self, serializer):
        # Risolvi il path del file
        workflow_id = serializer.validated_data.pop('workflow_id', None)
        workflow_file_name = serializer.validated_data.pop('workflow_file_name', None)
        workflow_file_path = serializer.validated_data.get('workflow_file_path')
        
        try:
            resolved_path = resolve_workflow_file_path(
                workflow_id=workflow_id,
                workflow_file_name=workflow_file_name,
                workflow_file_path=workflow_file_path
            )
            serializer.validated_data['workflow_file_path'] = resolved_path
        except LLMServiceError as e:
            raise serializers.ValidationError({'workflow_file_path': str(e)})
        
        # Crea l'analisi
        analysis = serializer.save()
        
        # Processa l'analisi
        try:
            processed_analysis = process_workflow_file_analysis(analysis)
            return processed_analysis
        except LLMServiceError as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
            return analysis
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        analysis = self.perform_create(serializer)
        
        # Restituisci l'analisi processata
        response_serializer = WorkflowFileAnalysisSerializer(analysis)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def get_file(self, request):
        """Endpoint per ottenere il contenuto di un file workflow specifico"""
        workflow_id = request.query_params.get('workflow_id')
        workflow_file_name = request.query_params.get('workflow_file_name')
        workflow_file_path = request.query_params.get('workflow_file_path')
        
        if not any([workflow_id, workflow_file_name, workflow_file_path]):
            return Response(
                {'error': 'Specificare almeno uno tra workflow_id, workflow_file_name o workflow_file_path'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Risolvi il path del file
            resolved_path = resolve_workflow_file_path(
                workflow_id=workflow_id,
                workflow_file_name=workflow_file_name,
                workflow_file_path=workflow_file_path
            )
            
            # Leggi il contenuto del file
            with open(resolved_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Ottieni informazioni sul file
            stat = os.stat(resolved_path)
            
            return Response({
                'workflow_id': os.path.basename(os.path.dirname(resolved_path)),
                'file_name': os.path.basename(resolved_path),
                'file_path': resolved_path,
                'content': file_content,
                'file_size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime)
            })
            
        except LLMServiceError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Errore nella lettura del file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def check_workflow_status(self, request):
        """Endpoint per verificare lo status di un workflow prima dell'analisi"""
        workflow_id = request.query_params.get('workflow_id')
        
        if not workflow_id:
            return Response(
                {'error': 'workflow_id è richiesto'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from ..workflow_generator.models import WorkflowGeneration
            
            workflow = WorkflowGeneration.objects.filter(id=workflow_id).first()
            if not workflow:
                return Response(
                    {'error': f'Workflow {workflow_id} non trovato nel database'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Controlla anche se il file esiste fisicamente
            file_exists = False
            file_path = None
            if workflow.status == 'completed' and workflow.generated_file_path:
                file_exists = os.path.exists(workflow.generated_file_path)
                file_path = workflow.generated_file_path
            
            response_data = {
                'workflow_id': str(workflow.id),
                'status': workflow.status,
                'config_name': workflow.config_name,
                'generated_class_name': workflow.generated_class_name,
                'generated_file_path': workflow.generated_file_path,
                'file_exists': file_exists,
                'created_at': workflow.created_at,
                'completed_at': workflow.completed_at,
                'error_message': workflow.error_message,
                'ready_for_analysis': workflow.status == 'completed' and file_exists
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Errore nella verifica del workflow: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_files(self, request):
        """Endpoint per ottenere la lista dei file workflow disponibili"""
        try:
            files = get_available_workflow_files()
            serializer = AvailableWorkflowFileSerializer(files, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Errore nel recupero dei file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def quick_analysis(self, request):
        """Endpoint per analisi rapide senza salvare nel database"""
        logger.info("QUICK_ANALYSIS: Ricevuta richiesta POST")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"Content-Type: {request.content_type}")
        logger.debug(f"Request method: {request.method}")
        
        # Debug: controlla i modelli disponibili
        available_models = LLMModel.objects.filter(is_active=True)
        logger.info(f"Modelli disponibili nel database: {available_models.count()}")
        for model in available_models:
            logger.debug(f"  - ID: {model.id}, Nome: {model.name}, Display: {model.display_name}, Provider: {model.provider.name}")
        
        serializer = CreateWorkflowFileAnalysisSerializer(data=request.data)
        logger.debug(f"🔧 Serializer creato con data: {request.data}")
        
        if serializer.is_valid():
            logger.info("Serializer valido, procedendo con l'analisi...")
            logger.debug(f"Validated data: {serializer.validated_data}")
            
            try:
                # Risolvi il path del file
                workflow_id = serializer.validated_data.get('workflow_id')
                workflow_file_name = serializer.validated_data.get('workflow_file_name')
                workflow_file_path = serializer.validated_data.get('workflow_file_path')
                
                logger.debug(f"Parametri per risoluzione path:")
                logger.debug(f"  - workflow_id: {workflow_id}")
                logger.debug(f"  - workflow_file_name: {workflow_file_name}")
                logger.debug(f"  - workflow_file_path: {workflow_file_path}")
                
                # Validation: se viene fornito un workflow_id, verifica lo stato prima di procedere
                if workflow_id:
                    try:
                        from ..workflow_generator.models import WorkflowGeneration
                        workflow = WorkflowGeneration.objects.filter(id=workflow_id).first()
                        if workflow:
                            logger.info(f"Workflow {workflow_id} trovato - Status: {workflow.status}")
                            if workflow.status != 'completed':
                                error_msg = f"Il workflow {workflow_id} non è completato (status: {workflow.status}). "
                                if workflow.status == 'failed':
                                    error_msg += f"Errore: {workflow.error_message}"
                                elif workflow.status == 'processing':
                                    error_msg += "Attendi il completamento della generazione."
                                elif workflow.status == 'pending':
                                    error_msg += "Il workflow non è ancora stato processato."
                                logger.error(f"❌ {error_msg}")
                                return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            error_msg = f"Il workflow {workflow_id} non esiste nel database."
                            logger.error(f"❌ {error_msg}")
                            return Response({'error': error_msg}, status=status.HTTP_404_NOT_FOUND)
                    except Exception as db_error:
                        logger.error(f"❌ Errore nella verifica del workflow: {str(db_error)}")
                        return Response({'error': f"Errore nella verifica del workflow: {str(db_error)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                resolved_path = resolve_workflow_file_path(
                    workflow_id=workflow_id,
                    workflow_file_name=workflow_file_name,
                    workflow_file_path=workflow_file_path
                )
                logger.info(f"✅ Path risolto: {resolved_path}")
                
                # Leggi il contenuto del file
                logger.info("Leggendo contenuto file...")
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    workflow_content = f.read()
                logger.debug(f"Contenuto letto: {len(workflow_content)} caratteri")
                
                # Crea un'analisi temporanea (non salvata nel DB)
                logger.info("Creando analisi temporanea...")
                logger.debug(f"Modello selezionato: {serializer.validated_data['model']}")
                
                temp_analysis = WorkflowFileAnalysis(
                    model=serializer.validated_data['model'],
                    workflow_file_path=resolved_path,
                    workflow_content=workflow_content,
                    system_prompt=serializer.validated_data.get('system_prompt', WorkflowFileAnalysis._meta.get_field('system_prompt').default),
                    user_prompt=serializer.validated_data.get('user_prompt', '')
                )
                logger.debug("✅ Analisi temporanea creata")
                
                # Processa l'analisi senza salvare
                logger.info("Processando analisi...")
                processed_analysis = process_workflow_file_analysis(temp_analysis)
                logger.info(f"✅ Analisi processata con status: {processed_analysis.status}")
                
                # Restituisci solo i dati essenziali
                response_data = {
                    'workflow_file_path': resolved_path,
                    'analysis_response': processed_analysis.analysis_response,
                    'status': processed_analysis.status,
                    'error_message': processed_analysis.error_message,
                    'tokens_used': processed_analysis.tokens_used,
                    'response_time_ms': processed_analysis.response_time_ms
                }
                logger.debug(f"Restituendo risposta: {list(response_data.keys())}")
                return Response(response_data)
                
            except Exception as e:
                logger.error(f"❌ Errore durante l'analisi: {str(e)}")
                logger.error(f"Tipo errore: {type(e).__name__}")
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            logger.error("❌ Serializer NON valido")
            logger.error(f"Errori serializer: {serializer.errors}")
            logger.debug(f"Data ricevuta: {request.data}")
            logger.debug(f"Fields del serializer: {list(serializer.fields.keys())}")
            
            # Log dettagliato per ogni campo
            for field_name, field_errors in serializer.errors.items():
                logger.error(f"Campo '{field_name}': {field_errors}")
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def latest_generated(self, request):
        """Endpoint per ottenere l'ultimo workflow generato"""
        try:
            # Ottieni tutti i file disponibili ordinati per data di creazione (più recente prima)
            files = get_available_workflow_files()
            
            if not files:
                return Response(
                    {'error': 'Nessun workflow generato trovato'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prendi il primo file (il più recente)
            latest_file = files[0]
            
            # Leggi il contenuto del file
            with open(latest_file['file_path'], 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Ottieni informazioni aggiuntive sul file
            stat = os.stat(latest_file['file_path'])
            
            return Response({
                'workflow_id': latest_file['workflow_id'],
                'file_name': latest_file['file_name'],
                'file_path': latest_file['file_path'],
                'content': file_content,
                'file_size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'is_latest': True
            })
            
        except Exception as e:
            return Response(
                {'error': f'Errore nel recupero dell\'ultimo workflow: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Riprova un'analisi fallita"""
        analysis = self.get_object()
        
        if analysis.status != 'failed':
            return Response(
                {'error': 'Solo le analisi fallite possono essere riprovate'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset dello stato
        analysis.status = 'pending'
        analysis.error_message = ''
        analysis.analysis_response = ''
        analysis.save()
        
        try:
            processed_analysis = process_workflow_file_analysis(analysis)
            response_serializer = WorkflowFileAnalysisSerializer(processed_analysis)
            return Response(response_serializer.data)
        except Exception as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
            response_serializer = WorkflowFileAnalysisSerializer(analysis)
            return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)
