import logging

from celery import shared_task
from cbng_reviewer.libs.edit_set import utils
from cbng_reviewer.libs.edit_set.utils import mark_edit_as_deleted

logger = logging.getLogger(__name__)


@shared_task
def update_edit_classification(edit_id: int) -> None:
    from cbng_reviewer.models import Edit

    edit = Edit.objects.get(id=edit_id)
    edit.update_classification()


@shared_task
def import_training_data(edit_id: int) -> None:
    from cbng_reviewer.models import Edit
    from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
    from cbng_reviewer.libs.wikipedia.training import WikipediaTraining

    edit = Edit.objects.get(id=edit_id)
    if WikipediaReader().has_revision_been_deleted(edit.id):
        logger.info(f"Edit has been deleted, marking as such: {edit.id}")
        mark_edit_as_deleted(edit)

    else:
        logger.info(f"Fetching training data for {edit.id}")
        wp_edit = WikipediaTraining().build_wp_edit(edit)
        if wp_edit.has_complete_training_data:
            utils.import_training_data(edit, wp_edit)
