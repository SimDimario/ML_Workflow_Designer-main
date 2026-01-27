from django.contrib import admin
from django.urls import path, include
from .views import GoogleLoginAPIView, MeView, GooglePrefillAPIView,GoogleRegisterAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
   # path('accounts/', include('allauth.urls')),  # login Google
    path('auth/login/google', GoogleLoginAPIView.as_view()),
    path('auth/me', MeView.as_view()),
    path('auth/google/prefill', GooglePrefillAPIView.as_view()),
    path('auth/register/google', GoogleRegisterAPIView.as_view()),


    ]
