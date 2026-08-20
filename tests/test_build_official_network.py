import unittest

from scripts.build_official_network import build_network


class BuildNetworkTests(unittest.TestCase):
    def test_creates_ordered_edges_and_excludes_airport_link_line(self):
        lines = [
            {"line_no": 1, "color": "#e3002b"},
            {"line_no": 51, "color": "#cccccc"},
        ]
        stations_by_line = {
            1: {"levels": [{"locations": [
                {"id": "station0111", "title": "莘庄"},
                {"id": "station0112", "title": "外环路"},
            ]}]},
        }

        network = build_network(lines, stations_by_line, fetched_at="2026-08-20T00:00:00Z")

        self.assertEqual([line["id"] for line in network["lines"]], ["1"])
        self.assertEqual(network["edges"], [{
            "id": "1:station0111:station0112",
            "from_station_id": "station0111",
            "to_station_id": "station0112",
            "line_id": "1",
            "distance_m": None,
            "distance_source": None,
            "verification": "pending_pdf",
        }])
        self.assertEqual(network["planned_lines"][0]["id"], "19")
        self.assertFalse(network["planned_lines"][0]["enabled_by_default"])

    def test_keeps_same_named_station_across_lines_separate_with_zero_transfer(self):
        lines = [{"line_no": 1}, {"line_no": 2}]
        stations_by_line = {
            1: {"levels": [{"locations": [{"id": "station0123", "title": "人民广场"}]}]},
            2: {"levels": [{"locations": [{"id": "station0201", "title": "人民广场"}]}]},
        }

        network = build_network(lines, stations_by_line, fetched_at="2026-08-20T00:00:00Z")

        self.assertEqual({station["id"] for station in network["stations"]}, {"station0123", "station0201"})
        self.assertEqual(network["transfers"], [{
            "id": "transfer:station0123:station0201",
            "from_station_id": "station0123",
            "to_station_id": "station0201",
            "distance_m": 0,
        }])


if __name__ == "__main__":
    unittest.main()
