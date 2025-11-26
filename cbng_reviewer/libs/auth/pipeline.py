import logging

from django.conf import settings

from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader


logger = logging.getLogger(__name__)


def update_username_from_central_auth(backend, user, *args, **kwargs):
    # The default social auth pipeline mangles the usernames
    # While they get fixed by `update_usernames`, the auto allocation of rights doesn't happen
    if backend.name == settings.SOCIAL_AUTH_BACKEND_NAME:
        if central_user := WikipediaReader().get_central_user(user_id=user.central_user_id):
            if user.username != central_user.username:
                logger.info(f"Fixing {user.username} to {central_user.username} ({central_user.id})")
                user.username = central_user.username
                user.save()


def check_for_auto_reviewer_rights(backend, user, *args, **kwargs):
    if backend.name == settings.SOCIAL_AUTH_BACKEND_NAME:
        # Note: notify IRC but not the user, this is within their login flow so is transparent
        AutoReviewerRightsChecker().execute(user, notify_user=False)
