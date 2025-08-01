import random

from django.test import TestCase

from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.models import User, Edit, Classification


class UserStatsTestCase(TestCase):
    def testFilteringNoEdits(self):
        User.objects.create(username="test-1", is_reviewer=True)
        User.objects.create(username="test-2", is_reviewer=True)
        user_stats = Statistics().get_user_statistics()
        self.assertEqual(user_stats, {})

    def testFilteringReviewers(self):
        User.objects.create(username="test-1")
        User.objects.create(username="test-2", is_reviewer=True)
        User.objects.create(username="test-3", is_admin=True)

        for edit_id in {1, 2, 3}:
            edit = Edit.objects.create(id=edit_id)
            for user in User.objects.filter(username__in={"test-1", "test-2", "test-3"}):
                Classification.objects.create(edit=edit, user=user, classification=random.randint(0, 2))  # nosec: B311

        user_stats = Statistics().get_user_statistics(False)
        self.assertEqual(user_stats, {"test-2": {"is_admin": False, "total_classifications": 3}})

    def testAdminFlag(self):
        User.objects.create(username="test-1")
        User.objects.create(username="test-2", is_reviewer=True)
        User.objects.create(username="test-3", is_reviewer=True, is_admin=True)

        for edit_id in {1, 2, 3}:
            edit = Edit.objects.create(id=edit_id)
            for user in User.objects.filter(username__in={"test-1", "test-2", "test-3"}):
                Classification.objects.create(edit=edit, user=user, classification=random.randint(0, 2))  # nosec: B311

        user_stats = Statistics().get_user_statistics(False)
        self.assertEqual(
            user_stats,
            {
                "test-2": {"is_admin": False, "total_classifications": 3},
                "test-3": {"is_admin": True, "total_classifications": 3},
            },
        )

    def testExtended(self):
        User.objects.create(username="test-1")
        User.objects.create(username="test-2", is_reviewer=True)
        User.objects.create(username="test-3", is_reviewer=True, is_admin=True)

        for edit_id in {1, 2, 3}:
            edit = Edit.objects.create(id=edit_id)
            for user in User.objects.filter(username__in={"test-1", "test-2", "test-3"}):
                Classification.objects.create(edit=edit, user=user, classification=random.randint(0, 2))  # nosec: B311

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "test-2": {
                    "is_admin": False,
                    "total_classifications": 3,
                    "accuracy": None,
                    "accuracy_classifications": 0,
                },
                "test-3": {
                    "is_admin": True,
                    "total_classifications": 3,
                    "accuracy": None,
                    "accuracy_classifications": 0,
                },
            },
        )

    def testCalculateAccuracyNotDoneEdits(self):
        user_1 = User.objects.create(username="user-1", is_reviewer=True)
        user_2 = User.objects.create(username="user-2", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 50:
            edit = Edit.objects.create(id=edit_id, status=2 if edit_id <= 10 else 1, classification=0)
            Classification.objects.create(edit=edit, user=user_1, classification=0)
            Classification.objects.create(edit=edit, user=user_2, classification=0)
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user-1": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": None,
                    "accuracy_classifications": 10,
                },
                "user-2": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": None,
                    "accuracy_classifications": 10,
                },
            },
        )

    def testCalculateAccuracyOverallSkippedEdits(self):
        user = User.objects.create(username="user", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 50:
            edit = Edit.objects.create(id=edit_id, status=2, classification=2 if edit_id <= 40 else 0)
            Classification.objects.create(edit=edit, user=user, classification=0)
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": None,
                    "accuracy_classifications": 10,
                },
            },
        )

    def testCalculateAccuracyUserSkippedEdits(self):
        user = User.objects.create(username="user", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 50:
            edit = Edit.objects.create(id=edit_id, status=2, classification=0)
            Classification.objects.create(edit=edit, user=user, classification=2 if edit_id <= 40 else 0)
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": None,
                    "accuracy_classifications": 10,
                },
            },
        )

    def testCalculateAccuracyGoodMath(self):
        user = User.objects.create(username="user", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 50:
            edit = Edit.objects.create(id=edit_id, status=2, classification=0)
            Classification.objects.create(edit=edit, user=user, classification=0)
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": 100.0,
                    "accuracy_classifications": 50,
                },
            },
        )

    def testCalculateAccuracyQuestionableMath(self):
        user = User.objects.create(username="user", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 60:
            edit = Edit.objects.create(id=edit_id, status=2, classification=0)
            Classification.objects.create(
                edit=edit, user=user, classification=(2 if edit_id <= 10 else (0 if edit_id <= 30 else 1))
            )
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user": {
                    "is_admin": False,
                    "total_classifications": 60,
                    "accuracy": 40.0,
                    "accuracy_classifications": 50,
                },
            },
        )

    def testCalculateAccuracyPoorMath(self):
        user = User.objects.create(username="user", is_reviewer=True)

        # Enough edits, but not done
        edit_id = 1
        while edit_id <= 50:
            edit = Edit.objects.create(id=edit_id, status=2, classification=0)
            Classification.objects.create(edit=edit, user=user, classification=0 if edit_id <= 5 else 1)
            edit_id += 1

        user_stats = Statistics().get_user_statistics()
        self.assertEqual(
            user_stats,
            {
                "user": {
                    "is_admin": False,
                    "total_classifications": 50,
                    "accuracy": 10.0,
                    "accuracy_classifications": 50,
                },
            },
        )
