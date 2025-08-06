from django.test import TestCase

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.models import Edit, EditGroup, TrainingData, CurrentRevision, PreviousRevision


class ApiEditGroupTestCase(TestCase):
    def testFetchGroups(self):
        EditGroup.objects.create(id=1, name="Report Interface Import", group_type=1)
        EditGroup.objects.create(id=2, name="Sampled Main Namespace Edits", group_type=0)
        edit_group = EditGroup.objects.create(id=3, name="Original Testing Set - C", group_type=0)
        EditGroup.objects.create(id=4, name="Training", group_type=2, related_to=edit_group)
        EditGroup.objects.create(id=5, name="Trial", group_type=3, related_to=edit_group)

        r = self.client.get("/api/v1/edit-groups/")
        self.assertEqual(r.status_code, 200)
        entries = r.json()

        self.assertIn(
            {"id": 1, "name": "Report Interface Import", "related_to": None, "type": "Reported False Positives"},
            entries,
        )
        self.assertIn({"id": 2, "name": "Sampled Main Namespace Edits", "related_to": None, "type": "Generic"}, entries)
        self.assertIn({"id": 3, "name": "Original Testing Set - C", "related_to": None, "type": "Generic"}, entries)
        self.assertIn(
            {"id": 4, "name": "Original Testing Set - C - Training", "related_to": 3, "type": "Training"}, entries
        )
        self.assertIn({"id": 5, "name": "Original Testing Set - C - Trial", "related_to": 3, "type": "Trial"}, entries)

    def testReportStatusExportFiltering(self):
        edit_group_1 = EditGroup.objects.create(name="Report Interface Import", group_type=1)
        edit_group_2 = EditGroup.objects.create(name="Sampled Main Namespace Edits", group_type=0)

        r = self.client.get(f"/api/v1/edit-groups/{edit_group_2.id}/dump-report-status/")
        self.assertEqual(r.status_code, 404)

        r = self.client.get(f"/api/v1/edit-groups/{edit_group_1.id}/dump-report-status/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {})

        edit = Edit.objects.create(id=1234, status=2, classification=0)
        edit.groups.add(edit_group_1)

        r = self.client.get(f"/api/v1/edit-groups/{edit_group_1.id}/dump-report-status/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"1234": 2})

    def testReportStatusExportMapping(self):
        edit_group = EditGroup.objects.create(name="Report Interface Import", group_type=1)

        edit = Edit.objects.create(id=1000, status=0)
        edit.groups.add(edit_group)
        edit = Edit.objects.create(id=1001, status=1)
        edit.groups.add(edit_group)
        edit = Edit.objects.create(id=1002, status=2, classification=0)
        edit.groups.add(edit_group)
        edit = Edit.objects.create(id=1003, status=2, classification=1)
        edit.groups.add(edit_group)
        edit = Edit.objects.create(id=1004, status=2, classification=2)
        edit.groups.add(edit_group)
        edit = Edit.objects.create(id=1005, is_deleted=True)
        edit.groups.add(edit_group)

        r = self.client.get(f"/api/v1/edit-groups/{edit_group.id}/dump-report-status/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "1000": 0,
                "1001": 1,
                "1002": 2,
                "1003": 3,
                "1004": 4,
                "1005": 5,
            },
        )

    def testEmptyEditSet(self):
        edit_group = EditGroup.objects.create(name="Report Interface Import", group_type=1)
        r = self.client.get(f"/api/v1/edit-groups/{edit_group.id}/dump-editset/")
        self.assertEqual(r.status_code, 200)

        # StreamingHttpResponse - iter over map()
        xml = "".join([part.decode("utf-8") for part in r.streaming_content])
        self.assertEqual(xml, "<WPEditSet>\n</WPEditSet>\n")

    def testEditSet(self):
        edit_group = EditGroup.objects.create(name="Report Interface Import", group_type=1)

        edit = Edit.objects.create(id=1234, status=2, classification=1)
        edit.groups.add(edit_group)

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

        r = self.client.get(f"/api/v1/edit-groups/{edit_group.id}/dump-editset/")
        self.assertEqual(r.status_code, 200)

        # StreamingHttpResponse - iter over map()
        xml = "".join([part.decode("utf-8") for part in r.streaming_content])
        self.assertEqual(xml, f"<WPEditSet>\n{wp_edit}\n</WPEditSet>\n")
