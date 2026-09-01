import unittest

from feature_flags import normalize_feature_flags


class FeatureFlagHiddenTests(unittest.TestCase):
    def test_case_only_duplicates_collapse(self):
        self.assertEqual(["rollout"], normalize_feature_flags("ROLLOUT,rollout,Rollout"))

    def test_all_empty_input_is_empty(self):
        self.assertEqual([], normalize_feature_flags(" , ,,  "))


if __name__ == "__main__":
    unittest.main()
