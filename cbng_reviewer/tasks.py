import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def update_edit_classification(edit_id: int) -> None:
    from cbng_reviewer.models import Edit

    edit = Edit.objects.get(id=edit_id)
    edit.update_classification()


@shared_task
def notify_irc_about_completed_edit(edit_id: int) -> None:
    from cbng_reviewer.libs.irc import IrcRelay
    from cbng_reviewer.libs.messages import Messages
    from cbng_reviewer.models import Edit

    edit = Edit.objects.get(id=edit_id)
    message = Messages().notify_irc_about_edit_completion(edit)
    IrcRelay().send_message(message)


@shared_task
def import_training_data(edit_id: int) -> None:
    from cbng_reviewer.models import Edit
    from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
    from cbng_reviewer.libs.wikipedia.training import WikipediaTraining

    edit = Edit.objects.get(id=edit_id)
    if WikipediaReader().has_revision_been_deleted(edit.id):
        logger.info(f"Edit has been deleted, marking as such: {edit.id}")
        edit.deleted = True
        edit.save()

    else:
        logger.info(f"Fetching training data for {edit.id}")
        wp_edit = WikipediaTraining().build_wp_edit(edit)
        if wp_edit.has_complete_training_data:
            import_training_data(edit, wp_edit)
