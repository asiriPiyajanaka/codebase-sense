import os
import unittest


class CancellationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("WAREHOUSE_TEST_DATABASE"):
            raise RuntimeError("WAREHOUSE_TEST_DATABASE is not provisioned; integration check blocked")
        raise RuntimeError("warehouse test driver is not installed")

    def test_cancellation_persists(self):
        self.fail("unreachable without the integration environment")
