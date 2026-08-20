import unittest

from route_server import route_response


class RouteServerTests(unittest.TestCase):
    def test_returns_display_ready_route_data(self):
        network = {
            "stations": [{"id": "a", "name": "甲"}, {"id": "b", "name": "乙"}],
            "lines": [{"id": "1", "name": "1号线", "color": "#e23646"}],
            "edges": [{"id": "1:a:b", "from_station_id": "a", "to_station_id": "b", "line_id": "1", "distance_m": 1200}],
            "transfers": [],
        }

        response = route_response(network, "甲", "乙")

        self.assertEqual(response["distance_m"], 1200)
        self.assertEqual(response["fare_yuan"], 3)
        self.assertEqual(response["station_ids"], ["a", "b"])
        self.assertEqual(response["edge_ids"], ["1:a:b"])
        self.assertEqual(response["legs"][0]["stations"], ["甲", "乙"])


if __name__ == "__main__":
    unittest.main()
