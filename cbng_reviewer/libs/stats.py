import logging
from typing import Tuple, Optional

from django.conf import settings

from cbng_reviewer.models import EditGroup, Classification, Edit, TrainingData, CurrentRevision, PreviousRevision
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Statistics:
    def get_edit_group_statistics(self):
        return {
            edit_group.contextual_name: {
                "weight": edit_group.weight,
                "pending": edit_group.edit_set.filter(status=0).count(),
                "partial": edit_group.edit_set.filter(status=1).count(),
                "done": edit_group.edit_set.filter(status=2).count(),
            }
            for edit_group in EditGroup.objects.all()
            if edit_group.edit_set.count() > 0
        }

    def _calculate_accuracy(self, user: User) -> Tuple[Optional[float], int]:
        total, correct = 0, 0
        for classification in (
            Classification.objects.filter(user=user)
            .filter(edit__status=2)
            .exclude(edit__classification=None)
            .prefetch_related("edit")
        ):
            # Skipped
            if classification.edit.classification == 2 or classification.classification == 2:
                continue

            total += 1
            if classification.edit.classification == classification.classification:
                correct += 1

        if total > settings.CBNG_MINIMUM_EDITS_FOR_USER_ACCURACY:
            accuracy = (correct / total) * 100.0 if correct > 0 else 0.0
            return accuracy, total
        return None, total

    def get_user_statistics(self, extended=True):
        user_statistics = {}

        for user in sorted(User.objects.exclude(is_bot=True), key=lambda u: u.username):
            if not user.is_reviewer:
                continue

            user_statistics[user.username] = {
                "is_admin": user.is_admin,
                "total_classifications": (
                    user.historical_edit_count + Classification.objects.filter(user=user).count()
                ),
            }

            # Extended essentially = Wiki not homepage
            if extended:
                accuracy, accuracy_classifications = self._calculate_accuracy(user)
                user_statistics[user.username] |= {
                    "accuracy": accuracy,
                    "accuracy_classifications": accuracy_classifications,
                }

        return {username: stats for username, stats in user_statistics.items() if stats["total_classifications"] > 0}

    def get_internal_statistics(self):
        return [
            ("Number Of Administrators", User.objects.filter(is_admin=True).count()),
            ("Number Of Reviewers", User.objects.filter(is_reviewer=True).count()),
            ("Number Of Pending Accounts", User.objects.filter(is_reviewer=False).count()),
            ("Last Review", Classification.objects.all().order_by("-created")[0].created),
            ("Number Of Edit Groups", EditGroup.objects.all().count()),
            ("Number Of Edits", Edit.objects.all().count()),
            ("Number Of Edits Marked As Deleted", Edit.objects.filter(is_deleted=True).count()),
            ("Number Of Edits Marked As Having Training Data", Edit.objects.filter(has_training_data=True).count()),
            ("Number Of Training Data Entries", TrainingData.objects.all().count()),
            ("Number Of Current Revision Entries", CurrentRevision.objects.all().count()),
            ("Number Of Previous Revision Entries", PreviousRevision.objects.all().count()),
        ]

    def generate_wikimarkup(self) -> Optional[str]:
        users = self.get_user_statistics(True)
        edit_groups = self.get_edit_group_statistics()

        # We expect data - don't wipe the current page if we didn't find some
        if not users or not edit_groups:
            return None

        markup = "{{/EditGroupHeader}}\n"
        for name, stats in sorted(edit_groups.items(), key=lambda s: s[0]):
            markup += "{{/EditGroup\n"
            markup += f"|name={name}\n"
            markup += f"|weight={stats['weight']}\n"
            markup += f"|notdone={stats['pending']}\n"
            markup += f"|partial={stats['partial']}\n"
            markup += f"|done={stats['done']}\n"
            markup += "}}\n"
        markup += "{{/EditGroupFooter}}\n"

        markup += "{{/UserHeader}}\n"

        for username, stats in sorted(users.items(), key=lambda s: s[1]["total_classifications"]):
            markup += "{{/User\n"
            markup += f"|nick={username}\n"
            markup += f"|admin={'true' if stats['is_admin'] else 'false'}\n"
            markup += f"|count={stats['total_classifications']}\n"
            markup += f"|accuracy={stats['accuracy'] if stats['accuracy'] else 'NaN'}\n"
            markup += f"|accuracyedits={stats['accuracy_classifications']}\n"
            markup += "}}\n"

        markup += "{{/UserFooter}}\n"

        markup += "{{/InternalHeader}}\n"
        for key, value in self.get_internal_statistics():
            markup += "{{/Internal\n"
            markup += f"|key={key}\n"
            markup += f"|value={value}\n"
            markup += "}}\n"
        markup += "{{/InternalFooter}}\n"

        markup += "{{/FootNotes}}\n"

        return markup
