from typing import Optional

from social_django.models import UserSocialAuth

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User


def notify_user_review_rights_granted(user: User):
    messages = Messages()
    IrcRelay().send_message(messages.notify_irc_about_granted_reviewer_access(user))
    Wikipedia(True).send_user_message(user.username, messages.notify_user_about_reviewer_access(user))


def create_user_with_central_auth_mapping(username: str) -> Optional[User]:
    if central_uid := Wikipedia().fetch_user_central_id(username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create(username=username)
            UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)
        return user
    return None
