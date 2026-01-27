from django.shortcuts import redirect, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.keycloak_client import delete_user, login as kc_login
from .models import AuthSession
from .services.keycloak_client import get_google_login_url, exchange_code_for_token

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            token = kc_login(
                request.data["username"],
                request.data["password"]
            )
        except Exception:
            return Response(
                {"error": "Credenziali errate"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        AuthSession.objects.create(
            username=request.data["username"],
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            expires_in=token["expires_in"],
        )

        return Response({
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
        })

class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            token = refresh(request.data["refresh_token"])
        except Exception:
            return Response(status=401)

        return Response(token)

class LogoutView(APIView):
    def post(self, request):
        logout(request.data["refresh_token"])
        return Response(status=204)

import jwt
from django.conf import settings
from .authentication import KeycloakAuthentication
from rest_framework.permissions import IsAuthenticated
from .services.keycloak_client import public_keys

class MeView(APIView):
    authentication_classes = [KeycloakAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "token_payload": request.user.payload
        })
    
class PublicKeysView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        keys = public_keys()
        return Response(keys)


class UserCreatedView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data = request.data

        try:
            create_user(
                username=data["username"],
                password=data["password"],
                email=data.get("email", ""),
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "user created"},
            status=status.HTTP_201_CREATED,
        )

from .services.keycloak_client import refresh, logout,create_user

class UserDeletedView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request):
        data = request.data

        try:
            delete_user(
                username=data["username"],
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "user deleted"},
            status=status.HTTP_200_OK,
        )
    
