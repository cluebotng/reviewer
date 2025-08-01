from datetime import datetime

from django.test import TestCase

from cbng_reviewer.libs.wikipedia.training import WikipediaTraining
from cbng_reviewer.tests.utils import load_sql_to_replica


class WikipediaTrainingTestCase(TestCase):
    databases = {
        "replica",
    }

    def testPageTitleClean(self):
        wikipedia_training = WikipediaTraining()
        self.assertEqual(wikipedia_training._clean_page_title("HelloWorld"), "HelloWorld")
        self.assertEqual(wikipedia_training._clean_page_title("Hello World"), "Hello_World")

    def testMinorClassification(self):
        wikipedia_training = WikipediaTraining()
        self.assertFalse(wikipedia_training._is_revision_minor({}))
        self.assertTrue(wikipedia_training._is_revision_minor({"minor": "1"}))

    # API based
    def testGetEditMetadata(self):
        wikipedia_training = WikipediaTraining()
        title, namespace = wikipedia_training.get_edit_metadata(1070107186)
        self.assertEqual(title, "User:ClueBot NG/ReviewInterface/Stats")
        self.assertEqual(namespace, "user")

    def testGetMissingEditMetadata(self):
        wikipedia_training = WikipediaTraining()
        title, namespace = wikipedia_training.get_edit_metadata(534808651)
        self.assertIsNone(title)
        self.assertIsNone(namespace)

    def testGetPageRevisions(self):
        wikipedia_training = WikipediaTraining()
        current, previous = wikipedia_training.get_page_revisions("User:ClueBot NG/ReviewInterface/Stats", 1070107186)
        self.assertTrue(current.has_complete_training_data)
        self.assertTrue(previous.has_complete_training_data)

    def testGetMissingPageRevisions(self):
        wikipedia_training = WikipediaTraining()
        current, previous = wikipedia_training.get_page_revisions("Ursula von der Leyen", 1302016402)
        self.assertTrue(current.has_complete_training_data)
        self.assertFalse(previous.has_complete_training_data)

    # Database based
    def testGetPageCreationMetadata(self):
        load_sql_to_replica(["enwiki_p", "page_creation_metadata"])

        wikipedia_training = WikipediaTraining()
        created_at, created_by = wikipedia_training.get_page_creation_metadata("User:ClueBot NG", "user")
        self.assertEqual(created_at, datetime(2010, 10, 20, 17, 3, 30))
        self.assertEqual(created_by, "NaomiAmethyst")

    # def testGetMissingPageCreationMetadata(self):
    #     load_sql_to_replica(["enwiki_p"])
    #
    #     wikipedia_training = WikipediaTraining()
    #     created_at, created_by = wikipedia_training.get_page_creation_metadata("Wibble Wobble", "main")
    #     self.assertIsNone(created_at)
    #     self.assertIsNone(created_by)
