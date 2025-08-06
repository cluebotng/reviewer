import logging
from pathlib import PosixPath
from typing import Optional, List

import requests
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia.management import WikipediaManagement
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


def notify_user_review_rights_granted(user: User, notify_user: bool = True, reason: Optional[str] = None):
    messages = Messages()
    IrcRelay().send_message(messages.notify_irc_about_granted_reviewer_access(user, reason))
    if notify_user:
        WikipediaManagement().send_user_message(user.username, messages.notify_user_about_reviewer_access(user))


def update_access_from_rights(user: User, user_rights: List[str]) -> None:
    for right in ["rollback", "block", "deleterevision", "editprotected"]:
        if right in user_rights and not user.is_reviewer:
            logger.info(f"Marking {user.username} as a reviewer based on {right} right")
            user.is_reviewer = True
            user.save()
            notify_user_review_rights_granted(user, notify_user=False, reason=f"user has '{right}' rights")


def create_user_with_central_auth_mapping(username: str) -> Optional[User]:
    central_uid, user_rights = WikipediaReader().get_user(username)
    if central_uid:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create(username=username)
            UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)

        update_access_from_rights(user, user_rights)
        return user
    return None


def download_file(
    target: PosixPath,
    url: str,
    timeout: int = 10,
    chunk_size: int = 512,
    user_agent: str = "ClueBot NG Reviewer - Download File",
):
    r = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": user_agent,
        },
        stream=True,
    )
    r.raise_for_status()
    with target.open("wb") as fh:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fh.write(chunk)
