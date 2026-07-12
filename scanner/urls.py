from django.urls import path
from . import views

urlpatterns = [
    path("ec2/", views.scan_ec2, name="scan_ec2"),
    path("s3/", views.scan_s3, name="scan_s3"),
    path("ebs/", views.scan_ebs, name="scan_ebs"),
    path("rds/", views.scan_rds, name="scan_rds"),
    path("ec2/stop/<str:instance_id>/", views.stop_ec2_instance, name="stop_ec2"),
    path("ec2/terminate/<str:instance_id>/", views.terminate_ec2_instance, name="terminate_ec2"),
    path("ebs/delete/<str:volume_id>/", views.delete_ebs_volume, name="delete_ebs"),
    path("rds/delete/<str:region_name>/<str:db_id>/", views.delete_rds_instance, name="delete_rds"),
    path("s3/delete/<str:bucket_name>/", views.delete_s3_bucket, name="delete_s3"),
    path("dismiss/<str:service>/<str:resource_id>/", views.dismiss_resource, name="dismiss_resource"),
    path("alerts/", views.alert_center, name="alert_center"),
]