from django.db import models

class AuthSession(models.Model):
    username = models.CharField(max_length=150)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

