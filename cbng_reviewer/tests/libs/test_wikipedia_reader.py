from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.tests.utils import load_sql_to_replica


class WikipediaReaderTestCase(TestCase):
    databases = {"default", "replica"}

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
