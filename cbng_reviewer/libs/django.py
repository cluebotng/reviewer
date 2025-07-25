from functools import wraps
from typing import Callable, Any

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from cbng_reviewer import settings


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
