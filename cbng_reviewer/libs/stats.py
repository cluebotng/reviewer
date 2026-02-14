import logging
from typing import Tuple, Optional, List, Dict

import requests
from django.conf import settings
from django.db import models
from django.db.models import Count, Q

from cbng_reviewer.models import EditGroup, Classification, Edit, TrainingData, CurrentRevision, PreviousRevision
from cbng_reviewer.models import User

logger = logging.getLogger(__name__)


class Statistics:
    def get_edit_group_statistics(self):
        edits_with_single_group = (
            Edit.groups.through.objects.values("edit_id")
            .annotate(group_count=Count("editgroup_id"))
            .filter(group_count=1)
            .values("edit_id")
        )

        edit_group_unique_edits = {
            row["editgroup_id"]: row["count"]
            for row in Edit.groups.through.objects.filter(edit_id__in=edits_with_single_group)
            .values("editgroup_id")
            .annotate(count=Count("edit_id"))
        }

        return {
            edit_group.contextual_name: {
                "weight": edit_group.weight,
                "unique": edit_group_unique_edits.get(edit_group.id, 0),
                "pending": edit_group.pending,
                "partial": edit_group.partial,
                "done": edit_group.done,
            }
            for edit_group in EditGroup.objects.annotate(
                total=Count("edit", distinct=True),
                pending=Count("edit", filter=Q(edit__status=0)),
                partial=Count("edit", filter=Q(edit__status=1)),
                done=Count("edit", filter=Q(edit__status=2)),
            ).filter(total__gt=0)
        }

    def calculate_user_accuracy(self, users: List[User]) -> Dict[int, Tuple[Optional[float], int]]:
        user_accuracy = {}
        for row in (
            Classification.objects.filter(user__in=users, edit__status=2)
            .exclude(edit__classification=None)
            .exclude(classification=2)
            .exclude(edit__classification=2)
            .values("user_id")
            .annotate(
                total=Count("id"),
                correct=Count("id", filter=Q(classification=models.F("edit__classification"))),
            )
        ):
            accuracy = None
            if row["total"] > settings.CBNG_MINIMUM_EDITS_FOR_USER_ACCURACY:
                accuracy = (row["correct"] / row["total"]) * 100.0 if row["correct"] > 0 else 0.0

            user_accuracy[row["user_id"]] = (accuracy, row["total"])

        return user_accuracy

    def get_user_statistics(self, extended=True):
        user_accuracy, user_statistics = {}, {}

        target_users = list(User.objects.exclude(is_bot=True))
        if extended:
            user_accuracy = self.calculate_user_accuracy(target_users)

        for user in sorted(target_users, key=lambda u: u.username):
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
                accuracy, accuracy_classifications = user_accuracy.get(user.id, (None, 0))
                user_statistics[user.username] |= {
                    "accuracy": accuracy,
                    "accuracy_classifications": accuracy_classifications,
                }

        return user_statistics

    def get_internal_statistics(self):
        latest_classification = next(iter(Classification.objects.all().order_by("-created")), None)
        return [
            ("Number Of Administrators", User.objects.filter(is_admin=True).count()),
            ("Number Of Reviewers", User.objects.filter(is_reviewer=True).count()),
            ("Number Of Pending Accounts", User.objects.filter(is_reviewer=False).count()),
            ("Last Review", latest_classification.created if latest_classification else ""),
            ("Number Of Edit Groups", EditGroup.objects.all().count()),
            ("Number Of Edits", Edit.objects.all().count()),
            ("Number Of Edits Marked As Deleted", Edit.objects.filter(is_deleted=True).count()),
            ("Number Of Edits Marked As Having Training Data", Edit.objects.filter(has_training_data=True).count()),
            ("Number Of Training Data Entries", TrainingData.objects.all().count()),
            ("Number Of Current Revision Entries", CurrentRevision.objects.all().count()),
            ("Number Of Previous Revision Entries", PreviousRevision.objects.all().count()),
        ]

    def get_historical_user_statistics(self) -> List[Tuple[str, int]]:
        return [
            ("tonyb", 15),
            ("Dvyjones2", 40),
            ("woz2", 156),
            ("Mentifisto", 5),
            ("Cit Helper", 305),
            ("Logan-old", 55),
            ("Matthewrbowker", 16),
            ("Zachlipton", 54),
            ("BlastOButter42", 8),
            ("Dvyjones3", 5),
            ("Helder.wiki", 26),
            ("Harsh_2580", 21),
            ("AddWittyUserName", 9),
        ]

    def get_external_statistics(self):
        r = requests.get(
            "https://cluebotng.toolforge.org/api/",
            timeout=10,
            params={
                "action": "reports.list",
                "status": 0,
            },
        )
        r.raise_for_status()
        return [
            ("Number Of Reports Pending", len(r.json().keys())),
        ]

    def generate_wikimarkup(self) -> Optional[str]:
        users = self.get_user_statistics(True)
        historical_users = self.get_historical_user_statistics()
        edit_groups = self.get_edit_group_statistics()

        # We expect data - don't wipe the current page if we didn't find some
        if not users or not edit_groups:
            return None

        markup = "{{/EditGroupHeader}}\n"
        for name, stats in sorted(edit_groups.items(), key=lambda s: (s[1]["unique"], s[0]), reverse=True):
            markup += "{{/EditGroup\n"
            markup += f"|name={name}\n"
            markup += f"|unique={stats['unique']}\n"
            markup += f"|weight={stats['weight']}\n"
            markup += f"|notdone={stats['pending']}\n"
            markup += f"|partial={stats['partial']}\n"
            markup += f"|done={stats['done']}\n"
            markup += "}}\n"
        markup += "{{/EditGroupFooter}}\n"

        markup += "{{/UserHeader}}\n"

        for username, stats in sorted(users.items(), key=lambda s: (s[1]["total_classifications"], s[0]), reverse=True):
            markup += "{{/User\n"
            markup += f"|nick={username}\n"
            if stats["is_admin"]:
                markup += "|admin=true\n"
            markup += f"|count={stats['total_classifications']}\n"
            markup += f"|accuracy={round(stats['accuracy'], 1) if stats['accuracy'] else 'NaN'}\n"
            markup += f"|accuracyedits={stats['accuracy_classifications']}\n"
            markup += "}}\n"

        for username, edit_count in sorted(historical_users, key=lambda s: (s[1], s[0]), reverse=True):
            markup += "{{/User\n"
            markup += f"|nick={username}\n"
            markup += "|legacy=true\n"
            markup += f"|count={edit_count}\n"
            markup += "}}\n"

        markup += "{{/UserFooter}}\n"

        markup += "{{/InternalHeader}}\n"
        for key, value in self.get_internal_statistics() + self.get_external_statistics():
            markup += "{{/Internal\n"
            markup += f"|key={key}\n"
            markup += f"|value={value}\n"
            markup += "}}\n"
        markup += "{{/InternalFooter}}\n"

        markup += "{{/FootNotes}}\n"

        return markup
