from django.urls import path
from . import views

urlpatterns = [
    path("", views.cost_dashboard, name="billing"),
]