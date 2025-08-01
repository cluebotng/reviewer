from pathlib import PosixPath
from typing import Optional

import requests
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia.management import WikipediaManagement
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User


def notify_user_review_rights_granted(user: User):
    messages = Messages()
    IrcRelay().send_message(messages.notify_irc_about_granted_reviewer_access(user))
    WikipediaManagement().send_user_message(user.username, messages.notify_user_about_reviewer_access(user))


def create_user_with_central_auth_mapping(username: str) -> Optional[User]:
    if central_uid := WikipediaReader().get_central_auth_user_id(username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create(username=username)
            UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)
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
