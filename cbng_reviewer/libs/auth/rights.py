import functools
import logging
from typing import Tuple, Optional

from cbng_reviewer.libs.models.wikipedia import LocalWikiUser
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class AutoReviewerRightsChecker:
    def __init__(self):
        self._wikipedia_reader = WikipediaReader()

    def _user_is_rollbacker(self, wiki_user: Optional[LocalWikiUser]) -> Tuple[bool, Optional[str]]:
        if wiki_user and "rollbacker" in wiki_user.groups:
            return True, "user has rollbacker access"
        return False, None

    def _user_is_reviewer(self, wiki_user: Optional[LocalWikiUser]) -> Tuple[bool, Optional[str]]:
        if wiki_user and "reviewer" in wiki_user.groups:
            return True, "user has reviewer access"
        return False, None

    def _user_is_admin(self, wiki_user: Optional[LocalWikiUser]) -> Tuple[bool, Optional[str]]:
        if wiki_user and "sysop" in wiki_user.groups:
            return True, "user has admin access"
        return False, None

    def _user_is_extendedconfirmed(self, wiki_user: Optional[LocalWikiUser]) -> Tuple[bool, Optional[str]]:
        if wiki_user and "extendedconfirmed" in wiki_user.groups:
            return True, "user is extended confirmed"
        return False, None

    def _user_has_edit_history(self, wiki_user: Optional[LocalWikiUser]) -> Tuple[bool, Optional[str]]:
        # Edits > 50, warnings < 10%. The same logic the bot uses for exclusion.
        if wiki_user:
            edit_count = self._wikipedia_reader.get_user_edit_count(wiki_user.username)
            if edit_count is None:
                logger.warning(f"Failed to get edit count for {wiki_user.username}")
                return False, None

            if edit_count > 50:
                warning_count = self._wikipedia_reader.get_user_warning_count(wiki_user.username)
                if warning_count is None:
                    logger.warning(f"Failed to get warning count for {wiki_user.username}")
                    return False, None

                warning_perc = warning_count / edit_count
                if warning_perc < 0.10:
                    return True, "user has edit count"
                logger.debug(f"{wiki_user.username} has edit count, but > 10% are warnings ({warning_perc})")
        return False, None

    def should_have_access(self, user: User) -> Tuple[bool, Optional[str]]:
        wiki_user = self._wikipedia_reader.get_local_user(user.username)

        # Quickest to slowest
        for check in [
            functools.partial(self._user_is_admin, wiki_user=wiki_user),
            functools.partial(self._user_is_reviewer, wiki_user=wiki_user),
            functools.partial(self._user_is_rollbacker, wiki_user=wiki_user),
            functools.partial(self._user_is_extendedconfirmed, wiki_user=wiki_user),
            functools.partial(self._user_has_edit_history, wiki_user=wiki_user),
        ]:
            should_have_access, reason = check()
            if should_have_access:
                return True, reason
        return False, None

    def execute(self, user: User, force: bool = False, notify_user: bool = False):
        if user.is_reviewer and not force:
            logger.info(f"{user.username} ({user.central_user_id}) is already a reviewer")
            return

        should_have_access, reason = self.should_have_access(user)
        if should_have_access:
            if user.is_reviewer:
                logger.info(f"Skipping marking {user.username} as a reviewer: {reason}")
                return

            logger.info(f"Marking {user.username} as a reviewer: {reason}")
            user.is_reviewer = True
            user.save()

            # Note: IRC, but not via Mail
            from cbng_reviewer.libs.utils import notify_user_review_rights_granted

            notify_user_review_rights_granted(user, notify_user=notify_user, reason=reason)
