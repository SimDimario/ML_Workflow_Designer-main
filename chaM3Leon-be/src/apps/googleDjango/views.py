from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import requests

User = get_user_model()

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.models import SocialAccount


class GoogleLoginAPIView(APIView):
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"error": "Token mancante"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # ✅ verifica ID token Google
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.SOCIALACCOUNT_GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response(
                {"error": "Token Google non valido"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not idinfo.get("email_verified"):
            return Response(
                {"error": "Email non verificata"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        google_sub = idinfo["sub"]

        # 🔎 CERCA UTENTE GIÀ REGISTRATO
        try:
            social = SocialAccount.objects.get(
                provider="google",
                uid=google_sub
            )
        except SocialAccount.DoesNotExist:
            return Response(
                {"error": "Utente non registrato"},
                status=status.HTTP_403_FORBIDDEN
            )

        user = social.user

        # 🔑 JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        })

    

from rest_framework.permissions import IsAuthenticated

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return {
            "email": request.user.email,
            "username": request.user.username
        }


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.config.settings.base import SOCIALACCOUNT_GOOGLE_CLIENT_ID

class GooglePrefillAPIView(APIView):
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"error": "Token mancante"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                SOCIALACCOUNT_GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response(
                {"error": "Token Google non valido"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not idinfo.get("email_verified"):
            return Response(
                {"error": "Email non verificata"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response({
            "email": idinfo["email"],
            "first_name": idinfo.get("given_name", ""),
            "last_name": idinfo.get("family_name", ""),
            "avatar": idinfo.get("picture"),
            "google_sub": idinfo["sub"],  # ⚠️ servirà dopo
        })




User = get_user_model()


class GoogleRegisterAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")
        google_sub = request.data.get("google_sub")
        username = request.data.get("username")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        if not all([email, google_sub, username]):
            return Response(
                {"error": "Campi mancanti"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔒 evita doppie registrazioni Google
        if SocialAccount.objects.filter(
            provider="google",
            uid=google_sub
        ).exists():
            return Response(
                {"error": "Account Google già registrato"},
                status=status.HTTP_409_CONFLICT
            )

        # 🔒 evita doppie email
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email già registrata"},
                status=status.HTTP_409_CONFLICT
            )

        # 🆕 crea utente
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        # 🔗 collega Google
        SocialAccount.objects.create(
            user=user,
            provider="google",
            uid=google_sub,
            extra_data={},
        )

        # 🔑 JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        })
