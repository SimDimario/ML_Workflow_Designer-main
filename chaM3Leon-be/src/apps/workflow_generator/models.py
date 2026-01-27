from django.db import models
from django.contrib.auth.models import User
import uuid
import os

class WorkflowGeneration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workflow_generations', null=True, blank=True)
    config_name = models.CharField(max_length=200)
    config_data = models.JSONField()
    generated_class_name = models.CharField(max_length=200, blank=True)
    generated_file_path = models.CharField(max_length=500, blank=True)
    generated_content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Workflow {self.config_name} - {self.status}"
    
    @property
    def output_directory(self):
        return os.path.join('/app/src/generated_workflows', str(self.id))