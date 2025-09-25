import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import CommandParser

from cbng_reviewer.models import Edit
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--workers", type=int, default=5)

    def _handle_edit(self, edit: Edit):
        edit.update_classification()

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit classification/status based on user classifications."""
        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = []
            for edit in Edit.objects.all() if options["force"] else Edit.objects.exclude(status=2):
                executor.submit(self._handle_edit, edit)

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
