from django.db import models
from django.contrib.auth.models import User

class AWSAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    access_key = models.CharField(max_length=100)
    secret_key = models.CharField(max_length=200)
    region = models.CharField(max_length=50, default="ap-south-1")

    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.region}"