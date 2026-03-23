from django.test import TestCase

from cbng_reviewer.libs.models.message import Message
from cbng_reviewer.models import Edit, User, Classification, TrainingData, CurrentRevision, PreviousRevision


TRAINING_DATA_FIELDS = {
    "timestamp": 0,
    "user": "user",
    "user_edit_count": 0,
    "user_distinct_pages": 0,
    "user_warns": 0,
    "user_reg_time": 0,
    "page_title": "Page",
    "page_namespace": 0,
    "page_created_time": 0,
    "page_creator": "creator",
    "page_num_recent_edits": 0,
    "page_num_recent_reverts": 0,
}
REVISION_FIELDS = {"is_minor": False, "timestamp": 0, "text": b"text"}


class EditTrainingDataFlagTestCase(TestCase):
    def testEarlyReturnWhenAlreadySet(self):
        edit = Edit.objects.create(id=1234, has_training_data=True)
        edit.update_training_data_flag()
        self.assertTrue(edit.has_training_data)

    def testFalseWithNoRelatedObjects(self):
        edit = Edit.objects.create(id=1234)
        edit.update_training_data_flag()
        self.assertFalse(edit.has_training_data)

    def testFalseWithTrainingDataOnly(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(edit=edit, **TRAINING_DATA_FIELDS)
        edit.update_training_data_flag()
        self.assertFalse(edit.has_training_data)

    def testFalseWithCurrentRevisionOnly(self):
        edit = Edit.objects.create(id=1234)
        CurrentRevision.objects.create(edit=edit, is_creation=False, **REVISION_FIELDS)
        edit.update_training_data_flag()
        self.assertFalse(edit.has_training_data)

    def testFalseWithCurrentAndPreviousButNoTrainingData(self):
        edit = Edit.objects.create(id=1234)
        CurrentRevision.objects.create(edit=edit, is_creation=False, **REVISION_FIELDS)
        PreviousRevision.objects.create(edit=edit, **REVISION_FIELDS)
        edit.update_training_data_flag()
        self.assertFalse(edit.has_training_data)

    def testTrueWithCurrentPreviousAndTrainingData(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(edit=edit, **TRAINING_DATA_FIELDS)
        CurrentRevision.objects.create(edit=edit, is_creation=False, **REVISION_FIELDS)
        PreviousRevision.objects.create(edit=edit, **REVISION_FIELDS)
        edit.update_training_data_flag()
        self.assertTrue(edit.has_training_data)

    def testTrueWithCreationEditAndTrainingData(self):
        edit = Edit.objects.create(id=1234)
        TrainingData.objects.create(edit=edit, **TRAINING_DATA_FIELDS)
        CurrentRevision.objects.create(edit=edit, is_creation=True, **REVISION_FIELDS)
        edit.update_training_data_flag()
        self.assertTrue(edit.has_training_data)

    def testFalseWithCreationEditButNoTrainingData(self):
        edit = Edit.objects.create(id=1234)
        CurrentRevision.objects.create(edit=edit, is_creation=True, **REVISION_FIELDS)
        edit.update_training_data_flag()
        self.assertFalse(edit.has_training_data)

    def testForceRecalculatesWhenAlreadyTrue(self):
        edit = Edit.objects.create(id=1234, has_training_data=True)
        edit.save()
        edit.update_training_data_flag(force=True)
        self.assertFalse(edit.has_training_data)


class EditClassificationTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        self.message = Message(body="")
        super(EditClassificationTestCase, self).__init__(*args, **kwargs)

    def testHistoricalStatus(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)
        self.assertFalse(edit.update_classification())

    def testHistoricalWithClassificationsStatus(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user"), classification=1)
        self.assertTrue(edit.update_classification())

    def testDeletedWithClassificationsStatus(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0, is_deleted=True)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user"), classification=1)
        self.assertFalse(edit.update_classification())

    def testClassificationRequiredEdits(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user"), classification=1)
        self.assertTrue(edit.update_classification())
        self.assertEqual(edit.status, 1)

    def testClassificationAsSkipped(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-1"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-2"), classification=0)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 0)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-3"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-4"), classification=1)
        edit.update_classification()
        self.assertEqual(edit.status, 1)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-5"), classification=2)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-6"), classification=2)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-7"), classification=2)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-8"), classification=2)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-9"), classification=2)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 2)

    def testClassificationAsConstructive(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-1"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-2"), classification=0)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 0)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-3"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-4"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-5"), classification=1)

        edit.update_classification()
        self.assertEqual(edit.status, 1)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-6"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-7"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-8"), classification=1)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 1)

    def testClassificationAsVandalism(self):
        edit = Edit.objects.create(id=1234, status=2, classification=0)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-1"), classification=1)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-2"), classification=1)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 1)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-3"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-4"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-5"), classification=0)

        edit.update_classification()
        self.assertEqual(edit.status, 1)

        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-6"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-7"), classification=0)
        Classification.objects.create(edit=edit, user=User.objects.create(username="test-user-8"), classification=0)
        edit.update_classification()
        self.assertEqual(edit.status, 2)
        self.assertEqual(edit.classification, 0)
