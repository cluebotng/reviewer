import functools

from django.conf import settings
from django.test import TestCase
from freezegun import freeze_time

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.libs.edit_set.parser import EditSetParser
from cbng_reviewer.libs.edit_set.utils import import_wp_edit_to_edit_group
from cbng_reviewer.models import Edit, TrainingData, CurrentRevision, PreviousRevision, EditGroup, Classification, User


class EditSetReaderTestCase(TestCase):
    def testNoExportOnMissingTrainingData(self):
        edit = Edit.objects.create(id=1234)
        CurrentRevision.objects.create(
            edit=edit, text="current".encode("utf-8"), is_minor=False, is_creation=False, timestamp=1234
        )
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), is_minor=False, timestamp=1230)
        self.assertIsNone(EditSetDumper().generate_wp_edit(edit))

    def testNoExportOnMissingCurrentRevision(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(
            edit=edit,
            timestamp=1234,
            user="Bob Smith",
            user_edit_count=5,
            user_distinct_pages=6,
            user_warns=2,
            user_reg_time=54321,
            prev_user="Jill Smith",
            page_title="Experiment",
            page_namespace=0,
            page_created_time=1230,
            page_creator="Jane Smith",
            page_num_recent_edits=1,
            page_num_recent_reverts=3,
        )
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), is_minor=False, timestamp=1230)
        self.assertIsNone(EditSetDumper().generate_wp_edit(edit))

    @freeze_time("2025-09-05T16:00Z")
    def testValidPendingExport(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(
            edit=edit,
            timestamp=1234,
            user="Bob Smith",
            comment="Hello World",
            user_edit_count=5,
            user_distinct_pages=6,
            user_warns=2,
            user_reg_time=54321,
            prev_user="Jill Smith",
            page_title="Experiment",
            page_namespace=0,
            page_created_time=1220,
            page_creator="Jane Smith",
            page_num_recent_edits=1,
            page_num_recent_reverts=3,
        )
        CurrentRevision.objects.create(
            edit=edit, text="current".encode("utf-8"), is_minor=False, is_creation=False, timestamp=1234
        )
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), is_minor=False, timestamp=1230)

        wp_edit_xml = EditSetDumper().generate_wp_edit(edit)
        self.assertIsNotNone(wp_edit_xml)
        assert wp_edit_xml == (
            "<WPEdit>\n"
            " <EditDB>\n"
            "  <isActive>true</isActive>\n"
            "  <lastUpdated>1757088000</lastUpdated>\n"
            " </EditDB>\n"
            " <EditType>change</EditType>\n"
            " <EditID>1234</EditID>\n"
            " <comment>Hello World</comment>\n"
            " <user>Bob Smith</user>\n"
            " <user_edit_count>5</user_edit_count>\n"
            " <user_distinct_pages>6</user_distinct_pages>\n"
            " <user_warns>2</user_warns>\n"
            " <prev_user>Jill Smith</prev_user>\n"
            " <user_reg_time>54321</user_reg_time>\n"
            " <common>\n"
            "  <page_made_time>1220</page_made_time>\n"
            "  <title>Experiment</title>\n"
            "  <namespace>Main</namespace>\n"
            "  <creator>Jane Smith</creator>\n"
            "  <num_recent_edits>1</num_recent_edits>\n"
            "  <num_recent_reversions>3</num_recent_reversions>\n"
            " </common>\n"
            " <current>\n"
            "  <minor>false</minor>\n"
            "  <timestamp>1234</timestamp>\n"
            "  <text>current</text>\n"
            " </current>\n"
            " <previous>\n"
            "  <timestamp>1230</timestamp>\n"
            "  <text>previous</text>\n"
            " </previous>\n"
            " <ReviewInterface>\n"
            "  <status>Pending</status>\n"
            " </ReviewInterface>\n"
            "</WPEdit>"
        )  # nosec:B101

    @freeze_time("2025-09-05T16:00Z")
    def testValidCreationExport(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(
            edit=edit,
            timestamp=1234,
            user="Bob Smith",
            comment="Hello World",
            user_edit_count=5,
            user_distinct_pages=6,
            user_warns=2,
            user_reg_time=54321,
            prev_user="Jill Smith",
            page_title="Experiment",
            page_namespace=0,
            page_created_time=1220,
            page_creator="Jane Smith",
            page_num_recent_edits=1,
            page_num_recent_reverts=3,
        )
        CurrentRevision.objects.create(
            edit=edit, text="current".encode("utf-8"), is_minor=False, is_creation=True, timestamp=1234
        )

        wp_edit_xml = EditSetDumper().generate_wp_edit(edit)
        self.assertIsNotNone(wp_edit_xml)
        assert wp_edit_xml == (
            "<WPEdit>\n"
            " <EditDB>\n"
            "  <isActive>true</isActive>\n"
            "  <lastUpdated>1757088000</lastUpdated>\n"
            " </EditDB>\n"
            " <EditType>change</EditType>\n"
            " <EditID>1234</EditID>\n"
            " <comment>Hello World</comment>\n"
            " <user>Bob Smith</user>\n"
            " <user_edit_count>5</user_edit_count>\n"
            " <user_distinct_pages>6</user_distinct_pages>\n"
            " <user_warns>2</user_warns>\n"
            " <prev_user>Jill Smith</prev_user>\n"
            " <user_reg_time>54321</user_reg_time>\n"
            " <common>\n"
            "  <page_made_time>1220</page_made_time>\n"
            "  <title>Experiment</title>\n"
            "  <namespace>Main</namespace>\n"
            "  <creator>Jane Smith</creator>\n"
            "  <num_recent_edits>1</num_recent_edits>\n"
            "  <num_recent_reversions>3</num_recent_reversions>\n"
            " </common>\n"
            " <current>\n"
            "  <minor>false</minor>\n"
            "  <timestamp>1234</timestamp>\n"
            "  <text>current</text>\n"
            " </current>\n"
            " <previous></previous>\n"
            " <ReviewInterface>\n"
            "  <status>Pending</status>\n"
            " </ReviewInterface>\n"
            "</WPEdit>"
        )  # nosec:B101

    def _test_valid_export(self, edit_id: int, group_name: str, classification: int, reviewers: int):
        expected_file = settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "edit" / f"{edit_id}.xml"
        target_group = EditGroup.objects.create(name=group_name)

        # Import the edit data from the WPEdit
        callback_func = functools.partial(import_wp_edit_to_edit_group, target_group=target_group, skip_existing=False)
        EditSetParser().read_file(expected_file, callback_func)

        # Fake some entries (reviews) to get the Edit metadata into a state that matches what we expect
        edit = target_group.edit_set.all()[0]

        for x in range(0, reviewers):
            Classification.objects.create(
                edit=edit, user=User.objects.create(username=f"test_{x}"), classification=classification
            )
        edit.update_classification()

        # Dump our version of WPEdit
        generated_xml = EditSetDumper().generate_wp_edit(edit, target_group)

        # Compare with the raw version of the original WPEdit
        with expected_file.open("r") as fh:
            expected_xml = fh.read().strip()

        assert generated_xml == expected_xml  # nosec:B101

    # pytest.mark.parametrize doesn't play well with Django
    @freeze_time("2010-11-24T00:14:06Z")
    def testValidEditSetExport(self):
        self._test_valid_export(394517773, "Random Edits", 2, 2)

    @freeze_time("2010-11-15T05:16:03Z")
    def testValidEditDbExport(self):
        self._test_valid_export(353452767, "pan.webis.de", 0, 0)
