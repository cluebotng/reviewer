import logging
from datetime import datetime, timedelta, UTC
from typing import Any

from django.conf import settings
from django.db.models import Count, Q

from cbng_reviewer.models import User
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def handle(self, *args: Any, **options: Any) -> None:
        """Cleanup user records for those with no rights."""
        cutoff_limit = datetime.now(tz=UTC) - timedelta(days=settings.CBNG_CLEANUP_USER_DAYS)
        for user in User.objects.annotate(classification_count=Count("classification_set")).filter(
            Q(date_joined__lte=cutoff_limit)
            & Q(classification_count=0)
            & ~Q(is_admin=True)
            & ~Q(is_reviewer=True)
            & ~Q(historical_edit_count__gt=0)
        ):
            logger.info(f"Removing (pending) user record for {user.username} ({user.date_joined})")
            user.delete()
