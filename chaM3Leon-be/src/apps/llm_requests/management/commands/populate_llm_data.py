from django.core.management.base import BaseCommand
from src.apps.llm_requests.models import LLMProvider, LLMModel

class Command(BaseCommand):
    help = 'Popola il database con provider e modelli LLM predefiniti'

    def handle(self, *args, **options):
        self.stdout.write('Popolamento dei provider e modelli LLM...')
        
        # Crea i provider
        providers_data = [
            {'name': 'openai', 'display_name': 'OpenAI'},
            {'name': 'anthropic', 'display_name': 'Anthropic'},
            {'name': 'gemini', 'display_name': 'Google Gemini'},
        ]
        
        for provider_data in providers_data:
            provider, created = LLMProvider.objects.get_or_create(
                name=provider_data['name'],
                defaults={'display_name': provider_data['display_name']}
            )
            if created:
                self.stdout.write(f'✓ Creato provider: {provider.display_name}')
            else:
                self.stdout.write(f'- Provider già esistente: {provider.display_name}')
        
        # Crea i modelli
        models_data = [
            # OpenAI Models
            {
                'provider': 'openai',
                'name': 'gpt-4o',
                'display_name': 'GPT-4o',
                'max_tokens': 4096,
                'supports_streaming': True
            },
            {
                'provider': 'openai',
                'name': 'gpt-4o-mini',
                'display_name': 'GPT-4o Mini',
                'max_tokens': 16384,
                'supports_streaming': True
            },
            {
                'provider': 'openai',
                'name': 'gpt-3.5-turbo',
                'display_name': 'GPT-3.5 Turbo',
                'max_tokens': 4096,
                'supports_streaming': True
            },
            
            # Anthropic Models
            {
                'provider': 'anthropic',
                'name': 'claude-3-5-sonnet-20241022',
                'display_name': 'Claude 3.5 Sonnet',
                'max_tokens': 8192,
                'supports_streaming': True
            },
            {
                'provider': 'anthropic',
                'name': 'claude-3-haiku-20240307',
                'display_name': 'Claude 3 Haiku',
                'max_tokens': 4096,
                'supports_streaming': True
            },
            
            # Gemini Models
            {
                'provider': 'gemini',
                'name': 'gemini-2.5-flash',
                'display_name': 'Gemini 2.5 Flash',
                'max_tokens': 8192,
                'supports_streaming': False
            },
            {
                'provider': 'gemini',
                'name': 'gemini-1.5-pro',
                'display_name': 'Gemini 1.5 Pro',
                'max_tokens': 32768,
                'supports_streaming': False
            },
        ]
        
        for model_data in models_data:
            provider = LLMProvider.objects.get(name=model_data['provider'])
            model, created = LLMModel.objects.get_or_create(
                provider=provider,
                name=model_data['name'],
                defaults={
                    'display_name': model_data['display_name'],
                    'max_tokens': model_data['max_tokens'],
                    'supports_streaming': model_data['supports_streaming']
                }
            )
            if created:
                self.stdout.write(f'✓ Creato modello: {model.display_name}')
            else:
                self.stdout.write(f'- Modello già esistente: {model.display_name}')
        
        self.stdout.write(
            self.style.SUCCESS('✅ Popolamento completato con successo!')
        )