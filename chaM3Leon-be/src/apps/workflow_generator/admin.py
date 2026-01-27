from django.contrib import admin
from .models import WorkflowGeneration

@admin.register(WorkflowGeneration)
class WorkflowGenerationAdmin(admin.ModelAdmin):
    list_display = ['config_name', 'generated_class_name', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['config_name', 'generated_class_name']
    readonly_fields = ['id', 'created_at', 'completed_at']
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('id', 'user', 'config_name', 'status')
        }),
        ('Configurazione Input', {
            'fields': ('config_data',),
            'classes': ('collapse',)
        }),
        ('Output Generato', {
            'fields': ('generated_class_name', 'generated_file_path', 'generated_content'),
            'classes': ('collapse',)
        }),
        ('Errori', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
