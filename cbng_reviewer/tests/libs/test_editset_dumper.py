from django.test import TestCase

from cbng_reviewer.libs.edit_set.dumper import EditSetDumper
from cbng_reviewer.models import Edit, TrainingData, CurrentRevision, PreviousRevision


class EditSetReaderTestCase(TestCase):
    def testNoExportOnMissingTrainingData(self):
        edit = Edit.objects.create(id=1234)
        CurrentRevision.objects.create(edit=edit, text="current".encode("utf-8"), minor=False, timestamp=1234)
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), minor=False, timestamp=1230)
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
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), minor=False, timestamp=1230)
        self.assertIsNone(EditSetDumper().generate_wp_edit(edit))

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
        CurrentRevision.objects.create(edit=edit, text="current".encode("utf-8"), minor=False, timestamp=1234)
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), minor=False, timestamp=1230)

        wp_edit_xml = EditSetDumper().generate_wp_edit(edit)
        self.assertIsNotNone(wp_edit_xml)
        self.assertEqual(
            wp_edit_xml,
            "<WPEdit><EditType>change</EditType><EditID>1234</EditID><comment>Hello World</comment>"
            "<user>Bob Smith</user><user_edit_count>5</user_edit_count>"
            "<user_distinct_pages>6</user_distinct_pages><user_warns>2</user_warns>"
            "<prev_user>Jill Smith</prev_user><user_reg_time>54321</user_reg_time>"
            "<common><page_made_time>1220</page_made_time><title>Experiment</title>"
            "<namespace>main</namespace><creator>Jane Smith</creator>"
            "<num_recent_edits>1</num_recent_edits><num_recent_reversions>3</num_recent_reversions>"
            "</common><current><minor>false</minor><timestamp>1234</timestamp><text>current</text></current>"
            "<previous><minor>false</minor><timestamp>1230</timestamp><text>previous</text></previous>"
            "<reviewStatus>Pending</reviewStatus></WPEdit>",
        )

    def testValidExport(self):
        edit = Edit.objects.create(id=1234, status=2)
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
        CurrentRevision.objects.create(edit=edit, text="current".encode("utf-8"), minor=False, timestamp=1234)
        PreviousRevision.objects.create(edit=edit, text="previous".encode("utf-8"), minor=False, timestamp=1230)

        wp_edit_xml = EditSetDumper().generate_wp_edit(edit)
        self.assertIsNotNone(wp_edit_xml)
        self.assertEqual(
            wp_edit_xml,
            "<WPEdit><EditType>change</EditType><EditID>1234</EditID><comment>Hello World</comment>"
            "<user>Bob Smith</user><user_edit_count>5</user_edit_count>"
            "<user_distinct_pages>6</user_distinct_pages><user_warns>2</user_warns>"
            "<prev_user>Jill Smith</prev_user><user_reg_time>54321</user_reg_time>"
            "<common><page_made_time>1220</page_made_time><title>Experiment</title>"
            "<namespace>main</namespace><creator>Jane Smith</creator>"
            "<num_recent_edits>1</num_recent_edits><num_recent_reversions>3</num_recent_reversions>"
            "</common><current><minor>false</minor><timestamp>1234</timestamp><text>current</text></current>"
            "<previous><minor>false</minor><timestamp>1230</timestamp><text>previous</text></previous>"
            "<isVandalism>false</isVandalism></WPEdit>",
        )
