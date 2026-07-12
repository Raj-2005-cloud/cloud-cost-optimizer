from django.db import models
from django.contrib.auth.models import User

class AWSAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    access_key = models.CharField(max_length=100)
    secret_key = models.CharField(max_length=200)
    region = models.CharField(max_length=50, default="ap-south-1")
    alert_email = models.EmailField(max_length=255, blank=True, null=True)

    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.region}"


class DismissedResource(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource_id = models.CharField(max_length=255)
    service = models.CharField(max_length=50) # 'EC2', 'EBS', 'S3', 'RDS'
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'resource_id')

    def __str__(self):
        return f"{self.user.username} dismissed {self.service} - {self.resource_id}"