import logging
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.libs.report_interface import ReportInterface
from cbng_reviewer.libs.wikipedia import Wikipedia

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Import edits from the report interface."""
        logger.info(f"Fetching reported edits")
        report_interface = ReportInterface()
        added_edits = report_interface.create_entries_for_reported_edits()

        wikipedia = Wikipedia()
        for edit in added_edits:
            logger.info(f"Fetching training data for {edit.id}")
            wikipedia.create_training_data_for_edit(edit)
