import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.tests.utils import load_sql_to_replica


class WikipediaReaderTestCase(TestCase):
    databases = {"default", "replica"}

    def testRevisionHasNotBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertFalse(wikipedia_reader.has_revision_been_deleted(239153997))

    def testRevisionHasBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertTrue(wikipedia_reader.has_revision_been_deleted(812910653))

    def testCentralAuthUserLookup(self):
        wikipedia_reader = WikipediaReader()
        self.assertEqual(wikipedia_reader.get_central_auth_user_id("DamianZaremba"), 8219921)

    def testCentralAuthUserMissing(self):
        wikipedia_reader = WikipediaReader()
        self.assertIsNone(wikipedia_reader.get_central_auth_user_id(uuid.uuid4().hex))

    def testSampledEdits(self):
        load_sql_to_replica(["enwiki_p", "sampled_revisions"])

        current_time = datetime.now()
        sampled_edits = WikipediaReader().get_sampled_edits(
            settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID["main"],
            current_time - timedelta(days=settings.CBNG_SAMPLED_EDITS_LOOKBACK_DAYS),
            current_time,
            1,
        )
        self.assertEqual(len(sampled_edits), 1)
