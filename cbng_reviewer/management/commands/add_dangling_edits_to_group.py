import logging
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.models import EditGroup, Edit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Add dangling edits to group."""
        dangling_edits = []
        for edit in Edit.objects.all():
            if edit.groups.count() == 0:
                dangling_edits.append(edit)

        if dangling_edits:
            logger.info(f"Found {len(dangling_edits)} dangling edits")

            edit_group, _ = EditGroup.objects.get_or_create(name="Dangling Edits")
            for edit in dangling_edits:
                edit.groups.add(edit_group)
