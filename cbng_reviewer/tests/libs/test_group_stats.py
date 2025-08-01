from django.test import TestCase

from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.models import Edit, EditGroup


class GroupStatsTestCase(TestCase):
    def testFilteringNoEdits(self):
        EditGroup.objects.create(name="test-1")
        EditGroup.objects.create(name="test-2")
        group_stats = Statistics().get_edit_group_statistics()
        self.assertEqual(group_stats, {})

    def testEditClassifications(self):
        eg = EditGroup.objects.create(name="test-1")

        for edit_id in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            edit = Edit.objects.create(id=edit_id, status=0)
            edit.groups.add(eg)

        for edit_id in [20, 21, 22, 23, 24, 25]:
            edit = Edit.objects.create(id=edit_id, status=1)
            edit.groups.add(eg)

        for edit_id in [26, 27, 28]:
            edit = Edit.objects.create(id=edit_id, status=2)
            edit.groups.add(eg)

        group_stats = Statistics().get_edit_group_statistics()
        self.assertEqual(group_stats, {"test-1": {"weight": 0, "pending": 10, "partial": 6, "done": 3}})
