import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "current"))
from controller import get_invoice


class ControllerTests(unittest.TestCase):
    def test_delegates_authorized_request(self):
        with patch("controller.invoice_for", return_value={"amount": 10}) as service:
            get_invoice({"i1": {"owner": "alice"}}, "alice", "i1")
            service.assert_called_once_with({"i1": {"owner": "alice"}}, "alice", "i1")
