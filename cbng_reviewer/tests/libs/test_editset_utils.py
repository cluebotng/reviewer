import functools

from django.conf import settings
from django.test import TestCase

from cbng_reviewer.libs.edit_set.parser import EditSetParser
from cbng_reviewer.libs.edit_set.utils import import_wp_edit_to_edit_group
from cbng_reviewer.models import EditGroup


class EditSetUtilsTestCase(TestCase):
    def testCreateWithTraining(self):
        target_group = EditGroup.objects.create(name="imported-from-multiple")
        callback_func = functools.partial(
            import_wp_edit_to_edit_group,
            target_group=target_group,
            skip_existing=False,
        )

        EditSetParser().read_file(
            settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "editsets" / "complete.xml", callback_func
        )
        self.assertEqual(target_group.edit_set.all().count(), 1)
        edit = target_group.edit_set.first()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 1)
        self.assertTrue(edit.has_training_data)

    def testCreateWithNoTraining(self):
        target_group = EditGroup.objects.create(name="imported-from-multiple")
        callback_func = functools.partial(
            import_wp_edit_to_edit_group,
            target_group=target_group,
            skip_existing=False,
        )

        EditSetParser().read_file(
            settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "editsets" / "incomplete.xml", callback_func
        )
        self.assertEqual(target_group.edit_set.all().count(), 1)
        edit = target_group.edit_set.first()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 0)
        self.assertFalse(edit.has_training_data)
