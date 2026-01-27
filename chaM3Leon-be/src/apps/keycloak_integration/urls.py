from django.urls import path
from .views import LoginView, RefreshView, LogoutView, MeView, PublicKeysView,UserCreatedView,UserDeletedView


urlpatterns = [
    path("auth/login", LoginView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/logout", LogoutView.as_view()),
    path("auth/me", MeView.as_view()),
    path("auth/keys", PublicKeysView.as_view()),
    path("auth/user", UserCreatedView.as_view()),
    path("auth/user/delete", UserDeletedView.as_view()),



]
