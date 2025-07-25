import logging
from typing import Tuple, Optional

from cbng_reviewer import settings
from cbng_reviewer.models import EditGroup, Classification
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Statistics:
    def get_edit_group_statistics(self):
        return {
            edit_group.name: {
                "weight": edit_group.weight,
                "pending": edit_group.edit_set.filter(status=0).count(),
                "in_progress": edit_group.edit_set.filter(status=1).count(),
                "done": edit_group.edit_set.exclude(status=2).count(),
            }
            for edit_group in EditGroup.objects.all()
        }

    def _calculate_accuracy(self, user: User) -> Tuple[Optional[float], int]:
        total, correct = 0, 0
        for classification in (
            Classification.objects.filter(user=user).exclude(edit__classification=None).prefetch_related("edit")
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

        for user in sorted(User.objects.all(), key=lambda u: u.username):
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
