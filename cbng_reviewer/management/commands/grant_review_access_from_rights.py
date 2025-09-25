import logging
from typing import Any

from cbng_reviewer.libs.utils import update_access_from_rights
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def handle(self, *args: Any, **options: Any) -> None:
        """Grant reviewer access, based on user has rights."""
        for user in User.objects.filter(is_reviewer=False):
            central_uid, user_rights = WikipediaReader().get_user(user.username)
            if central_uid:
                update_access_from_rights(user, user_rights)
