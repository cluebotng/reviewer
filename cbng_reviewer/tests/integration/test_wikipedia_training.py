from unittest.mock import MagicMock, patch

from django.test import TestCase

from cbng_reviewer.libs.wikipedia.training import WikipediaTraining


class WikipediaTrainingTestCase(TestCase):
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

    @patch("requests.Session.get")
    def testGetPageRevisions(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "29881390": {
                        "pageid": 29881390,
                        "ns": 2,
                        "title": "User:ClueBot NG/ReviewInterface/Stats",
                        "revisions": [
                            {
                                "revid": 1070107186,
                                "parentid": 1068228521,
                                "user": "ClueBot NG",
                                "timestamp": "2022-02-05T18:35:18Z",
                                "comment": "Uploading Stats",
                                "slots": {
                                    "main": {
                                        "contentmodel": "wikitext",
                                        "contentformat": "text/x-wiki",
                                        "*": "{{/EditGroupHeader}}\n{{/EditGroupFooter}}",
                                    }
                                },
                            },
                            {
                                "revid": 1068228521,
                                "parentid": 1067818664,
                                "user": "ClueBot NG",
                                "timestamp": "2022-01-27T09:15:29Z",
                                "comment": "Uploading Stats",
                                "slots": {
                                    "main": {
                                        "contentmodel": "wikitext",
                                        "contentformat": "text/x-wiki",
                                        "*": "{{/EditGroupHeader}}\n{{/EditGroupFooter}}",
                                    }
                                },
                            },
                        ],
                    }
                }
            }
        }
        mock_get.return_value = mock_response

        wikipedia_training = WikipediaTraining()
        current, previous = wikipedia_training.get_page_revisions("User:ClueBot NG/ReviewInterface/Stats", 1070107186)
        self.assertTrue(current.has_complete_training_data)
        self.assertTrue(previous.has_complete_training_data)

    def testGetMissingPageRevisions(self):
        wikipedia_training = WikipediaTraining()
        current, previous = wikipedia_training.get_page_revisions("Ursula von der Leyen", 1302016402)
        self.assertTrue(current.has_complete_training_data)
        self.assertFalse(previous.has_complete_training_data)
