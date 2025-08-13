from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

from cbng_reviewer import views

urlpatterns = [
    # For developers
    path("internal/admin/", admin.site.urls),
    path("internal/health/", lambda r: HttpResponse("OK")),
    path("internal/metrics/", views.metrics),
    # Authentication
    path("oauth/", include("social_django.urls", namespace="social")),
    path("logout/", views.logout, name="logout"),
    # Api
    path("api/", include("cbng_reviewer.api.urls")),
    # Admin
    path("admin/", include("cbng_reviewer.admin.urls"), name="admin"),
    # Reviewer
    path("review/", views.reviewer, name="review"),
    # Public
    path("", views.home, name="home"),
]
