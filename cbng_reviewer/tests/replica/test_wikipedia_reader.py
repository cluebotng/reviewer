from datetime import datetime, timedelta

from django.conf import settings

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.tests.utils import WikipediaReplicaTransactionTestCase, load_replica_sql


class WikipediaReaderTestCase(WikipediaReplicaTransactionTestCase):
    @load_replica_sql("sampled_revisions")
    def testSampledEdits(self):
        current_time = datetime.now()
        sampled_edits = WikipediaReader().get_sampled_edits(
            settings.WIKIPEDIA_NAMESPACE_NAME_TO_ID["main"],
            current_time - timedelta(days=settings.CBNG_SAMPLED_EDITS_LOOKBACK_DAYS),
            current_time,
            1,
        )
        self.assertEqual(len(sampled_edits), 1)

    @load_replica_sql("sampled_revisions")
    def testRevisionHasNotBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertFalse(wikipedia_reader.has_revision_been_deleted(57160200))

    @load_replica_sql("sampled_revisions")
    def testRevisionHasBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertTrue(wikipedia_reader.has_revision_been_deleted(57160201))
