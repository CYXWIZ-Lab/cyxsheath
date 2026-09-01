import unittest

from ranges import merge_ranges


class RangeMergeHiddenTests(unittest.TestCase):
    def test_adjacent_ranges_merge(self) -> None:
        self.assertEqual([(1, 7)], merge_ranges([(1, 3), (4, 7)]))

    def test_reversed_endpoints_normalize_before_sorting(self) -> None:
        self.assertEqual([(1, 8)], merge_ranges([(8, 5), (1, 4)]))

    def test_empty_input_and_input_preservation(self) -> None:
        source = [(6, 7), (1, 2)]
        self.assertEqual([], merge_ranges([]))
        merge_ranges(source)
        self.assertEqual([(6, 7), (1, 2)], source)


if __name__ == "__main__":
    unittest.main()
