import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_metro_map import build_map


class BuildMetroMapTests(unittest.TestCase):
    def test_uses_official_coordinates_and_line_colour(self):
        network = {
            "stations": [
                {"id": "station0111", "name": "莘庄"},
                {"id": "station0112", "name": "外环路"},
            ],
            "lines": [{"id": "1", "color": "#e3002b"}],
            "edges": [{"id": "1:station0111:station0112", "from_station_id": "station0111", "to_station_id": "station0112", "line_id": "1"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory)
            (snapshot / "line-1.json").write_text(json.dumps({"levels": [{"locations": [
                {"id": "station0111", "title": "莘庄", "x": "0.3201", "y": "0.6252"},
                {"id": "station0112", "title": "外环路", "x": "0.3320", "y": "0.6099"},
            ]}]}))
            metro_map = build_map(network, snapshot)

        self.assertEqual(metro_map["stations"][0], {"id": "station0111", "name": "莘庄", "x": 320.1, "y": 625.2})
        self.assertEqual(metro_map["edges"][0]["color"], "#e3002b")
        self.assertEqual(metro_map["view_box"], {"x": 285.1, "y": 574.9, "width": 81.9, "height": 85.3})


if __name__ == "__main__":
    unittest.main()
