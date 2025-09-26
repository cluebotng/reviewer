import logging
from pathlib import PosixPath
from typing import Optional

import requests

from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker
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


def create_user(
    username: str, require_central_id: bool = True, grant_reviewer_rights: bool = False, auto_grant_rights: bool = True
) -> Optional[User]:
    central_user = WikipediaReader().get_central_user(username=username)
    if not central_user and require_central_id:
        return None

    user, _ = User.objects.get_or_create(username=username)
    if central_user:
        user.central_user_id = central_user.id

    if grant_reviewer_rights:
        user.is_reviewer = True
        user.save()
    elif auto_grant_rights:
        AutoReviewerRightsChecker().execute(user)
    return user


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
