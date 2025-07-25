import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.conf import settings
from django.core.management import BaseCommand

from cbng_reviewer.models import Edit, Classification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def _handle_edit(self, edit: Edit):
        original_status, original_classification = edit.status, edit.classification

        vandalism = Classification.objects.filter(edit=edit, classification=0).count()
        constructive = Classification.objects.filter(edit=edit, classification=1).count()
        skipped = Classification.objects.filter(edit=edit, classification=2).count()

        total_classifications = vandalism + constructive + skipped

        edit.status = 0 if total_classifications == 0 else 1
        if total_classifications >= settings.CBNG_MINIMUM_EDITS_FOR_USER_ACCURACY:
            if 2 * skipped > vandalism + constructive:
                edit.classification = 2
                edit.status = 2

            elif constructive >= 3 * vandalism:
                edit.classification = 1
                edit.status = 2

            elif vandalism >= 3 * constructive:
                edit.classification = 0
                edit.status = 2

        if edit.status != original_status or edit.classification != original_classification:
            logger.info(f"Updating {edit.id} to {edit.get_classification_display()} [{edit.get_status_display()}]")
            edit.save()

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit classification/status based on user classifications."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            for edit in Edit.objects.exclude(status=2):
                executor.submit(self._handle_edit, edit)
            executor.shutdown()
