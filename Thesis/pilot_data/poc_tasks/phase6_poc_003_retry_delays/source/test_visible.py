import unittest

from retry import retry_delays


class RetryDelayVisibleTests(unittest.TestCase):
    def test_basic_schedule(self) -> None:
        self.assertEqual([1.0, 2.0, 4.0], retry_delays(4, 1.0))


if __name__ == "__main__":
    unittest.main()
