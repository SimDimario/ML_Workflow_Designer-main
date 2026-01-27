from django.apps import AppConfig


class SshDeploymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.ssh_deployment'
    verbose_name = 'SSH Deployment'
