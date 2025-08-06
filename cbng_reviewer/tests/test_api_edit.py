from django.test import TestCase

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.models import Edit, TrainingData, CurrentRevision, PreviousRevision


class ApiEditTestCase(TestCase):
    def testPendingEdit(self):
        edit = Edit.objects.create(id=1234, status=0)
        r = self.client.get(f"/api/v1/edit/{edit.id}/dump-wpedit/")
        self.assertEqual(r.status_code, 404)

    def testMissingRevisionData(self):
        edit = Edit.objects.create(id=1234, status=2, classification=1)

        TrainingData.objects.create(
            edit=edit,
            timestamp=1753826200,
            comment="Example Change",
            user="Bob Smith",
            user_edit_count=4,
            user_distinct_pages=2,
            user_warns=0,
            user_reg_time=1753824103,
            prev_user="Alice Smith",
            page_title="Very Important",
            page_namespace=0,
            page_created_time=1753814103,
            page_creator="Dog",
            page_num_recent_edits=1,
            page_num_recent_reverts=0,
        )
        CurrentRevision.objects.create(edit=edit, timestamp=1753826150, minor=False, text=b"Current Text")

        r = self.client.get(f"/api/v1/edit/{edit.id}/dump-wpedit/")
        self.assertEqual(r.status_code, 404)

    def testMissingTrainingData(self):
        edit = Edit.objects.create(id=1234, status=2, classification=1)

        CurrentRevision.objects.create(edit=edit, timestamp=1753826150, minor=False, text=b"Current Text")
        PreviousRevision.objects.create(edit=edit, timestamp=1753826000, minor=True, text=b"Previous Text")

        r = self.client.get(f"/api/v1/edit/{edit.id}/dump-wpedit/")
        self.assertEqual(r.status_code, 404)

    def testWpEdit(self):
        edit = Edit.objects.create(id=1234, status=2, classification=1)

        TrainingData.objects.create(
            edit=edit,
            timestamp=1753826200,
            comment="Example Change",
            user="Bob Smith",
            user_edit_count=4,
            user_distinct_pages=2,
            user_warns=0,
            user_reg_time=1753824103,
            prev_user="Alice Smith",
            page_title="Very Important",
            page_namespace=0,
            page_created_time=1753814103,
            page_creator="Dog",
            page_num_recent_edits=1,
            page_num_recent_reverts=0,
        )
        CurrentRevision.objects.create(edit=edit, timestamp=1753826150, minor=False, text=b"Current Text")
        PreviousRevision.objects.create(edit=edit, timestamp=1753826000, minor=True, text=b"Previous Text")

        wp_edit = EditSetDumper().generate_wp_edit(edit)

        r = self.client.get(f"/api/v1/edit/{edit.id}/dump-wpedit/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, wp_edit)
