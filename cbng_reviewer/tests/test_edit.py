from django.test import TestCase

from cbng_reviewer.libs.models.message import Message
from cbng_reviewer.models import Edit, User, Classification


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
