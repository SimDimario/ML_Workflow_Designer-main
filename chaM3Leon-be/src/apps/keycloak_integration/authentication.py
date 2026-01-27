from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt

class KeycloakUser:
    def __init__(self, username, payload):
        self.username = username
        self.payload = payload
        self.is_authenticated = True   

class KeycloakAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth = request.headers.get("Authorization")

        if not auth:
            return None

        try:
            prefix, token = auth.split()
            if prefix.lower() != "bearer":
                raise AuthenticationFailed("Invalid token prefix")

            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )

        except Exception:
            raise AuthenticationFailed("Invalid token")

        username = payload.get("preferred_username")
        if not username:
            raise AuthenticationFailed("User not found in token")

        user = KeycloakUser(username, payload)

        return (user, token)
