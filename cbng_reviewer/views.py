import secrets

from django.conf import settings
from django.contrib import auth
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from cbng_reviewer.libs.django import reviewer_required
from cbng_reviewer.libs.metrics import MetricsExporter
from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.models import User


def home(request):
    statistics = Statistics()
    user_statistics = cache.get_or_set(
        "home_page_user_statistics",
        lambda: sorted(
            [(username, stats["total_classifications"]) for username, stats in statistics.get_user_statistics().items()]
            + [(username, edit_count) for username, edit_count in statistics.get_historical_user_statistics()],
            key=lambda x: x[1],
            reverse=True,
        ),
        300,
    )
    return render(
        request,
        "cbng_reviewer/home.html",
        {
            "user_statistics": user_statistics,
            "administrators": User.objects.filter(is_admin=True).values_list("username", flat=True),
            "admin_only_mode": settings.CBNG_ADMIN_ONLY,
            "user": request.user,
        },
    )


def login(request):
    next_url = request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""

    if request.user.is_authenticated:
        return redirect(next_url or settings.LOGIN_REDIRECT_URL)
    return render(request, "cbng_reviewer/login.html", {"next": next_url})


def logout(request):
    auth.logout(request)
    return redirect("/")


def metrics(request):
    if settings.CBNG_MONITORING_SHARED_SECRET and not secrets.compare_digest(
        request.headers.get("Authorization", "").encode(), f"Bearer {settings.CBNG_MONITORING_SHARED_SECRET}".encode()
    ):
        return HttpResponseForbidden()

    MetricsExporter().update_metrics()
    return HttpResponse(content=generate_latest(), content_type=CONTENT_TYPE_LATEST)


@reviewer_required()
def reviewer(request):
    return render(request, "cbng_reviewer/reviewer.html")
