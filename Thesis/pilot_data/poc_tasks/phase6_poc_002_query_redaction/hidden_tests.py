import unittest

from redaction import redact_query


class QueryRedactionHiddenTests(unittest.TestCase):
    def test_case_insensitive_and_percent_encoded_keys(self) -> None:
        self.assertEqual(
            "https://example.test/?TOKEN=%5BREDACTED%5D&api_key=%5BREDACTED%5D",
            redact_query("https://example.test/?TOKEN=a&api%5Fkey=b"),
        )

    def test_preserves_repeated_keys_order_and_blank_values(self) -> None:
        self.assertEqual(
            "https://example.test/p?tag=a&empty=&tag=b&Password=%5BREDACTED%5D#f",
            redact_query("https://example.test/p?tag=a&empty=&tag=b&Password=x#f"),
        )


if __name__ == "__main__":
    unittest.main()
