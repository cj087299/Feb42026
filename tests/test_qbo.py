import unittest
from src.qbo_client import QBOClient

class TestQBOClient(unittest.TestCase):
    def setUp(self):
        self.client = QBOClient("id", "secret", "refresh", "realm")

    def test_init(self):
        self.assertEqual(self.client.client_id, "id")
        self.assertEqual(self.client.realm_id, "realm")

    def test_make_request(self):
        # Since make_request is a stub, we just check it returns a dict
        response = self.client.make_request("query")
        self.assertIsInstance(response, dict)

if __name__ == '__main__':
    unittest.main()
