import logging
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.models import (
    Revision,
    CurrentRevision,
    PreviousRevision,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Migrate existing revision data."""
        for revision in Revision.objects.filter(type=0):
            CurrentRevision.objects.create(
                edit=revision.edit,
                minor=revision.minor,
                timestamp=revision.timestamp,
                text=revision.text,
            )

        for revision in Revision.objects.filter(type=1):
            PreviousRevision.objects.create(
                edit=revision.edit,
                minor=revision.minor,
                timestamp=revision.timestamp,
                text=revision.text,
            )
