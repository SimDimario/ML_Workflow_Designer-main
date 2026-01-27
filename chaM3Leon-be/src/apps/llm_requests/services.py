import os
import glob
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from decouple import config
import openai
import anthropic
from google import genai
from .models import LLMRequest, LLMConversation, ConversationMessage
from ..workflow_generator.models import WorkflowGeneration

# Configura il logger
logger = logging.getLogger(__name__)

class LLMServiceError(Exception):
    """Eccezione personalizzata per errori del servizio LLM"""
    pass

class BaseLLMService:
    """Classe base per i servizi LLM"""
    
    def __init__(self):
        self.client = None
        self.setup_client()
    
    def setup_client(self):
        """Configura il client per il provider specifico"""
        raise NotImplementedError
    
    def generate_response(self, request: LLMRequest) -> Dict[str, Any]:
        """Genera una risposta dal modello LLM"""
        raise NotImplementedError

class OpenAIService(BaseLLMService):
    """Servizio per OpenAI GPT"""
    
    def setup_client(self):
        logger.info("Setting up OpenAI client...")
        api_key = config('OPENAI_API_KEY', default='')
        logger.debug(f"OpenAI API key configured: {'Yes' if api_key and api_key != 'your-openai-api-key-here' else 'No'}")
        
        if not api_key or api_key == 'your-openai-api-key-here':
            logger.error("OpenAI API key non configurata")
            raise LLMServiceError("OpenAI API key non configurata")
        
        self.client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client configurato con successo")
    
    def generate_response(self, request: LLMRequest) -> Dict[str, Any]:
        logger.info("Generando risposta OpenAI...")
        logger.debug(f"Modello: {request.model.name}, Prompt length: {len(request.prompt)}")
        
        try:
            start_time = time.time()
            
            messages = []
            if request.system_message:
                messages.append({"role": "system", "content": request.system_message})
                logger.debug("System message aggiunto")
            
            # Se fa parte di una conversazione, aggiungi i messaggi precedenti
            if request.conversation:
                conversation_messages = request.conversation.messages.all()
                logger.debug(f"Aggiungendo {conversation_messages.count()} messaggi dalla conversazione")
                for msg in conversation_messages:
                    messages.append({"role": msg.role, "content": msg.content})
            
            messages.append({"role": "user", "content": request.prompt})
            logger.debug(f"Totale messaggi da inviare: {len(messages)}")
            
            logger.info("Chiamando API OpenAI...")
            response = self.client.chat.completions.create(
                model=request.model.name,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            logger.info(f"Risposta OpenAI ricevuta in {response_time_ms}ms")
            logger.debug(f"Token utilizzati: {response.usage.total_tokens if response.usage else 'N/A'}")
            
            return {
                'response': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'response_time_ms': response_time_ms,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Errore OpenAI: {str(e)}")
            return {
                'status': 'failed',
                'error_message': str(e)
            }

class AnthropicService(BaseLLMService):
    """Servizio per Anthropic Claude"""
    
    def setup_client(self):
        api_key = config('ANTHROPIC_API_KEY', default='')
        if not api_key or api_key == 'your-anthropic-api-key-here':
            raise LLMServiceError("Anthropic API key non configurata")
        
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def generate_response(self, request: LLMRequest) -> Dict[str, Any]:
        try:
            start_time = time.time()
            
            messages = []
            
            # Se fa parte di una conversazione, aggiungi i messaggi precedenti
            if request.conversation:
                for msg in request.conversation.messages.all():
                    if msg.role != 'system':  # Claude gestisce il system message separatamente
                        messages.append({"role": msg.role, "content": msg.content})
            
            messages.append({"role": "user", "content": request.prompt})
            
            response = self.client.messages.create(
                model=request.model.name,
                max_tokens=request.max_tokens or 1000,
                temperature=request.temperature,
                system=request.system_message if request.system_message else None,
                messages=messages
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            return {
                'response': response.content[0].text,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
                'response_time_ms': response_time_ms,
                'status': 'completed'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': str(e)
            }

class GeminiService(BaseLLMService):
    """Servizio per Google Gemini"""
    
    def setup_client(self):
        api_key = config('GEMINI_API_KEY', default='')
        if not api_key or api_key == 'your-gemini-api-key-here':
            raise LLMServiceError("Gemini API key non configurata")
        
        self.client = genai.Client(api_key=api_key)
    
    def generate_response(self, request: LLMRequest) -> Dict[str, Any]:
        try:
            start_time = time.time()
            
            # Costruisci il contenuto per Gemini
            contents = []
            
            # Se c'è un system message, aggiungilo come primo messaggio
            if request.system_message:
                contents.append(f"System: {request.system_message}\n\n")
            
            # Se fa parte di una conversazione, aggiungi i messaggi precedenti
            if request.conversation:
                for msg in request.conversation.messages.all():
                    contents.append(f"{msg.role.capitalize()}: {msg.content}\n")
            
            # Aggiungi il prompt corrente
            contents.append(f"User: {request.prompt}")
            
            # Unisci tutto in un singolo contenuto
            full_content = "\n".join(contents)
            
            response = self.client.models.generate_content(
                model=request.model.name,
                contents=full_content
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            return {
                'response': response.text,
                'tokens_used': None,  # Gemini non fornisce sempre info sui token
                'response_time_ms': response_time_ms,
                'status': 'completed'
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': str(e)
            }

class LLMServiceFactory:
    """Factory per creare i servizi LLM appropriati"""
    
    _services = {
        'openai': OpenAIService,
        'anthropic': AnthropicService,
        'gemini': GeminiService,
    }
    
    @classmethod
    def get_service(cls, provider_name: str) -> BaseLLMService:
        """Restituisce il servizio appropriato per il provider"""
        logger.info(f"Creando servizio per provider: {provider_name}")
        
        service_class = cls._services.get(provider_name)
        if not service_class:
            logger.error(f"Provider {provider_name} non supportato. Provider disponibili: {list(cls._services.keys())}")
            raise LLMServiceError(f"Provider {provider_name} non supportato")
        
        logger.debug(f"Servizio trovato per {provider_name}: {service_class.__name__}")
        return service_class()

def process_llm_request(request: LLMRequest) -> LLMRequest:
    """Processa una richiesta LLM e aggiorna il database"""
    logger.info(f"Processando richiesta LLM ID: {request.id if request.id else 'NUOVO'}")
    logger.debug(f"Dettagli richiesta - Modello: {request.model.name}, Provider: {request.model.provider.name}")
    
    try:
        request.status = 'processing'
        request.save()
        logger.debug("Status aggiornato a 'processing'")
        
        # Ottieni il servizio appropriato
        logger.info(f"Ottenendo servizio per provider: {request.model.provider.name}")
        service = LLMServiceFactory.get_service(request.model.provider.name)
        
        # Genera la risposta
        logger.info("Generando risposta...")
        result = service.generate_response(request)
        
        # Aggiorna la richiesta con il risultato
        logger.debug(f"Aggiornando richiesta con risultato: status={result.get('status')}")
        request.response = result.get('response', '')
        request.status = result.get('status', 'failed')
        request.error_message = result.get('error_message', '')
        request.tokens_used = result.get('tokens_used')
        request.response_time_ms = result.get('response_time_ms')
        
        if request.status == 'completed':
            request.completed_at = timezone.now()
            logger.info("Richiesta completata con successo")
            
            # Se fa parte di una conversazione, aggiungi i messaggi
            if request.conversation:
                logger.debug("Aggiungendo messaggi alla conversazione...")
                # Aggiungi il messaggio dell'utente
                ConversationMessage.objects.create(
                    conversation=request.conversation,
                    role='user',
                    content=request.prompt
                )
                
                # Aggiungi la risposta dell'assistente
                ConversationMessage.objects.create(
                    conversation=request.conversation,
                    role='assistant',
                    content=request.response
                )
                logger.debug("Messaggi aggiunti alla conversazione")
        else:
            logger.warning(f"Richiesta completata con errore: {request.error_message}")
        
        request.save()
        logger.debug("Richiesta salvata nel database")
        return request
        
    except Exception as e:
        logger.error(f"Errore durante il processing della richiesta: {str(e)}")
        request.status = 'failed'
        request.error_message = str(e)
        request.save()
        return request


def get_available_workflow_files():
    """Restituisce la lista dei file workflow disponibili"""
    from django.conf import settings
    
    generated_workflows_dir = os.path.join(settings.BASE_DIR, 'src', 'generated_workflows')
    workflow_files = []
    
    if os.path.exists(generated_workflows_dir):
        # Cerca tutti i file .py nelle sottodirectory
        pattern = os.path.join(generated_workflows_dir, '*', '*.py')
        for file_path in glob.glob(pattern):
            # Estrai l'ID del workflow dal path
            workflow_id = os.path.basename(os.path.dirname(file_path))
            file_name = os.path.basename(file_path)
            
            # Ottieni informazioni sul file
            stat = os.stat(file_path)
            
            workflow_files.append({
                'workflow_id': workflow_id,
                'file_name': file_name,
                'file_path': file_path,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'file_size': stat.st_size
            })
    
    return sorted(workflow_files, key=lambda x: x['created_at'], reverse=True)

def resolve_workflow_file_path(workflow_id=None, workflow_file_name=None, workflow_file_path=None):
    """Risolve il path del file workflow da analizzare"""
    from django.conf import settings
    
    logger.info(f"🔍 Risolvendo path file workflow...")
    logger.debug(f"Parametri ricevuti - workflow_id: {workflow_id}, workflow_file_name: {workflow_file_name}, workflow_file_path: {workflow_file_path}")
    
    if workflow_file_path and os.path.exists(workflow_file_path):
        logger.info(f"Path completo fornito e verificato: {workflow_file_path}")
        return workflow_file_path
    
    generated_workflows_dir = os.path.join(settings.BASE_DIR, 'src', 'generated_workflows')
    logger.debug(f"Directory workflows: {generated_workflows_dir}")
    
    # Verifica che la directory base esista
    if not os.path.exists(generated_workflows_dir):
        logger.error(f"Directory base workflows non esiste: {generated_workflows_dir}")
        raise LLMServiceError(f"Directory base workflows non configurata: {generated_workflows_dir}")
    
    if workflow_id:
        # Cerca il file nella directory del workflow
        workflow_dir = os.path.join(generated_workflows_dir, str(workflow_id))
        logger.debug(f"Cercando in directory workflow: {workflow_dir}")
        
        if os.path.exists(workflow_dir):
            # Cerca il primo file .py nella directory
            py_files = glob.glob(os.path.join(workflow_dir, '*.py'))
            logger.debug(f"File .py trovati: {py_files}")
            
            if py_files:
                resolved_path = py_files[0]
                logger.info(f"File trovato tramite workflow_id: {resolved_path}")
                return resolved_path
            else:
                logger.warning(f"Directory workflow esiste ma non contiene file .py: {workflow_dir}")
        else:
            logger.warning(f"Directory workflow non esiste: {workflow_dir}")
            
            # Verifica se il workflow esiste nel database ma il file non è stato generato
            try:
                from ..workflow_generator.models import WorkflowGeneration
                workflow = WorkflowGeneration.objects.filter(id=workflow_id).first()
                if workflow:
                    logger.info(f"Workflow trovato nel DB - Status: {workflow.status}")
                    if workflow.status == 'failed':
                        raise LLMServiceError(f"Il workflow {workflow_id} è fallito durante la generazione: {workflow.error_message}")
                    elif workflow.status == 'processing':
                        raise LLMServiceError(f"Il workflow {workflow_id} è ancora in elaborazione. Riprova tra qualche momento.")
                    elif workflow.status == 'pending':
                        raise LLMServiceError(f"Il workflow {workflow_id} non è ancora stato processato.")
                    else:
                        raise LLMServiceError(f"Il workflow {workflow_id} sembra completato ma il file non è stato trovato nella directory prevista: {workflow_dir}")
                else:
                    raise LLMServiceError(f"Il workflow {workflow_id} non esiste nel database.")
            except Exception as db_error:
                logger.error(f"Errore nella verifica del database: {str(db_error)}")
                raise LLMServiceError(f"Il workflow {workflow_id} non è stato trovato. Verifica che sia stato generato correttamente.")
    
    if workflow_file_name:
        # Cerca il file per nome in tutte le directory
        pattern = os.path.join(generated_workflows_dir, '*', workflow_file_name)
        logger.debug(f"Cercando con pattern: {pattern}")
        
        matches = glob.glob(pattern)
        logger.debug(f"File trovati con pattern: {matches}")
        
        if matches:
            resolved_path = matches[0]
            logger.info(f"File trovato tramite workflow_file_name: {resolved_path}")
            return resolved_path
    
    # Lista i file disponibili per aiutare il debug
    available_workflows = []
    try:
        if os.path.exists(generated_workflows_dir):
            for item in os.listdir(generated_workflows_dir):
                item_path = os.path.join(generated_workflows_dir, item)
                if os.path.isdir(item_path):
                    py_files = glob.glob(os.path.join(item_path, '*.py'))
                    if py_files:
                        available_workflows.append({
                            'id': item,
                            'files': [os.path.basename(f) for f in py_files]
                        })
        
        if available_workflows:
            logger.info(f"Workflow disponibili: {available_workflows}")
            available_list = ', '.join([f"{w['id']} ({', '.join(w['files'])})" for w in available_workflows])
            raise LLMServiceError(f"File workflow non trovato. Workflow disponibili: {available_list}")
        else:
            logger.warning("Nessun workflow generato trovato nella directory")
            raise LLMServiceError("Nessun workflow generato trovato. Assicurati di aver generato almeno un workflow prima di richiederne l'analisi.")
            
    except Exception as list_error:
        logger.error(f"Errore nel listare i workflow disponibili: {str(list_error)}")
        
    logger.error("File workflow non trovato con nessuno dei metodi")
    raise LLMServiceError("File workflow non trovato")

def process_workflow_file_analysis(analysis: 'WorkflowFileAnalysis') -> 'WorkflowFileAnalysis':
    """Processa un'analisi di file workflow tramite LLM"""
    logger.info(f"Iniziando analisi workflow file...")
    logger.debug(f"Analisi ID: {analysis.id if analysis.id else 'NUOVO'}, Path: {analysis.workflow_file_path}")
    logger.debug(f"Modello: {analysis.model.name}, Provider: {analysis.model.provider.name}")
    
    try:
        analysis.status = 'processing'
        analysis.save()
        logger.debug("Status analisi aggiornato a 'processing'")
        
        # Leggi il contenuto del file
        logger.info(f"Leggendo file: {analysis.workflow_file_path}")
        if not os.path.exists(analysis.workflow_file_path):
            error_msg = f"File non trovato: {analysis.workflow_file_path}"
            logger.error(f"{error_msg}")
            raise LLMServiceError(error_msg)
        
        with open(analysis.workflow_file_path, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
        
        logger.debug(f"Contenuto file letto: {len(workflow_content)} caratteri")
        analysis.workflow_content = workflow_content
        analysis.save()
        
        # Costruisci il prompt completo con istruzioni specifiche per solo codice
        default_system_prompt = """Sei un esperto sviluppatore Python specializzato in Metaflow. 
Analizza al fine di completare e migliorare il codice fornito. 
IMPORTANTE: Rispondi SOLO con il codice Python migliorato, senza commenti, spiegazioni o testo aggiuntivo.
Il tuo output deve essere codice Python valido che può essere salvato direttamente in un file .py."""
        
        system_prompt = analysis.system_prompt if analysis.system_prompt else default_system_prompt
        logger.debug(f"System prompt lunghezza: {len(system_prompt)} caratteri")
        
        user_prompt_parts = [
            "Migliora il seguente codice Python di un workflow Metaflow:",
            "",
            "```python",
            workflow_content,
            "```"
        ]
        
        if analysis.user_prompt:
            logger.debug(f"User prompt personalizzato fornito: {len(analysis.user_prompt)} caratteri")
            user_prompt_parts.extend([
                "",
                "Richieste specifiche:",
                analysis.user_prompt
            ])
        
        user_prompt_parts.extend([
            "",
            "RICORDA: Rispondi SOLO con il codice Python migliorato, senza commenti o spiegazioni."
        ])
        
        full_user_prompt = "\n".join(user_prompt_parts)
        logger.debug(f"Prompt completo creato: {len(full_user_prompt)} caratteri")
        
        # Crea una richiesta LLM temporanea per l'analisi
        from .models import LLMRequest
        logger.info("Creando richiesta LLM temporanea...")
        
        temp_request = LLMRequest(
            model=analysis.model,
            prompt=full_user_prompt,
            system_message=system_prompt,
            temperature=0.3  # Temperatura più bassa per analisi più consistenti
        )
        logger.debug("Richiesta LLM temporanea creata")
        
        # Ottieni il servizio appropriato
        logger.info(f"Ottenendo servizio per provider: {analysis.model.provider.name}")
        service = LLMServiceFactory.get_service(analysis.model.provider.name)
        
        # Genera la risposta
        logger.info("Generando risposta analisi...")
        result = service.generate_response(temp_request)
        
        # Aggiorna l'analisi con il risultato
        logger.debug(f"Aggiornando analisi con risultato: status={result.get('status')}")
        analysis.analysis_response = result.get('response', '')
        analysis.status = result.get('status', 'failed')
        analysis.error_message = result.get('error_message', '')
        analysis.tokens_used = result.get('tokens_used')
        analysis.response_time_ms = result.get('response_time_ms')
        
        if analysis.status == 'completed' and analysis.analysis_response:
            analysis.completed_at = timezone.now()
            logger.info("Analisi completata con successo")
            
            # Pulisci la risposta rimuovendo eventuali markdown code blocks
            logger.debug("Pulendo risposta da markdown...")
            cleaned_response = analysis.analysis_response.strip()
            original_length = len(cleaned_response)
            
            if cleaned_response.startswith('```python'):
                cleaned_response = cleaned_response[9:]  # Rimuovi ```python
                logger.debug("Rimosso ```python iniziale")
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Rimuovi ```
                logger.debug("Rimosso ``` iniziale")
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Rimuovi ``` finale
                logger.debug("Rimosso ``` finale")
            
            cleaned_response = cleaned_response.strip()
            logger.debug(f"Pulizia completata: {original_length} -> {len(cleaned_response)} caratteri")
            
            # Sovrascrivi il file originale con il codice migliorato
            try:
                logger.info(f"Sovrascrivendo file originale: {analysis.workflow_file_path}")
                with open(analysis.workflow_file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_response)
                
                # Aggiorna il campo workflow_content con il nuovo contenuto
                analysis.workflow_content = cleaned_response
                logger.info("File sovrascritto con successo")
                
                # DEPLOYMENT AUTOMATICO DEL FILE FINALE
                try:
                    logger.info("Iniziando deployment del file migliorato...")
                    from ..ssh_deployment.services import deploy_workflow_to_ml_runner, deploy_workflow_to_ml_runner_with_folder
                    
                    # Estrai il workflow_id dal path
                    workflow_id = None
                    try:
                        # Il path dovrebbe essere: {BASE_DIR}/src/generated_workflows/{workflow_id}/{file_name}
                        # Normalizziamo il path per Windows
                        normalized_path = os.path.normpath(analysis.workflow_file_path)
                        path_parts = normalized_path.split(os.sep)
                        
                        if 'generated_workflows' in path_parts:
                            workflow_idx = path_parts.index('generated_workflows')
                            if len(path_parts) > workflow_idx + 1:
                                workflow_id = path_parts[workflow_idx + 1]
                                logger.info(f"Workflow ID estratto: {workflow_id}")
                        
                        # Fallback: cerca pattern UUID nel path
                        if not workflow_id:
                            import re
                            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                            for part in path_parts:
                                if re.match(uuid_pattern, part, re.IGNORECASE):
                                    workflow_id = part
                                    logger.info(f"Workflow ID trovato tramite UUID pattern: {workflow_id}")
                                    break
                                    
                    except Exception as extract_error:
                        logger.warning(f"Impossibile estrarre workflow ID: {extract_error}")
                        logger.debug(f"Path analizzato: {analysis.workflow_file_path}")
                    
                    # Nome del file
                    file_name = os.path.basename(analysis.workflow_file_path)
                    
                    # Se abbiamo un workflow_id, crea una cartella specifica
                    if workflow_id:
                        # Deployment con cartella workflow_id
                        deployment = deploy_workflow_to_ml_runner_with_folder(
                            file_content=cleaned_response,
                            file_name=file_name,
                            workflow_id=workflow_id
                        )
                        
                        logger.info(f"File deployato in cartella: {workflow_id}/{file_name}")
                        logger.info(f"Path Jupyter: {workflow_id}/{file_name}")
                    else:
                        # Deployment normale
                        deployment = deploy_workflow_to_ml_runner(
                            file_content=cleaned_response,
                            file_name=file_name,
                            workflow_id=workflow_id
                        )
                        logger.info(f"File deployato: {file_name}")
                    
                    logger.info(f"Status deployment: {deployment.status}")
                    
                except Exception as deployment_error:
                    logger.error(f"Errore nel deployment (file comunque aggiornato): {str(deployment_error)}")
                
            except Exception as file_error:
                error_msg = f"Errore nella scrittura del file: {str(file_error)}"
                logger.error(f"{error_msg}")
                analysis.error_message = error_msg
                analysis.status = 'failed'
        else:
            logger.warning(f"Analisi non completata correttamente: {analysis.error_message}")
        
        analysis.save()
        logger.debug("Analisi salvata nel database")
        return analysis
        
    except Exception as e:
        logger.error(f"Errore durante l'analisi workflow: {str(e)}")
        analysis.status = 'failed'
        analysis.error_message = str(e)
        analysis.save()
        return analysis
