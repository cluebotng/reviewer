import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save, pre_delete
from social_django.models import UserSocialAuth

from cbng_reviewer.hooks import (
    notify_irc_about_deleted_account,
    notify_irc_about_pending_account,
    update_edit_classification_from_classification,
    import_training_data_for_edit,
)

logger = logging.getLogger(__name__)

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
EDIT_SET_TYPES = (
    (0, "Generic"),
    (1, "Reported False Positives"),
    (2, "Training"),
    (3, "Trial"),
)


class User(AbstractUser):
    is_reviewer = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    historical_edit_count = models.IntegerField(default=0)

    @property
    def central_user_id(self) -> Optional[int]:
        try:
            return UserSocialAuth.objects.get(provider=settings.SOCIAL_AUTH_BACKEND_NAME, user_id=self.id).uid
        except UserSocialAuth.DoesNotExist:
            return None

    @central_user_id.setter
    def central_user_id(self, central_id: int):
        try:
            social_auth_obj = UserSocialAuth.objects.get(provider=settings.SOCIAL_AUTH_BACKEND_NAME, user_id=self.id)
        except UserSocialAuth.DoesNotExist:
            logger.info(f"Creating social-auth mapping for {self.username} ({self.id}) to {central_id}")
            UserSocialAuth.objects.create(provider=settings.SOCIAL_AUTH_BACKEND_NAME, user_id=self.id, uid=central_id)
        else:
            if f'{social_auth_obj.uid}' == f'{central_id}':
                logger.debug(f"social-auth mapping for {self.username} ({self.id}) to {central_id} already exists")
            else:
                logger.info(f"Updating social-auth mapping for {self.username} ({self.id}) to {central_id} from {social_auth_obj.uid}")
                social_auth_obj.uid = central_id
                social_auth_obj.save()


class EditGroup(models.Model):
    name = models.CharField(max_length=255)
    weight = models.IntegerField(default=0)

    related_to = models.ForeignKey("EditGroup", on_delete=models.PROTECT, null=True, blank=True)
    group_type = models.IntegerField(choices=EDIT_SET_TYPES, default=0)

    @property
    def contextual_name(self):
        if self.related_to:
            return f"{self.related_to.name} - {self.name}"
        return self.name

    def __str__(self):
        return self.contextual_name

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "related_to"], name="unique_contextual_name")]


class Edit(models.Model):
    groups = models.ManyToManyField(EditGroup)
    status = models.IntegerField(choices=STATUSES, default=0)
    classification = models.IntegerField(choices=CLASSIFICATIONS, null=True)

    # Internal flags
    is_deleted = models.BooleanField(default=False)
    has_training_data = models.BooleanField(default=False)

    # Internal metadata
    last_updated = models.DateTimeField(auto_now_add=True)
    number_of_reviewers = models.IntegerField(default=0)
    number_of_agreeing_reviewers = models.IntegerField(default=0)

    def update_training_data_flag(self, force: bool = False):
        if self.has_training_data and not force:
            return

        has_training_data = all(
            [
                TrainingData.objects.filter(edit=self).exists(),
                any(
                    [
                        all(
                            [
                                CurrentRevision.objects.filter(edit=self).exists(),
                                PreviousRevision.objects.filter(edit=self).exists(),
                            ]
                        ),
                        CurrentRevision.objects.filter(edit=self, is_creation=True).exists(),
                    ]
                ),
            ]
        )
        if self.has_training_data != has_training_data:
            logger.info(f"Marking {self.id} has_training_data = {has_training_data}")
            self.has_training_data = has_training_data
            self.save(update_fields=["has_training_data"])

    def update_classification(
        self,
        skip_completed_with_no_internal_classifications: bool = True,
        skip_deleted_edits_with_classifications: bool = True,
    ) -> bool:
        original_status, original_classification = self.status, self.classification

        vandalism = Classification.objects.filter(edit=self, classification=0).count()
        constructive = Classification.objects.filter(edit=self, classification=1).count()
        skipped = Classification.objects.filter(edit=self, classification=2).count()
        total_classifications = vandalism + constructive + skipped

        if skip_completed_with_no_internal_classifications and (
            total_classifications == 0 and self.status == 2 and self.classification is not None
        ):
            logger.info(f"Not touching completed edit {self.id}, likely historical")
            return False

        if skip_deleted_edits_with_classifications and (
            self.status == 2 and self.is_deleted and self.classification is not None
        ):
            logger.info(f"Not touching deleted edit {self.id}, likely historical")
            return False

        self.status = 0 if total_classifications == 0 else 1
        if max(constructive, max(vandalism, skipped)) >= settings.CBNG_MINIMUM_CLASSIFICATIONS_FOR_EDIT:
            if 2 * skipped > vandalism + constructive + skipped:
                self.classification = 2
                self.status = 2

            elif constructive >= 3 * vandalism:
                self.classification = 1
                self.status = 2

            elif vandalism >= 3 * constructive:
                self.classification = 0
                self.status = 2

        if self.status == 2:
            original_number_of_reviewers = self.number_of_reviewers
            self.number_of_reviewers = Classification.objects.filter(edit=self).count()

            original_number_of_agreeing_reviewers = self.number_of_agreeing_reviewers
            self.number_of_agreeing_reviewers = Classification.objects.filter(
                edit=self, classification=self.classification
            ).count()

            if (
                self.number_of_reviewers != original_number_of_reviewers
                or self.number_of_agreeing_reviewers != original_number_of_agreeing_reviewers
            ):
                logger.info(
                    f"Updating {self.id} reviewers to {self.number_of_reviewers} / {self.number_of_agreeing_reviewers}"
                )

        if self.status != original_status or self.classification != original_classification:
            logger.info(f"Updating {self.id} to {self.get_classification_display()} [{self.get_status_display()}]")

        if self.status != original_status and self.status == 2 and self.classification is not None:
            from cbng_reviewer.libs.irc import IrcRelay
            from cbng_reviewer.libs.messages import Messages

            IrcRelay().send_message(Messages().notify_irc_about_edit_completion(self))

        self.save()
        return True


class Classification(models.Model):
    edit = models.ForeignKey(Edit, on_delete=models.PROTECT, related_name="user_classification")
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    classification = models.IntegerField(choices=CLASSIFICATIONS)
    comment = models.TextField(null=True, default=None)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["edit", "user"], name="one_edit_classification_per_user")]


class CurrentRevision(models.Model):
    edit = models.OneToOneField(Edit, on_delete=models.CASCADE)
    is_minor = models.BooleanField()
    is_creation = models.BooleanField()
    timestamp = models.IntegerField()
    text = models.BinaryField()


class PreviousRevision(models.Model):
    edit = models.OneToOneField(Edit, on_delete=models.CASCADE)
    is_minor = models.BooleanField()
    timestamp = models.IntegerField()
    text = models.BinaryField()


class TrainingData(models.Model):
    edit = models.OneToOneField(Edit, on_delete=models.CASCADE)
    timestamp = models.IntegerField()

    comment = models.TextField(null=True)
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


if not settings.IN_TEST:
    pre_delete.connect(notify_irc_about_deleted_account, sender=User)
    post_save.connect(notify_irc_about_pending_account, sender=User)
    post_save.connect(update_edit_classification_from_classification, sender=Classification)
    post_save.connect(import_training_data_for_edit, sender=Edit)
