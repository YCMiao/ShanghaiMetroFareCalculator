import unittest

from scripts.build_official_network import apply_branch_corrections


class BranchTopologyTests(unittest.TestCase):
    def test_replaces_false_edge_with_confirmed_branch_edge(self):
        edges = [{"id": "5:station:闵行开发区:station:江川路", "line_id": "5"}]

        corrected = apply_branch_corrections(edges)

        self.assertNotIn("5:station:闵行开发区:station:江川路", {edge["id"] for edge in corrected})
        self.assertIn("5:station:东川路:station:江川路", {edge["id"] for edge in corrected})


if __name__ == "__main__":
    unittest.main()
