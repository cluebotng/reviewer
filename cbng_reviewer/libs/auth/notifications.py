from typing import Optional

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia.management import WikipediaManagement
from cbng_reviewer.models import User


def notify_user_review_rights_granted(user: User, notify_user: bool = True, reason: Optional[str] = None):
    messages = Messages()
    IrcRelay().send_message(messages.notify_irc_about_granted_reviewer_access(user, reason))
    if notify_user:
        WikipediaManagement().send_user_message(user.username, messages.notify_user_about_reviewer_access(user))
