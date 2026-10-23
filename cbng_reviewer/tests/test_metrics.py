from django.test import TestCase
from django.test.utils import override_settings


class MetricsTestCase(TestCase):
    @override_settings(CBNG_MONITORING_SHARED_SECRET=None)
    def testNoSharedSecret(self):
        r = self.client.get("/internal/metrics/")
        self.assertEqual(r.status_code, 200)

    @override_settings(CBNG_MONITORING_SHARED_SECRET="very secret")
    def testMissingHeader(self):
        r = self.client.get("/internal/metrics/")
        self.assertEqual(r.status_code, 403)

    @override_settings(CBNG_MONITORING_SHARED_SECRET="very secret")
    def testInvalidHeader(self):
        r = self.client.get("/internal/metrics/", headers={"Authorization": "Bearer wrong"})
        self.assertEqual(r.status_code, 403)

    @override_settings(CBNG_MONITORING_SHARED_SECRET="very secret")
    def testValidHeader(self):
        r = self.client.get("/internal/metrics/", headers={"Authorization": "Bearer very secret"})
        self.assertEqual(r.status_code, 200)
