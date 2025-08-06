import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.models import Edit

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")
        parser.add_argument("--workers", type=int, default=5)

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit training data flag."""
        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = []
            for edit in (
                Edit.objects.filter(id=options["edit_id"])
                if options["edit_id"]
                else Edit.objects.filter(has_training_data=False)
            ):
                futures.append(executor.submit(edit.update_training_data_flag, True))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
