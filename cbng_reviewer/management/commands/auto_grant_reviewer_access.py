import logging
from typing import Any

from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker
from cbng_reviewer.models import User
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def handle(self, *args: Any, **options: Any) -> None:
        """Grant reviewer access automatically.."""
        checker = AutoReviewerRightsChecker()
        for user in User.objects.filter(is_reviewer=False):
            checker.execute(user)
