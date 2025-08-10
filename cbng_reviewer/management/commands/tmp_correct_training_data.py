import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.libs.wikipedia.training import WikipediaTraining
from cbng_reviewer.models import Edit, TrainingData, EditGroup

logger = logging.getLogger(__name__)
HISTORICAL_EDIT_SETS = {
    "Original Training Set - C - Train",
    "Original Training Set - C - Trail",
    "Original Training Set - D - Train",
    "Original Training Set - D - Trail",
    "Original Training Set - D - Bays Train",
    "Original Training Set - D - All",
    "Original Testing Training Set - Auto - Train",
    "Original Testing Training Set - Auto - Trail",
    "Original Testing Training Set - Old Triplet - Train",
    "Original Testing Training Set - Old Triplet - Trail",
    "Original Testing Training Set - Old Triplet - Bays Train",
    "Original Testing Training Set - Old Triplet - All",
    "Original Testing Training Set - Random Edits 50/50 - Train",
    "Original Testing Training Set - Random Edits 50/50 - Trail",
    "Original Testing Training Set - Random Edits 50/50 - All",
    "Original Testing Training Set - Very Large - Train",
    "Original Testing Training Set - Very Large - Trail",
    "Original Testing Training Set - Very Large - Bays Train",
    "Original Testing Training Set - Very Large - All",
}


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        self._wikipedia_training = WikipediaTraining()
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--workers", type=int, default=5)

    def _handle_edit(self, training_data: TrainingData):
        user_warning_count = self._wikipedia_training.get_user_warning_count(
            training_data.user, datetime.fromtimestamp(training_data.timestamp)
        )
        if training_data.user_warns == user_warning_count:
            logger.debug(f"user_warns are consistent for {training_data.edit.id}")
            return

        logger.info(f"[{training_data.edit.id}] changing user_warns {training_data.user_warns} -> {user_warning_count}")
        training_data.user_warns = user_warning_count
        training_data.save()

    def handle(self, *args: Any, **options: Any) -> None:
        """Correct training data with potentially incorrect user warnings count."""
        exclude_edit_groups = set(EditGroup.objects.filter(name__in=HISTORICAL_EDIT_SETS).values_list("pk", flat=True))

        targets = set()
        for edit in Edit.objects.filter(has_training_data=True).exclude(is_deleted=True):
            if edit.groups.filter(pk__in=exclude_edit_groups).exists():
                logger.debug(f"Ignoring edit as it exists in a historical edit set ({edit.id})")
                continue

            try:
                training_data = TrainingData.objects.get(edit=edit)
            except TrainingData.DoesNotExist:
                continue

            if training_data.user != self._wikipedia_training._clean_page_title(training_data.user):
                logger.debug(f"Found potential incorrect user: {training_data.user} ({edit.id})")
                targets.add(training_data)

        logger.info(f"Found {len(targets)} edits to re-generate data for")
        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = []
            for training_data in targets:
                futures.append(executor.submit(self._handle_edit, training_data))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
