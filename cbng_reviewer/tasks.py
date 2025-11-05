import logging

from celery import shared_task

from cbng_reviewer.libs.core import Core
from cbng_reviewer.libs.edit_set import utils
from cbng_reviewer.libs.edit_set.utils import import_score_data
from cbng_reviewer.libs.report_interface import ReportInterface

logger = logging.getLogger(__name__)


@shared_task
def update_edit_classification(edit_id: int) -> None:
    from cbng_reviewer.models import Edit

    edit = Edit.objects.get(id=edit_id)
    edit.update_classification()


@shared_task
def import_training_data(edit_id: int, force: bool = False) -> None:
    from cbng_reviewer.models import Edit
    from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
    from cbng_reviewer.libs.wikipedia.training import WikipediaTraining

    edit = Edit.objects.get(id=edit_id)
    if edit.has_training_data and not force:
        logger.info(f"Edit already has training data: {edit.id}")
        return

    if WikipediaReader().has_revision_been_deleted(edit.id):
        logger.info(f"Found deleted revision for {edit.id}, skipping training data import")
        return

    logger.info(f"Fetching training data for {edit.id}")
    wp_edit = WikipediaTraining().build_wp_edit(edit)
    if wp_edit.has_complete_training_data:
        utils.import_training_data(edit, wp_edit)

        if score := Core().score_edit(edit):
            import_score_data(edit, training=score)


@shared_task
def import_vandalism_score_data(edit_id: int) -> None:
    from cbng_reviewer.models import Edit

    edit = Edit.objects.get(id=edit_id)
    if score := ReportInterface().fetch_vandalism_score(edit):
        import_score_data(edit, reverted=score)
