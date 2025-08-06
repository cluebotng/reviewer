import logging
from typing import Optional

from django.template import loader
from django.utils.html import escape

from cbng_reviewer.libs.models.message import Message
from cbng_reviewer.models import User, Edit

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
        return Message(body=f"\x0314[[\x0303 New User Account \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_deleted_account(self, user: User) -> Message:
        return Message(body=f"\x0314[[\x0313 Removed User Account \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_granted_reviewer_access(self, user: User, reason: Optional[str] = None) -> Message:
        body = f"\x0314[[\x0307 Reviewer Access Granted \x0314]]\x0301 {escape(user.username)}"
        if reason:
            body += f" ({reason})"
        return Message(body=body)

    def notify_irc_about_granted_admin_access(self, user: User) -> Message:
        return Message(body=f"\x0314[[\x0313 Admin Access Granted \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_granted_super_access(self, user: User) -> Message:
        return Message(body=f"\x0314[[\x0313 Superuser Access Granted \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_removed_reviewer_access(self, user: User) -> Message:
        return Message(body=f"\x0314[[\x0304 Reviewer Access Removed \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_removed_admin_access(self, user: User) -> Message:
        return Message(body=f"\x0314[[\x034 Admin Access Removed \x0314]]\x0301 {escape(user.username)}")

    def notify_irc_about_edit_completion(self, edit: Edit) -> Message:
        return Message(
            body=f"\x0314[[\x036 Review Completed \x0314]]\x0301 {edit.id} classified as {edit.get_classification_display()} [{edit.get_status_display()}]"
        )

    def notify_irc_about_edit_pending(self, edit: Edit) -> Message:
        return Message(body=f"\x0314[[\x032 New Edit Pending Review \x0314]]\x0301 {edit.id}")

    def notify_irc_about_edit_in_progress(self, edit: Edit) -> Message:
        return Message(body=f"\x0314[[\x032 Edit Review In Progress \x0314]]\x0301 {edit.id}")

    def notify_irc_about_edit_deletion(self, edit: Edit) -> Message:
        return Message(body=f"\x0314[[\x035 Edit Has Been Deleted \x0314]]\x0301 {edit.id}")
