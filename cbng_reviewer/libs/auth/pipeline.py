from django.conf import settings

from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker


def check_for_auto_reviewer_rights(backend, user, *args, **kwargs):
    if backend.name == settings.SOCIAL_AUTH_BACKEND_NAME:
        AutoReviewerRightsChecker().execute(user)
