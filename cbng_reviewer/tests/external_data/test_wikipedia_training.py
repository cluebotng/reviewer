from datetime import datetime

from cbng_reviewer.libs.wikipedia.training import WikipediaTraining
from cbng_reviewer.tests.utils import WikipediaReplicaTransactionTestCase, replica_test_sql_file


class WikipediaTrainingTestCase(WikipediaReplicaTransactionTestCase):

    @replica_test_sql_file("page_creation_metadata")
    # Database based
    def testGetPageCreationMetadata(self):
        wikipedia_training = WikipediaTraining()
        created_at, created_by = wikipedia_training.get_page_creation_metadata("User:ClueBot NG", "user")
        self.assertEqual(created_at, datetime(2010, 10, 20, 17, 3, 30))
        self.assertEqual(created_by, "NaomiAmethyst")

    def testGetMissingPageCreationMetadata(self):
        wikipedia_training = WikipediaTraining()
        created_at, created_by = wikipedia_training.get_page_creation_metadata("Wibble Wobble", "main")
        self.assertIsNone(created_at)
        self.assertIsNone(created_by)

    @replica_test_sql_file("page_recent_edit_count")
    def testGetPageRecentEditCount(self):
        wikipedia_training = WikipediaTraining()
        recent_edit_count = wikipedia_training.get_page_recent_edit_count(
            "Bimble Bottle", "main", datetime(2025, 7, 15)
        )
        self.assertEqual(recent_edit_count, 5)

    @replica_test_sql_file("page_recent_revert_count")
    def testGetPageRecentRevertCount(self):
        wikipedia_training = WikipediaTraining()
        recent_edit_count = wikipedia_training.get_page_recent_revert_count(
            "Juicy Juggles", "main", datetime(2024, 7, 15)
        )
        self.assertEqual(recent_edit_count, 1)

    @replica_test_sql_file("user_edit_count")
    def testGetUserEditCount(self):
        wikipedia_training = WikipediaTraining()
        recent_edit_count = wikipedia_training.get_user_edit_count("Example User", datetime(2021, 4, 3))
        self.assertEqual(recent_edit_count, 6)

    @replica_test_sql_file("user_warning_count")
    def testGetUserWarningCount(self):
        wikipedia_training = WikipediaTraining()
        recent_warning_count = wikipedia_training.get_user_warning_count("Example User", datetime(2025, 7, 15))
        self.assertEqual(recent_warning_count, 2)
