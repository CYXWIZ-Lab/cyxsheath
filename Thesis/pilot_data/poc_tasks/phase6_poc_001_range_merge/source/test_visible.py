import unittest

from ranges import merge_ranges


class RangeMergeVisibleTests(unittest.TestCase):
    def test_overlapping_and_separate_ranges(self) -> None:
        self.assertEqual([(1, 5), (9, 10)], merge_ranges([(3, 5), (1, 4), (9, 10)]))


if __name__ == "__main__":
    unittest.main()
