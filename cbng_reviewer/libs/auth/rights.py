import logging
from typing import Tuple, Optional

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class AutoReviewerRightsChecker:
    def _current_rights_logic(self, user: User) -> Tuple[bool, Optional[str]]:
        user_rights = WikipediaReader().get_user_rights(user.username)
        for right in ["rollback", "block", "deleterevision", "editprotected"]:
            if right in user_rights:
                return True, f"user has '{right}' rights"
        return False, None

    def should_have_access(self, user: User) -> Tuple[bool, Optional[str]]:
        for check in [self._current_rights_logic]:
            should_grant_access, reason = check(user)
            if should_grant_access:
                return True, reason
        return False, None

    def execute(self, user: User, force: bool = False):
        if user.is_reviewer and not force:
            logger.info(f"{user.username} ({user.central_user_id}) is already a reviewer")
            return

        should_grant_access, reason = self.should_have_access(user)
        if should_grant_access:
            logger.info(f"Marking {user.username} as a reviewer: {reason}")
            user.is_reviewer = True
            user.save()

            # Note: IRC, but not via Mail
            from cbng_reviewer.libs.utils import notify_user_review_rights_granted

            notify_user_review_rights_granted(user, notify_user=False, reason=reason)


if __name__ == "__main__":
    AutoReviewerRightsChecker().execute(User.objects.get(username="DamianZaremba"))
