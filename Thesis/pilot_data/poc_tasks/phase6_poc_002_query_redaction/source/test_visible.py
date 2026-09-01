import unittest

from redaction import redact_query


class QueryRedactionVisibleTests(unittest.TestCase):
    def test_redacts_lowercase_token(self) -> None:
        self.assertEqual(
            "https://example.test/path?token=%5BREDACTED%5D&mode=fast#part",
            redact_query("https://example.test/path?token=secret&mode=fast#part"),
        )


if __name__ == "__main__":
    unittest.main()
