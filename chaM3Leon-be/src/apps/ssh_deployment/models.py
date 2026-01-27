from django.db import models
from django.contrib.auth.models import User
import uuid


class SSHConnection(models.Model):
    """Modello per gestire le connessioni SSH"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Nome identificativo della connessione")
    host = models.CharField(max_length=255, help_text="Hostname o IP del server")
    port = models.IntegerField(default=22, help_text="Porta SSH")
    username = models.CharField(max_length=100, help_text="Username per la connessione")
    password = models.CharField(max_length=255, blank=True, help_text="Password (opzionale se si usa chiave)")
    private_key_path = models.CharField(max_length=500, blank=True, help_text="Path alla chiave privata")
    remote_base_path = models.CharField(max_length=500, default="/app/workflows", help_text="Path base remoto dove salvare i file")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "SSH Connection"
        verbose_name_plural = "SSH Connections"

    def __str__(self):
        return f"{self.name} ({self.username}@{self.host}:{self.port})"


class FileDeployment(models.Model):
    """Modello per tracciare i deployment dei file"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ssh_connection = models.ForeignKey(SSHConnection, on_delete=models.CASCADE, related_name='deployments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='file_deployments')
    
    # File information
    local_file_path = models.CharField(max_length=1000, help_text="Path locale del file")
    remote_file_path = models.CharField(max_length=1000, help_text="Path remoto dove salvare il file")
    file_name = models.CharField(max_length=255, help_text="Nome del file")
    file_content = models.TextField(help_text="Contenuto del file da deployare")
    
    # Deployment status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, help_text="Messaggio di errore se il deployment fallisce")
    
    # Metadata
    workflow_id = models.UUIDField(null=True, blank=True, help_text="ID del workflow associato")
    deployment_notes = models.TextField(blank=True, help_text="Note aggiuntive sul deployment")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "File Deployment"
        verbose_name_plural = "File Deployments"

    def __str__(self):
        return f"{self.file_name} -> {self.ssh_connection.name} ({self.status})"
