import unittest

from feature_flags import normalize_feature_flags


class FeatureFlagTests(unittest.TestCase):
    def test_normalizes_and_deduplicates_in_first_seen_order(self):
        self.assertEqual(
            ["search-v2", "dark_mode"],
            normalize_feature_flags(" Search-V2, dark_mode, search-v2 "),
        )

    def test_ignores_empty_items(self):
        self.assertEqual(["alpha", "beta"], normalize_feature_flags("alpha, ,beta,,"))


if __name__ == "__main__":
    unittest.main()
