import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import BaseCommand, CommandParser

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import Edit, Revision, TrainingData, Classification, EditGroup

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        self._wikipedia = Wikipedia()
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--edit-id")

    def _handle_edit(self, edit: Edit):
        if not self._wikipedia.has_revision_been_deleted(edit.id):
            logger.debug(f"Edit {edit.id} has not been deleted")
            return

        # If we are a completed edit and our training data exists,
        # then keep the data around - it can be used for training
        if edit.status == 2 and edit.has_training_data:
            logger.info(f"Keeping edit {edit.id} with local data")
        else:
            # We are an incomplete edit without training data,
            # we can never be used for training, but we might be referenced in e.g. the report interface,
            # keep the 'meta' entry around for export purposes
            logger.info(f"Cleaning dangling edit {edit.id}")
            Classification.objects.filter(edit=edit).delete()
            TrainingData.objects.filter(edit=edit).delete()
            Revision.objects.filter(edit=edit).delete()

        # Set the flag
        if not edit.deleted:
            edit.deleted = True
            edit.save()

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit classification based on user classifications."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for edit_group in EditGroup.objects.get(
                name__in=[
                    "Legacy Report Interface Import",
                    "Report Interface Import"
                ]
            ):
            for edit in edit_group.edit_set.filter(deleted=False):
                futures.append(executor.submit(self._handle_edit, edit))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logger.exception(e)

            executor.shutdown()
