import logging
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.libs.report_interface import ReportInterface

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--include-in-progress", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        """Import edits from the report interface."""
        logger.info("Fetching reported edits")
        ReportInterface().create_entries_for_reported_edits(options["include_in_progress"])
