import unittest

from scripts.build_official_network import apply_branch_corrections


class BranchTopologyTests(unittest.TestCase):
    def test_replaces_false_edge_with_confirmed_branch_edge(self):
        stations = {
            "station0501": {"name": "闵行开发区"},
            "station0502": {"name": "江川路"},
            "station0503": {"name": "东川路"},
        }
        edges = [
            {"id": "5:station0501:station0502", "line_id": "5", "from_station_id": "station0501", "to_station_id": "station0502"},
            {"id": "5:station0503:station0501", "line_id": "5", "from_station_id": "station0503", "to_station_id": "station0501"},
        ]

        corrected = apply_branch_corrections(edges, stations)

        self.assertNotIn("5:station0501:station0502", {edge["id"] for edge in corrected})
        self.assertIn("5:station0503:station0502", {edge["id"] for edge in corrected})


if __name__ == "__main__":
    unittest.main()
