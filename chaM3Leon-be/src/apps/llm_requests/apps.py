from django.apps import AppConfig


class LlmRequestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.llm_requests'
    verbose_name = 'LLM Requests'
    
    def ready(self):
        # Importa i segnali se necessario
        pass
