import logging

import kombu.exceptions

logger = logging.getLogger(__name__)


def notify_irc_about_pending_account(instance, created, **kwargs):
    if created:
        from cbng_reviewer.libs.irc import IrcRelay
        from cbng_reviewer.libs.messages import Messages

        IrcRelay().send_message(Messages().notify_irc_about_pending_account(instance))


def notify_irc_about_deleted_account(instance, **kwargs):
    from cbng_reviewer.libs.irc import IrcRelay
    from cbng_reviewer.libs.messages import Messages

    IrcRelay().send_message(Messages().notify_irc_about_deleted_account(instance))


def update_edit_classification_from_classification(instance, **kwargs):
    from cbng_reviewer import tasks

    try:
        tasks.update_edit_classification.apply_async([instance.edit_id])
    except kombu.exceptions.OperationalError as e:
        logger.error(f"Failed to create update_edit_classification task: {e}")


def import_training_data_for_edit(instance, created, **kwargs):
    if created:
        from cbng_reviewer import tasks

        try:
            tasks.import_training_data.apply_async([instance.id])
        except kombu.exceptions.OperationalError as e:
            logger.error(f"Failed to create import_training_data task: {e}")


def notify_irc_about_pending_edit(instance, created, **kwargs):
    if created:
        from cbng_reviewer.libs.irc import IrcRelay
        from cbng_reviewer.libs.messages import Messages

        IrcRelay().send_message(Messages().notify_irc_about_edit_pending(instance))
