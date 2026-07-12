from django.urls import path
from . import views

urlpatterns = [
    path("pdf/", views.generate_pdf, name="generate_pdf"),
]