import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import Edit, Revision, TrainingData, Classification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        self._wikipedia = Wikipedia()
        super(Command, self).__init__(*args, **kwargs)

    def _have_training_data(self, edit: Edit):
        # If we are a completed edit, with stored training data and stored revision data,
        # then we can be used for training, even if the original revision has been deleted.
        #
        # If we do not have the training/revision data stored and the edit is not completed,
        # then it never will be, so we can remove it as dangling.
        return all(
            [
                edit.status == 2,
                Revision.objects.filter(edit=edit, type__in=0).exists(),
                TrainingData.objects.filter(edit=edit).exists(),
            ]
        )

    def _handle_edit(self, edit: Edit):
        if not self._wikipedia.has_revision_been_deleted(edit.id):
            logger.debug(f"Edit {edit.id} has not bee deleted")
            return

        if self._have_training_data(edit):
            logger.info(f"Keeping edit {edit.id} with local data")
            edit.deleted = True
            edit.save()
            return

        logger.info(f"Removing dangling edit {edit.id}")
        Classification.objects.filter(edit=edit).delete()
        TrainingData.objects.filter(edit=edit).delete()
        Revision.objects.filter(edit=edit).delete()
        edit.delete()

    def handle(self, *args: Any, **options: Any) -> None:
        """Update edit classification based on user classifications."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            for edit in Edit.objects.filter(deleted=False):
                executor.submit(self._handle_edit, edit)
            executor.shutdown()
