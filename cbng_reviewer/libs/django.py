import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class AuthenticatedRequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._logger = logging.getLogger("cbng_reviewer.access_log")

    def __call__(self, request: HttpRequest):
        processing_start = time.monotonic()
        response = self.get_response(request)
        processing_finish = time.monotonic()

        if request.user.is_authenticated:
            self._logger.info(
                '%s [%s] "%s %s" %d %s "%s" "%s" %dms',
                request.user.get_username(),
                datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000"),
                request.method,
                request.get_full_path(),
                response.status_code,
                response.get("Content-Length", "-"),
                request.META.get("HTTP_REFERER", "-"),
                request.META.get("HTTP_USER_AGENT", "-"),
                int((processing_finish - processing_start) * 1000),
            )

        return response


def admin_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            # Require the user to be authenticated
            if not request.user.is_authenticated:
                return redirect_to_login(request.path)

            # Require the user to be an admin
            if not request.user.is_admin:
                raise PermissionDenied

            # All good
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def reviewer_required() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            # Require the user to be authenticated
            if not request.user.is_authenticated:
                return redirect_to_login(request.path)

            # Require the user to be a reviewer (or an admin)
            if not (request.user.is_admin or (request.user.is_reviewer and not settings.CBNG_ADMIN_ONLY)):
                raise PermissionDenied

            # All good
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
