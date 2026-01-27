from django.conf import settings
from src.config.settings.base import KEYCLOAK

def kc_url(path):
    return KEYCLOAK["BASE_URL"] + path.format(
        realm=KEYCLOAK["REALM"]
    )
