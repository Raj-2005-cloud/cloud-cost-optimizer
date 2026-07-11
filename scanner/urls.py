from django.urls import path
from . import views

urlpatterns = [
    path("ec2/", views.scan_ec2, name="scan_ec2"),
    path("s3/", views.scan_s3, name="scan_s3"),
    path("ebs/", views.scan_ebs, name="scan_ebs"),
     path("rds/", views.scan_rds, name="scan_rds"),
]