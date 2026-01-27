from django.contrib import admin
from .models import LLMProvider, LLMModel, LLMRequest, LLMConversation, ConversationMessage

@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name']

@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'provider', 'max_tokens', 'supports_streaming', 'is_active']
    list_filter = ['provider', 'supports_streaming', 'is_active', 'created_at']
    search_fields = ['name', 'display_name']

class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ['created_at']

@admin.register(LLMConversation)
class LLMConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__username']
    inlines = [ConversationMessageInline]

@admin.register(LLMRequest)
class LLMRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'model', 'status', 'tokens_used', 'response_time_ms', 'created_at']
    list_filter = ['status', 'model__provider', 'created_at']
    search_fields = ['user__username', 'prompt']
    readonly_fields = ['id', 'created_at', 'completed_at']
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('id', 'user', 'model', 'conversation')
        }),
        ('Richiesta', {
            'fields': ('prompt', 'system_message', 'max_tokens', 'temperature')
        }),
        ('Risposta', {
            'fields': ('response', 'status', 'error_message')
        }),
        ('Metadati', {
            'fields': ('tokens_used', 'response_time_ms', 'created_at', 'completed_at')
        }),
    )
