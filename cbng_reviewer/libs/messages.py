import logging

from django.template import loader

from cbng_reviewer.libs.models.message import Message
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Messages:
    def notify_user_about_reviewer_access(self, user: User) -> Message:
        template = loader.get_template("cbng_reviewer/messages/notify_user_about_reviewer_access.txt")
        return Message(
            subject="ClueBot NG Review Interface Account Approved",
            body=template.render(
                {
                    "user": user,
                    "administrators": User.objects.filter(is_admin=True).values_list("username", flat=True),
                }
            ),
        )

    def notify_irc_about_pending_account(self, user: User) -> Message:
        template = loader.get_template("cbng_reviewer/messages/notify_irc_about_pending_account.txt")
        return Message(
            body=template.render(
                {
                    "user": user,
                }
            )
        )

    def notify_irc_about_reviewer_access(self, user: User) -> Message:
        template = loader.get_template("cbng_reviewer/messages/notify_irc_about_reviewer_access.txt")
        return Message(
            body=template.render(
                {
                    "user": user,
                }
            )
        )
