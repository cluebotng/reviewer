from django.conf import settings
from django.contrib import auth
from django.shortcuts import render, redirect

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


@reviewer_required()
def reviewer(request):
    return render(request, "cbng_reviewer/reviewer.html")
