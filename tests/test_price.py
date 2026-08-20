import unittest

from scripts.price import fare_yuan


class PriceTests(unittest.TestCase):
    def test_base_fare_applies_through_six_kilometres(self):
        self.assertEqual(fare_yuan(0), 3)
        self.assertEqual(fare_yuan(6000), 3)

    def test_adds_one_yuan_for_each_started_ten_kilometres_after_base_distance(self):
        self.assertEqual(fare_yuan(6001), 4)
        self.assertEqual(fare_yuan(16000), 4)
        self.assertEqual(fare_yuan(16001), 5)
        self.assertEqual(fare_yuan(26001), 6)
        self.assertEqual(fare_yuan(6000.1), 4)
        self.assertEqual(fare_yuan(16000.1), 5)

    def test_rejects_invalid_distance(self):
        with self.assertRaises(ValueError):
            fare_yuan(-1)


if __name__ == "__main__":
    unittest.main()
