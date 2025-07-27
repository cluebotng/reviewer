from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User


def notify_user_review_rights_granted(user: User):
    messages = Messages()
    IrcRelay().send_message(messages.notify_irc_about_granted_reviewer_access(user))
    Wikipedia(True).send_user_message(user.username, messages.notify_user_about_reviewer_access(user))
