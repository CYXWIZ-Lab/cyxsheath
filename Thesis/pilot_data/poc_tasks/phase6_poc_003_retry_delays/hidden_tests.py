import unittest

from retry import retry_delays


class RetryDelayHiddenTests(unittest.TestCase):
    def test_cap_applies_to_every_delay(self) -> None:
        self.assertEqual([2.0, 5.0, 5.0], retry_delays(4, 2.0, multiplier=3.0, max_delay=5.0))

    def test_one_attempt_has_no_delay(self) -> None:
        self.assertEqual([], retry_delays(1, 1.0))

    def test_invalid_values_are_rejected(self) -> None:
        for arguments in ((0, 1.0, 2.0, None), (2, 0.0, 2.0, None), (2, 1.0, 0.5, None), (2, 1.0, 2.0, 0.0)):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    retry_delays(*arguments)


if __name__ == "__main__":
    unittest.main()
