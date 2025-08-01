from django.test import TestCase
from django.test.utils import override_settings

from cbng_reviewer.models import Edit, User, Classification, EditGroup


class ApiReviewerTestCase(TestCase):
    def testNotAuthenticated(self):
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 302)

    def testMissingRights(self):
        self.client.force_login(user=User.objects.create(username="test-user"))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 403)

    @override_settings(CBNG_ADMIN_ONLY=True)
    def testAdminOnlyMode(self):
        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 403)

        self.client.force_login(user=User.objects.create(username="test-admin", is_admin=True))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 200)

    @override_settings(CBNG_ADMIN_ONLY=False)
    def testNoPendingEdits(self):
        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsNone(data["edit_id"])
        self.assertEqual(data["message"], "No Pending Edit Found")

    def testPreferHigherWeightedNextEdit(self):
        edit_group_1 = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234)
        edit_1.groups.add(edit_group_1)

        edit_group_2 = EditGroup.objects.create(name="Group 2", weight=15)
        edit_2 = Edit.objects.create(id=4321)
        edit_2.groups.add(edit_group_2)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["edit_id"], edit_1.id)

    def testPreferInProgressEdit(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234)
        edit_1.groups.add(edit_group)

        edit_2 = Edit.objects.create(id=4321, status=1)
        edit_2.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["edit_id"], edit_2.id)

    def testExcludeAlreadyClassifiedEdits(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234)
        edit_1.groups.add(edit_group)

        edit_2 = Edit.objects.create(id=4321)
        edit_2.groups.add(edit_group)

        user = User.objects.create(username="test-user", is_reviewer=True, is_admin=True)
        Classification.objects.create(user=user, edit=edit_1, classification=0)
        Classification.objects.create(user=user, edit=edit_2, classification=1)

        self.client.force_login(user=user)
        r = self.client.get("/api/v1/reviewer/next-edit/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsNone(data["edit_id"])
        self.assertEqual(data["message"], "No Pending Edit Found")

    def testClassifyEditNoConfirmation(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 1,
                "comment": "",
                "confirmation": False,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Review stored"})

    def testDuplicateClassifyEdit(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))

        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 1,
                "comment": "",
                "confirmation": False,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Review stored"})

        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 1,
                "comment": "",
                "confirmation": False,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Review already stored"})

    def testClassifyEditNeedingConfirmation(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 0,
                "comment": "",
                "confirmation": False,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["require_confirmation"])

    def testClassifyEditWithConfirmation(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 0,
                "comment": "",
                "confirmation": True,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "Review stored"})

    def testBadClassification(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 5000,
                "comment": "",
            },
        )
        self.assertEqual(r.status_code, 400)

    def testPartialClassificationData(self):
        edit_group = EditGroup.objects.create(name="Group 1", weight=20)
        edit_1 = Edit.objects.create(id=1234, classification=1)
        edit_1.groups.add(edit_group)

        self.client.force_login(user=User.objects.create(username="test-user", is_reviewer=True, is_admin=True))
        r = self.client.post(
            "/api/v1/reviewer/classify-edit/",
            content_type="application/json",
            data={
                "edit_id": edit_1.id,
                "classification": 2,
            },
        )
        self.assertEqual(r.status_code, 200)
