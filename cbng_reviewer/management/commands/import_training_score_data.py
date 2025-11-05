import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import CommandParser

from cbng_reviewer.libs.core import Core
from cbng_reviewer.libs.edit_set.utils import import_score_data
from cbng_reviewer.models import Edit, ScoreData
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def __init__(self, *args, **kwargs):
        self._core = Core()
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--workers", type=int, default=5)
        parser.add_argument("--edit-id")
        parser.add_argument("--force", action="store_true")

    def _handle_edit(self, edit: Edit):
        if score := self._core.score_edit(edit):
            import_score_data(edit, training=score)

    def handle(self, *args: Any, **options: Any) -> None:
        """Import training score data for edits."""
        target_edits = (
            Edit.objects.filter(id=options["edit_id"]) if options["edit_id"] else Edit.objects.filter(is_deleted=False)
        )
        if not options["force"]:
            edits_with_score_data = ScoreData.objects.exclude(training=None).values_list("edit__id", flat=True)
            target_edits = target_edits.exclude(pk__in=edits_with_score_data)

        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = []
            for edit in target_edits:
                futures.append(executor.submit(self._handle_edit, edit))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
