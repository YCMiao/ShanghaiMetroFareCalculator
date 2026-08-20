import unittest

from route import format_route, shortest_path


def network():
    return {
        "stations": [
            {"id": "a", "name": "甲"}, {"id": "b1", "name": "乙"},
            {"id": "b2", "name": "乙"}, {"id": "c", "name": "丙"},
            {"id": "d", "name": "丁"},
        ],
        "edges": [
            {"id": "1:a:b1", "from_station_id": "a", "to_station_id": "b1", "line_id": "1", "distance_m": 100},
            {"id": "2:b2:c", "from_station_id": "b2", "to_station_id": "c", "line_id": "2", "distance_m": 200},
            {"id": "3:d:c", "from_station_id": "d", "to_station_id": "c", "line_id": "3", "distance_m": 50},
        ],
        "transfers": [{"id": "transfer:b1:b2", "from_station_id": "b1", "to_station_id": "b2", "distance_m": 0}],
    }


class RouteTests(unittest.TestCase):
    def test_calculates_distance_across_zero_distance_transfer(self):
        route = shortest_path(network(), "甲", "丙")

        self.assertEqual(route.distance_m, 300)
        self.assertEqual(route.station_ids, ["a", "b1", "b2", "c"])
        output = format_route(network(), route)
        self.assertIn("乙（1号线 → 2号线）", output)
        self.assertNotIn("乙 → 乙", output)
        self.assertIn("票价：3 元", output)

    def test_chooses_best_official_station_for_same_name_input(self):
        route = shortest_path(network(), " 乙 ", "丙")

        self.assertEqual(route.distance_m, 200)
        self.assertEqual(route.station_ids, ["b2", "c"])

    def test_rejects_unknown_station_name(self):
        with self.assertRaisesRegex(ValueError, "unknown origin station"):
            shortest_path(network(), "不存在", "丙")

    def test_accepts_fractional_distance(self):
        data = network()
        data["edges"][0]["distance_m"] = 100.5

        route = shortest_path(data, "甲", "丙")

        self.assertEqual(route.distance_m, 300.5)
        self.assertIn("总距离：300.5 m", format_route(data, route))


if __name__ == "__main__":
    unittest.main()
