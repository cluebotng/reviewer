from django.conf import settings
from django.contrib import auth
from django.http import HttpResponse
from django.shortcuts import render, redirect
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from cbng_reviewer.libs.django import reviewer_required
from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.models import User


def home(request):
    return render(
        request,
        "cbng_reviewer/home.html",
        {
            "user_statistics": sorted(
                [
                    (username, stats["total_classifications"])
                    for username, stats in Statistics().get_user_statistics().items()
                ],
                key=lambda x: x[1],
                reverse=True,
            ),
            "administrators": User.objects.filter(is_admin=True).values_list("username", flat=True),
            "admin_only_mode": settings.CBNG_ADMIN_ONLY,
            "user": request.user,
        },
    )


def logout(request):
    auth.logout(request)
    return redirect("/")


def metrics(request):
    return HttpResponse(content=generate_latest(), content_type=CONTENT_TYPE_LATEST)


@reviewer_required()
def reviewer(request):
    return render(request, "cbng_reviewer/reviewer.html")
