from django.contrib import admin
from .models import SSHConnection, FileDeployment


@admin.register(SSHConnection)
class SSHConnectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'username', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'host', 'username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('id', 'name', 'is_active')
        }),
        ('Connessione', {
            'fields': ('host', 'port', 'username', 'password', 'private_key_path')
        }),
        ('Configurazione', {
            'fields': ('remote_base_path',)
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FileDeployment)
class FileDeploymentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'ssh_connection', 'status', 'workflow_id', 'created_at']
    list_filter = ['status', 'created_at', 'ssh_connection']
    search_fields = ['file_name', 'workflow_id', 'ssh_connection__name']
    readonly_fields = ['id', 'created_at', 'started_at', 'completed_at']
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('id', 'ssh_connection', 'user', 'status')
        }),
        ('File', {
            'fields': ('file_name', 'local_file_path', 'remote_file_path')
        }),
        ('Contenuto', {
            'fields': ('file_content',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('workflow_id', 'deployment_notes', 'error_message')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )