from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

STATUSES = (
    (0, "Pending"),
    (1, "Partial"),
    (2, "Done"),
)
CLASSIFICATIONS = (
    (0, "Vandalism"),
    (1, "Constructive"),
    (2, "Skipped"),
)
CLASSIFICATION_IDS = {i for i, _ in CLASSIFICATIONS}


class User(AbstractUser):
    is_reviewer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    historical_edit_count = models.IntegerField(default=0)


class EditGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    weight = models.IntegerField(default=0)


class Edit(models.Model):
    groups = models.ManyToManyField(EditGroup)
    # required = models.BooleanField()
    deleted = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUSES, default=0)
    classification = models.IntegerField(choices=CLASSIFICATIONS, null=True)


class Classification(models.Model):
    edit = models.ForeignKey(Edit, on_delete=models.PROTECT, related_name="user_classification")
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    classification = models.IntegerField(choices=CLASSIFICATIONS)
    comment = models.TextField(null=True, default=None)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["edit", "user"], name="one_edit_classification_per_user")]


class Revision(models.Model):
    edit = models.ForeignKey(Edit, on_delete=models.CASCADE)
    type = models.IntegerField(choices=((0, "current"), (1, "previous")))
    minor = models.BooleanField()
    timestamp = models.IntegerField()
    text = models.BinaryField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["edit", "type"], name="one_revision_type_per_edit")]


class TrainingData(models.Model):
    edit = models.OneToOneField(Edit, on_delete=models.CASCADE)
    timestamp = models.IntegerField()

    comment = models.TextField()
    user = models.CharField(max_length=255)
    user_edit_count = models.IntegerField()
    user_distinct_pages = models.IntegerField()
    user_warns = models.IntegerField()
    user_reg_time = models.IntegerField()
    prev_user = models.CharField(max_length=255, null=True)

    page_title = models.CharField(max_length=255)
    page_namespace = models.IntegerField()
    page_created_time = models.IntegerField()
    page_creator = models.CharField(max_length=255)

    page_num_recent_edits = models.IntegerField()
    page_num_recent_reverts = models.IntegerField()


@receiver(post_save, sender=User)
def notify_irc_about_pending_account(sender, instance, created, **kwargs):
    if created:
        from cbng_reviewer.libs.irc import IrcRelay
        from cbng_reviewer.libs.messages import Messages

        IrcRelay().send_message(Messages().notify_irc_about_pending_account(instance))


@receiver(pre_delete, sender=User)
def notify_irc_about_deleted_account(sender, instance, **kwargs):
    from cbng_reviewer.libs.irc import IrcRelay
    from cbng_reviewer.libs.messages import Messages

    IrcRelay().send_message(Messages().notify_irc_about_deleted_account(instance))
