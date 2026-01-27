from django.db import models
from django.contrib.auth.models import User
import uuid

class LLMProvider(models.Model):
    """Modello per i provider LLM supportati"""
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('gemini', 'Google Gemini'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.display_name

class LLMModel(models.Model):
    """Modello per i modelli LLM specifici di ogni provider"""
    provider = models.ForeignKey(LLMProvider, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)  # es: gpt-4, claude-3-sonnet, gemini-2.5-flash
    display_name = models.CharField(max_length=150)
    max_tokens = models.IntegerField(null=True, blank=True)
    supports_streaming = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['provider', 'name']
    
    def __str__(self):
        return f"{self.provider.display_name} - {self.display_name}"

class LLMConversation(models.Model):
    """Modello per le conversazioni con LLM"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='llm_conversations', null=True, blank=True)  # TEMPORANEO per test
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"Conversation {self.id} - {username}"

class ConversationMessage(models.Model):
    """Modello per i messaggi in una conversazione"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(LLMConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class LLMRequest(models.Model):
    """Modello per le richieste singole agli LLM"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='llm_requests', null=True, blank=True)  # TEMPORANEO per test
    conversation = models.ForeignKey(LLMConversation, on_delete=models.CASCADE, related_name='requests', null=True, blank=True)
    model = models.ForeignKey(LLMModel, on_delete=models.CASCADE)
    
    # Parametri della richiesta
    prompt = models.TextField()
    system_message = models.TextField(blank=True)
    max_tokens = models.IntegerField(null=True, blank=True)
    temperature = models.FloatField(default=0.7)
    
    # Risposta
    response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Metadati
    tokens_used = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Request {self.id} - {self.model.display_name}"

class WorkflowFileAnalysis(models.Model):
    """Modello per l'analisi dei file workflow generati tramite LLM"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflow_analyses', null=True, blank=True)
    model = models.ForeignKey(LLMModel, on_delete=models.CASCADE)
    
    # File workflow da analizzare - RESO OPZIONALE
    workflow_file_path = models.CharField(max_length=500, blank=True)  # Path del file nella cartella generated_workflows
    workflow_content = models.TextField(blank=True)  # Contenuto del file Python
    
    # Prompting
    system_prompt = models.TextField(default="Sei un esperto sviluppatore Python specializzato nell'analisi di workflow Metaflow. Analizza il codice fornito e fornisci feedback dettagliato su struttura, logica, possibili miglioramenti e best practices.")
    user_prompt = models.TextField(blank=True)  # Prompt aggiuntivo dell'utente
    
    # Risposta LLM
    analysis_response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Metadati
    tokens_used = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Workflow Analysis {self.id} - {self.workflow_file_path}"
