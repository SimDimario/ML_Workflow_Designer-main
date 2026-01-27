# src/apps/googleDjango/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        # Qui indichi la tua view Django che genera JWT
        return "/auth/social/callback/"
