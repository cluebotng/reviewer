from django.conf import settings

from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker


def check_for_auto_reviewer_rights(backend, user, *args, **kwargs):
    if backend.name == settings.SOCIAL_AUTH_BACKEND_NAME:
        # Note: notify IRC but not the user, this is within their login flow so is transparent
        AutoReviewerRightsChecker().execute(user, notify_user=False)
