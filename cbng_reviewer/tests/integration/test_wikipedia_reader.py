import uuid

from django.test import TestCase

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader


class WikipediaReaderTestCase(TestCase):
    def testRevisionHasNotBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertFalse(wikipedia_reader.has_revision_been_deleted(239153997))

    def testRevisionHasBeenDeleted(self):
        wikipedia_reader = WikipediaReader()
        self.assertTrue(wikipedia_reader.has_revision_been_deleted(812910653))

    def testCentralAuthUserLookup(self):
        wikipedia_reader = WikipediaReader()
        self.assertEqual(wikipedia_reader.get_user("DamianZaremba")[0], 8219921)

    def testCentralAuthUserMissing(self):
        wikipedia_reader = WikipediaReader()
        self.assertIsNone(wikipedia_reader.get_user(uuid.uuid4().hex)[0])
