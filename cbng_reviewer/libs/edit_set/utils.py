import logging

from django.conf import settings

from cbng_reviewer.libs.models.edit_set import WpEdit
from cbng_reviewer.models import EditGroup, Edit, TrainingData, PreviousRevision, CurrentRevision

logger = logging.getLogger(__name__)


def import_training_data(edit: Edit, wp_edit: WpEdit):
    TrainingData.objects.filter(edit=edit).delete()
    TrainingData.objects.create(
        edit=edit,
        timestamp=wp_edit.current.timestamp.timestamp(),
        comment=wp_edit.comment,
        user=wp_edit.user,
        user_edit_count=wp_edit.user_edit_count,
        user_distinct_pages=wp_edit.user_distinct_pages,
        user_warns=wp_edit.user_warns,
        user_reg_time=wp_edit.user_reg_time.timestamp(),
        prev_user=wp_edit.prev_user,
        page_title=wp_edit.title,
        page_namespace=settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID[wp_edit.namespace.lower()],
        page_created_time=wp_edit.page_made_time.timestamp(),
        page_creator=wp_edit.creator,
        page_num_recent_edits=wp_edit.num_recent_edits,
        page_num_recent_reverts=wp_edit.num_recent_reversions,
    )

    if wp_edit.current and wp_edit.current.has_complete_training_data:
        CurrentRevision.objects.filter(edit=edit).delete()
        CurrentRevision.objects.create(
            edit=edit,
            minor=wp_edit.current.minor,
            timestamp=wp_edit.current.timestamp.timestamp(),
            text=wp_edit.current.text.encode("utf-8"),
        )

    if wp_edit.previous and wp_edit.previous.has_complete_training_data:
        PreviousRevision.objects.filter(edit=edit).delete()
        PreviousRevision.objects.create(
            edit=edit,
            minor=wp_edit.previous.minor,
            timestamp=wp_edit.previous.timestamp.timestamp(),
            text=wp_edit.previous.text.encode("utf-8"),
        )

    edit.update_training_data_flag(True)


def import_wp_edit_to_edit_group(target_group: EditGroup, wp_edit: WpEdit, skip_existing: bool):
    edit, created = Edit.objects.get_or_create(id=wp_edit.edit_id)
    if created:
        # If we are a new entry, then set that status to what we know
        edit.classification = 0 if wp_edit.is_vandalism else 1
        edit.status = 2
        edit.save()

    # Ensure we exist in the correct group - also for existing edits
    if not edit.groups.filter(pk=target_group.pk).exists():
        logger.info(f"Adding {edit.id} to {target_group.name}")
        edit.groups.add(target_group)

    # Add training data as required
    if not (skip_existing and edit.has_training_data):
        if wp_edit.has_complete_training_data:
            logger.info(f"Importing training data from {wp_edit}")
            import_training_data(edit, wp_edit)
        else:
            logger.info(f"Missing training data for {wp_edit}")
            # Do nothing - `import_training_data` or `update_deleted_edits` will deal with this


def mark_edit_as_deleted(edit: Edit):
    from cbng_reviewer.libs.irc import IrcRelay
    from cbng_reviewer.libs.messages import Messages

    if not edit.is_deleted:
        IrcRelay().send_message(Messages().notify_irc_about_edit_deletion(edit))
        edit.is_deleted = True
        edit.save()
