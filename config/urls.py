from django.contrib import admin
from django.urls import path, include
from dashboard.views import home, dashboard, analytics

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("analytics/", analytics, name="analytics"),

    path("", include("accounts.urls")),
    path("scanner/", include("scanner.urls")),
    path("billing/", include("billing.urls")),
    path("optimizer/", include("optimizer.urls")),
    path("reports/", include("reports.urls")), 
]